"""Check #2, independent of form_model: ages from UFCStats tott DOB (own parsing), angle membership by the stated rule,
over every decided bout 2022-01-15..2026-11-07 that has an odds block in the site's event files. Compare the member sets
with the fresh build's (instrumented form_model)."""
import csv, json, glob, datetime as dt, collections
dob = {}
for r in csv.DictReader(open("/tmp/e5/.form_cache/ufc_fighter_tott.csv", encoding="utf-8")):
    try: dob.setdefault(r["FIGHTER"].strip(), []).append(dt.datetime.strptime(r["DOB"].strip(), "%b %d, %Y").date())
    except ValueError: pass
age = lambda nm, d: (d - dob[nm][0]).days / 365.25 if nm in dob and len(set(dob[nm])) == 1 else None
mine = collections.defaultdict(set)
for p in glob.glob("/tmp/e5/form/data/events/*.json"):
    e = json.load(open(p)); d = dt.date.fromisoformat(e["date"])
    if not (dt.date(2022, 1, 15) <= d <= dt.date(2026, 11, 7)): continue
    for f in e["fights"]:
        r = f.get("result") or {}
        if not f.get("odds") or r.get("kind") != "win": continue
        a, b = f["a"]["name"], f["b"]["name"]; A, B = age(a, d), age(b, d)
        if A is None or B is None: continue
        for s, me, op in (("a", A, B), ("b", B, A)):
            k = (e["date"], frozenset((a, b)), a if s == "a" else b)
            if op - me >= 5: mine["younger5"].add(k)
            if op >= 36 and me < 32: mine["vs_36"].add(k)
            if me >= 37: mine["age37"].add(k)
fresh = collections.defaultdict(set)
for l in open("/tmp/angle_members.txt"):
    k, d, a, b, s = l.strip().split("|")
    fresh[k].add((d, frozenset((a, b)), a if s == "a" else b))
for ang in ("age37", "younger5", "vs_36"):
    only_m = mine[ang] - fresh[ang]; only_f = fresh[ang] - mine[ang]
    print(f"{ang}: independent {len(mine[ang])}, fresh build {len(fresh[ang])}, both {len(mine[ang] & fresh[ang])}; only independent {len(only_m)} {sorted((x[0], x[2]) for x in only_m)[:6]}; only fresh {len(only_f)} {sorted((x[0], x[2]) for x in only_f)[:6]}")
# --- why they differ
dup = {nm for nm, v in dob.items() if len(set(v)) > 1}
def why(x, ang, side_only_in):
    d, pair, me = x; other = next(iter(pair - {me})) if len(pair) == 2 else None
    if me in dup or other in dup: return "name shared by 2+ UFCStats fighters (independent check skips; build takes the first DOB)"
    if me not in dob or other not in dob: return "no DOB in UFCStats tott for one side"
    if ang == "age37" and side_only_in == "independent" and (d, pair, other) in fresh[ang]: return "BOTH fighters 37+: the build keeps only one side (dict overwrite)"
    return "other"
for ang in ("age37", "younger5", "vs_36"):
    c = collections.Counter([("only independent", why(x, ang, "independent")) for x in mine[ang] - fresh[ang]] + [("only fresh", why(x, ang, "fresh")) for x in fresh[ang] - mine[ang]])
    print(ang, dict(c))
    oth = [x for x in (mine[ang] ^ fresh[ang]) if why(x, ang, "independent" if x in mine[ang] else "fresh") == "other"]
    if oth: print("   other:", [(x[0], x[2], sorted(x[1])) for x in oth][:6])
