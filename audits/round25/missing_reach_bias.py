"""Missing_Reach_Bias_PREREG (sha 7d8626075082). Branch build event files + fighter files."""
import json, glob, math, collections
FD = "<branch>/form/data"
F = {}
for p in glob.glob(f"{FD}/fighters/*.json"):
    x = json.load(open(p)); F[x["slug"]] = bool((x.get("bio") or {}).get("reach"))
G = collections.defaultdict(list); M1 = []
for p in glob.glob(f"{FD}/events/*.json"):
    e = json.load(open(p))
    for f in e["fights"]:
        r = f.get("result") or {}; fm = f.get("form") or {}
        if r.get("kind") != "win" or fm.get("p") is None or r.get("winner") not in ("a", "b"): continue
        ra, rb = F.get(f["a"].get("slug")), F.get(f["b"].get("slug"))
        if ra is None or rb is None: continue
        pa = fm["p"]; won_a = 1 if r["winner"] == "a" else 0
        g = "L" if ra and rb else "M2" if not ra and not rb else "M1"
        G[g].append((pa, won_a, e["date"]))
        if g == "M1":
            pm, wm = (pa, won_a) if not ra else (1 - pa, 1 - won_a)
            M1.append(wm - pm)
n = len(M1); m = sum(M1) / n; sd = math.sqrt(sum((x - m) ** 2 for x in M1) / (n - 1)); se = sd / math.sqrt(n)
print(f"PRIMARY (M1, fighter with the missing reach): n {n}, mean(won - Form p) {m:+.4f}, 95% CI {m - 1.96*se:+.4f} to {m + 1.96*se:+.4f}")
flag = abs(m) >= 0.03 and (m - 1.96 * se > 0 or m + 1.96 * se < 0)
print("BAR (|mean| >= 0.03 and CI excludes 0):", "BIAS FLAGGED" if flag else "not met: no evidence of bias")
print("\nSECONDARY (descriptive): Form favorite's calibration and Brier by group")
for g in ("L", "M1", "M2"):
    rows = G[g]; br = sum((p - w) ** 2 for p, w, _ in rows) / len(rows)
    yrs = sorted(d[:4] for _, _, d in rows)
    out = []
    for lo, hi in ((.5, .6), (.6, .7), (.7, .8), (.8, 1.01)):
        xs = [(max(p, 1 - p), w if p >= .5 else 1 - w) for p, w, _ in rows if lo <= max(p, 1 - p) < hi]
        if xs: out.append(f"{int(lo*100)}-{int(min(hi,1)*100)}: n {len(xs)} Form {sum(a for a, _ in xs)/len(xs)*100:.1f}% won {sum(b for _, b in xs)/len(xs)*100:.1f}%")
    print(f"{g}: n {len(rows)} ({yrs[0]}-{yrs[-1]}), Brier {br:.4f} | " + " | ".join(out))
