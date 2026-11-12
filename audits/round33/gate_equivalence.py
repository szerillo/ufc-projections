"""Kirk round 33: MP-1 (verify_projections.manual_hit) vs the go-live Listed gate (build_line_history.listed_check) on the full
odds archive, for tonight's two typed prices and the plant prices. Run from the repo: python3 audits/round33/gate_equivalence.py <cache>"""
import json, os, sys
sys.path.insert(0, "scripts"); cache = sys.argv[1]
os.environ["MANUAL_PRICE_ARCHIVE"] = os.path.join(cache, "mma/oddsapi_live.jsonl")
import verify_projections as V, build_line_history as BL, build_form as BF
by_id = BF.load_odds(__import__("pathlib").Path(cache)); idx = BF.index_odds(by_id)
import datetime as dt
until = "2026-11-12T21:41:39Z"
cases = [("Uros Medic", "Kevin Holland", "fav", p) for p in (-154, -150, -147, -105, -110, -180)] + [("Samuel Sanches", "Evan Elder", "fav", p) for p in (-115, -110, -100)] + [("Uros Medic", "Kevin Holland", "dog", p) for p in (140, 130, 200)]
bad = 0
for fav, dog, side, p in cases:
    eid, fl = BF.find_odds(idx, by_id, fav, dog, dt.date(2026, 11, 14))
    lf, ld = (p, None) if side == "fav" else (None, p)
    r, _ = BL.listed_check(by_id[eid], fl, fav, lf, ld, until)
    gate = r["a" if side == "fav" else "b"]["ok"]
    mp = isinstance(V.manual_hit(fav if side == "fav" else dog, dog if side == "fav" else fav, p, until), tuple)
    bad += gate != mp
    print(f"{fav if side == 'fav' else dog:16} {p:+5d}  gate {'pass' if gate else 'fail':4}  MP-1 {'accept' if mp else 'pending':7}  {'same' if gate == mp else 'DIFFERENT'}")
print(f"gate vs MP-1: {len(cases) - bad}/{len(cases)} agree"); sys.exit(1 if bad else 0)
