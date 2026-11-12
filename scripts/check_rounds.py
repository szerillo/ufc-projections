#!/usr/bin/env python3
"""Five-round check (Kirk round 15, call 3). Two modes.

pre  (default): the upcoming event file must build every main event and title bout as 5 rounds, and every bout in
     data/card_overrides.json "five_rounds" as 5 rounds. Within 72 h of the card's first bout, the card's overrides entry
     must carry a "five_rounds" key (an empty list means "checked, none"); a missing key fails.
post (--post): for final events, the built round count must match UFCStats "TIME FORMAT" (ufc_fight_results.csv).
Exit 1 on any failure, so friday_refresh.sh and the rehearsal stop.

  python3 scripts/check_rounds.py --slug ufc_334 --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json
  python3 scripts/check_rounds.py --post --cache .form_cache [--since 2026-01-01]
"""
import argparse, csv, datetime as dt, glob, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import card_overrides as CO  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def utc(x):
    return dt.datetime.fromisoformat(str(x).replace("Z", "+00:00").replace(" ", "T")).replace(tzinfo=dt.timezone.utc)


def pre(slug, event, now, ovr_path=CO.OVR_PATH):
    ev = json.load(open(event)); bad = []
    ovr = CO.load(slug, ovr_path) or {}
    fights = ev["fights"]
    main_n = max(f["n"] for f in fights)
    titles = ovr.get("title", []); fives = ovr.get("five_rounds")
    for f in fights:
        a, b = f["a"]["name"], f["b"]["name"]
        why = ("main event" if f["n"] == main_n else "title bout" if (f.get("title") or any(CO.bout_is(a, b, x, y) for x, y in titles))
               else "five_rounds flag" if any(CO.bout_is(a, b, x, y) for x, y in (fives or [])) else None)
        if why and f.get("sched") != 5:
            bad.append(f"{a} vs {b}: {why} built as {f.get('sched')} rounds")
    starts = [utc(f["start"]) for f in fights if f.get("start")]
    first = min(starts) if starts else utc(ev["date"] + "T22:00:00")
    hrs = (first - now).total_seconds() / 3600
    if fives is None and hrs <= 72:
        bad.append(f'card_overrides.json "{slug}" has no "five_rounds" key and the card starts in {hrs:.0f} h (set [] if UFC.com lists no other five-round bout)')
    return bad, hrs


def post(cache, since):
    res = list(csv.DictReader(open(Path(cache) / "ufc_fight_results.csv", encoding="utf-8")))
    fmt = {}
    for r in res:
        m = re.match(r"(\d+) Rnd", r["TIME FORMAT"].strip())
        a, b = [x.strip() for x in r["BOUT"].split(" vs. ")] if r["BOUT"].count(" vs. ") == 1 else (None, None)
        if m and a: fmt.setdefault(r["EVENT"].strip(), []).append((a, b, int(m.group(1))))
    bad = []; n = 0
    for p in sorted(glob.glob(str(REPO / "form/data/events/*.json"))):
        ev = json.load(open(p))
        if ev.get("status") != "final" or ev["date"] < since: continue
        rows = fmt.get(ev["name"].strip(), [])
        for f in ev["fights"]:
            hit = [s for a, b, s in rows if CO.bout_is(f["a"]["name"], f["b"]["name"], a, b)]
            if not hit or f.get("sched") is None: continue
            n += 1
            if hit[0] != f["sched"]: bad.append(f'{ev["date"]} {f["a"]["name"]} vs {f["b"]["name"]}: built {f["sched"]}, UFCStats {hit[0]}')
    return bad, n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug"); ap.add_argument("--event"); ap.add_argument("--post", action="store_true")
    ap.add_argument("--cache", default=str(REPO / ".form_cache")); ap.add_argument("--since", default="2022-01-01")
    ap.add_argument("--now", default=None, help="test only: pretend the time is this (UTC ISO)"); ap.add_argument("--overrides", default=str(CO.OVR_PATH))
    a = ap.parse_args()
    if a.post:
        bad, n = post(a.cache, a.since); print(f"ROUNDS POST-CARD: {n} final bouts since {a.since} compared with UFCStats Time format, {len(bad)} mismatches")
    else:
        now = utc(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
        bad, hrs = pre(a.slug, a.event, now, Path(a.overrides)); print(f"ROUNDS PRE-FIGHT: {a.slug}, card starts in {hrs:.0f} h, {len(bad)} failures")
    for x in bad: print("  FAIL " + x)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
