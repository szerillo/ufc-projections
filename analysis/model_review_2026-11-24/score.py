"""Model review (Nov 24 2026), parts A/B: score the UFC Model sheet's graded Snapshots (10 cards, Sep 19 to Nov 21 2026).
Inputs: argv[1] = xlsx export of the sheet (Snapshots, PropSnap), argv[2] = close.json from build_close.py,
argv[3] = repo checkout (for scripts/fighter_names.py). Read-only; prints the report body."""
import sys, math, json, collections, numpy as np, pandas as pd
sys.path.insert(0, "/tmp/rev/scripts"); from load import load
sys.path.insert(0, sys.argv[3] + "/scripts"); import fighter_names as FN
S, PS = load(sys.argv[1]); CL = json.load(open(sys.argv[2]))
rng = np.random.default_rng(20261124)
imp = lambda o: (-o / (-o + 100)) if o < 0 else 100 / (o + 100)
dec_odds = lambda o: 1 + (o / 100 if o > 0 else 100 / -o)
lg = lambda p: np.log(p / (1 - p))
def br(p, y): return float(np.mean((np.asarray(p, float) - y) ** 2))
def ll(p, y): p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
def auc(p, y):
    p, y = np.asarray(p, float), np.asarray(y, float); pos, neg = p[y == 1], p[y == 0]
    return float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg])) if len(pos) and len(neg) else float("nan")
def boot(df, f, n=4000):
    """Card-clustered bootstrap: resample cards, return (point, lo5, hi95)."""
    cards = df["event"].unique(); g = {c: df[df["event"] == c] for c in cards}; pt = f(df); vals = []
    for _ in range(n):
        d = pd.concat([g[c] for c in rng.choice(cards, len(cards))]); vals.append(f(d))
    return pt, float(np.percentile(vals, 5)), float(np.percentile(vals, 95))
S = S[S["dog won"].notna()].copy(); S["y"] = S["dog won"].astype(float)
print(f"# A. Graded sample: {len(S)} bouts, {S['event'].nunique()} cards ({S['date'].min():%b %d} to {S['date'].max():%b %d %Y}); draws/NC excluded")
# ---- data timing
print("\n## A0. When each card was snapshotted (snapshot time minus card date)")
for (d, e), g in S.groupby(["date", "event"]):
    lag = (g["snapshot time"].iloc[0] - pd.Timestamp(d)).total_seconds() / 3600
    print(f"{d:%m-%d} {e[:45]:<45} snapshot {g['snapshot time'].iloc[0]:%m-%d %H:%M}Z  (+{lag:5.1f} h after 00:00Z card date)  graded {g['graded'].iloc[0]:%m-%d %H:%M}")
# ---- attach independent bot close (US books, last price before scheduled start)
def bot(r):
    for c in CL:
        if "ml_pa" not in c: continue
        if FN.name_match(c["a"], r["dog"]) and FN.name_match(c["b"], r["fav"]): return c["ml_pa"], c["ml_last"]
        if FN.name_match(c["b"], r["dog"]) and FN.name_match(c["a"], r["fav"]): return 1 - c["ml_pa"], c["ml_last"]
    return None, None
S[["bot", "bot_last"]] = S.apply(lambda r: pd.Series(bot(r)), axis=1)
S["Jsh"] = (S["Markov J"] - 0.1086).clip(0.02, 0.98)
S["mult_list"] = S.apply(lambda r: imp(r["dog price (D)"]) / (imp(r["dog price (D)"]) + imp(r["fav price (I)"])) if pd.notna(r["dog price (D)"]) and pd.notna(r["fav price (I)"]) else np.nan, axis=1)
def powdv(a, b):
    ia, ib = imp(a), imp(b); lo, hi = 1.0, 3.0
    for _ in range(60):
        k = (lo + hi) / 2; lo, hi = (k, hi) if ia ** k + ib ** k > 1 else (lo, k)
    return ia ** k
S["pow_list"] = S.apply(lambda r: powdv(r["dog price (D)"], r["fav price (I)"]) if pd.notna(r["dog price (D)"]) else np.nan, axis=1)
print(f"\nSheet listed G vs de-vig of its own D/I prices: mean |G - multiplicative| {np.nanmean(abs(S['dog listed G (sheet)'] - S['mult_list'])) * 100:.2f} pts; mean |G - power| {np.nanmean(abs(S['dog listed G (sheet)'] - S['pow_list'])) * 100:.2f} pts  (D/I are best prices, G is consensus, so neither is exact)")
both = S[S["bot"].notna() & S["dog CLOSE (consensus)"].notna()]
print(f"Snapshot 'dog CLOSE' vs bot pre-start US close (n={len(both)}): mean diff {np.mean(both['dog CLOSE (consensus)'] - both['bot']) * 100:+.2f} pts, mean |diff| {np.mean(abs(both['dog CLOSE (consensus)'] - both['bot'])) * 100:.2f}; Brier snapshot-close {br(both['dog CLOSE (consensus)'], both['y']):.4f} vs bot close {br(both['bot'], both['y']):.4f}")
# ---- A1 moneyline
print("\n## A1. Moneyline (dog win prob). Lower Brier / log loss is better.")
M = S[S["dog CLOSE (consensus)"].notna()].copy(); M["close"] = M["dog CLOSE (consensus)"]
cols = [("close (snapshot consensus)", "close"), ("listed G", "dog listed G (sheet)"), ("sheet model Q", "model Q"), ("Markov J raw", "Markov J"), ("Markov J - 0.1086", "Jsh"), ("exchange fair", "exch fair dog (AG)")]
print(f"n={len(M)} (rows with a snapshot close)")
print("| Prob | Brier | log loss | AUC | Brier minus close [90% CI, card bootstrap] |\n|---|---|---|---|---|")
for lab, c in cols:
    d = M[M[c].notna()]
    if lab.startswith("close"): print(f"| {lab} | {br(d[c], d['y']):.4f} | {ll(d[c], d['y']):.4f} | {auc(d[c], d['y']):.3f} | - |"); continue
    pt, lo, hi = boot(d, lambda x: br(x[c], x["y"]) - br(x["close"], x["y"]))
    print(f"| {lab} (n={len(d)}) | {br(d[c], d['y']):.4f} | {ll(d[c], d['y']):.4f} | {auc(d[c], d['y']):.3f} | {pt:+.4f} [{lo:+.4f}, {hi:+.4f}] |")
dd = M[M["bot"].notna()]
pt, lo, hi = boot(dd, lambda x: br(x["model Q"], x["y"]) - br(x["bot"], x["y"]))
print(f"Q vs independent bot close (n={len(dd)}): {pt:+.4f} [{lo:+.4f}, {hi:+.4f}]")
pt, lo, hi = boot(M, lambda x: br(x["model Q"], x["y"]) - br(x["dog listed G (sheet)"], x["y"]))
print(f"Q vs its own anchor G: {pt:+.4f} [{lo:+.4f}, {hi:+.4f}]  (what the blend + public fade add on top of the listed price)")
print(f"mean Q - G {np.mean(M['model Q'] - M['dog listed G (sheet)']) * 100:+.2f} pts (sd {np.std(M['model Q'] - M['dog listed G (sheet)']) * 100:.2f}); mean J - close {np.mean(M['Markov J'] - M['close']) * 100:+.2f}; dogs won {M['y'].mean() * 100:.1f}% vs close {M['close'].mean() * 100:.1f}%")
# best Markov weight on top of the close: y ~ logit(close) + w*(logit(J)-logit(close)), fixed slope 1 offset
from math import exp
def wfit(d, col):
    L = lg(d["close"].clip(.02, .98).values); G = lg(d[col].clip(.02, .98).values) - L; y = d["y"].values
    ws = np.linspace(-0.5, 1.0, 301); l = [ll(1 / (1 + np.exp(-(L + w * G))), y) for w in ws]; return ws[int(np.argmin(l))]
for col in ("Markov J", "Jsh"):
    w0 = wfit(M, col); bw = []
    cards = M["event"].unique(); g = {c: M[M["event"] == c] for c in cards}
    for _ in range(1000): bw.append(wfit(pd.concat([g[c] for c in rng.choice(cards, len(cards))]), col))
    print(f"best weight on Markov ({col}) on top of close: {w0:+.2f} [90% {np.percentile(bw, 5):+.2f}, {np.percentile(bw, 95):+.2f}] (sheet uses 0.15)")
print("\nCalibration, favorite side (prob of the favorite per source):")
print("| bucket | n | close | Q | Markov J | fav won |\n|---|---|---|---|---|---|")
M["pf_c"] = 1 - M["close"]; M["pf_q"] = 1 - M["model Q"]; M["pf_j"] = 1 - M["Markov J"]; M["fw"] = 1 - M["y"]
for lo, hi in ((.5, .6), (.6, .7), (.7, .8), (.8, 1.0)):
    d = M[(M["pf_c"] >= lo) & (M["pf_c"] < hi)]
    print(f"| close fav {int(lo * 100)}-{int(hi * 100)} | {len(d)} | {d['pf_c'].mean() * 100:.1f} | {d['pf_q'].mean() * 100:.1f} | {d['pf_j'].mean() * 100:.1f} | {d['fw'].mean() * 100:.1f} |")
d = M[M["close"] > 0.5]; print(f"| close flips (sheet 'dog' priced 50+) | {len(d)} | | | | |")
# ---- A2 recs and edge buckets at listed prices, Sean's unit rule
print("\n## A2. Units at the prices we'd have bet (listed best price D/I; favorite bet to win 1u, dog risk 1u)")
def pl(price, won):
    if price < 0: return 1.0 if won else price / 100
    return price / 100 if won else -1.0
R = S[S["bet rec"].astype(str).str.match(r"^(BET|lean)")].copy()
R["side_dog"] = R.apply(lambda r: any(FN.name_match(w, r["dog"]) for w in [r["bet rec"].split(" ", 1)[1].split(" [")[0].split(" (")[0]]), axis=1)
R["price"] = np.where(R["side_dog"], R["dog price (D)"], R["fav price (I)"]); R["won"] = np.where(R["side_dog"], R["y"] == 1, R["y"] == 0)
R["u"] = [pl(p, w) for p, w in zip(R["price"], R["won"])]; R["risk"] = [(-p / 100 if p < 0 else 1.0) for p in R["price"]]
R["kind"] = R["bet rec"].str.extract(r"^(BET|lean)")[0] + np.where(R["bet rec"].str.contains("80%"), " 80%", np.where(R["bet rec"].str.contains("fade sharp"), " fade-sharp-dog", ""))
for k, g in R.groupby("kind"):
    print(f"{k:<20} n={len(g):>2}  {int(g['won'].sum())}-{int((~g['won']).sum())}  units {g['u'].sum():+.2f}  risked {g['risk'].sum():.2f}  ROI {g['u'].sum() / g['risk'].sum() * 100:+.1f}%")
print(f"all recs: {int(R['won'].sum())}-{int((~R['won']).sum())}, {R['u'].sum():+.2f}u on {R['risk'].sum():.2f}u risked; dog-side recs fired: {int(R['side_dog'].sum())}")
print(f"sheet's own 'rec ML P/L' column sums to {S['rec ML P/L (u)'].sum():+.2f}: it risks 1u on favorites (e.g. -135 win = +0.74), not the to-win unit")
# edge buckets: every side with edge vs listed best price, flat 1u by the unit rule
E = []
for _, r in M.iterrows():
    for side, p_true, price, won in (("dog", r["model Q"], r["dog price (D)"], r["y"] == 1), ("fav", 1 - r["model Q"], r["fav price (I)"], r["y"] == 0)):
        if pd.isna(price): continue
        E.append(dict(event=r["event"], side=side, edge=p_true - imp(price), u=pl(price, won), risk=(-price / 100 if price < 0 else 1.0), clv=None))
E = pd.DataFrame(E)
print("Every side by sheet edge (Q vs listed best price):")
for lab, lo, hi in (("< 0", -1, 0), ("0-2", 0, .02), ("2-5", .02, .05), ("5-8", .05, .08), ("8+", .08, 1)):
    for sd in ("fav", "dog"):
        g = E[(E["edge"] >= lo) & (E["edge"] < hi) & (E["side"] == sd)]
        if len(g): print(f"  {sd} edge {lab:<4} n={len(g):>3}  units {g['u'].sum():+6.2f}  ROI {g['u'].sum() / g['risk'].sum() * 100:+6.1f}%")
# vetoed dogs shadow
print("Dog vetoes, shadow record if the dog had been bet at listed price (risk 1u):")
for fl, g in M.groupby(M["flag AA"].astype(str).str.split(" -").str[0].str.split(" \\(").str[0]):
    u = [pl(p, w) for p, w in zip(g["dog price (D)"], g["y"] == 1) if pd.notna(p)]
    print(f"  {fl:<28} n={len(g):>3} dogs won {int(g['y'].sum())}  shadow dog units {sum(u):+.2f}")
# ---- A3 duration
print("\n## A3. Duration: went the distance (GTD)")
G = S[S["GTD"].notna()].copy(); G["g"] = G["GTD"].astype(float)
print(f"n={len(G)}; actual GTD {G['g'].mean() * 100:.1f}%; listed {G['GTD listed'].mean() * 100:.1f}; close {G['GTD close'].mean() * 100:.1f}; sheet fight GTD {G['Fight GTD model'].mean() * 100:.1f}; Markov P(dec) {G['Markov P(dec)'].mean() * 100:.1f} (n={G['Markov P(dec)'].notna().sum()})")
GG = G[G["GTD close"].notna()]
for lab, c in (("GTD listed", "GTD listed"), ("sheet fight GTD", "Fight GTD model"), ("Markov P(dec)", "Markov P(dec)")):
    d = GG[GG[c].notna()]; pt, lo, hi = boot(d, lambda x: br(x[c], x["g"]) - br(x["GTD close"], x["g"]))
    print(f"  {lab:<18} n={len(d):>3} Brier {br(d[c], d['g']):.4f} vs close {br(d['GTD close'], d['g']):.4f}: diff {pt:+.4f} [{lo:+.4f}, {hi:+.4f}]")
d = GG[GG["Markov P(dec)"].notna()]
print(f"  Markov gap to close vs result: {[(lab, len(x), round(x['g'].mean() * 100, 1), round(x['GTD close'].mean() * 100, 1), round(x['Markov P(dec)'].mean() * 100, 1)) for lab, x in (('Markov 8+ above', d[d['Markov P(dec)'] - d['GTD close'] >= .08]), ('within 8', d[abs(d['Markov P(dec)'] - d['GTD close']) < .08]), ('Markov 8+ below', d[d['Markov P(dec)'] - d['GTD close'] <= -.08]))]}  (label, n, GTD %, close, Markov)")
plays = G[G["GTD/ITD play"].astype(str).str.match(r"^(GTD|ITD)")]
print(f"  GTD/ITD plays: n={len(plays)}, sheet P/L column {plays['GTD/ITD play P/L (u)'].sum():+.2f}u; by type: " + "; ".join(f"{k} n={len(g)} {g['GTD/ITD play P/L (u)'].sum():+.2f}u" for k, g in plays.groupby(plays['GTD/ITD play'].astype(str).str.extract(r'^((?:GTD|ITD)(?: \([^)]*\))?)')[0])))
# ---- A4 totals
print("\n## A4. Round totals")
for lab, col, res in (("O1.5 listed", "O1.5 listed", "over 1.5"), ("O2.5 listed", "O2.5 listed", "over 2.5"), ("O2.5 model", "O2.5 model", "over 2.5"), ("O4.5 listed", "O4.5 listed", "over 4.5")):
    d = S[S[col].notna() & S[res].notna()]
    if res == "over 4.5": d = d[d["tag"].astype(str).str.endswith("-5")]
    print(f"  {lab:<12} n={len(d):>3}  priced {d[col].mean() * 100:5.1f}  hit {d[res].mean() * 100:5.1f}  Brier {br(d[col], d[res]):.4f}")
d = S[S["O2.5 model"].notna() & S["O2.5 listed"].notna() & S["over 2.5"].notna()]
pt, lo, hi = boot(d, lambda x: br(x["O2.5 model"], x["over 2.5"]) - br(x["O2.5 listed"], x["over 2.5"]))
print(f"  O2.5 model minus listed: {pt:+.4f} [{lo:+.4f}, {hi:+.4f}] n={len(d)}")
# ---- A5 method
print("\n## A5. Method (6-way: dog/fav x DEC/KO/SUB)")
MM = S[S["method outcome"].notna()].copy(); K6 = ["dogDEC", "dogKO", "dogSUB", "favDEC", "favKO", "favSUB"]
def m6(d, pre):
    P = d[[f"{pre} {k}" for k in K6]].astype(float).values; P = P / P.sum(1, keepdims=True)
    Y = np.array([[1.0 if o == k else 0.0 for k in K6] for o in d["method outcome"]])
    return float(np.mean(((P - Y) ** 2).sum(1))), float(-np.mean(np.log(np.clip((P * Y).sum(1), 1e-4, 1))))
MM = MM.dropna(subset=[f"{p} {k}" for p in ("P model", "P mkt") for k in K6])
for pre in ("P model", "P mkt"):
    b, l = m6(MM, pre); print(f"  {pre:<8} n={len(MM)}  multi-Brier {b:.4f}  log loss {l:.4f}")
pt, lo, hi = boot(MM, lambda x: m6(x, "P model")[0] - m6(x, "P mkt")[0]); print(f"  model minus market: {pt:+.4f} [{lo:+.4f}, {hi:+.4f}]")
oc = MM["method outcome"].value_counts(normalize=True)
for k in ("DEC", "KO", "SUB"):
    print(f"  {k}: actual {sum(oc.get(s + k, 0) for s in ('dog', 'fav')) * 100:.1f}%  model {MM[[f'P model dog{k}', f'P model fav{k}']].sum(1).mean() * 100:.1f}  market {MM[[f'P mkt dog{k}', f'P mkt fav{k}']].sum(1).mean() * 100:.1f}")
# ---- A6 PropSnap sources
print("\n## A6. Market-only props (PropSnap): which price source scores best, same bouts and markets")
Pg = PS[PS["result"].notna() & PS["prob"].notna()].copy()
key = ["pk", "tab", "row", "market"]; piv = Pg.pivot_table(index=key, columns="source", values="prob", aggfunc="first"); res = Pg.groupby(key)["result"].first()
for mk in sorted(Pg["market"].unique()):
    sub = piv.loc[piv.index.get_level_values(3) == mk]; out = []
    for s_ in [c for c in sub.columns if c != "books"]:
        com = sub[["books", s_]].dropna()
        if len(com) < 15: continue
        y = res.loc[com.index].values.astype(float); out.append(f"{s_} {br(com[s_], y) - br(com['books'], y):+.4f} (n={len(com)})")
    d = sub["books"].dropna(); y = res.loc[d.index].values.astype(float)
    print(f"  {mk:<8} books n={len(d):>3} priced {d.mean() * 100:5.1f} hit {y.mean() * 100:5.1f} Brier {br(d, y):.4f} | vs books: " + ", ".join(out))
pg = PS.groupby("event")["result"].agg(["size", "count"])
print("  graded share by card: " + "; ".join(f"{e[:30]} {c}/{n}" for e, (n, c) in pg.iterrows()))
print("  PropSnap holds market prices only: no model column for props, so model props cannot be graded from it.")
# ---- B segments (Markov and Q residual by segment)
print("\n# B. Where the sheet / Markov is off on these 10 cards (n small: every row is noise unless |z| > 2.5)")
M["wc"] = M["tag"].astype(str).str.replace("-5", "").str.replace(".0", "", regex=False)
M["women"] = M["wc"].str.startswith("w"); M["five"] = M["tag"].astype(str).str.endswith("-5")
def srow(lab, d):
    if len(d) < 5: return
    z = (d["y"].sum() - d["close"].sum()) / math.sqrt((d["close"] * (1 - d["close"])).sum())
    print(f"| {lab} | {len(d)} | {d['close'].mean() * 100:.1f} | {d['model Q'].mean() * 100:.1f} | {d['Markov J'].mean() * 100:.1f} | {d['y'].mean() * 100:.1f} | {z:+.2f} | {br(d['model Q'], d['y']) - br(d['close'], d['y']):+.4f} | {br(d['Jsh'], d['y']) - br(d['close'], d['y']):+.4f} |")
print("| segment | n | dog close | dog Q | dog Markov | dog won | z (won vs close) | Q minus close Brier | Markov-shifted minus close Brier |\n|---|---|---|---|---|---|---|---|---|")
srow("all", M); srow("women", M[M["women"]]); srow("men", M[~M["women"]]); srow("5 rounds", M[M["five"]])
srow("flyweight-bantam (125-135 men)", M[M["wc"].isin(["125", "135"])]); srow("145-170", M[M["wc"].isin(["145", "155", "170"])]); srow("185-205", M[M["wc"].isin(["185", "205"])]); srow("heavyweight", M[M["wc"] == "265"])
srow("close dog 40-50", M[(M["close"] >= .4)]); srow("close dog 25-40", M[(M["close"] >= .25) & (M["close"] < .4)]); srow("close dog < 25", M[M["close"] < .25])
srow("Markov 10+ above close", M[M["Markov J"] - M["close"] >= .10]); srow("Markov within 10", M[abs(M["Markov J"] - M["close"]) < .10]); srow("Markov 10+ below close", M[M["Markov J"] - M["close"] <= -.10])
srow("D code (debut dog)", M[M["K code"].astype(str).str.strip() == "D"])
print(f"\nShort notice, layoff, age and style are not captured in Snapshots (K code holds D x4, one numeric, nothing else); these segments are tested on the 2022-2026 history in part C instead.")

# ---- A1b decomposition of Q - G
print("\n## A1b. What earns Q's edge over its anchor G: each term added alone to G")
shift = {e: 0.0 for e in M["event"].unique()}
e334 = [e for e in shift if "334" in e][0]; eq = [e for e in shift if "Stirling" in e][0]
shift[e334] = float(np.mean(M[M["event"] == e334]["Markov J"] - M[M["event"] == e334]["dog listed G (sheet)"])); shift[eq] = 0.1086
M["mk"] = [0.15 * (min(.98, max(.02, j - shift[e])) - g) for j, g, e in zip(M["Markov J"], M["dog listed G (sheet)"], M["event"])]
M["wo"] = np.where(M["women"], -0.04, 0.0); M["rest"] = M["model Q"] - M["dog listed G (sheet)"] - M["mk"] - M["wo"]
print(f"334 card shift used {shift[e334]:.4f}; cards 1-8 no shift (v4.6 formula live from Nov 9; see B42 doc)")
for lab, add in (("G + Markov term", M["mk"]), ("G + women -4", M["wo"]), ("G + public fade / context (residual)", M["rest"]), ("G + all (= Q)", M["mk"] + M["wo"] + M["rest"])):
    M["_t"] = (M["dog listed G (sheet)"] + add).clip(.01, .99)
    pt, lo, hi = boot(M, lambda x: br(x["_t"], x["y"]) - br(x["dog listed G (sheet)"], x["y"]))
    print(f"  {lab:<40} mean shift {add.mean() * 100:+.2f} pts (sd {add.std() * 100:.2f})  Brier vs G {pt:+.4f} [{lo:+.4f}, {hi:+.4f}]")
print(f"  women rows: {int(M['women'].sum())}, dogs won {int(M[M['women']]['y'].sum())}")
