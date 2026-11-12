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


def src(dog, fav, inp, **over):
    """The Feed row a correct publish exports as price_source (Block 46, OPP-1)."""
    return {"order": 13, "dog": dog, "fav": fav, "best_dog": f"{inp['dog_odds']:+d} FanDuel", "best_fav": f"{inp['fav_odds']:+d} BetRivers",
            "cons_dog": "", "cons_fav": "", **over}


def odds(*names):
    """A minimal BettingPros odds file with one bout per pair of names (OPP-2)."""
    return {"fights": [{"fighter_a": {"name": a}, "fighter_b": {"name": b}} for a, b in zip(names[::2], names[1::2])]}


def main() -> int:
    fails = 0
    for fx in FIXTURES:
        r = V.S.row({**fx["inputs"], "dog": fx["dog"], "fav": fx["fav"]})
        doc = {"schema": 1, "slug": "fixture", "prices_loaded": dt.datetime.now(dt.timezone.utc).isoformat(), "fights": [{
            "dog": fx["dog"], "fav": fx["fav"], "publish": True, "inputs": fx["inputs"],
            "sheet": {**{ok: r[rk] for rk, ok in V.NUM_KEYS}, "flag": fx["expected_flag"], "rec": fx["expected_rec"]},
            "price_source": src(fx["dog"], fx["fav"], fx["inputs"])}]}
        errs = V.check(doc, Path("fixture_projections.json"), odds_doc=odds(fx["dog"], fx["fav"]))
        print(("PASS " if not errs else "FAIL ") + fx["name"])
        for e in errs:
            print("   ", e)
        fails += bool(errs)
    fails += method_cases()
    fails += stamp_cases()
    fails += opponent_cases()
    fails += pending_cases()
    fails += drift_cases()
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


def stamp_cases() -> int:
    """The Feed 'Loaded' stamp is written in the sheet's time zone (America/New_York); the script exports it with
    toISOString(), i.e. UTC with a Z. A refresh at 11:30 pm ET on Nov 12 is 04:30 UTC on Nov 13 (the UTC date has moved)."""
    now = dt.datetime(2026, 11, 13, 5, 0, tzinfo=dt.timezone.utc)          # 12:00 am ET Nov 13
    cases = [("written 11:30 pm ET, exported as UTC Z", "2026-11-13T04:30:00.000Z", "green", 0.5),
             ("same moment with an explicit -05:00 offset", "2026-11-12T23:30:00-05:00", "green", 0.5),
             ("same wall-clock time with no offset", "2026-11-12T23:30:00", "red", None),
             ("written 11:30 pm ET the night before (Nov 11)", "2026-11-12T04:30:00.000Z", "red", 24.5),
             ("11:30 pm ET read as if it were UTC (the mistake to avoid)", "2026-11-12T23:30:00Z", "red", 5.5)]
    fails = 0
    for name, stamp, want, hours in cases:
        doc = {"schema": 1, "slug": "fixture", "prices_loaded": stamp, "fights": [{"dog": "a b", "fav": "c d", "publish": True,
               "inputs": {"dog_odds": 150, "fav_odds": -170}, "sheet": {}}]}
        errs = [e for e in V.check(doc, Path("fixture_projections.json"), now=now) if "prices" in e]
        try:
            age = V.price_age_h(doc, now)
        except ValueError:
            age = None
        got = "red" if errs else "green"
        ok = got == want and (hours is None or abs(age - hours) < 1e-9)
        print(("PASS " if ok else "FAIL ") + f"stamp {stamp:28} ({name}): age {age if age is None else round(age, 2)} h -> {got}")
        fails += not ok
    return fails


def opponent_cases() -> int:
    """Opponent-match guard (pre-registered Block 46). Alatengheili replaced Adrian Yanez against Juan Diaz; the DK DFS list
    still pairs Diaz with Yanez. The price must come from the Feed row for this bout, and the bout must be in the odds file."""
    inp = {"dog_odds": 275, "fav_odds": -335}
    feed = odds("Alateng Heili", "Juan Diaz")                     # BettingPros spells it in two words
    cases = [("Diaz priced from his own bout", src("Alatengheili", "Juan Diaz", inp), "Alatengheili", feed, False),
             ("Diaz priced from a Yanez vs Diaz row", src("Adrian Yanez", "Juan Diaz", inp), "Alatengheili", feed, True),
             ("names right, Feed price +300 vs input +275", src("Alatengheili", "Juan Diaz", inp, best_dog="+300 FanDuel"), "Alatengheili", feed, True),
             ("blank best price falls back to consensus 275", src("Alatengheili", "Juan Diaz", inp, best_dog="", cons_dog="275"), "Alatengheili", feed, False),
             ("fight listed as Yanez vs Diaz (not in odds file)", src("Adrian Yanez", "Juan Diaz", inp), "Adrian Yanez", feed, True),
             ("no price_source (old script)", None, "Alatengheili", feed, True),
             ("no odds file", src("Alatengheili", "Juan Diaz", inp), "Alatengheili", None, True)]
    fails = 0
    for name, ps, dog, od, want_red in cases:
        f = {"dog": dog, "fav": "Juan Diaz", "inputs": inp}
        if ps is not None:
            f["price_source"] = ps
        errs = V.opponent_errs({"slug": "fixture"}, [f], od)
        ok = bool(errs) == want_red
        print(("PASS " if ok else "FAIL ") + f"opponent guard, {name}: {'red' if errs else 'green'}")
        fails += not ok
    return fails


def pending_cases() -> int:
    """Line pending (pre-registered Block 47): opponent-guard errors hold one bout back; anything else stays whole-file red."""
    doc = {"fights": [{"dog": "Alatengheili", "fav": "Juan Diaz"}, {"dog": "Evan Elder", "fav": "Samuel Sanches"}]}
    opp = "Alatengheili vs Juan Diaz: price taken from Feed row 12 'Adrian Yanez vs Juan Diaz', whose dog is not Alatengheili (OPP-1)"
    cases = [("only Diaz fails the guard", [opp], 0, 1), ("Diaz guard + a number off on Elder", [opp, "Evan Elder vs Samuel Sanches: true_dog sheet 1 vs 2"], 1, 1),
             ("odds file missing", ["odds file data/x_odds.json missing or unreadable, so no fight can be matched to a real bout (OPP-2)"], 1, 0),
             ("both fights fail the guard", [opp, "Evan Elder vs Samuel Sanches: no such bout in data/x_odds.json (OPP-2)"], 1, 2)]
    fails = 0
    for name, errs, want_hard, want_pend in cases:
        hard, pend = V.split_pending(doc, errs)
        ok = (len(hard) > 0) == (want_hard > 0) and len(pend) == want_pend
        print(("PASS " if ok else "FAIL ") + f"line pending, {name}: {'red' if hard else 'green'}, {len(pend)} pending")
        fails += not ok
    return fails


def drift_cases() -> int:
    """Frozen-shift drift note (pre-registered Block 50): a note above 0.001, never a failure."""
    B = 0.14693199554239184
    cases = [("equal", B, True and False), ("+0.0011", B + 0.0011, True), ("+0.0009", B + 0.0009, False), ("absent", None, False)]
    fails = 0
    for name, mean, want in cases:
        doc = {"params": {"shift": B, **({"shift_card_mean": mean} if mean is not None else {})}}
        got = V.drift_note(doc) is not None
        ok = got == want
        print(("PASS " if ok else "FAIL ") + f"drift note, card mean {name}: {'note' if got else 'no note'}")
        fails += not ok
    return fails


if __name__ == "__main__":
    sys.exit(main())
