#!/usr/bin/env python3
"""Fixture test for the fighter-name rule, run on the Python copy and on the JS copy (node) so they cannot drift.

    python3 -I scripts/test_fighter_names.py            # exit 0 = every pair as expected in both languages
    python3 -I scripts/test_fighter_names.py --old      # the pre-Nov-11 matchers, for comparison (expected to fail)

Pairs: every UFC 334 spelling difference seen between the page roster, the sheet and the odds feed; spellings the
feed has used on earlier cards; made-up next misspellings (one letter off, short first names); and pairs that must
NOT match (different fighters who share a surname).
"""
from __future__ import annotations

import json
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fighter_names import NAME_MATCH_JS, bout_slots, name_match, strict_match  # noqa: E402

MATCH = [
    ("Charles Radtke", "Charlie Radke"), ("Chris Duncan", "Christopher Duncan"), ("Terrance McKinney", "Terrance Mckinney"),
    ("Alatengheili", "Alateng Heili"), ("Uros Medic", "Uroš Medić"), ("Josh Hokit", "Joshua Hokit"),
    ("Alex Pereira", "Alexander Pereira"), ("Mike Malott", "Michael Malott"), ("Tom Nolan", "Thomas Nolan"),
    ("Kai Kamaka III", "Kai Kamaka"), ("Wang Cong", "Cong Wang"), ("Allen Frye Jr.", "Allen Frye"),
    ("Doo Ho Choi", "Dooho Choi"), ("Jose Delano", "José Delano"), ("Joe Kropschot", "Joseph Kropschot"),
    # made-up next misspellings: one letter off in a 5+ letter surname, short first names
    ("Kevin Holland", "Kevin Holand"), ("Stephen Thompson", "Steve Thomson"), ("Melquizael Costa", "Melquizael Costta"),
    ("Samuel Sanches", "Sam Sanchez"), ("Cesar Almeida", "Cesar Almedia"),
]
NO_MATCH = [
    ("Josh Hokit", "Jake Hokit"), ("Yana Santos", "Luana Santos"), ("Daniel Santos", "Yana Santos"),
    ("Mike Malott", "Mitch Malott"), ("Kevin Holland", "Kevin Holloway"), ("Juan Diaz", "Nate Diaz"),
    ("Ciryl Gane", "Tom Aspinall"), ("Bia Mesquita", "Bia Mesquite Silva"), ("Jim Miller", "Jim Muller Jones"),
    # different people the first version of the rule merged (pairwise run over all 4,628 UFCStats fighters, Block 41)
    ("Chris Duncan", "Christian Leroy Duncan"), ("Sangwook Kim", "SangWon Kim"), ("SeungWoo Choi", "SeungGuk Choi"),
    ("Shane Young", "Shanna Young"), ("Jorge de Oliveira", "Jorge Oliveira"), ("Min Soo Kim", "MinWoo Kim"),
    ("Jong Wang Kim", "Jong Won Kim"), ("Jong Wang Kim", "Jong Man Kim"), ("Jong Won Kim", "Jong Man Kim"),
]
# strict tier: (a, b, strict?) -- a loose-only match must never stand alone
STRICT = [("Alatengheili", "Alateng Heili", True), ("Wang Cong", "Cong Wang", True), ("Uros Medic", "Uroš Medić", True),
          ("Terrance McKinney", "Terrance Mckinney", True), ("Lance Gibson", "Lance Gibson Jr.", False),
          ("Charles Radtke", "Charlie Radke", False), ("Chris Duncan", "Christopher Duncan", False)]
# bouts: (page a, page b, other a, other b, expected slots)
BOUTS = [("Charles Radtke", "Stephen Thompson", "Charlie Radke", "Stephen Thompson", "same"),
         ("Chris Duncan", "Drew Dober", "Drew Dober", "Christopher Duncan", "swap"),
         ("Alatengheili", "Juan Diaz", "Alateng Heili", "Juan Diaz", "same"),
         ("Ciryl Gane", "Josh Hokit", "Ciryl Gane", "Jake Hokit", None),             # late replacement, same surname
         ("Charles Radtke", "Stephen Thompson", "Charlie Radke", "Steve Thomson", None),  # both names off: no bout
         ("Chris Duncan", "Drew Dober", "Christian Leroy Duncan", "Drew Dober", None)]


def old_py(a: str, b: str) -> bool:  # build_card_page.same() before Nov 11 (surname + first initial, no aliases)
    n = lambda s: " ".join(w for w in "".join(ch if "a" <= ch <= "z" else " " for ch in unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).split() if w not in ("jr", "ii", "iii"))
    ta, tb = n(a).split(), n(b).split()
    if not ta or not tb:
        return False
    if " ".join(ta) == " ".join(tb) or "".join(ta) == "".join(tb):
        return True
    return ta[-1] == tb[-1] and ta[0][0] == tb[0][0]


def run_js(pairs, strict, bouts):
    js = NAME_MATCH_JS + """
const D = JSON.parse(require('fs').readFileSync(0, 'utf8'));
console.log(JSON.stringify([D.p.map(([a, b]) => fighterNameMatch(a, b)), D.s.map(([a, b]) => fighterStrictMatch(a, b)),
                            D.b.map(([a, b, c, d]) => fighterBoutSlots(a, b, c, d))]));"""
    out = subprocess.run(["node", "-e", js], input=json.dumps({"p": pairs, "s": strict, "b": bouts}), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main() -> int:
    old = "--old" in sys.argv
    pairs = [(a, b, True) for a, b in MATCH] + [(a, b, False) for a, b in NO_MATCH]
    py = [old_py(a, b) if old else name_match(a, b) for a, b, _ in pairs]
    if old:
        js = py
    else:
        js, js_s, js_b = run_js([(a, b) for a, b, _ in pairs], [(a, b) for a, b, _ in STRICT], [x[:4] for x in BOUTS])
    fails = 0
    for (a, b, want), p, j in zip(pairs, py, js):
        ok = p == want and j == want
        fails += not ok
        if not ok or "-v" in sys.argv:
            print(f"{'ok  ' if ok else 'FAIL'} {a!r} vs {b!r}: want {want}, python {p}" + ("" if old else f", js {j}"))
    n = len(pairs)
    if not old:
        for (a, b, want), j in zip(STRICT, js_s):
            p = strict_match(a, b); ok = p == want and j == want; fails += not ok; n += 1
            if not ok or "-v" in sys.argv:
                print(f"{'ok  ' if ok else 'FAIL'} strict {a!r} vs {b!r}: want {want}, python {p}, js {j}")
        for (a, b, c, d, want), j in zip(BOUTS, js_b):
            p = bout_slots(a, b, c, d); ok = p == want and j == want; fails += not ok; n += 1
            if not ok or "-v" in sys.argv:
                print(f"{'ok  ' if ok else 'FAIL'} bout {a} vs {b} / {c} vs {d}: want {want}, python {p}, js {j}")
    print(f"{'old matcher' if old else 'fighter_names'}: {n - fails}/{n} as expected"
          + ("" if old else f" ({len(MATCH)} must-match and {len(NO_MATCH)} must-not-match names, {len(STRICT)} strict-tier, {len(BOUTS)} bouts)"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
