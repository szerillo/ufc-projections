#!/usr/bin/env python3
"""Five-round check (Kirk round 15, call 3). Two modes.

pre  (default): the upcoming event file must build every main event and title bout as 5 rounds, and every bout in
     data/card_overrides.json "five_rounds" as 5 rounds. Within 72 h of the card's first bout, the card's overrides entry
     must carry a "five_rounds" key (an empty list means "checked, none"); a missing key fails.
post (--post): for final events, the round count the site showed before the card (newest committed "upcoming" version
     of the event file) must match UFCStats "TIME FORMAT". Fails when there is nothing to compare (a vacuous pass).
Exit 1 on any failure, so friday_refresh.sh and the rehearsal stop.

  python3 scripts/check_rounds.py --slug ufc_334 --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json
  python3 scripts/check_rounds.py --post --cache .form_cache [--since 2026-01-01]
"""
import argparse, csv, datetime as dt, glob, json, re, subprocess, sys
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
    # Kirk round 16 A: two independent sources for the five-round list; any disagreement makes the flag UNVERIFIED (fails)
    srcs = {k: v for k, v in (ovr.get("five_rounds_sources") or {}).items() if not k.startswith("_")}
    if fives is not None and len(srcs) < 2:
        bad.append(f'five_rounds is set but has {len(srcs)} source(s) in five_rounds_sources; two are required')
    def bout_key(x, y):
        hit = next((f for f in fights if CO.bout_is(f["a"]["name"], f["b"]["name"], x, y)), None)
        return hit["n"] if hit else f"{x} vs {y} (not on card)"
    sets = {k: sorted({bout_key(x, y) for x, y in v}, key=str) for k, v in srcs.items()}
    if len({json.dumps(v) for v in sets.values()}) > 1:
        bad.append("five_rounds UNVERIFIED: sources disagree: " + "; ".join(f"{k.split(',')[0]} -> {v}" for k, v in sets.items()))
    elif sets and fives is not None:
        non_title = {n for n in next(iter(sets.values())) if isinstance(n, int) and n != main_n
                     and not any(CO.bout_is(f["a"]["name"], f["b"]["name"], x, y) for f in fights if f["n"] == n for x, y in titles)
                     and not next(f for f in fights if f["n"] == n).get("title")}
        flagged = {bout_key(x, y) for x, y in fives}
        if non_title != flagged:
            bad.append(f"five_rounds {sorted(flagged, key=str)} does not match the sources' non-title five-round bouts {sorted(non_title, key=str)}")
    starts = [utc(f["start"]) for f in fights if f.get("start")]
    first = min(starts) if starts else utc(ev["date"] + "T22:00:00")
    hrs = (first - now).total_seconds() / 3600
    if fives is None and hrs <= 72:
        bad.append(f'card_overrides.json "{slug}" has no "five_rounds" key and the card starts in {hrs:.0f} h (set [] if UFC.com lists no other five-round bout)')
    return bad, hrs


def prefight_versions(rel, ref):
    """Kirk round 16 D: the round count the site showed BEFORE the card. A final event file is rebuilt from UFCStats, whose
    "TIME FORMAT" is the very field this check compares against, so the final file can never disagree (vacuous pass).
    The comparison uses the newest committed version of the file whose status was still "upcoming"."""
    hs = subprocess.run(["git", "-C", str(REPO), "log", "--format=%H", ref, "--", rel], capture_output=True, text=True).stdout.split()
    for h in hs:
        try: d = json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{h}:{rel}"], capture_output=True, text=True, check=True).stdout)
        except Exception: continue
        if d.get("status") == "upcoming": return h, d
    return None, None


def post(cache, since, ref="HEAD"):
    res = list(csv.DictReader(open(Path(cache) / "ufc_fight_results.csv", encoding="utf-8")))
    fmt = {}
    for r in res:
        m = re.match(r"(\d+) Rnd", r["TIME FORMAT"].strip())
        a, b = [x.strip() for x in r["BOUT"].split(" vs. ")] if r["BOUT"].count(" vs. ") == 1 else (None, None)
        if m and a: fmt.setdefault(r["EVENT"].strip(), []).append((a, b, int(m.group(1))))
    bad = []; n = 0; ev_n = ev_pre = 0; unmatched = 0
    for p in sorted(glob.glob(str(REPO / "form/data/events/*.json"))):
        ev = json.load(open(p))
        if ev.get("status") != "final" or ev["date"] < since: continue
        ev_n += 1
        rel = str(Path(p).relative_to(REPO)); h, pre_ = prefight_versions(rel, ref)
        if not pre_: continue
        ev_pre += 1; rows = fmt.get(ev["name"].strip(), [])
        for f in pre_["fights"]:
            hit = [s for a, b, s in rows if CO.bout_is(f["a"]["name"], f["b"]["name"], a, b)]
            if not hit: unmatched += 1; continue
            if f.get("sched") is None: continue
            n += 1
            if hit[0] != f["sched"]: bad.append(f'{ev["date"]} {f["a"]["name"]} vs {f["b"]["name"]}: shown pre-fight as {f["sched"]} rounds (commit {h[:8]}), UFCStats {hit[0]}')
    print(f"  final events since {since}: {ev_n}; with a committed pre-fight (upcoming) version: {ev_pre}; pre-fight bouts with no UFCStats match: {unmatched}")
    if n == 0:
        bad.append("nothing to compare: no final event has a committed pre-fight version (a 0-mismatch result here would be vacuous)")
    return bad, n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug"); ap.add_argument("--event"); ap.add_argument("--post", action="store_true")
    ap.add_argument("--cache", default=str(REPO / ".form_cache")); ap.add_argument("--since", default="2022-01-01"); ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--now", default=None, help="test only: pretend the time is this (UTC ISO)"); ap.add_argument("--overrides", default=str(CO.OVR_PATH))
    a = ap.parse_args()
    if a.post:
        bad, n = post(a.cache, a.since, a.ref); print(f"ROUNDS POST-CARD: {n} pre-fight bouts compared with UFCStats Time format, {len(bad)} failures")
    else:
        now = utc(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
        bad, hrs = pre(a.slug, a.event, now, Path(a.overrides)); print(f"ROUNDS PRE-FIGHT: {a.slug}, card starts in {hrs:.0f} h, {len(bad)} failures")
    for x in bad: print("  FAIL " + x)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
