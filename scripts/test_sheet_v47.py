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

import datetime as dt
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
        doc = {"schema": 1, "slug": "fixture", "prices_loaded": dt.datetime.now(dt.timezone.utc).isoformat(), "fights": [{
            "dog": fx["dog"], "fav": fx["fav"], "publish": True, "inputs": fx["inputs"],
            "sheet": {**{ok: r[rk] for rk, ok in V.NUM_KEYS}, "flag": fx["expected_flag"], "rec": fx["expected_rec"]}}]}
        errs = V.check(doc, Path("fixture_projections.json"))
        print(("PASS " if not errs else "FAIL ") + fx["name"])
        for e in errs:
            print("   ", e)
        fails += bool(errs)
    fails += method_cases()
    return 1 if fails else 0


# Method split and fight GTD (Block 44): Charles Radtke vs Stephen Thompson as read from the sheet on 2026-11-12 01:19Z
# (Prelims row 2, Calculator row 8). Expected values are the tab's own V:AB and Q (sheet output, not derived).
RADTKE = {"L": 0.4032602267, "mi": {"ap": 0.34, "aq": 0.4, "ad": 0.68, "ae": 0.25, "ah": 0.83, "ai": 0.17, "al": 0.474, "am": 0.333,
          "an": 0.193, "s": 0.5687832924663905, "cx": 0.5137, "cy": 0.4958, "ko_dog": 505.0, "sub_dog": 750.0, "ko_fav": 390.0,
          "sub_fav": 2200.0}, "b41": 0.5, "b45": 0.15,
          "method": {"dog": {"dec": 0.5335807519, "ko": 0.3077197945, "sub": 0.1586994536},
                     "fav": {"dec": 0.5498332427, "ko": 0.3846250137, "sub": 0.06554174364}}, "gtd": 0.5432792596}


def method_cases() -> int:
    fails = 0
    r = V.S.method_gtd(RADTKE["L"], {**RADTKE["mi"], "b41": RADTKE["b41"], "b45": RADTKE["b45"]})
    worst = max([abs(r[s][k] - RADTKE["method"][s][k]) for s in ("dog", "fav") for k in ("dec", "ko", "sub")] + [abs(r["gtd"] - RADTKE["gtd"])])
    ok = worst < 1e-9
    print(("PASS " if ok else "FAIL ") + f"method/GTD mirror reproduces the sheet (Radtke vs Thompson), worst diff {worst:.1e}")
    fails += not ok
    # the check must go red when one method share moves 3 pts and its partner moves back (sum still 1), and when GTD moves
    base = {"schema": 1, "slug": "fixture", "prices_loaded": dt.datetime.now(dt.timezone.utc).isoformat(),
            "params": {"b41": RADTKE["b41"], "b45": RADTKE["b45"]}}
    for name, mutate, want_red in (("method/GTD unchanged", lambda f: None, False),
                                   ("KO +3 / DEC -3 (sums to 1)", lambda f: (f["method"]["dog"].__setitem__("ko", f["method"]["dog"]["ko"] + 0.03), f["method"]["dog"].__setitem__("dec", f["method"]["dog"]["dec"] - 0.03)), True),
                                   ("GTD +3", lambda f: f.__setitem__("gtd", f["gtd"] + 0.03), True)):
        f = {"dog": "Charles Radtke", "fav": "Stephen Thompson", "sheet": {"true_dog": RADTKE["L"]}, "method_inputs": dict(RADTKE["mi"]),
             "method": {s: dict(v) for s, v in RADTKE["method"].items()}, "gtd": RADTKE["gtd"]}
        mutate(f)
        errs = [e for e in V.check({**base, "fights": [f]}, Path("fixture_projections.json")) if "GTD" in e or " dec " in e or " ko " in e or " sub " in e]
        ok = bool(errs) == want_red
        print(("PASS " if ok else "FAIL ") + f"check on {name}: {'red' if errs else 'green'}")
        fails += not ok
    return fails


if __name__ == "__main__":
    sys.exit(main())
