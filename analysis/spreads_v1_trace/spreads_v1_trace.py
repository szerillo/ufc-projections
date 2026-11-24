"""Spreads trace (Nov 24 2026): where Fight Form round-winning strength enters the v0 spread price, and whether it
predicts decision margins beyond the closing price. Run from a szerillo/ufc-projections checkout (main f4d3d5fd) with
the UFCStats CSV cache:  python3 -I analysis/spreads_v1_trace/spreads_v1_trace.py .form_cache > .../spreads_v1_trace_out.txt
Round won = the site's rule (scripts/build_embed_metrics.py): a round ending in a finish goes to the finisher, any other
round is scored with labs.json scoring.coef (ties half). Pre-fight rates use only fights before the fight date."""
import csv, json, re, sys, math, glob, os, collections, datetime as dt, unicodedata
import numpy as np
sys.path.insert(0, "scripts"); import build_embed_metrics as B
D = sys.argv[1]
fold = B.fold
alias = {fold(k): v for k, v in json.load(open("form/data/name_aliases.json")).items() if not k.startswith("_")}
canon = lambda s: fold(alias.get(fold(s), s))
date = {r["EVENT"].strip(): dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").date().isoformat() for r in csv.DictReader(open(f"{D}/ufc_event_details.csv", encoding="utf-8"))}
res = {(r["EVENT"].strip(), r["BOUT"].strip()): r for r in csv.DictReader(open(f"{D}/ufc_fight_results.csv", encoding="utf-8"))}
rows = collections.defaultdict(dict)
for r in csv.DictReader(open(f"{D}/ufc_fight_stats.csv", encoding="utf-8")):
    m = re.match(r"Round (\d+)", r["ROUND"] or "")
    if m: rows[(r["EVENT"].strip(), r["BOUT"].strip())][(int(m.group(1)), r["FIGHTER"].strip())] = r
# chronological pass: per fighter cumulative rounds won / rounds; snapshot before each fight
cum = collections.defaultdict(lambda: [0.0, 0]); pre = {}
for (e, b), r in sorted(res.items(), key=lambda kv: date.get(kv[0][0], "")):
    d_ = date.get(e); byr = rows.get((e, b)); names = [x.strip() for x in b.split(" vs. ")]
    if not d_ or not byr or len(names) != 2: continue
    for n_ in names: pre[(d_, canon(n_))] = tuple(cum[canon(n_)])
    decided = r["OUTCOME"] in ("W/L", "L/W"); last_r = int(r["ROUND"]); winner = names[0] if r["OUTCOME"] == "W/L" else names[1] if decided else None
    for rd in range(1, min(last_r, 5) + 1):
        x, y = byr.get((rd, names[0])), byr.get((rd, names[1]))
        if not x or not y: continue
        if rd == last_r and decided and "Decision" not in r["METHOD"]: wa = 1.0 if winner == names[0] else 0.0
        else:
            sc = B.rscore(x) - B.rscore(y); wa = 1.0 if sc > 0 else 0.0 if sc < 0 else 0.5
        cum[canon(names[0])][0] += wa; cum[canon(names[1])][0] += 1 - wa; cum[canon(names[0])][1] += 1; cum[canon(names[1])][1] += 1
K = 5.0
def rate(t): return None if t is None or t[1] < 3 else (t[0] + 0.5 * K) / (t[1] + K)   # shrunk toward .5, 3+ UFC rounds
def log5(a, b): return a * (1 - b) / (a * (1 - b) + (1 - a) * b)
lg = lambda p: math.log(p / (1 - p)); sg = lambda x: 1 / (1 + math.exp(-x))
J = json.load(open("form/data/judges.json")); cards = collections.defaultdict(list)
for v in J.values():
    for r in v["rows"]:
        m = re.match(r"(\d+)-(\d+)$", r[5])
        if m: cards[(r[1], r[2])].append((r[3], r[4], int(m.group(1)), int(m.group(2))))
X = []
for p in sorted(glob.glob("form/data/events/*.json")):
    ev = json.load(open(p)); slug = os.path.basename(p)[:-5]; d_ = slug[:10]
    for f in ev["fights"]:
        c = (f.get("odds") or {}).get("close"); res_ = f.get("result") or {}
        if not isinstance(c, dict) or c.get("p") is None or res_.get("kind") != "win" or f.get("sched") != 3: continue
        pc = c["p"]; fav = "a" if pc >= 0.5 else "b"; fa, fb = (f["a"], f["b"]) if fav == "a" else (f["b"], f["a"])
        ra, rb = rate(pre.get((d_, canon(fa["name"])))), rate(pre.get((d_, canon(fb["name"]))))
        if ra is None or rb is None: continue
        dec = res_.get("method", "").startswith("Decision"); marg = None
        if dec:
            cc = cards.get((slug, f["n"]))
            if not cc or len(cc) != 3: continue
            an = f["a"]["name"]; s = 0; ok = True
            for a, b, x, y in cc:
                if a == an: s += x - y
                elif b == an: s += y - x
                else: ok = False
            if not ok: continue
            marg = s if fav == "a" else -s
        X.append(dict(date=d_, pf=max(pc, 1 - pc), q=log5(ra, rb), ra=ra, rb=rb, favwin=res_["winner"] == fav, dec=dec, marg=marg))
def fit(Xm, y):
    Xm = np.asarray(Xm, float); y = np.asarray(y, float); b = np.zeros(Xm.shape[1])
    for _ in range(60):
        pr = 1 / (1 + np.exp(-Xm @ b)); W = pr * (1 - pr) + 1e-9; H = Xm.T @ (Xm * W[:, None]); b += np.linalg.solve(H + 1e-6 * np.eye(len(b)), Xm.T @ (y - pr))
    pr = 1 / (1 + np.exp(-Xm @ b)); ll = -np.mean(y * np.log(pr) + (1 - y) * np.log(1 - pr))
    return b, np.sqrt(np.diag(np.linalg.inv(H))), ll
print(f"3R fights with close price and both fighters' pre-fight round rates (3+ UFC rounds): {len(X)} ({min(x['date'] for x in X)} to {max(x['date'] for x in X)})")
print("matchup round-win q = log5(fav rate, dog rate), rates shrunk toward 50% with 5 pseudo-rounds")
FD = [x for x in X if x["dec"] and x["marg"] > 0]; DD = [x for x in X if x["dec"]]
for lab, S, y in (("P(margin>=4 | fav wins decision)", FD, [x["marg"] >= 4 for x in FD]),
                  ("P(fav wins | decision)", DD, [x["marg"] > 0 for x in DD]),
                  ("P(fav covers -3.5), all fights", X, [(x["favwin"] and not x["dec"]) or (x["dec"] and x["marg"] >= 4) for x in X])):
    b0, s0, l0 = fit([[1, lg(x["pf"])] for x in S], y); b1, s1, l1 = fit([[1, lg(x["pf"]), lg(x["q"])] for x in S], y)
    print(f"\n{lab}: n={len(S)}\n  price only:        b = {b0.round(3).tolist()}, log loss {l0:.4f}\n  price + logit(q):  b = {b1.round(3).tolist()}, q coef SE {s1[2]:.3f}, z {b1[2]/s1[2]:.2f}, log loss {l1:.4f}")
    # walk-forward by year: fit on earlier years, score the year
    yrs = sorted({x["date"][:4] for x in S}); wins = 0; tot = 0
    for yv in yrs[1:]:
        tr = [i for i, x in enumerate(S) if x["date"][:4] < yv]; te = [i for i, x in enumerate(S) if x["date"][:4] == yv]
        if len(tr) < 100 or len(te) < 20: continue
        ya = np.array(y, float)
        bA = fit([[1, lg(S[i]["pf"])] for i in tr], ya[tr])[0]; bB = fit([[1, lg(S[i]["pf"]), lg(S[i]["q"])] for i in tr], ya[tr])[0]
        def ll(bb, cols):
            Xm = np.array([cols(S[i]) for i in te]); pr = 1 / (1 + np.exp(-Xm @ bb)); yy = ya[te]; return -np.mean(yy * np.log(pr) + (1 - yy) * np.log(1 - pr))
        a_ = ll(bA, lambda x: [1, lg(x["pf"])]); b_ = ll(bB, lambda x: [1, lg(x["pf"]), lg(x["q"])]); tot += 1; wins += b_ < a_
        print(f"  walk-forward {yv}: n={len(te)}  price-only {a_:.4f}  +q {b_:.4f}  {'+q better' if b_ < a_ else 'price better'}")
    print(f"  +q better in {wins} of {tot} test years")
# Hooker vs Ortega, pre-fight
last = max(date.values()); assert last < "2026-11-21", "cache includes the card: use pre-fight snapshots"
HK, BO = tuple(cum[canon("Dan Hooker")]), tuple(cum[canon("Brian Ortega")]); hk, bo = rate(HK), rate(BO)
print(f"\nCSV cache ends {last} (before the card), so pre-fight = all cached rounds")
print(f"Hooker round-win rate {hk:.3f} (won {HK[0]:.1f} of {HK[1]} UFC rounds), Ortega {bo:.3f} (won {BO[0]:.1f} of {BO[1]}); matchup q {log5(hk, bo):.3f}")
qs = [x["q"] for x in X]; print(f"q percentile of Hooker-Ortega among {len(X)} historical 3R favorites: {sum(q <= log5(hk, bo) for q in qs) / len(qs) * 100:.0f}th")

qh = log5(hk, bo); pf = 0.659   # Hooker consensus no-vig at the Nov 20 18:13Z pull (spreads_v0 output, card table)
for lab, S, y in (("P(margin>=4 | fav wins decision)", FD, [x["marg"] >= 4 for x in FD]), ("P(fav wins | decision)", DD, [x["marg"] > 0 for x in DD])):
    b0 = fit([[1, lg(x["pf"])] for x in S], y)[0]; b1 = fit([[1, lg(x["pf"]), lg(x["q"])] for x in S], y)[0]
    print(f"Hooker {lab}: price only {sg(b0[0] + b0[1]*lg(pf)):.3f}; price + q {sg(b1[0] + b1[1]*lg(pf) + b1[2]*lg(qh)):.3f}")
# v0 spread with the margin term swapped to price + q (sheet finish / decision split unchanged: 36.9% finish, 31.2% decision win)
bM = fit([[1, lg(x["pf"]), lg(x["q"])] for x in FD], [x["marg"] >= 4 for x in FD])[0]; pm = sg(bM[0] + bM[1]*lg(pf) + bM[2]*lg(qh))
print(f"Hooker -3.5 with the round-dominance margin term: 0.369 + 0.312 x {pm:.3f} = {0.369 + 0.312*pm:.3f}")
# what a pure round model would say: Hooker's per-round q in every round, rounds independent, judges unanimous
pw = 3*qh**2 - 2*qh**3; print(f"Independent-rounds model: P(Hooker wins decision | decision) {pw:.3f}, P(sweep | Hooker dec win) {qh**3/pw:.3f}")
emp = [x for x in FD]; print(f"History: P(3-0 margin>=4 | fav dec win) {sum(x['marg']>=4 for x in emp)/len(emp):.3f}: rounds within a fight are correlated, so independence understates sweeps")
# frozen coefficients for the tracker (registered Nov 24 2026; never re-fit after a result without a new registration)
FR = {"registered": "2026-11-24", "K_pseudo_rounds": K, "min_rounds": 3, "v0": {}, "v1": {}, "q_on_price": None}
for sched in (3, 5):
    allf = [r for r in X if r["dec"] and r["marg"] > 0] if sched == 3 else None
for k in (2, 3, 4, 5, 6, 7):
    yk = [x["marg"] >= k for x in FD]
    FR["v1"][f"3_{k}"] = fit([[1, lg(x["pf"]), lg(x["q"])] for x in FD], yk)[0].tolist()
# v0 coefficients exactly as spreads_v0 fits them: every fav decision win since 2022 with 3 cards and a close price (no round-rate filter)
V0R = []
for p_ in sorted(glob.glob("form/data/events/*.json")):
    ev_ = json.load(open(p_)); sl_ = os.path.basename(p_)[:-5]
    for f in ev_["fights"]:
        c = (f.get("odds") or {}).get("close"); r_ = f.get("result") or {}
        if not isinstance(c, dict) or c.get("p") is None or r_.get("kind") != "win" or not f.get("sched") or not r_.get("method", "").startswith("Decision"): continue
        fav = "a" if c["p"] >= 0.5 else "b"; cc = cards.get((sl_, f["n"]))
        if r_["winner"] != fav or not cc or len(cc) != 3: continue
        an = f["a"]["name"]; s_ = 0; ok = True
        for a_, b_, x_, y_ in cc:
            if a_ == an: s_ += x_ - y_
            elif b_ == an: s_ += y_ - x_
            else: ok = False
        if ok: V0R.append((f["sched"], max(c["p"], 1 - c["p"]), s_ if fav == "a" else -s_))
FR["v0"] = {}
for sched in (3, 5):
    S_ = [r for r in V0R if r[0] == sched]
    for k in (2, 3, 4, 5, 6, 7):
        FR["v0"][f"{sched}_{k}"] = fit([[1, lg(r[1])] for r in S_], [r[2] >= k for r in S_])[0].tolist()
    print(f"v0 frozen from {len(S_)} {sched}R fav decision wins (spreads_v0 method); P(m>=4) at p=.66: {sg(FR['v0'][f'{sched}_4'][0] + FR['v0'][f'{sched}_4'][1]*lg(.66)):.3f}")
A = np.c_[np.ones(len(X)), [lg(x["pf"]) for x in X]]; FR["q_on_price"] = np.linalg.lstsq(A, np.array([lg(x["q"]) for x in X]), rcond=None)[0].tolist()
FR["q_resid_sd"] = float(np.std(np.array([lg(x["q"]) for x in X]) - A @ np.array(FR["q_on_price"])))
print("\nFROZEN", json.dumps(FR))
