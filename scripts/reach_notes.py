#!/usr/bin/env python3
"""Kirk round 26 call 1: fights on the given upcoming card where either fighter has no listed reach (no reach in the fighter
file, or no fighter file: a debut). Writes form/data/reach_notes.json; the site shows "Reach not listed; Form treats it as
equal." next to those fights' Form Lines. Only the fact; no claim about the direction of any error.
  python3 scripts/reach_notes.py --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json"""
import argparse, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; FD = REPO / "form/data"
ap = argparse.ArgumentParser(); ap.add_argument("--event", required=True); a = ap.parse_args()
# Kirk round 27 C: use what the Form model reads. A fighter file's bio is the Form input (it carries the round-23 Hasan fill);
# a debut has no file, but the Form model still reads its UFCStats bio row (build_form.load_ufcstats: first row per name), so
# a debut is "not listed" only if that row has no reach too. (Round 26 read only the files and wrongly noted Sanches.)
import csv, sys; sys.path.insert(0, str(REPO / "scripts")); from form_model import norm
TOTT = {}
for r in csv.DictReader(open(REPO / ".form_cache/ufc_fighter_tott.csv", encoding="utf-8")): TOTT.setdefault(norm(r["FIGHTER"]), r)
def has_reach(side):
    p = FD / "fighters" / f"{side.get('slug')}.json"
    if side.get("slug") and p.exists(): return bool((json.loads(p.read_text()).get("bio") or {}).get("reach"))
    r = TOTT.get(norm(side["name"])); return bool(r and r["REACH"].strip() not in ("", "--"))
ev = json.loads((REPO / a.event).read_text()); out = []
for f in ev["fights"]:
    miss = [f[s]["name"] for s in "ab" if not has_reach(f[s])]
    if miss: out.append({"n": f["n"], "missing": miss})
slug = Path(a.event).stem
J = {"text": "Reach not listed; Form treats it as equal.", "events": {slug: sorted(out, key=lambda x: x["n"])}}
(FD / "reach_notes.json").write_text(json.dumps(J, indent=1)); print(json.dumps(J["events"]))
