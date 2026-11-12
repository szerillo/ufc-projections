"""Kirk round 21 call 3: are the symmetric-angle overwrite bug's numbers live on main's Labs page, and how many displayed numbers change?
Members: instrumented scratch build (/tmp/s21, angle_sides unchanged + a multi-side twin logging every qualifying side;
flag 1 = the side the build kept). Published set = fresh members whose bout has odds in MAIN's event files; prices, no-vig p and winners come
from main's event files (so membership is fresh-code, pricing is exactly what main published). Stats rebuilt per angle exactly as form_model.research does them; the CURRENT variant
must reproduce main's research.json for all 46 angles before the FIXED variant (every qualifying side) is trusted.
Displayed fields (form/app.js Labs angles table): n, act (pct 1dp), exp (pct 1dp), z (2dp), roi_c (pct 1dp), roi_o (pct 1dp),
one ROI-by-year entry per year (integer pct)."""
import sys, json, subprocess, math, datetime as dt, importlib.util, pathlib, collections
repo = pathlib.Path("/tmp/e5"); sys.path.insert(0, str(repo / "scripts"))
sp = importlib.util.spec_from_file_location("bf", repo / "scripts/build_form.py"); BF = importlib.util.module_from_spec(sp); sp.loader.exec_module(BF)
by = BF.load_odds(repo / ".form_cache"); idx = BF.index_odds(by)
git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout
def odds_bouts(ref):
    out = set()
    for p in git("ls-tree", "--name-only", ref, "form/data/events/").split():
        e = json.loads(git("show", f"{ref}:{p}"))
        for f in e["fights"]:
            if f.get("odds"): out.add((e["date"], frozenset((f["a"]["name"], f["b"]["name"]))))
    return out
NEW = odds_bouts("HEAD") - odds_bouts("origin/main")
MAIN = {x["id"]: x for x in json.loads(git("show", "origin/main:form/data/research.json"))["angles"]}
W = {}
for pth in (repo / "form/data/events").glob("*.json"):
    e = json.load(open(pth))
    for f in e["fights"]: W[(e["date"], f["a"]["name"], f["b"]["name"])] = (f.get("result") or {}).get("winner")
dec = lambda m: None if m is None else 1 + (m / 100 if m > 0 else 100 / -m)
# Prices and winners from MAIN's own event files (what main's research.json was built from), oriented to this row's a/b.
MO = {}
for p_ in git("ls-tree", "--name-only", "origin/main", "form/data/events/").split():
    e = json.loads(git("show", f"origin/main:{p_}"))
    for f in e["fights"]:
        if f.get("odds"): MO[(e["date"], frozenset((f["a"]["name"], f["b"]["name"])))] = (f["a"]["name"], f["odds"], (f.get("result") or {}).get("winner"))
def bet(d, a, b, s):
    an, o, w = MO[(d, frozenset((a, b)))]
    if an != a:  # flip to this row's orientation
        o = {k: {"p": 1 - o[k]["p"], "ma": o[k]["mb"], "mb": o[k]["ma"]} for k in ("open", "close")}; w = {"a": "b", "b": "a"}.get(w)
    return {"p": o["close"]["p"] if s == "a" else 1 - o["close"]["p"], "dc": dec(o["close"]["ma" if s == "a" else "mb"]),
            "do": dec(o["open"]["ma" if s == "a" else "mb"]), "won": w == s, "y": d[:4]}
def stats(bets):
    n = len(bets); w = sum(x["won"] for x in bets); exp = sum(x["p"] for x in bets) / n; act = w / n
    se = math.sqrt(max(exp * (1 - exp), 1e-9) / n)
    pc = sum(((x["dc"] - 1) if x["won"] else -1) for x in bets if x["dc"]); po = [((x["do"] - 1) if x["won"] else -1) for x in bets if x["do"]]
    yrs = collections.defaultdict(lambda: [0, 0, 0.0])
    for x in bets:
        v = yrs[x["y"]]; v[0] += 1; v[1] += x["won"]; v[2] += ((x["dc"] - 1) if x["won"] else -1) if x["dc"] else 0
    return {"n": n, "w": w, "act": round(act, 4), "exp": round(exp, 4), "z": round((act - exp) / se, 2), "roi_c": round(pc / n, 4), "pnl_c": round(pc, 2),
            "roi_o": round(sum(po) / len(po), 4) if po else None, "years": {y: [v[0], v[1], round(v[2], 2)] for y, v in sorted(yrs.items())}}
def shown(r):
    f = lambda x: None if x is None else round(x * 100, 1)
    d = {"n": r["n"], "act": f(r["act"]), "exp": f(r["exp"]), "z": r["z"], "roi_c": f(r["roi_c"]), "roi_o": f(r["roi_o"])}
    for y, v in r["years"].items(): d["y" + y] = round(v[2] / v[0] * 100)
    return d
rows = [l.strip().split("|") for l in open("/tmp/s21_members_multi.txt") if l.strip()]
pubrows = [r for r in rows if (r[1], frozenset((r[2], r[3]))) in MO]
NS = json.load(open(pathlib.Path(__file__).with_name("namesake_effect.json")))
rem = {(d, frozenset((a, b)), k, (a if sd == "a" else b)) for d, a, b, k, sd, act in NS if act == "REMOVE"}
add = [(d, a, b, k, sd) for d, a, b, k, sd, act in NS if act == "ADD" and (d, frozenset((a, b))) in MO]
def nm_(r): return (r[1], frozenset((r[2], r[3])), r[0], r[2] if r[4] == "a" else r[3])
res = {}; bad = []
for ang in MAIN:
    cur = [bet(r[1], r[2], r[3], r[4]) for r in pubrows if r[0] == ang and r[5] == "1"]
    fix = [bet(r[1], r[2], r[3], r[4]) for r in pubrows if r[0] == ang]
    both = [bet(r[1], r[2], r[3], r[4]) for r in pubrows if r[0] == ang and nm_(r) not in rem] + [bet(d, a, b, sd) for d, a, b, k, sd in add if k == ang]
    sc, sf, sb = stats(cur), stats(fix), stats(both)
    m = MAIN[ang]
    ok = sc["n"] == m["n"] and sc["w"] == m["w"] and sc["exp"] == m["exp"] and sc["z"] == m["z"] and sc["roi_c"] == m["roi_c"] and sc["roi_o"] == m["roi_o"] and \
        {y: v for y, v in sc["years"].items()} == {y: v for y, v in m["years"].items()}
    if not ok: bad.append((ang, sc, m))
    a, b = shown(sc), shown(sf)
    ch = {k: (a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}
    c_ = shown(sb); ch2 = {k: (a.get(k), c_.get(k)) for k in sorted(set(a) | set(c_)) if a.get(k) != c_.get(k)}
    res[ang] = {"reproduces_main": ok, "added_bets": sf["n"] - sc["n"], "current": sc, "fixed": sf, "displayed_changes": ch,
                "both_fixes": sb, "both_n_change": sb["n"] - sc["n"], "displayed_changes_both": ch2}
print("angles reproducing main research.json exactly:", sum(v["reproduces_main"] for v in res.values()), "of", len(res))
for a_, sc, m in bad: print("  MISMATCH", a_, {k: (sc.get(k), m.get(k)) for k in ("n", "w", "exp", "z", "roi_c", "roi_o")})
tot = 0
for ang, v in res.items():
    if v["added_bets"]:
        tot += len(v["displayed_changes"])
        print(f"{ang}: +{v['added_bets']} bets; displayed changes {len(v['displayed_changes'])}: {v['displayed_changes']}")
print("total displayed numbers that change (symmetric fix only):", tot, "| angles affected:", sum(1 for v in res.values() if v["added_bets"]))
print("--- both fixes (symmetric + right namesake row), vs main as published")
t2 = 0
for ang, v in res.items():
    if v["displayed_changes_both"]:
        t2 += len(v["displayed_changes_both"]); print(f"{ang}: n {v['current']['n']} -> {v['both_fixes']['n']}; {len(v['displayed_changes_both'])} displayed changes: {v['displayed_changes_both']}")
print("TOTAL displayed numbers that change with both fixes:", t2, "| angles:", sum(1 for v in res.values() if v["displayed_changes_both"]), "of", len(res))
json.dump(res, open(pathlib.Path(__file__).with_suffix(".json"), "w"), indent=1)
