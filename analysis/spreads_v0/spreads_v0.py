"""UFC point-spread pricing v0 (Nov 20 2026). Run from a szerillo/ufc-projections checkout at main 19dd47f0:
   python3 -I analysis/spreads_v0/spreads_v0.py > analysis/spreads_v0/spreads_v0_out.txt
Inputs (all committed in the repo): form/data/judges.json (each judge's final card per decision),
form/data/events/*.json (results, closing no-vig p), form/data/fighters/*.json (per-fight sig strikes),
data/pending/fn_prochazka_stirling_projections.json (Sean's Nov 19 23:42Z export), data/fn_prochazka_stirling_odds.json.
Model: P(fav covers -s) = P(fav wins by finish) + P(fav wins decision) * P(combined 3-judge margin > s | fav wins decision),
the last term a logistic fit on the closing no-vig fav p (and, variant B, the pre-fight career strike-differential gap)."""
import json, glob, collections, re, math, os, sys
import numpy as np
sys.path.insert(0, "scripts"); import fighter_names as FN
lg = lambda p: math.log(p / (1 - p)); sg = lambda x: 1 / (1 + math.exp(-x))
def ml(p): return f"-{round(100*p/(1-p))}" if p >= 0.5 else f"+{round(100*(1-p)/p)}"
def imp(o): return 100/(o+100) if o > 0 else -o/(-o+100)
def fit(X, y):
    X = np.asarray(X, float); y = np.asarray(y, float); b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1/(1+np.exp(-X@b)); W = p*(1-p)+1e-9; H = X.T@(X*W[:, None]); b += np.linalg.solve(H+1e-6*np.eye(len(b)), X.T@(y-p))
    return b, np.sqrt(np.diag(np.linalg.inv(H)))
J = json.load(open("form/data/judges.json")); cards = collections.defaultdict(list)
for v in J.values():
    for r in v["rows"]:
        m = re.match(r"(\d+)-(\d+)$", r[5])
        if m: cards[(r[1], r[2])].append((r[3], r[4], int(m.group(1)), int(m.group(2))))
FC = {}
def presd(slug, date):
    if slug not in FC:
        p = f"form/data/fighters/{slug}.json"; FC[slug] = json.load(open(p)) if slug and os.path.exists(p) else None
    d = FC[slug]
    if not d: return None
    sl = sa = sec = 0
    for z in d["fights"]:
        if z["d"] < date and z.get("s") and z.get("secs"): sl += z["s"][0]; sa += z["s"][2]; sec += z["secs"]
    return (sl - sa) / (sec / 60) if sec >= 900 else None
R = []
for p in sorted(glob.glob("form/data/events/*.json")):
    ev = json.load(open(p)); slug = os.path.basename(p)[:-5]; date = slug[:10]
    for f in ev["fights"]:
        c = (f.get("odds") or {}).get("close"); res = f.get("result") or {}
        if not isinstance(c, dict) or c.get("p") is None or res.get("kind") != "win" or not f.get("sched"): continue
        pc = c["p"]; fav = "a" if pc >= 0.5 else "b"; dec = res.get("method", "").startswith("Decision"); marg = None
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
        fa, fb = (f["a"], f["b"]) if fav == "a" else (f["b"], f["a"])
        ga, gb = presd(fa.get("slug"), date), presd(fb.get("slug"), date)
        R.append(dict(date=date, pf=max(pc, 1-pc), sched=f["sched"], favwin=res["winner"] == fav, dec=dec, marg=marg,
                      gap=None if ga is None or gb is None else ga - gb))
print(f"graded fights: {len(R)} ({min(r['date'] for r in R)} to {max(r['date'] for r in R)}); 3R {sum(r['sched']==3 for r in R)}, 5R {sum(r['sched']==5 for r in R)}")
R3 = [r for r in R if r["sched"] == 3]
def cover(r, s): return 1 if (r["favwin"] and not r["dec"]) or (r["dec"] and r["marg"] > s) else 0
print("\nA. Base rates, 3R, by closing fav no-vig p")
print("bucket       n  favwin fav_fin  dec   fav_dec P(m>=4|fav dec) cover-2.5 cover-3.5 cover-4.5")
for lo, hi in ((.5, .6), (.6, .65), (.65, .7), (.7, .75), (.75, .8), (.8, 1)):
    S = [r for r in R3 if lo <= r["pf"] < hi]; n = len(S); fd = [r for r in S if r["dec"] and r["marg"] > 0]
    print(f"{lo:.2f}-{hi:.2f} {n:5d}  {sum(r['favwin'] for r in S)/n:.3f}  {sum(r['favwin'] and not r['dec'] for r in S)/n:.3f}  {sum(r['dec'] for r in S)/n:.3f}  {len(fd)/n:.3f}  {sum(r['marg']>=4 for r in fd)/len(fd):.3f}           {sum(cover(r,2.5) for r in S)/n:.3f}     {sum(cover(r,3.5) for r in S)/n:.3f}     {sum(cover(r,4.5) for r in S)/n:.3f}")
fd3 = [r for r in R3 if r["dec"] and r["marg"] > 0]
print("3R margin when the favorite wins a decision:", sorted(collections.Counter(r["marg"] for r in fd3).items()))
M = {}
for sched in (3, 5):
    fd = [r for r in R if r["sched"] == sched and r["dec"] and r["marg"] > 0]
    for k in (3, 4, 5, 6): M[(sched, k)] = fit([[1, lg(r["pf"])] for r in fd], [r["marg"] >= k for r in fd])[0]
    print(f"{sched}R fav decision wins n={len(fd)}; fitted P(margin>=k) at p=.66:", {k: round(sg(M[(sched,k)][0]+M[(sched,k)][1]*lg(.66)), 3) for k in (3,4,5,6)})
G = [r for r in fd3 if r["gap"] is not None]
bg, se = fit([[1, lg(r["pf"]), r["gap"]] for r in G], [r["marg"] >= 4 for r in G])
print(f"\nB. Strike-differential gap (pre-fight career SD/min, fav minus dog, 15+ UFC min each), n={len(G)}:")
print(f"   logit P(m>=4 | fav dec win) = {bg[0]:.3f} + {bg[1]:.3f} logit(p) + {bg[2]:.3f} gap  (gap SE {se[2]:.3f}, z {bg[2]/se[2]:.2f})")
E = json.load(open("data/pending/fn_prochazka_stirling_projections.json")); O = json.load(open("data/fn_prochazka_stirling_odds.json"))
EM = json.load(open("form/data/embed_metrics/fn_prochazka_stirling.json"))["fighters"]
def nv(fav):
    for f in O["fights"]:
        for o in f["markets"]["moneyline"]:
            if FN.name_match(o["label"], fav): return o["books"]["consensus"]["no_vig_pct"] / 100
def sd(name):
    for k, v in EM.items():
        if FN.name_match(k, name):
            fs = v.get("fights") or []; sec = sum(x.get("secs", 0) for x in fs)
            return (sum(x.get("sl", 0) for x in fs) - sum(x.get("sa", 0) for x in fs)) / (sec/60) if sec >= 900 else None
print(f"\nC. Card (Sean's export published {E['published_at']}; market p = consensus no-vig at {O['updated_at']})")
print("fav (rounds) | sheet win | fav finish | fav dec win | mkt p | fair P(cover) -2.5 / -3.5 / -4.5 / -5.5 | -3.5 with SD gap")
for f in sorted(E["fights"], key=lambda f: -f["sheet"]["true_fav"]):
    s = f["sheet"]; m = f["method"]; sched = 5 if f["tag"].endswith("-5") else 3; pfav = s["true_fav"]
    ff = pfav*(m["fav"]["ko"]+m["fav"]["sub"]); fdw = pfav*m["fav"]["dec"]; pf = nv(f["fav"]) or pfav
    res = {l: ff + fdw*sg(M[(sched,k)][0]+M[(sched,k)][1]*lg(pf)) for l, k in ((2.5,3),(3.5,4),(4.5,5),(5.5,6))}
    ga, gb = sd(f["fav"]), sd(f["dog"]); gtxt = "n/a"
    if sched == 3 and ga is not None and gb is not None:
        pg = ff + fdw*sg(bg[0]+bg[1]*lg(pf)+bg[2]*(ga-gb)); gtxt = f"{pg*100:.1f}% ({ml(pg)}) gap {ga-gb:+.2f}"
    print(f"{f['fav']} ({sched}R) | {pfav*100:.1f} | {ff*100:.1f} | {fdw*100:.1f} | {pf*100:.1f} | " + " / ".join(f"{res[l]*100:.1f}% ({ml(res[l])})" for l in (2.5,3.5,4.5,5.5)) + f" | {gtxt}")
h = next(f for f in E["fights"] if "Hooker" in f["fav"]); s = h["sheet"]; m = h["method"]
ff = s["true_fav"]*(m["fav"]["ko"]+m["fav"]["sub"]); fdw = s["true_fav"]*m["fav"]["dec"]; pf = nv(h["fav"])
pa = ff + fdw*sg(M[(3,4)][0]+M[(3,4)][1]*lg(pf)); pb = ff + fdw*sg(bg[0]+bg[1]*lg(pf)+bg[2]*(sd("Dan Hooker")-sd("Brian Ortega")))
print(f"\nHOOKER -3.5 at -120 (implied {imp(-120)*100:.1f}%): fair {pa*100:.1f}% ({ml(pa)}), edge {(pa-imp(-120))*100:+.1f}; with SD gap {pb*100:.1f}% ({ml(pb)}), edge {(pb-imp(-120))*100:+.1f}")
print(f"HOOKER ML: sheet {s['true_fav']*100:.1f}%; edge {(s['true_fav']-imp(-185))*100:+.1f} at -185, {(s['true_fav']-imp(-193))*100:+.1f} at -193")
print(f"Break-even for -3.5 at -120 needs P(m>=4 | Hooker dec win) = {(imp(-120)-ff)/fdw:.3f}; +3 pts needs {(imp(-120)+.03-ff)/fdw:.3f}")
