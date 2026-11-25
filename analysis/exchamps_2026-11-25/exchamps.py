"""Ex-champions after losing the belt vs the market (PREREG_exchamps_2026-11-25.md, sha256 92a91b90...).
Run from a szerillo/ufc-projections checkout at origin/main:
  python3 exchamps.py sample <cache> <qatar_results.json>            -> counts only (definition choice, no odds)
  python3 exchamps.py score  <cache> <qatar_results.json> <A|B> <xlsx> <outdir>
"""
import csv, json, glob, os, re, sys, math, collections, datetime as dt
import numpy as np
sys.path.insert(0, "scripts"); import build_embed_metrics as Bm; import fighter_names as FN
MODE, D, QR = sys.argv[1], sys.argv[2], sys.argv[3]
fold = Bm.fold
alias = {fold(k): v for k, v in json.load(open("form/data/name_aliases.json")).items() if not k.startswith("_")}
canon = lambda s: fold(alias.get(fold(s), s))
date = {r["EVENT"].strip(): dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").date() for r in csv.DictReader(open(f"{D}/ufc_event_details.csv", encoding="utf-8"))}
B = []
for r in csv.DictReader(open(f"{D}/ufc_fight_results.csv", encoding="utf-8")):
    e = r["EVENT"].strip(); d = date.get(e); names = [x.strip() for x in r["BOUT"].split(" vs. ")]
    if not d or len(names) != 2: continue
    o = r["OUTCOME"].strip(); w = names[0] if o == "W/L" else names[1] if o == "L/W" else None
    B.append(dict(date=d, event=e, a=names[0], b=names[1], winner=w, loser=(names[1] if w == names[0] else names[0]) if w else None,
                  wc=r["WEIGHTCLASS"].strip(), method=r["METHOD"].strip()))
for f in json.load(open(QR))["fights"]:   # Nov 21 2026 Qatar card (after the cache)
    B.append(dict(date=dt.date(2026, 11, 21), event="UFC Fight Night: Prochazka vs. Stirling", a=f["winner"], b=f["loser"], winner=f["winner"],
                  loser=f["loser"], wc="", method=f["method"]))
B.sort(key=lambda x: (x["date"], x["event"]))
TB = re.compile(r"^UFC (Interim )?(.+?) Title Bout$")
def belts(defn):
    """Walk title bouts; return list of title losses (fighter, date, belt)."""
    hold = {}; losses = []
    for x in B:
        m = TB.match(x["wc"])
        if not m: continue
        interim, div = bool(m.group(1)), m.group(2)
        key = (div, interim); fs = {canon(x["a"]), canon(x["b"])}
        if not interim and (div, True) in hold and hold[(div, True)] not in fs: hold.pop((div, True))   # unification clears interim
        h = hold.get(key)
        if h and h not in fs: hold.pop(key); h = None                                                   # vacated / stripped
        if x["winner"] is None: continue
        if h and canon(x["loser"]) == h and x["date"] >= dt.date(2001, 1, 1) and (defn == "B" or not interim):
            losses.append(dict(f=canon(x["loser"]), name=x["loser"], date=x["date"], belt=("Interim " if interim else "") + div))
        if not interim and (div, True) in hold and canon(x["loser"]) == hold[(div, True)] and defn == "B":   # interim holder loses unification
            losses.append(dict(f=canon(x["loser"]), name=x["loser"], date=x["date"], belt="Interim " + div + " (unification)"))
            hold.pop((div, True))
        hold[key] = canon(x["winner"])
        if not interim: hold.pop((div, True), None)
    return losses
def sample(defn):
    L = belts(defn); first = {}
    for l in L: first.setdefault(l["f"], l)
    fights = []
    for x in B:
        for side, opp in ((x["a"], x["b"]), (x["b"], x["a"])):
            c = canon(side)
            if c in first and x["date"] > first[c]["date"]:
                last_loss = max(l["date"] for l in L if l["f"] == c and l["date"] < x["date"])
                fights.append(dict(fighter=side, f=c, opp=opp, date=x["date"], event=x["event"], wc=x["wc"], method=x["method"],
                                   won=None if x["winner"] is None else (canon(x["winner"]) == c),
                                   first_back=not any(y["date"] > first[c]["date"] and y["date"] < x["date"] and c in (canon(y["a"]), canon(y["b"])) for y in B)
                                   if x["date"] > first[c]["date"] else None, loss_date=first[c]["date"], last_loss=last_loss))
    return L, first, fights
if MODE == "sample":
    for defn in ("A", "B"):
        L, first, F = sample(defn); w = sum(1 for f in F if f["won"] is True); l = sum(1 for f in F if f["won"] is False)
        print(f"definition {defn}: title losses {len(L)} by {len(first)} champions; post-loss UFC record {w}-{l} (+{sum(1 for f in F if f['won'] is None)} draw/NC); "
              f"lost first fight back {sum(1 for f in F if f['first_back'] and f['won'] is False)}/{sum(1 for f in F if f['first_back'] and f['won'] is not None)}")
    print("Feldman: 103 losses by 87 champions; 261-283; 52% lost first fight back")
    sys.exit()

# ---------------- score
DEFN, XLSX, OUT = sys.argv[4], sys.argv[5], sys.argv[6]
L, first, F = sample(DEFN)
excham_at = collections.defaultdict(list)
for l in L: excham_at[l["f"]].append(l["date"])
is_ex = lambda c, d: any(ld < d for ld in excham_at.get(c, []))
w = sum(1 for f in F if f["won"] is True); l_ = sum(1 for f in F if f["won"] is False)
print(f"# Sample (definition {DEFN}): {len(L)} title losses by {len(first)} champions; post-loss UFC record {w}-{l_} (Feldman 261-283)")
# prior UFC fights + dob
prior = collections.Counter(); nprior = {}
for x in B:
    for s in (x["a"], x["b"]): nprior[(canon(s), x["date"], x["event"])] = prior[canon(s)]
    for s in (x["a"], x["b"]): prior[canon(s)] += 1
dob = {}
for r in csv.DictReader(open(f"{D}/ufc_fighter_tott.csv", encoding="utf-8")):
    try: dob.setdefault(canon(r["FIGHTER"].strip()), dt.datetime.strptime(r["DOB"].strip(), "%b %d, %Y").date())
    except Exception: pass
imp = lambda o: (-o / (-o + 100)) if o < 0 else 100 / (o + 100)
def power(a, b):
    ia, ib = imp(a), imp(b); lo, hi = 1.0, 3.0
    for _ in range(60):
        k = (lo + hi) / 2; lo, hi = (k, hi) if ia ** k + ib ** k > 1 else (lo, k)
    return ia ** k
def units(price, won):
    if price < 0: return (1.0 if won else price / 100), -price / 100
    return (price / 100 if won else -1.0), 1.0
# archive odds, all sides (for the placebo pool too)
SIDES = []
for p in sorted(glob.glob("form/data/events/202[2-6]-*.json")):
    ev = json.load(open(p)); d_ = dt.date.fromisoformat(os.path.basename(p)[:10])
    for f in ev["fights"]:
        c = (f.get("odds") or {}).get("close"); o = (f.get("odds") or {}).get("open"); r_ = f.get("result") or {}
        if not isinstance(c, dict) or not (c.get("ma") and c.get("mb")): continue
        if r_.get("kind") != "win" and not (d_ == dt.date(2026, 11, 21)): continue
        pa = power(c["ma"], c["mb"])
        for side, opp, ps, price, oprice, wl in ((f["a"]["name"], f["b"]["name"], pa, c["ma"], c["mb"], "a"), (f["b"]["name"], f["a"]["name"], 1 - pa, c["mb"], c["ma"], "b")):
            won = (r_.get("winner") == wl) if r_.get("kind") == "win" else None
            op = (o.get("p") if wl == "a" else 1 - o.get("p")) if isinstance(o, dict) and o.get("p") is not None else None
            SIDES.append(dict(date=d_, fighter=side, f=canon(side), opp=opp, o=canon(opp), p=ps, pm=(c["p"] if wl == "a" else 1 - c["p"]),
                              price=price, oprice=oprice, won=won, open=op))
# Qatar results onto the Nov 21 sides
QRES = json.load(open(QR))["fights"]
for s in SIDES:
    if s["date"] == dt.date(2026, 11, 21) and s["won"] is None:
        for q in QRES:
            if FN.name_match(q["winner"], s["fighter"]) and FN.name_match(q["loser"], s["opp"]): s["won"] = True
            elif FN.name_match(q["loser"], s["fighter"]) and FN.name_match(q["winner"], s["opp"]): s["won"] = False
SIDES = [s for s in SIDES if s["won"] is not None]
def enrich(s):
    s["age"] = (s["date"] - dob[s["f"]]).days / 365.25 if s["f"] in dob else None
    s["n"] = next((v for (c, d_, e), v in nprior.items() if c == s["f"] and d_ == s["date"]), None)
    s["on"] = next((v for (c, d_, e), v in nprior.items() if c == s["o"] and d_ == s["date"]), None)
    return s
EX = []
for f in F:
    m = next((s for s in SIDES if s["date"] == f["date"] and FN.name_match(s["fighter"], f["fighter"]) and FN.name_match(s["opp"], f["opp"])), None)
    if m and f["won"] is not None:
        m = enrich(dict(m)); m.update(first_back=f["first_back"], since=(f["date"] - f["last_loss"]).days / 365.25, loss_date=str(f["loss_date"]), ex=True)
        EX.append(m)
post22 = [f for f in F if f["date"] >= dt.date(2022, 1, 1) and f["won"] is not None]
print(f"post-loss fights 2022-2026: {len(post22)}; with an archive close: {len(EX)} (unmatched {len(post22) - len(EX)})")
rng = np.random.default_rng(20261125)
def stats(S):
    if not S: return None
    won = np.array([s["won"] for s in S], float); p = np.array([s["p"] for s in S]); pm = np.array([s["pm"] for s in S])
    ue = [units(s["price"], s["won"]) for s in S]; uf = [units(s["oprice"], not s["won"]) for s in S]
    return dict(n=len(S), won=won.mean(), priced=p.mean(), priced_m=pm.mean(), resid=(won - p).mean(),
                z=(won - p).sum() / math.sqrt((p * (1 - p)).sum()), roi_ex=sum(a for a, _ in ue) / sum(b for _, b in ue),
                roi_fade=sum(a for a, _ in uf) / sum(b for _, b in uf), u_ex=sum(a for a, _ in ue), u_fade=sum(a for a, _ in uf),
                brier=float(np.mean((p - won) ** 2)))
def boot(S, key, n=4000):
    if len(S) < 5: return (float("nan"), float("nan"))
    by = collections.defaultdict(list)
    for s in S: by[s["f"]].append(s)
    ks = list(by); v = []
    for _ in range(n):
        R = [x for k in rng.choice(ks, len(ks)) for x in by[k]]; v.append(stats(R)[key])
    return float(np.percentile(v, 5)), float(np.percentile(v, 95))
def line(lab, S):
    st = stats(S)
    if not st: print(f"| {lab} | 0 | | | | | | |"); return None
    lo, hi = boot(S, "roi_fade"); rlo, rhi = boot(S, "resid")
    print(f"| {lab} | {st['n']} | {st['won'] * 100:.1f} | {st['priced'] * 100:.1f} | {st['resid'] * 100:+.1f} [{rlo * 100:+.1f}, {rhi * 100:+.1f}] | {st['roi_ex'] * 100:+.1f}% | {st['roi_fade'] * 100:+.1f}% [{lo * 100:+.1f}, {hi * 100:+.1f}] | {st['u_fade']:+.2f} |")
    return dict(segment=lab, n=st["n"], win_pct=round(st["won"] * 100, 1), implied_pct=round(st["priced"] * 100, 1), resid_pts=round(st["resid"] * 100, 1),
                resid_lo=round(rlo * 100, 1), resid_hi=round(rhi * 100, 1), roi_back=round(st["roi_ex"] * 100, 1), roi_fade=round(st["roi_fade"] * 100, 1),
                roi_fade_lo=round(lo * 100, 1), roi_fade_hi=round(hi * 100, 1), units_fade=round(st["u_fade"], 2))
print("\n## Results vs market (close, power de-vig; units at the close median price, Sean's unit rule)")
print("| Segment | n | Won % | Implied % | Won minus implied [90% CI] | ROI backing ex-champ | ROI fading [90% CI] | Fade units |\n|---|---|---|---|---|---|---|---|")
CH = []
segs = [("All post-loss fights 2022-26", EX), ("First fight back", [s for s in EX if s["first_back"]]), ("Later fights", [s for s in EX if not s["first_back"]]),
        ("Age under 35", [s for s in EX if s["age"] and s["age"] < 35]), ("Age 35+", [s for s in EX if s["age"] and s["age"] >= 35]),
        ("Under 1 yr since loss", [s for s in EX if s["since"] < 1]), ("1-2 yrs since loss", [s for s in EX if 1 <= s["since"] < 2]), ("2+ yrs since loss", [s for s in EX if s["since"] >= 2]),
        ("Ex-champ favorite", [s for s in EX if s["p"] >= .5]), ("Ex-champ underdog", [s for s in EX if s["p"] < .5]),
        ("Opponent prospect (<=5 UFC fights)", [s for s in EX if s["on"] is not None and s["on"] <= 5]), ("Opponent middle (6-7)", [s for s in EX if s["on"] in (6, 7)]),
        ("Opponent vet (8+ UFC fights)", [s for s in EX if s["on"] is not None and s["on"] >= 8])]
for lab, S in segs:
    r = line(lab, S)
    if r: CH.append(r)
print("\nBy year (fade ROI): " + "; ".join(f"{y}: n={len(S)} {stats(S)['roi_fade'] * 100:+.1f}%" for y in range(2022, 2027) for S in [[s for s in EX if s["date"].year == y]] if S))
st = stats(EX); print(f"multiplicative close sensitivity: implied {st['priced_m'] * 100:.1f}% vs power {st['priced'] * 100:.1f}%; Brier of close {st['brier']:.4f}")
# placebo
def cell(s):
    return (min(int(s["p"] * 20), 19), 0 if s["age"] is None else (0 if s["age"] < 30 else 1 if s["age"] < 35 else 2), None if s["n"] is None else (0 if s["n"] < 8 else 1 if s["n"] < 15 else 2))
POOL = collections.defaultdict(list)
for s in SIDES:
    if is_ex(s["f"], s["date"]): continue
    s = enrich(dict(s))
    if s["age"] is None or s["n"] is None: continue
    POOL[cell(s)].append(s["won"] - s["p"])
EXc = [s for s in EX if s["age"] is not None and s["n"] is not None]
matched = [s for s in EXc if POOL.get(cell(s))]
def champ_eff(S):
    if not S: return float("nan")
    return float(np.mean([s["won"] - s["p"] for s in S]) - np.mean([np.mean(POOL[cell(s)]) for s in S]))
ce = champ_eff(matched)
by = collections.defaultdict(list)
for s in matched: by[s["f"]].append(s)
ks = list(by); v = [champ_eff([x for k in rng.choice(ks, len(ks)) for x in by[k]]) for _ in range(4000)]
print(f"\n## Placebo (non-champs, same odds 5-pt bin x age bin x UFC-experience bin)\nmatched {len(matched)} of {len(EX)} ex-champ fights (dropped {len(EX) - len(matched)}: no cell / no dob); "
      f"placebo pool sides {sum(len(x) for x in POOL.values())}")
print(f"ex-champ won minus implied {np.mean([s['won'] - s['p'] for s in matched]) * 100:+.1f} pts; matched placebo {np.mean([np.mean(POOL[cell(s)]) for s in matched]) * 100:+.1f} pts; "
      f"champion effect {ce * 100:+.1f} pts [90% CI {np.percentile(v, 5) * 100:+.1f}, {np.percentile(v, 95) * 100:+.1f}]")
# mechanism: drift
dr = [s["p"] - s["open"] for s in EX if s["open"] is not None]
print(f"\n## Mechanism\nopen to close drift on the ex-champ side: mean {np.mean(dr) * 100:+.2f} pts (n={len(dr)}; positive = money toward the ex-champ); "
      f"share drifting toward him {np.mean([d > 0 for d in dr]) * 100:.0f}%")
pdr = [s["p"] - s["open"] for s in SIDES if s["open"] is not None and not is_ex(s["f"], s["date"])]
print(f"all non-ex-champ sides: mean drift {np.mean(pdr) * 100:+.2f} pts (n={len(pdr)})")
# bars
st_all = stats(EX); lo, hi = boot(EX, "roi_fade")
yrs = {y: stats([s for s in EX if s["date"].year == y]) for y in range(2022, 2027) if len([s for s in EX if s["date"].year == y]) >= 5}
b1 = st_all["roi_fade"] > 0 and lo > 0; b2 = all(v_["roi_fade"] > 0 for v_ in yrs.values()); b3 = np.percentile(v, 95) < 0; b4 = len(EX) >= 50
print(f"\n## Bars (overall fade)\n1 fade ROI > 0 with CI lower > 0: {b1} ({st_all['roi_fade'] * 100:+.1f}%, [{lo * 100:+.1f}, {hi * 100:+.1f}])\n"
      f"2 positive every year with 5+ bets: {b2} ({ {y: round(v_['roi_fade'] * 100, 1) for y, v_ in yrs.items()} })\n3 champion effect CI excludes 0 (fade side): {b3}\n4 n >= 50: {b4} (n={len(EX)})\n"
      f"VERDICT overall: {'BETTABLE' if all((b1, b2, b3, b4)) else 'NOT BETTABLE'}")
print("\nSubsets passing bars 1-3 with n >= 30 (exploratory):")
for lab, S in segs[1:]:
    if len(S) < 30: continue
    stS = stats(S); l2, _ = boot(S, "roi_fade")
    yS = [stats([s for s in S if s["date"].year == y]) for y in range(2022, 2027) if len([s for s in S if s["date"].year == y]) >= 5]
    mS = [s for s in S if s["age"] is not None and s["n"] is not None and POOL.get(cell(s))]
    byS = collections.defaultdict(list)
    for s in mS: byS[s["f"]].append(s)
    kS = list(byS); vS = [champ_eff([x for k in rng.choice(kS, len(kS)) for x in byS[k]]) for _ in range(2000)] if kS else [0]
    ok = stS["roi_fade"] > 0 and l2 > 0 and all(y_["roi_fade"] > 0 for y_ in yS) and np.percentile(vS, 95) < 0
    print(f"  {lab}: n={len(S)} fade {stS['roi_fade'] * 100:+.1f}% CI low {l2 * 100:+.1f}; years {[round(y_['roi_fade'] * 100) for y_ in yS]}; champ eff CI high {np.percentile(vS, 95) * 100:+.1f} -> {'PASS' if ok else 'fail'}")
# our model: Snapshots rows
import openpyxl
ws = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)["Snapshots"]; rows = list(ws.iter_rows(values_only=True)); H = rows[0]; ix = {h: i for i, h in enumerate(H)}
mod = []
for r in rows[1:]:
    if r[0] in (None, "") or r[ix["dog won"]] is None: continue
    d_ = r[1].date() if hasattr(r[1], "date") else None
    for side, isdog in ((r[ix["dog"]], True), (r[ix["fav"]], False)):
        if d_ and is_ex(canon(side), d_):
            q = r[ix["model Q"]]; j = r[ix["Markov J"]]; c = r[ix["dog CLOSE (consensus)"]]; y = float(r[ix["dog won"]])
            if not isdog: q, j, c, y = (1 - q if q is not None else None), (1 - j if j is not None else None), (1 - c if c is not None else None), 1 - y
            mod.append((side, str(d_), q, j, c, y))
print(f"\n## Our model on ex-champ fights (sheet Snapshots, 10 graded cards): n={len(mod)}")
for m in mod: print(f"  {m[1]} {m[0]}: close {m[4] if m[4] is None else round(m[4] * 100, 1)}  sheet Q {round(m[2] * 100, 1) if m[2] is not None else None}  Markov {round(m[3] * 100, 1) if m[3] is not None else None}  won {int(m[5])}")
mm = [m for m in mod if None not in (m[2], m[3], m[4])]
if mm:
    br = lambda k: np.mean([(m[k] - m[5]) ** 2 for m in mm])
    print(f"  Brier (n={len(mm)}): close {br(4):.4f}  sheet Q {br(2):.4f}  Markov {br(3):.4f}  (descriptive; n too small to judge)")
# outputs
os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/exchamps_fights.csv", "w", newline="") as fh:
    w_ = csv.writer(fh); w_.writerow(["date", "ex_champ", "opponent", "won", "implied_power", "implied_mult", "close_price_ex", "close_price_opp", "open_implied", "first_fight_back", "age", "years_since_loss", "opp_prior_ufc_fights", "units_back", "units_fade"])
    for s in sorted(EX, key=lambda s: s["date"]):
        w_.writerow([s["date"], s["fighter"], s["opp"], int(s["won"]), round(s["p"], 4), round(s["pm"], 4), s["price"], s["oprice"], None if s["open"] is None else round(s["open"], 4),
                     int(bool(s["first_back"])), None if s["age"] is None else round(s["age"], 1), round(s["since"], 2), s["on"], round(units(s["price"], s["won"])[0], 3), round(units(s["oprice"], not s["won"])[0], 3)])
with open(f"{OUT}/exchamps_chart.csv", "w", newline="") as fh:
    w_ = csv.DictWriter(fh, fieldnames=list(CH[0])); w_.writeheader(); w_.writerows(CH)
print(f"\nwrote {OUT}/exchamps_fights.csv ({len(EX)} rows), {OUT}/exchamps_chart.csv ({len(CH)} rows)")
