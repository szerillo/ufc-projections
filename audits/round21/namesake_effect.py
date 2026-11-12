"""Kirk round 21 call 3 + challenge A: bouts (2022+) where one fighter's UFCStats name is shared by 2+ fighters.
The build's bio (age, reach, stance) is the FIRST tott row for the name. The right row is the one whose fighter-details ID
appears on that bout's UFCStats fight-details page (ns_ids.txt, read in Sean's Chrome, same-origin fetch, 30 pages).
Recompute the five bio-based angles (younger5, vs_36, reach4, age37, southpaw) both ways, with every qualifying side
(symmetric-angle fix applied in both, so only the namesake effect is measured), and list membership changes."""
import csv, collections, datetime as dt, json, pathlib
H = pathlib.Path(__file__).parent
T = collections.defaultdict(list)
for r in csv.DictReader(open("/tmp/e5/.form_cache/ufc_fighter_tott.csv", encoding="utf-8")): T[r["FIGHTER"].strip()].append(r)
byid = {r["URL"].split("/")[-1]: r for v in T.values() for r in v}
fid = {l.split("|")[0]: (l.split("|")[1], l.strip().split("|")[2]) for l in open(H / "ns_ids.txt") if l.strip()}
bouts = json.load(open(H / "namesake_bouts.json"))
def attrs(row, d):
    dob = row["DOB"].strip(); rc = row["REACH"].strip().replace('"', "")
    age = (d - dt.datetime.strptime(dob, "%b %d, %Y").date()).days / 365.25 if dob not in ("", "--") else None
    return {"age": age, "reach": float(rc) if rc not in ("", "--") else None, "stance": row["STANCE"].strip(), "id": row["URL"].split("/")[-1]}
def angles(A, B):
    out = set()
    for s, me, op in (("a", A, B), ("b", B, A)):
        if me["age"] and op["age"]:
            if op["age"] - me["age"] >= 5: out.add(("younger5", s))
            if op["age"] >= 36 and me["age"] < 32: out.add(("vs_36", s))
        if me["reach"] and op["reach"] and me["reach"] - op["reach"] >= 4: out.add(("reach4", s))
        if me["age"] and me["age"] >= 37: out.add(("age37", s))
        if me["stance"] == "Southpaw" and op["stance"] == "Orthodox": out.add(("southpaw", s))
    return out
changes = []; wrong_row = 0
for d, a, b, url in bouts:
    D = dt.date.fromisoformat(d); nm, right = fid[url.split("/")[-1]]
    used = {n: attrs(T[n][0], D) for n in (a, b)}; good = dict(used)
    good[nm] = attrs(byid[right], D)
    if used[nm]["id"] != right: wrong_row += 1
    old, new = angles(used[a], used[b]), angles(good[a], good[b])
    for k, s in sorted(old - new): changes.append((d, a, b, k, s, "REMOVE"))
    for k, s in sorted(new - old): changes.append((d, a, b, k, s, "ADD"))
print(f"{len(bouts)} bouts; build used the wrong namesake row in {wrong_row}")
for c in changes: print(c)
print(dict(collections.Counter((c[3], c[5]) for c in changes)))
json.dump(changes, open(H / "namesake_effect.json", "w"))
