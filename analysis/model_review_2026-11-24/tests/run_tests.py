"""Model review registered tests T1(b), T3, T4, T5, T6 history. Bars: PREREG_model_review_2026-11-24.md; reading: tests/RUN_NOTES.md.
Run from a szerillo/ufc-projections checkout at origin/main: python3 run_tests.py <UFCStats cache dir> <close.json>."""
import json, glob, os, sys, math, collections, datetime as dt
import numpy as np
sys.path.insert(0, "scripts"); import build_embed_metrics as B; import fighter_names as FN
D, CLOSE = sys.argv[1], sys.argv[2]; fold = B.fold
alias = {fold(k): v for k, v in json.load(open("form/data/name_aliases.json")).items() if not k.startswith("_")}
canon = lambda s: fold(alias.get(fold(s), s))
imp = lambda o: (-o / (-o + 100)) if o < 0 else 100 / (o + 100)
def power(a, b):
    ia, ib = imp(a), imp(b); lo, hi = 1.0, 3.0
    for _ in range(60):
        k = (lo + hi) / 2; lo, hi = (k, hi) if ia ** k + ib ** k > 1 else (lo, k)
    return ia ** k
mult = lambda a, b: imp(a) / (imp(a) + imp(b))
lg = lambda p: math.log(p / (1 - p)); sg = lambda x: 1 / (1 + np.exp(-x))
def ll(p, y): p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6); y = np.asarray(y, float); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
def fit(M, y, it=60):
    b = np.zeros(M.shape[1])
    for _ in range(it):
        p = sg(M @ b); W = p * (1 - p); H = M.T @ (M * W[:, None]) + 1e-9 * np.eye(len(b)); b += np.linalg.solve(H, M.T @ (y - p))
    return b, np.sqrt(np.diag(np.linalg.inv(H)))
def pl_towin(price, won): return (1.0 if won else price / 100) if price < 0 else (price / 100 if won else -1.0)
dob = {}
for p in glob.glob("form/data/fighters/*.json"):
    f = json.load(open(p)); b_ = (f.get("bio") or {}).get("dob")
    if b_: dob[canon(f["name"])] = b_
X = []; EV = {}
for p in sorted(glob.glob("form/data/events/202[2-6]-*.json")):
    ev = json.load(open(p)); d_ = os.path.basename(p)[:10]; EV.setdefault(d_, []).append(ev)
    for f in ev["fights"]:
        c = (f.get("odds") or {}).get("close"); o = (f.get("odds") or {}).get("open"); r_ = f.get("result") or {}
        if not isinstance(c, dict) or c.get("p") is None or r_.get("kind") != "win" or not 0.01 < c["p"] < 0.99: continue
        if not (c.get("ma") and c.get("mb")): continue
        A, Bn = canon(f["a"]["name"]), canon(f["b"]["name"])
        age = lambda n: (dt.date.fromisoformat(d_) - dt.date.fromisoformat(dob[n])).days / 365.25 if n in dob else None
        X.append(dict(year=int(d_[:4]), pm=c["p"], pw=power(c["ma"], c["mb"]), ma=c["ma"], mb=c["mb"], y=1.0 if r_["winner"] == "a" else 0.0,
                      women=(f.get("wc") or "").startswith("Women"), open=(o or {}).get("p") if isinstance(o, dict) else None,
                      agea=age(A), ageb=age(Bn)))
YRS = [2022, 2023, 2024, 2025, 2026]
print(f"archive sample: {len(X)} bouts with close price pair + win result")

print("\n## T1 (b): bot pre-start US close set, best-price pair, power vs multiplicative de-vig")
CL = [c for c in json.load(open(CLOSE)) if c.get("best_a") is not None and c.get("best_b") is not None]
rows = []
for c in CL:
    d0 = dt.date.fromisoformat(c["sched"][:10]); hit = None
    for dd in (d0, d0 - dt.timedelta(days=1)):
        for ev in EV.get(dd.isoformat(), []):
            for f in ev["fights"]:
                r_ = f.get("result") or {}
                if r_.get("kind") != "win": continue
                if FN.name_match(f["a"]["name"], c["a"]) and FN.name_match(f["b"]["name"], c["b"]): hit = 1.0 if r_["winner"] == "a" else 0.0
                elif FN.name_match(f["b"]["name"], c["a"]) and FN.name_match(f["a"]["name"], c["b"]): hit = 1.0 if r_["winner"] == "b" else 0.0
    if hit is not None: rows.append((mult(c["best_a"], c["best_b"]), power(c["best_a"], c["best_b"]), hit))
m_, p_, y_ = map(np.array, zip(*rows))
d1 = ll(p_, y_) - ll(m_, y_)
print(f"bouts matched to a result: {len(rows)} of {len(CL)}; log loss G_mult {ll(m_, y_):.5f}  G_power {ll(p_, y_):.5f}  diff {d1:+.5f}")
print(f"T1 bar part 2 (power at or below mult on (b)): {'MET' if d1 <= 0 else 'NOT MET'}")
fav = np.maximum(p_, 1 - p_) >= .7; fy = np.where(p_ >= .5, y_, 1 - y_)
print(f"(b) favorites 70%+ (power): n={fav.sum()}  won {fy[fav].mean() * 100:.1f}  priced mult {np.maximum(m_, 1 - m_)[fav].mean() * 100:.1f} power {np.maximum(p_, 1 - p_)[fav].mean() * 100:.1f}  (part 3 is pooled with forward cards: PENDING)")
print("T1 parts (a) and (c): PENDING forward cards from 2026-12-05. T1 overall: PENDING.")

print("\n## T3: drifting-dog veto (risk 1u at the dog's close median price)")
def dogrow(x):
    if x["open"] is None: return None
    a_is_dog = x["pm"] < 0.5; cd = x["pm"] if a_is_dog else 1 - x["pm"]; od = x["open"] if a_is_dog else 1 - x["open"]
    price = x["ma"] if a_is_dog else x["mb"]; won = (x["y"] == 1) if a_is_dog else (x["y"] == 0)
    return dict(year=x["year"], drift=(od - cd) >= 0.03, u=pl_towin(price, won) if price > 0 else (1.0 if won else price / 100), risk=1.0 if price > 0 else -price / 100, won=won)
DG = [r for r in map(dogrow, X) if r]
lower = 0; higher = 0
for yr in YRS + ["pooled"]:
    S = [r for r in DG if yr == "pooled" or r["year"] == yr]
    a = [r for r in S if r["drift"]]; b = [r for r in S if not r["drift"]]
    ra = sum(r["u"] for r in a) / sum(r["risk"] for r in a); rb = sum(r["u"] for r in b) / sum(r["risk"] for r in b)
    if yr != "pooled": lower += ra < rb; higher += ra > rb
    print(f"{yr}: drifting n={len(a):>3} won {sum(r['won'] for r in a):>3} ROI {ra * 100:+6.1f}% | other dogs n={len(b):>3} won {sum(r['won'] for r in b):>3} ROI {rb * 100:+6.1f}%")
pa_ = [r for r in DG if r["drift"]]; pb_ = [r for r in DG if not r["drift"]]
pooled_lower = sum(r["u"] for r in pa_) / sum(r["risk"] for r in pa_) < sum(r["u"] for r in pb_) / sum(r["risk"] for r in pb_)
v3 = "KEEP" if lower >= 4 and pooled_lower else "DROP" if higher >= 4 else "KEEP + shadow log (neither bar met)"
print(f"drifting lower in {lower}/5 years, higher in {higher}/5, pooled lower: {pooled_lower} -> T3 {v3}")

print("\n## T4: women term (y = favorite won ~ logit(power fav p) + women)")
def favrow(x): pf = max(x["pw"], 1 - x["pw"]); return lg(pf), (x["y"] if x["pw"] >= .5 else 1 - x["y"]), float(x["women"])
fav_sign = 0; dog_sign = 0
for yr in YRS:
    R = [favrow(x) for x in X if x["year"] == yr]; L, y, w = map(np.array, zip(*R))
    b, s = fit(np.c_[np.ones(len(y)), L, w], y); fav_sign += b[2] > 0; dog_sign += b[2] < 0
    print(f"{yr}: n={len(y)} women n={int(w.sum())}  women coef {b[2]:+.3f} (SE {s[2]:.3f})")
out = 0
for yr in YRS[1:]:
    tr = [favrow(x) for x in X if x["year"] < yr]; L, y, w = map(np.array, zip(*tr)); b, _ = fit(np.c_[np.ones(len(y)), L, w], y)
    te = [favrow(x) for x in X if x["year"] == yr and x["women"]]; Lt = np.array([r[0] for r in te])
    shift = float(np.mean(sg(b[0] + b[1] * Lt + b[2]) - sg(b[0] + b[1] * Lt))) * 100   # favorite up = dog down, points
    out += not (2 <= shift <= 6); print(f"walk-forward {yr}: women bouts {len(te)}  fitted dog shift {-shift:+.2f} pts (sheet uses -4)")
v4 = "DROP" if dog_sign >= 3 else ("KEEP -4" if fav_sign >= 4 else "KEEP -4 (sign bar not met, drop bar not met)")
if out >= 3 and not v4.startswith("DROP"): v4 += "; RE-FIT size flagged (outside 2-6 pts in %d of 4 years)" % out
print(f"favors favorites in {fav_sign}/5 years, dogs in {dog_sign}/5; size outside 2-6 in {out}/4 -> T4 {v4}")

print("\n## T5: age difference on top of the power close")
AG = [x for x in X if x["agea"] and x["ageb"]]; signs = []
for yr in YRS:
    S = [x for x in AG if x["year"] == yr]; y = np.array([x["y"] for x in S]); L = np.array([lg(x["pw"]) for x in S]); v = np.array([x["agea"] - x["ageb"] for x in S])
    b, s = fit(np.c_[np.ones(len(y)), L, v], y); signs.append(np.sign(b[2])); print(f"{yr}: n={len(y)} age coef {b[2]:+.4f} (SE {s[2]:.4f})")
better = 0
for yr in YRS[1:]:
    tr = [x for x in AG if x["year"] < yr]; te = [x for x in AG if x["year"] == yr]
    M = lambda S, k: np.c_[np.ones(len(S)), [lg(x["pw"]) for x in S]] if k == 0 else np.c_[np.ones(len(S)), [lg(x["pw"]) for x in S], [x["agea"] - x["ageb"] for x in S]]
    yt = np.array([x["y"] for x in tr]); ye = np.array([x["y"] for x in te])
    b0, _ = fit(M(tr, 0), yt); b1, _ = fit(M(tr, 1), yt); l0 = ll(sg(M(te, 0) @ b0), ye); l1 = ll(sg(M(te, 1) @ b1), ye)
    better += l1 < l0; print(f"walk-forward {yr}: log loss price-only {l0:.5f}  + age {l1:.5f}  {'age better' if l1 < l0 else 'price-only better'}")
same = len(set(signs)) == 1
print(f"same sign 5/5: {same}; walk-forward better {better}/4 -> T5 {'ADOPT as proposal' if same and better == 4 else 'DROP'}")

print("\n## T6: 80%+ favorites at the close median price (archive, power close 0.80+), four sizings")
F = []
for x in X:
    if max(x["pw"], 1 - x["pw"]) < .8: continue
    price = x["ma"] if x["pw"] >= .5 else x["mb"]; won = (x["y"] == 1) if x["pw"] >= .5 else (x["y"] == 0)
    if price >= 0: continue
    F.append(dict(year=x["year"], price=price, won=won))
def size(r, k):
    risk_tw = -r["price"] / 100                       # risk to win 1u
    if k == "A": risk = risk_tw
    elif k == "B": risk = min(risk_tw, 2.0)
    elif k == "C": risk = risk_tw if r["price"] >= -500 else 0.0
    else: risk = 1.0
    win = risk * 100 / -r["price"]; return (win if r["won"] else -risk), risk
labs = {"A": "to-win 1u (current)", "B": "risk cap 2u", "C": "skip shorter than -500", "D": "flat risk 1u"}
print(f"bouts: {len(F)}, record {sum(r['won'] for r in F)}-{sum(not r['won'] for r in F)}, mean price {np.mean([r['price'] for r in F]):.0f}")
for k in "ABCD":
    res = [size(r, k) for r in F]; u = sum(a for a, _ in res); rk = sum(b for _, b in res); n = sum(b > 0 for _, b in res)
    worst = min(a for a, _ in res); yrs = {yr: sum(size(r, k)[0] for r in F if r["year"] == yr) for yr in YRS}
    print(f"{k} {labs[k]:<24} bets {n:>3}  units {u:+7.2f}  risked {rk:7.2f}  ROI {u / rk * 100:+5.1f}%  worst loss {worst:+.2f}  by year " + " ".join(f"{y_}:{v:+.2f}" for y_, v in yrs.items()))
for lo, hi in ((-500, -400), (-700, -500), (-1000, -700), (-99999, -1000)):
    S = [r for r in F if lo <= r["price"] < hi] if hi != -400 else [r for r in F if r["price"] >= -500]
    if not S: continue
    be = np.mean([imp(r["price"]) for r in S]); print(f"  price band {'-500 or longer' if hi == -400 else f'{hi} to {lo}'}: n={len(S)} won {np.mean([r['won'] for r in S]) * 100:.1f}% vs break-even {be * 100:.1f}%")
SH = [(-1000, False), (-900, True)]
print("sheet 80%+ recs on the 10 graded cards: Hasan -1000 lost, Jauregui -900 won -> " + "; ".join(f"{labs[k]} {sum(size(dict(price=p, won=w), k)[0] for p, w in SH):+.2f}u" for k in "ABCD"))
