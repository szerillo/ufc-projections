#!/usr/bin/env python3
"""MP-1 plants (Kirk round 33). A typed D/I price that differs from the Feed row passes the opponent guard only if a
US-regulated book showed it (or better) for this bout in the 24 h before the export; otherwise the fight stays line_pending.
Fixtures: tonight's real export (published 2026-11-12T21:41:39Z, Medic -154 and Sanches -115 typed from the Listed report),
the odds feed on main at that time, and the two bouts' rows from sharp-tracker's odds archive (US-regulated books only, plus one
synthetic row from a book outside that list).   python3 -I scripts/test_manual_price.py   -> exit 1 on any failure"""
import copy, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ["MANUAL_PRICE_ARCHIVE"] = str(HERE / "fixtures/manual_price_archive.jsonl")
sys.path.insert(0, str(HERE)); import verify_projections as V  # noqa: E402
DOC = json.loads((HERE / "fixtures/ufc_334_projections_mp.json").read_text()); ODDS = json.loads((HERE / "fixtures/ufc_334_odds_mp.json").read_text())
res = []
def run(doc, archive=None):
    V._MP_ARCH.clear(); V.MANUAL.clear()
    if archive: os.environ["MANUAL_PRICE_ARCHIVE"] = archive
    try: hard, pending = V.split_pending(doc, V.opponent_errs(doc, doc["fights"], ODDS))
    finally: os.environ["MANUAL_PRICE_ARCHIVE"] = str(HERE / "fixtures/manual_price_archive.jsonl")
    return hard, pending, list(V.MANUAL)
def typed(fav, side, price):
    d = copy.deepcopy(DOC); f = next(x for x in d["fights"] if x["fav"] == fav); f["inputs"][side + "_odds"] = price; return d
def case(name, doc, want_pending, want_manual, archive=None, reason=None):
    hard, pending, man = run(doc, archive)
    ok = not hard and sorted(p["fav"] for p in pending) == sorted(want_pending) and sorted(m["fav"] for m in man) == sorted(want_manual) \
         and (reason is None or all(reason in p["reason"] for p in pending))
    res.append(("PASS " if ok else "FAIL ") + name + f" | pending {[p['fav'] + ': ' + p['reason'] for p in pending] or 'none'} | manual {[m['fav'] + ' ' + m['seen'] for m in man] or 'none'}" + (f" | hard {hard}" if hard else ""))
case("T1 tonight's export: Medic -154 and Sanches -115 typed from the Listed report -> both accepted as manual prices", DOC, [], ["Uros Medic", "Samuel Sanches"])
case("T2 typed -105 for Medic, no book showed it -> line_pending", typed("Uros Medic", "fav", -105), ["Uros Medic"], ["Samuel Sanches"], reason="no US-regulated book showed it")
case("T3 typed +200 for Holland (dog side), no book showed it -> line_pending", typed("Uros Medic", "dog", 200), ["Uros Medic"], ["Uros Medic", "Samuel Sanches"])
case("T4 typed -147 for Medic, a US price seen only before the 24 h window -> line_pending", typed("Uros Medic", "fav", -147), ["Uros Medic"], ["Samuel Sanches"])
case("T5 typed -110 for Medic, shown only by a book outside the US-regulated list -> line_pending", typed("Uros Medic", "fav", -110), ["Uros Medic"], ["Samuel Sanches"])
case("T6 odds archive unreachable -> both typed prices line_pending, never a silent pass", DOC, ["Uros Medic", "Samuel Sanches"], [], archive="UNREACHABLE", reason="archive unreachable")
d7 = copy.deepcopy(DOC); d7["published_at"] = "2026-11-15T21:41:39.598Z"
case("T7 same typed prices, export 3 days later (seen prices fall outside the window) -> line_pending", d7, ["Uros Medic", "Samuel Sanches"], [])
case("T8 control: the Feed row's own price (-150) needs no manual check", typed("Uros Medic", "fav", -150), [], ["Samuel Sanches"])
for r in res: print(r)
nf = sum(r.startswith("FAIL") for r in res); print(f"manual price (MP-1): {len(res) - nf}/{len(res)} as expected"); sys.exit(1 if nf else 0)
