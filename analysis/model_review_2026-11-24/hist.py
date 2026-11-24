"""Model review (Nov 24 2026), part C: does the closing price leave signal on the table by segment / feature?
Run from a szerillo/ufc-projections checkout at origin/main with the UFCStats cache dir as argv[1]; out to stdout.
Sample: every 2022-2026 UFC bout in form/data/events with a close price and a win result (draws/NC excluded).
Per feature: logistic y(a wins) ~ logit(close pa) + feature (a minus b); coefficient z and walk-forward log loss by year
(train on all earlier years, test on the year). Segments: calibration-in-the-large of the close (won minus priced)."""
import csv, json, re, sys, math, glob, os, collections, datetime as dt
import numpy as np
sys.path.insert(0, "scripts"); import build_embed_metrics as B
D = sys.argv[1]; fold = B.fold
alias = {fold(k): v for k, v in json.load(open("form/data/name_aliases.json")).items() if not k.startswith("_")}
canon = lambda s: fold(alias.get(fold(s), s))
date = {r["EVENT"].strip(): dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").date().isoformat() for r in csv.DictReader(open(f"{D}/ufc_event_details.csv", encoding="utf-8"))}
res = {(r["EVENT"].strip(), r["BOUT"].strip()): r for r in csv.DictReader(open(f"{D}/ufc_fight_results.csv", encoding="utf-8"))}
rows = collections.defaultdict(dict)
for r in csv.DictReader(open(f"{D}/ufc_fight_stats.csv", encoding="utf-8")):
    m = re.match(r"Round (\d+)", r["ROUND"] or "")
    if m: rows[(r["EVENT"].strip(), r["BOUT"].strip())][(int(m.group(1)), r["FIGHTER"].strip())] = r
def of(s):
    m = re.match(r"(\d+) of (\d+)", s or ""); return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
# chronological pass: rounds won (site rule), rounds, TD landed, sig strikes landed / absorbed, last fight date, UFC fights
cum = collections.defaultdict(lambda: dict(w=0.0, r=0, td=0, sl=0, sa=0, last=None, n=0)); pre = {}
for (e, b), r in sorted(res.items(), key=lambda kv: date.get(kv[0][0], "")):
    d_ = date.get(e); byr = rows.get((e, b)); names = [x.strip() for x in b.split(" vs. ")]
    if not d_ or len(names) != 2: continue
    for n_ in names: pre[(d_, canon(n_))] = dict(cum[canon(n_)])
    if byr:
        decided = r["OUTCOME"] in ("W/L", "L/W"); last_r = int(r["ROUND"]); winner = names[0] if r["OUTCOME"] == "W/L" else names[1] if decided else None
        for rd in range(1, min(last_r, 5) + 1):
            x, y = byr.get((rd, names[0])), byr.get((rd, names[1]))
            if not x or not y: continue
            if rd == last_r and decided and "Decision" not in r["METHOD"]: wa = 1.0 if winner == names[0] else 0.0
            else:
                sc = B.rscore(x) - B.rscore(y); wa = 1.0 if sc > 0 else 0.0 if sc < 0 else 0.5
            for me, op, w in ((x, y, wa), (y, x, 1 - wa)):
                c = cum[canon(me["FIGHTER"].strip())]; c["w"] += w; c["r"] += 1
                c["td"] += of(me.get("TD"))[0]; c["sl"] += of(me.get("SIG.STR."))[0]; c["sa"] += of(op.get("SIG.STR."))[0]
    for n_ in names: cum[canon(n_)]["last"] = d_; cum[canon(n_)]["n"] += 1
K = 5.0
rate = lambda t: None if t["r"] < 3 else (t["w"] + 0.5 * K) / (t["r"] + K)
lg = lambda p: math.log(p / (1 - p)); sg = lambda x: 1 / (1 + np.exp(-x))
dob = {}
for p in glob.glob("form/data/fighters/*.json"):
    f = json.load(open(p)); b_ = (f.get("bio") or {}).get("dob")
    if b_: dob[canon(f["name"])] = b_
X = []
for p in sorted(glob.glob("form/data/events/202[2-6]-*.json")):
    ev = json.load(open(p)); d_ = os.path.basename(p)[:10]
    for f in ev["fights"]:
        c = (f.get("odds") or {}).get("close"); r_ = f.get("result") or {}
        if not isinstance(c, dict) or c.get("p") is None or r_.get("kind") != "win" or not 0.01 < c["p"] < 0.99: continue
        A, Bn = canon(f["a"]["name"]), canon(f["b"]["name"]); ta, tb = pre.get((d_, A)), pre.get((d_, Bn))
        if ta is None or tb is None: continue
        def age(n):
            return (dt.date.fromisoformat(d_) - dt.date.fromisoformat(dob[n])).days / 365.25 if n in dob else None
        def lay(t): return (dt.date.fromisoformat(d_) - dt.date.fromisoformat(t["last"])).days if t["last"] else None
        pw = None
        if c.get("ma") and c.get("mb"):
            ia, ib = [(-o / (-o + 100)) if o < 0 else 100 / (o + 100) for o in (c["ma"], c["mb"])]
            lo_, hi_ = 1.0, 3.0
            for _ in range(60):
                k_ = (lo_ + hi_) / 2; lo_, hi_ = (k_, hi_) if ia ** k_ + ib ** k_ > 1 else (lo_, k_)
            pw = ia ** k_
        X.append(dict(year=int(d_[:4]), pa=c["p"], pw=pw, y=1.0 if r_["winner"] == "a" else 0.0, sched=f.get("sched"), wc=f.get("wc") or "",
                      women=(f.get("wc") or "").startswith("Women"), ra=rate(ta), rb=rate(tb), na=ta["n"], nb=tb["n"],
                      tda=ta["td"] / ta["r"] if ta["r"] >= 3 else None, tdb=tb["td"] / tb["r"] if tb["r"] >= 3 else None,
                      sda=(ta["sl"] - ta["sa"]) / ta["r"] if ta["r"] >= 3 else None, sdb=(tb["sl"] - tb["sa"]) / tb["r"] if tb["r"] >= 3 else None,
                      agea=age(A), ageb=age(Bn), laya=lay(ta), layb=lay(tb), dec=str(r_.get("method", "")).startswith("Decision")))
print(f"sample: {len(X)} bouts 2022-2026 with close + win result; years {collections.Counter(x['year'] for x in X)}")
def ll(p, y): p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
def fit(M, y, it=50):
    b = np.zeros(M.shape[1])
    for _ in range(it):
        p = sg(M @ b); W = p * (1 - p); H = M.T @ (M * W[:, None]) + 1e-9 * np.eye(len(b)); b += np.linalg.solve(H, M.T @ (y - p))
    return b, np.sqrt(np.diag(np.linalg.inv(H)))
FEAT = {
 "round-win q (log5 of rates, logit)": lambda x: lg(x["ra"] * (1 - x["rb"]) / (x["ra"] * (1 - x["rb"]) + (1 - x["ra"]) * x["rb"])) if x["ra"] and x["rb"] else None,
 "age diff (years, a minus b)": lambda x: x["agea"] - x["ageb"] if x["agea"] and x["ageb"] else None,
 "age 35+ (a) minus (b)": lambda x: (x["agea"] >= 35) - (x["ageb"] >= 35) if x["agea"] and x["ageb"] else None,
 "layoff 365+ days (a) minus (b)": lambda x: (x["laya"] is not None and x["laya"] >= 365) - (x["layb"] is not None and x["layb"] >= 365) if x["na"] and x["nb"] else None,
 "TD landed per round diff": lambda x: x["tda"] - x["tdb"] if x["tda"] is not None and x["tdb"] is not None else None,
 "sig strike diff per round": lambda x: x["sda"] - x["sdb"] if x["sda"] is not None and x["sdb"] is not None else None,
 "UFC debut (a) minus (b)": lambda x: (x["na"] == 0) - (x["nb"] == 0),
}
print("\n## Features on top of the close (logistic, y = a wins)")
for name, fn in FEAT.items():
    S = [(x, fn(x)) for x in X]; S = [(x, v) for x, v in S if v is not None]
    if len(S) < 200: print(f"{name}: n={len(S)} too few"); continue
    y = np.array([x["y"] for x, _ in S]); L = np.array([lg(x["pa"]) for x, _ in S]); v = np.array([v for _, v in S], float)
    b0, _ = fit(np.c_[np.ones(len(y)), L], y); b1, s1 = fit(np.c_[np.ones(len(y)), L, v], y)
    wins = 0; tests = 0; det = []
    for yr in (2023, 2024, 2025, 2026):
        tr = np.array([x["year"] < yr for x, _ in S]); te = np.array([x["year"] == yr for x, _ in S])
        if tr.sum() < 100 or te.sum() < 50: continue
        a0, _ = fit(np.c_[np.ones(tr.sum()), L[tr]], y[tr]); a1, _ = fit(np.c_[np.ones(tr.sum()), L[tr], v[tr]], y[tr])
        l0 = ll(sg(np.c_[np.ones(te.sum()), L[te]] @ a0), y[te]); l1 = ll(sg(np.c_[np.ones(te.sum()), L[te], v[te]] @ a1), y[te])
        tests += 1; wins += l1 < l0; det.append(f"{yr}:{l0 - l1:+.4f}")
    print(f"{name}: n={len(S)}  coef {b1[2]:+.4f} (SE {s1[2]:.4f}, z {b1[2] / s1[2]:+.2f})  close slope {b1[1]:.3f}  walk-forward better {wins}/{tests}  [{' '.join(det)}]")
print("\n## Close calibration by segment (favorite side): priced vs won, z = (won - priced)/sd")
def seg(lab, S):
    if not S: return
    pf = np.array([max(x["pa"], 1 - x["pa"]) for x in S]); w = np.array([x["y"] if x["pa"] >= .5 else 1 - x["y"] for x in S])
    z = (w.sum() - pf.sum()) / math.sqrt((pf * (1 - pf)).sum())
    print(f"{lab:<34} n={len(S):>4}  priced {pf.mean() * 100:5.1f}  won {w.mean() * 100:5.1f}  z {z:+.2f}")
seg("all", X)
for lo, hi in ((.5, .6), (.6, .7), (.7, .8), (.8, .9), (.9, 1.0)): seg(f"fav {int(lo * 100)}-{int(hi * 100)}", [x for x in X if lo <= max(x["pa"], 1 - x["pa"]) < hi])
seg("women", [x for x in X if x["women"]]); seg("men", [x for x in X if not x["women"]])
seg("5 rounds", [x for x in X if x["sched"] == 5])
for w in ("Flyweight", "Bantamweight", "Featherweight", "Lightweight", "Welterweight", "Middleweight", "Light Heavyweight", "Heavyweight"):
    seg(w, [x for x in X if x["wc"] == w])
fa = lambda x, k: x[k + ("a" if x["pa"] >= .5 else "b")]; da = lambda x, k: x[k + ("b" if x["pa"] >= .5 else "a")]
seg("fav is 35+", [x for x in X if fa(x, "age") and fa(x, "age") >= 35]); seg("dog is 35+", [x for x in X if da(x, "age") and da(x, "age") >= 35])
seg("fav off 365+ layoff", [x for x in X if fa(x, "lay") and fa(x, "lay") >= 365]); seg("dog off 365+ layoff", [x for x in X if da(x, "lay") and da(x, "lay") >= 365])
seg("fav UFC debut", [x for x in X if fa(x, "n") == 0]); seg("dog UFC debut", [x for x in X if da(x, "n") == 0])
seg("fav wrestler (TD/rd >= 1.0)", [x for x in X if fa(x, "td") is not None and fa(x, "td") >= 1.0])
seg("dog wrestler (TD/rd >= 1.0)", [x for x in X if da(x, "td") is not None and da(x, "td") >= 1.0])
seg("wrestler fav vs striker dog", [x for x in X if fa(x, "td") is not None and da(x, "td") is not None and fa(x, "td") >= 1.0 and da(x, "td") < 0.3])
seg("striker fav vs wrestler dog", [x for x in X if fa(x, "td") is not None and da(x, "td") is not None and fa(x, "td") < 0.3 and da(x, "td") >= 1.0])

print("\n## Same, close de-vigged by the power method from the median price pair (multiplicative de-vig shades longshots up)")
Xp = [dict(x, pa=x["pw"], pa_m=x["pa"]) for x in X if x["pw"]]
seg("all (power)", Xp)
for lo, hi in ((.5, .6), (.6, .7), (.7, .8), (.8, .9)): seg(f"fav {int(lo * 100)}-{int(hi * 100)} (power)", [x for x in Xp if lo <= max(x["pa"], 1 - x["pa"]) < hi])
by = collections.defaultdict(list)
for x in Xp: by[x["year"]].append(x)
for yr in sorted(by): seg(f"{yr} (power)", by[yr])
y = np.array([x["y"] for x in Xp]); L = np.array([lg(x["pa"]) for x in Xp]); b, s_ = fit(np.c_[np.ones(len(y)), L], y)
print(f"slope on logit(power close): {b[1]:.3f} (SE {s_[1]:.3f}); 1.0 = calibrated")
seg("women (power)", [x for x in Xp if x["women"]]); seg("men (power)", [x for x in Xp if not x["women"]])
seg("5 rounds (power)", [x for x in Xp if x["sched"] == 5])
seg("dog is 35+ (power)", [x for x in Xp if da(x, "age") and da(x, "age") >= 35]); seg("dog UFC debut (power)", [x for x in Xp if da(x, "n") == 0])
seg("dog off 365+ layoff (power)", [x for x in Xp if da(x, "lay") and da(x, "lay") >= 365])
for yr in sorted(by): seg(f"fav 80+ {yr} (power)", [x for x in by[yr] if max(x["pa"], 1 - x["pa"]) >= .8])
def llset(key):
    y = np.array([x["y"] for x in Xp]); p = np.array([x[key] for x in Xp]); return ll(p, y)
print(f"log loss, same {len(Xp)} bouts: multiplicative close {llset('pa_m'):.4f}  power close {llset('pa'):.4f}")
yv = np.array([x["y"] for x in Xp]); pm = np.clip(np.array([x["pa_m"] for x in Xp]), 1e-6, 1 - 1e-6); pp = np.clip(np.array([x["pa"] for x in Xp]), 1e-6, 1 - 1e-6)
dl = -(yv * np.log(pp) + (1 - yv) * np.log(1 - pp)) + (yv * np.log(pm) + (1 - yv) * np.log(1 - pm))
print(f"power minus multiplicative log loss per bout: {dl.mean():+.5f} (SE {dl.std() / math.sqrt(len(dl)):.5f}, z {dl.mean() / (dl.std() / math.sqrt(len(dl))):+.2f}); better in years: " + " ".join(f"{yr}:{dl[np.array([x['year'] == yr for x in Xp])].mean():+.5f}" for yr in sorted(by)))
