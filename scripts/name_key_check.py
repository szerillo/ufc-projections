# Block 55 item 3: a name-keyed bout lookup (key = the two fighters' names, order-free, after the alias table) must
# return exactly one bout in every source the v3 embed could read, for all 13 UFC 334 bouts; 13 = Gane vs Hokit.
import json, re, sys, unicodedata
alias = {k: v for k, v in json.load(open(sys.argv[1])).items() if not k.startswith("_")}
fold = lambda s: re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())).strip()
canon = lambda s: fold(alias.get(fold(s), s)).replace(" ", "")
sur = lambda s: fold(alias.get(fold(s), s)).split()[-1]
src = {}
ev = json.load(open(sys.argv[2])); src["site event file"] = [(f["a"]["name"], f["b"]["name"]) for f in ev["fights"]]
pj = json.load(open(sys.argv[3])); src["projections file"] = [(f["dog"], f["fav"]) for f in pj["fights"]]
od = json.load(open(sys.argv[4])); src["odds feed"] = [(f["fighter_a"]["name"], f["fighter_b"]["name"]) for f in od["fights"]]
page = open(sys.argv[5]).read()
src["card page FIGHTS"] = re.findall(r'\n\s+a: \{ name: "([^"]+)".*?\n\s+b: \{ name: "([^"]+)"', page)
order = sorted(re.findall(r'n: (\d+), card:.*?\n\s+a: \{ name: "([^"]+)".*?\n\s+b: \{ name: "([^"]+)"', page), key=lambda t: -int(t[0]))
bad = 0
print("key form: full names (alias table, order-free) | surnames only")
for n, a, b in order:
    kf, ks = frozenset((canon(a), canon(b))), frozenset((sur(a), sur(b)))
    cf = {s: sum(1 for x, y in rows if frozenset((canon(x), canon(y))) == kf) for s, rows in src.items()}
    cs = {s: sum(1 for x, y in rows if frozenset((sur(x), sur(y))) == ks) for s, rows in src.items()}
    ok = all(v == 1 for v in cf.values()) and all(v == 1 for v in cs.values()); bad += not ok
    print(f"  {'ok ' if ok else 'BAD'} {n:>2} {a} vs {b}: full {list(cf.values())} | surname {list(cs.values())}")
print("sources:", list(src), "| bouts per source:", [len(v) for v in src.values()])
print(f"RESULT: {13 - bad} of 13 bouts return exactly one bout in every source;", "GREEN" if not bad else "RED")
sys.exit(1 if bad else 0)
