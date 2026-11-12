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
from fighter_names import NAME_MATCH_JS, name_match  # noqa: E402

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
]


def old_py(a: str, b: str) -> bool:  # build_card_page.same() before Nov 11 (surname + first initial, no aliases)
    n = lambda s: " ".join(w for w in "".join(ch if "a" <= ch <= "z" else " " for ch in unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).split() if w not in ("jr", "ii", "iii"))
    ta, tb = n(a).split(), n(b).split()
    if not ta or not tb:
        return False
    if " ".join(ta) == " ".join(tb) or "".join(ta) == "".join(tb):
        return True
    return ta[-1] == tb[-1] and ta[0][0] == tb[0][0]


def run_js(pairs: list[tuple[str, str]]) -> list[bool]:
    js = NAME_MATCH_JS + "\nconst P = JSON.parse(require('fs').readFileSync(0, 'utf8'));\nconsole.log(JSON.stringify(P.map(([a, b]) => fighterNameMatch(a, b))));"
    out = subprocess.run(["node", "-e", js], input=json.dumps(pairs), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main() -> int:
    old = "--old" in sys.argv
    pairs = [(a, b, True) for a, b in MATCH] + [(a, b, False) for a, b in NO_MATCH]
    py = [old_py(a, b) if old else name_match(a, b) for a, b, _ in pairs]
    js = py if old else run_js([(a, b) for a, b, _ in pairs])
    fails = 0
    for (a, b, want), p, j in zip(pairs, py, js):
        ok = p == want and j == want
        fails += not ok
        if not ok or "-v" in sys.argv:
            print(f"{'ok  ' if ok else 'FAIL'} {a!r} vs {b!r}: want {want}, python {p}" + ("" if old else f", js {j}"))
    print(f"{'old matcher' if old else 'fighter_names'}: {len(pairs) - fails}/{len(pairs)} as expected")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
