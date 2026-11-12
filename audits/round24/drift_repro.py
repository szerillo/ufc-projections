"""Reproduce Labs research.json 'drift' (main) from main's event files, then the distribution of the opening favorite's move.
research: dr = fights in F with odds n >= 4, open date before close date, year <= 2025; move = close - open of the OPENING
favorite's no-vig chance (positive = got shorter)."""
import json, subprocess, statistics, sys
git = lambda *a: subprocess.run(["git", "-C", "<branch>", *a], capture_output=True, text=True).stdout
R = json.loads(git("show", "origin/main:form/data/research.json"))
rows = {}
for p in git("ls-tree", "--name-only", "origin/main", "form/data/events/").split():
    e = json.loads(git("show", f"origin/main:{p}"))
    for f in e["fights"]:
        o = f.get("odds"); res = f.get("result") or {}
        if not o or not o.get("open") or not o.get("close"): continue
        rows[(e["date"], f["a"]["name"], f["b"]["name"])] = (o, res.get("kind"))
def variant(kinds):
    mv = []
    for (d, a, b), (o, k) in rows.items():
        if kinds and k not in kinds: continue
        if not (R["from"] <= d) or int(d[:4]) > 2025: continue
        if o["n"] < 4 or not (o["open"]["t"][:10] < o["close"]["t"][:10]): continue
        po, pc = o["open"]["p"], o["close"]["p"]; mv.append((pc - po) if po >= 0.5 else (po - pc))
    return mv
for kinds in (None, {"win"}, {"win", "draw"}):
    mv = variant(kinds)
    print(kinds, len(mv), round(statistics.mean(mv) * 100, 2), round(sum(m > 0.005 for m in mv) / len(mv), 4), round(sum(m < -0.005 for m in mv) / len(mv), 4))
print("published:", R["drift"])
