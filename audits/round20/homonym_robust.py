"""For fresh-build members of southpaw/reach4 in bouts with a UFCStats name shared by 2+ fighters: does membership hold
whichever of the namesakes' tott rows is used? robust = same answer for every combination."""
import csv, itertools, collections
T = collections.defaultdict(list)
for r in csv.DictReader(open("/tmp/e5/.form_cache/ufc_fighter_tott.csv", encoding="utf-8")): T[r["FIGHTER"].strip()].append(r)
dup = {k for k, v in T.items() if len(v) > 1}
reach = lambda r: float(r["REACH"].replace('"', "")) if r["REACH"].strip() not in ("--", "") else None
out = []
for ang in ("southpaw", "reach4"):
    for l in open("/tmp/angle_members.txt"):
        k, d, a, b, s = l.strip().split("|")
        if k != ang or not (a in dup or b in dup): continue
        me, op = (a, b) if s == "a" else (b, a)
        res = set()
        for rm, ro in itertools.product(T[me], T[op]):
            if ang == "southpaw": res.add(rm["STANCE"].strip() == "Southpaw" and ro["STANCE"].strip() == "Orthodox")
            else: res.add(reach(rm) is not None and reach(ro) is not None and reach(rm) - reach(ro) >= 4)
        out.append((ang, d, me, op, "robust (holds for every namesake row)" if res == {True} else "DEPENDS on which namesake" if len(res) > 1 else "WRONG under every namesake row"))
for o in out: print(o)
c = collections.Counter((o[0], o[4]) for o in out); print(dict(c))
