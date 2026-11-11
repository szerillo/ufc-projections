#!/usr/bin/env python3
"""Fixture test for scripts/sheet_v47.py, run through verify_projections.check().

    python3 -I scripts/test_sheet_v47.py        # exit 0 pass, 1 fail

Why this exists: the 13 UFC 334 fights read from the sheet on 2026-11-11 cannot tell the two
2026-11-11 fixes apart from the code they replaced (audit block 35 falsifier). Every sheet-observed
late tag is on a favorite BET, and the only sharps dog is not D-coded. These fixtures cover the gap.

Provenance, stated plainly:
- "expected" values below are FORMULA-DERIVED from Main Card!N2 and Calculator!AA as read in the
  audit (flag order D -> SHARPS -> ...; fade keys off LEFT(AA,6)="SHARPS"; late tag only on favorite
  BET strings). They are not sheet output. If Sean enters this case in the sheet and it disagrees,
  the sheet wins and this fixture is wrong.
- Inputs are Evan Elder vs Samuel Sanches as read from the sheet, with the context code set to "D".
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_projections as V  # noqa: E402

ELDER = {"dog_odds": 102, "fav_odds": -110, "open_dog": 0.5439222685, "markov": 0.41, "shift": 0.1440028602,
         "tap": 0.32, "junk": 0.45, "tip": 0.6, "manual": None, "women": False}

FIXTURES = [
    # D-coded dog with sharps (tip 0.60) and fav edge 2.3 pts. The flag is the D flag, so the fade rule
    # does not fire and the late tag does not go on a lean. Old code: "BET ... (fade sharp dog) [late: ...]".
    {"name": "D-coded sharps dog, fav edge 2-3 pts, fav drift 6 pts",
     "dog": "Evan Elder", "fav": "Samuel Sanches", "inputs": {**ELDER, "ctx": "D"},
     "expected_flag": "DEBUTANT DOG - no dog bet", "expected_rec": "lean Samuel Sanches"},
    # Same fight as the sheet has it (no code): sheet-observed rec on 2026-11-11, kept as the control.
    {"name": "control: same fight, no code (sheet-observed)",
     "dog": "Evan Elder", "fav": "Samuel Sanches", "inputs": {**ELDER, "ctx": None},
     "expected_flag": "SHARPS ON DOG - no dog bet",
     "expected_rec": "BET Samuel Sanches (fade sharp dog) [late: fav moved 6% from open]"},
]


def main() -> int:
    fails = 0
    for fx in FIXTURES:
        r = V.S.row({**fx["inputs"], "dog": fx["dog"], "fav": fx["fav"]})
        doc = {"schema": 1, "slug": "fixture", "fights": [{
            "dog": fx["dog"], "fav": fx["fav"], "publish": True, "inputs": fx["inputs"],
            "sheet": {**{ok: r[rk] for rk, ok in V.NUM_KEYS}, "flag": fx["expected_flag"], "rec": fx["expected_rec"]}}]}
        errs = V.check(doc, Path("fixture_projections.json"))
        print(("PASS " if not errs else "FAIL ") + fx["name"])
        for e in errs:
            print("   ", e)
        fails += bool(errs)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
