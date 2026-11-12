#!/usr/bin/env python3
"""Kirk round 26 call 1: fights on the given upcoming card where either fighter has no listed reach (no reach in the fighter
file, or no fighter file: a debut). Writes form/data/reach_notes.json; the site shows "Reach not listed; Form treats it as
equal." next to those fights' Form Lines. Only the fact; no claim about the direction of any error.
  python3 scripts/reach_notes.py --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json"""
import argparse, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; FD = REPO / "form/data"
ap = argparse.ArgumentParser(); ap.add_argument("--event", required=True); a = ap.parse_args()
ev = json.loads((REPO / a.event).read_text()); out = []
for f in ev["fights"]:
    miss = []
    for s in "ab":
        p = FD / "fighters" / f"{f[s].get('slug')}.json"
        b = (json.loads(p.read_text()).get("bio") or {}) if f[s].get("slug") and p.exists() else {}
        if not b.get("reach"): miss.append(f[s]["name"])
    if miss: out.append({"n": f["n"], "missing": miss})
slug = Path(a.event).stem
J = {"text": "Reach not listed; Form treats it as equal.", "events": {slug: sorted(out, key=lambda x: x["n"])}}
(FD / "reach_notes.json").write_text(json.dumps(J, indent=1)); print(json.dumps(J["events"]))
