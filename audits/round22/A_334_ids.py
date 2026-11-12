"""Kirk round 22 A: do any UFC 334 fighters' site data come from the wrong UFCStats fighter? Live UFCStats event page
402ea3b5ee233852 gives each fighter's ID (read in Sean's Chrome); compare with the fighter file the site built (bio.url ID,
DOB, reach, stance, dup_name) and count tott rows sharing the name."""
import csv, json, datetime as dt, collections, pathlib
H = pathlib.Path(__file__).parent; R = pathlib.Path("/tmp/e5")
T = collections.Counter(r["FIGHTER"].strip() for r in csv.DictReader(open(R / ".form_cache/ufc_fighter_tott.csv", encoding="utf-8")))
ev = json.load(open(R / "form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json"))
slug = {f[s]["name"]: f[s]["slug"] for f in ev["fights"] for s in "ab"}
n_ok = 0; probs = []
for l in open(H / "live_334_ids.txt"):
    nm, fid, reach, stance, dob = l.strip().split("|")
    F = json.load(open(R / f"form/data/fighters/{slug[nm]}.json")) if slug.get(nm) else None
    b = (F or {}).get("bio") or {}
    site = (b.get("url", "").split("/")[-1], b.get("reach"), b.get("stance"), b.get("dob"))
    live = (fid, reach, stance, dt.datetime.strptime(dob, "%b %d, %Y").date().isoformat())
    same = site == live and not (F or {}).get("dup_name") and T[nm] == 1
    n_ok += same
    print(f"{'OK  ' if same else 'DIFF'} {nm:20s} id {fid[:8]} site {site[0][:8]} | reach {reach}/{site[1]} | {stance}/{site[2]} | {live[3]}/{site[3]} | tott rows {T[nm]} | dup_name {(F or {}).get('dup_name')}")
    if not same: probs.append(nm)
print(f"{n_ok}/26 match on ID, reach, stance and DOB with one UFCStats row per name; problems: {probs or 'none'}")
