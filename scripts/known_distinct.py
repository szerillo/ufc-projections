#!/usr/bin/env python3
"""Which different UFCStats fighters does the loose name rule still join? Compares the answer with KNOWN_DISTINCT in
scripts/fighter_names.py. Run after each card (UFCStats adds debutants once they have fought):

    python3 -I scripts/known_distinct.py            # downloads the Greco1899 UFCStats mirror (same source as build_form.py)
    python3 -I scripts/known_distinct.py --dir D    # or reads ufc_fighter_details.csv from D

Exit 1 and prints the pairs to add when the list is out of date. Identical names (two "Bruno Silva" profiles) are
listed separately: no name rule can split them; the bout gate (the opponent) does.
"""
from __future__ import annotations

import csv
import io
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fighter_names as FN  # noqa: E402

URL = "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/ufc_fighter_details.csv"


def load(d: str | None) -> list[str]:
    text = Path(d, "ufc_fighter_details.csv").read_text(encoding="utf-8") if d else urllib.request.urlopen(URL, timeout=60).read().decode("utf-8")
    return [(r["FIRST"].strip() + " " + r["LAST"].strip()).strip() for r in csv.DictReader(io.StringIO(text))]


def loose_pairs(people: list[str]) -> tuple[set, set]:
    toks = [FN.tokens(p) for p in people]
    b = defaultdict(set)
    for i, t in enumerate(toks):
        if not t:
            continue
        b[("j", "".join(t))].add(i); b[("s", " ".join(sorted(t)))].add(i)
        if len(t) >= 2:
            s = t[-1]; b[("d", s)].add(i)
            for k in range(len(s)):
                b[("d", s[:k] + s[k + 1:])].add(i)
    merges, same = set(), set()
    for ids in b.values():
        ids = sorted(ids)
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                a, c = people[ids[x]], people[ids[y]]
                if FN.name_match(a, c):
                    (same if FN.raw_tokens(a) == FN.raw_tokens(c) else merges).add(tuple(sorted((a, c))))
    return merges, same


def main() -> int:
    d = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else None
    people = load(d)
    merges, same = loose_pairs(people)
    print(f"{len(people)} UFCStats fighters; loose matches between different names still standing: {len(merges)}; identical-name pairs: {len(same)}")
    for a, c in sorted(merges):
        print(f"  ADD to KNOWN_DISTINCT: ({a!r}, {c!r})")
    return 1 if merges else 0


if __name__ == "__main__":
    sys.exit(main())
