"""Check #2 for stance/reach angles: southpaw (me Southpaw vs Orthodox), reach4 (reach edge 4+ in), from UFCStats tott
directly; names shared by 2+ tott rows are skipped and reported."""
import csv, json, glob, datetime as dt, collections
T = collections.defaultdict(list)
for r in csv.DictReader(open("/tmp/e5/.form_cache/ufc_fighter_tott.csv", encoding="utf-8")): T[r["FIGHTER"].strip()].append(r)
dup = {k for k, v in T.items() if len(v) > 1}
st = lambda nm: T[nm][0]["STANCE"].strip() if nm in T and nm not in dup else None
rc = lambda nm: (float(T[nm][0]["REACH"].replace('"', "")) if T[nm][0]["REACH"].strip() not in ("--", "") else None) if nm in T and nm not in dup else None
mine = collections.defaultdict(set); skipped = collections.Counter()
for p in glob.glob("/tmp/e5/form/data/events/*.json"):
    e = json.load(open(p)); d = dt.date.fromisoformat(e["date"])
    if not (dt.date(2022, 1, 15) <= d <= dt.date(2026, 11, 7)): continue
    for f in e["fights"]:
        if not f.get("odds") or (f.get("result") or {}).get("kind") != "win": continue
        a, b = f["a"]["name"], f["b"]["name"]
        if a in dup or b in dup: skipped["homonym"] += 1; continue
        for me, op in ((a, b), (b, a)):
            if st(me) == "Southpaw" and st(op) == "Orthodox": mine["southpaw"].add((e["date"], frozenset((a, b)), me))
            if rc(me) is not None and rc(op) is not None and rc(me) - rc(op) >= 4: mine["reach4"].add((e["date"], frozenset((a, b)), me))
fresh = collections.defaultdict(set)
for l in open("/tmp/angle_members.txt"):
    k, d, a, b, s = l.strip().split("|")
    if k in ("southpaw", "reach4") and a not in dup and b not in dup: fresh[k].add((d, frozenset((a, b)), a if s == "a" else b))
print("bouts skipped (a UFCStats name shared by 2+ fighters):", dict(skipped))
for ang in ("southpaw", "reach4"):
    om, of = mine[ang] - fresh[ang], fresh[ang] - mine[ang]
    print(f"{ang}: independent {len(mine[ang])}, fresh {len(fresh[ang])}, both {len(mine[ang] & fresh[ang])}; only independent {len(om)} {sorted((x[0], x[2]) for x in om)[:5]}; only fresh {len(of)} {sorted((x[0], x[2]) for x in of)[:5]}")
