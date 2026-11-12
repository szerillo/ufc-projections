#!/usr/bin/env python3
"""Price-freshness alert for fight week (Kirk round 9, A; threshold 4 h per Staleness_Threshold_PREREG sha b935eef6).
    python3 -I scripts/check_price_freshness.py --event form/data/events/<slug>.json [--cache .form_cache] [--max-age-h 4] [--now ISO] [--download] [--status FILE]
For every bout on the card that has not started: the newest archive record that prices it, and its age. Exit 1 with an
ALERT line when any bout's newest price is older than --max-age-h (default 4 h). The archive's hourly MMA rows come from
szerillo/sharp-tracker sharp/mma_steam.py (signals.yml, dispatched about every 10 minutes by pulse.yml)."""
import argparse, datetime as dt, importlib.util, json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "scripts"))
sp = importlib.util.spec_from_file_location("build_form", REPO / "scripts/build_form.py"); BF = importlib.util.module_from_spec(sp); sp.loader.exec_module(BF)
ap = argparse.ArgumentParser(); ap.add_argument("--event", required=True); ap.add_argument("--cache", default=str(REPO / ".form_cache"))
ap.add_argument("--max-age-h", type=float, default=4.0); ap.add_argument("--now", default=None)
ap.add_argument("--download", action="store_true", help="fetch the archive's live and compact MMA files from sharp-tracker into --cache first")
ap.add_argument("--status", default=None, help="write a JSON status file (used by the scheduled workflow)"); a = ap.parse_args()
if a.download:
    for rel in ("mma/oddsapi_live.jsonl", "oddsapi/compact/mma.jsonl.gz"):
        BF.fetch(BF.ST_RAW + rel, Path(a.cache) / rel, timeout=300)
T = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
now = T(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
ev = json.loads(Path(a.event).read_text()); by = BF.load_odds(Path(a.cache)); idx = BF.index_odds(by); d = dt.date.fromisoformat(ev["date"])
stale = []; rows = []
for f in sorted(ev["fights"], key=lambda f: f["n"]):
    eid, fl = BF.find_odds(idx, by, f["a"]["name"], f["b"]["name"], d)
    if not eid: stale.append(f"{f['n']} {f['a']['name']} vs {f['b']['name']}: no archive record"); continue
    s = [x for x in by[eid] if x["books"]]; start = T(s[-1]["start"])
    # round 10: the archive's commence_time is an estimate (off by up to 85 min on UFC 334, both ways). Keep checking until the
    # LATER of it and the event file's start, so a bout listed early is not dropped while it is still being priced.
    if f.get("start"): start = max(start, T(f["start"].replace(" ", "T") + ("" if f["start"].endswith("Z") else "Z")))
    if now >= start: print(f"  {f['n']:>2} started; not checked"); continue
    t = s[-1]["t"]; age = (now - T(t)).total_seconds() / 3600
    print(f"  {f['n']:>2} {f['a']['name']} vs {f['b']['name']}: newest {t[:16]}Z, {age:.1f} h old"); rows.append({"n": f["n"], "bout": f"{f['a']['name']} vs {f['b']['name']}", "newest": t[:19] + "Z", "age_h": round(age, 2)})
    if age > a.max_age_h: stale.append(f"{f['n']} {f['a']['name']} vs {f['b']['name']}: {age:.1f} h")
if a.status:
    Path(a.status).write_text(json.dumps({"checked_at": now.isoformat()[:19] + "Z", "event": ev.get("name"), "max_age_h": a.max_age_h, "ok": not stale, "stale": stale, "bouts": rows}, indent=1))
if stale:
    print(f"ALERT: {len(stale)} bout(s) with no price in the last {a.max_age_h:g} h: " + "; ".join(stale)); sys.exit(1)
print(f"OK: every bout priced within {a.max_age_h:g} h")
