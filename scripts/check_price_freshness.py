#!/usr/bin/env python3
"""Price-freshness alert for fight week (Kirk round 9, A).
    python3 -I scripts/check_price_freshness.py --event form/data/events/<slug>.json [--cache .form_cache] [--max-age-h 3] [--now ISO]
For every bout on the card that has not started: the newest archive record that prices it, and its age. Exit 1 with an
ALERT line when any bout's newest price is older than --max-age-h (default 3 h). The archive's hourly MMA rows come from
szerillo/sharp-tracker sharp/mma_steam.py (signals.yml, dispatched about every 10 minutes by pulse.yml)."""
import argparse, datetime as dt, importlib.util, json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "scripts"))
sp = importlib.util.spec_from_file_location("build_form", REPO / "scripts/build_form.py"); BF = importlib.util.module_from_spec(sp); sp.loader.exec_module(BF)
ap = argparse.ArgumentParser(); ap.add_argument("--event", required=True); ap.add_argument("--cache", default=str(REPO / ".form_cache"))
ap.add_argument("--max-age-h", type=float, default=3.0); ap.add_argument("--now", default=None); a = ap.parse_args()
T = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
now = T(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
ev = json.loads(Path(a.event).read_text()); by = BF.load_odds(Path(a.cache)); idx = BF.index_odds(by); d = dt.date.fromisoformat(ev["date"])
stale = []
for f in sorted(ev["fights"], key=lambda f: f["n"]):
    eid, fl = BF.find_odds(idx, by, f["a"]["name"], f["b"]["name"], d)
    if not eid: stale.append(f"{f['n']} {f['a']['name']} vs {f['b']['name']}: no archive record"); continue
    s = [x for x in by[eid] if x["books"]]; start = T(s[-1]["start"])
    if now >= start: print(f"  {f['n']:>2} started; not checked"); continue
    t = s[-1]["t"]; age = (now - T(t)).total_seconds() / 3600
    print(f"  {f['n']:>2} {f['a']['name']} vs {f['b']['name']}: newest {t[:16]}Z, {age:.1f} h old")
    if age > a.max_age_h: stale.append(f"{f['n']} {f['a']['name']} vs {f['b']['name']}: {age:.1f} h")
if stale:
    print(f"ALERT: {len(stale)} bout(s) with no price in the last {a.max_age_h:g} h: " + "; ".join(stale)); sys.exit(1)
print(f"OK: every bout priced within {a.max_age_h:g} h")
