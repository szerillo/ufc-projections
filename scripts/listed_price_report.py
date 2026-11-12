#!/usr/bin/env python3
"""Current US-regulated price for every Listed cell (Kirk round 18, call 4). REPORT ONLY: writes nothing, changes nothing.

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
        BF.fetch(BF.ST_RAW + "mma/oddsapi_live.jsonl", cache / "mma" / "oddsapi_live.jsonl", timeout=300)
    ev = json.loads(Path(a.event).read_text()); d = dt.date.fromisoformat(ev["date"])
    exp = json.loads(Path(a.export or REPO / "data/pending" / f"{a.slug}_projections.json").read_text())
    by_id = BF.load_odds(cache); idx = BF.index_odds(by_id)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    newest = max(s["t"] for v in by_id.values() for s in v)
    print(f"LISTED PRICE REPORT {a.slug} at {now} UTC (report only). Archive newest snapshot {newest[:16]} UTC; export published {exp.get('published_at', '?')[:16]}")
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
            print(f"{nm:26} {(f'{L:+d}' if L is not None else '-'):>7} {best:>12} {book:10} {medt:>9} {snap:>11}  {'yes' if ok else 'NO: paste a current US-regulated price'}")
    print(f"\n{len(fails)} Listed cell(s) would fail the gate if republished now: {', '.join(fails) or 'none'}")


if __name__ == "__main__":
    main()
