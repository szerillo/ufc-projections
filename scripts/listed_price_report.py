#!/usr/bin/env python3
"""Current US-regulated price for every Listed cell (Kirk round 18, call 4). REPORT ONLY: writes nothing in the repo (round 26: the live odds file goes to a temp scratch copy).

Run right before pasting Listed prices into the sheet:
    python3 scripts/listed_price_report.py --slug ufc_334 --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json

For each fighter: the Listed price in the current export, the best US-regulated price in the newest archive snapshot (and the
book), the US-regulated median, and whether the Listed price would pass the go-live gate if the sheet were republished NOW
(the gate looks for the Listed price, or better, at a US-regulated book in the 24 h before the export's publish time; it uses
build_line_history.listed_check, the same code as the gate). It first pulls the newest live odds file from sharp-tracker
(--no-fetch to skip). Only US-regulated books are read or shown.
"""
import argparse, datetime as dt, json, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_form as BF  # noqa: E402
import build_line_history as BL  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
NAME = {"draftkings": "DraftKings", "fanduel": "FanDuel", "betmgm": "BetMGM", "williamhill_us": "Caesars", "betrivers": "BetRivers", "circasports": "Circa"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", required=True); ap.add_argument("--event", required=True)
    ap.add_argument("--cache", default=str(REPO / ".form_cache")); ap.add_argument("--export", default=None); ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()
    cache = Path(a.cache)
    if not a.no_fetch:
        # Kirk round 26 call 2: read-only. The newest live odds file goes to a scratch copy of the cache (the rest of the
        # archive is linked read-only), so the repo's .form_cache, which the checks read, is never written.
        import tempfile, atexit, shutil
        scratch = Path(tempfile.mkdtemp(prefix="listed_report_")); atexit.register(shutil.rmtree, scratch, True)
        for sub in ("oddsapi",):
            if (cache / sub).exists(): (scratch / sub).symlink_to((cache / sub).resolve(), target_is_directory=True)
        (scratch / "mma").mkdir()
        BF.fetch(BF.ST_RAW + "mma/oddsapi_live.jsonl", scratch / "mma" / "oddsapi_live.jsonl", timeout=300)
        cache = scratch
    ev = json.loads(Path(a.event).read_text()); d = dt.date.fromisoformat(ev["date"])
    exp = json.loads(Path(a.export or REPO / "data/pending" / f"{a.slug}_projections.json").read_text())
    by_id = BF.load_odds(cache); idx = BF.index_odds(by_id)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    newest = max(s["t"] for v in by_id.values() for s in v)
    print(f"LISTED PRICE REPORT {a.slug} at {now} UTC (report only). Archive newest snapshot {newest[:16]} UTC; export published {exp.get('published_at', '?')[:16]}")
    # Kirk round 19 C: never show an old price as "now". A bout whose newest US-regulated snapshot is older than STALE_H shows
    # UNKNOWN; a US-regulated book that priced the bout in the last 24 h but is missing from the newest snapshot is named.
    STALE_H = 4.0
    tnow = dt.datetime.now(dt.timezone.utc); age_h = lambda t: (tnow - BL.ts(t if t.endswith("Z") else t + "Z")).total_seconds() / 3600
    if age_h(newest) > STALE_H:
        print(f"!!! ARCHIVE STALE: newest snapshot is {age_h(newest):.1f} h old (limit {STALE_H:.0f} h). Every price below is UNKNOWN until the odds archive updates.")
    print(f"{'Fighter':26} {'Listed':>7} {'Best US now':>12} {'Book':10} {'US median':>9} {'Snapshot':>11}  Passes if republished now?")
    fails = []
    for pf in exp["fights"]:
        fav, dog = pf["fav"], pf["dog"]
        eid, fl = BF.find_odds(idx, by_id, fav, dog, d)
        if not eid:
            print(f"{fav + ' / ' + dog:26} no archive match"); continue
        snaps = by_id[eid]
        res, _ = BL.listed_check(snaps, fl, fav, pf["inputs"].get("fav_odds"), pf["inputs"].get("dog_odds"), now + "Z")
        last = next((s for s in reversed(snaps) if set(BL.side_prices(s, fav, fl)) & set(BL.REG)), None)
        for sd, nm, key in (("a", fav, "fav_odds"), ("b", dog, "dog_odds")):
            L = pf["inputs"].get(key)
            stale = last is None or age_h(last["t"]) > STALE_H
            recent = {b for s_ in snaps if age_h(s_["t"]) <= 24 for b in BL.side_prices(s_, fav, fl) if b in BL.REG}
            missing = sorted(NAME.get(b, b) for b in recent - set(BL.side_prices(last, fav, fl) if last else {}))
            if stale:
                ago = f"{age_h(last['t']):.1f} h ago" if last else "never"
                print(f"{nm:26} {(f'{L:+d}' if L is not None else '-'):>7} {'UNKNOWN':>12} {'-':10} {'-':>9} {'stale':>11}  UNKNOWN: last US-regulated price {ago}")
                fails.append(f"{nm} (unknown)"); continue
            if last:
                pr = {b: v for b, v in BL.side_prices(last, fav, fl).items() if b in BL.REG}
                ams = {b: BL.am(v[0] if sd == "a" else v[1]) for b, v in pr.items()}
                dec = lambda m: 1 + (m / 100 if m > 0 else 100 / -m)
                bb = max(ams, key=lambda b: dec(ams[b])); med = BL.am(statistics.median((v[0] if sd == "a" else v[1]) for v in pr.values()))
                best = f"{ams[bb]:+d}"; book = NAME.get(bb, bb); medt = f"{med:+d}"; snap = last["t"][5:16].replace("T", " ")
            else:
                best = book = medt = snap = "-"
            ok = res[sd]["ok"]
            if not ok: fails.append(f"{nm} {L:+d}" if L is not None else nm)
            note = f"  [missing now, priced in last 24 h: {', '.join(missing)}]" if missing else ""
            print(f"{nm:26} {(f'{L:+d}' if L is not None else '-'):>7} {best:>12} {book:10} {medt:>9} {snap:>11}  {'yes' if ok else 'NO: paste a current US-regulated price'}{note}")
    print(f"\n{len(fails)} Listed cell(s) would fail the gate or are UNKNOWN: {', '.join(fails) or 'none'}")


if __name__ == "__main__":
    main()
