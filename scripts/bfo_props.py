"""Parse a BFO props read-back ({slug}_props.txt from scripts/collect/bfo_props.js) into
de-vigged market numbers per bout. Paper output only: prints a table and, with --json, writes
a JSON file. Nothing here writes to the sheet or the site.

Method (same as the sheet and the odds archive): per book, two-sided multiplicative de-vig
(p_i / (p_a + p_b)); a book counts only if it prices both sides. Consensus = median across
counted books. Prediction markets (PM, KA) are reported in their own column and are not in
the sportsbook median.

Caveat printed with the output: BetRivers and Unibet both run on Kambi and usually post the
same prop prices, so two of them are one opinion, not two.

    python3 -I scripts/bfo_props.py data_in/ufc334_props.txt [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys

EXCHANGES = {"PM", "KA"}
KAMBI = {"BR", "UB"}


def implied(odds: int) -> float:
    return 100 / (odds + 100) if odds > 0 else -odds / (-odds + 100)


def parse_prices(cell: str) -> dict[str, int]:
    out = {}
    for tok in filter(None, cell.split(",")):
        m = re.fullmatch(r"([A-Z]{2,4})([+-]\d+)", tok.strip())
        if m:                      # 'BWn/a' and other non-prices are skipped
            out[m.group(1)] = int(m.group(2))
    return out


def read(path: str) -> dict:
    bouts: dict = {}
    cur = None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("H;"):
            continue
        if line.startswith("#"):
            cur = bouts.setdefault(line[1:], {"ml": {}, "props": {}})
            continue
        kind, label, cells = (line.split(";", 2) + ["", ""])[:3]
        if cur is None:
            continue
        (cur["ml"] if kind == "M" else cur["props"])[label] = parse_prices(cells)
    return bouts


def devig(a: dict, b: dict) -> dict[str, float]:
    """Book -> de-vigged P(side a), books pricing both sides only."""
    out = {}
    for bk in set(a) & set(b):
        pa, pb = implied(a[bk]), implied(b[bk])
        out[bk] = pa / (pa + pb)
    return out


def consensus(per_book: dict[str, float]) -> dict:
    books = {k: v for k, v in per_book.items() if k not in EXCHANGES}
    ex = {k: v for k, v in per_book.items() if k in EXCHANGES}
    indep = len(books) - (1 if KAMBI <= set(books) else 0)
    return {
        "median": round(statistics.median(books.values()), 4) if books else None,
        "books": sorted(books), "independent_books": indep,
        "exchanges": {k: round(v, 4) for k, v in sorted(ex.items())},
    }


def summarize(bouts: dict) -> dict:
    res = {}
    for key, b in bouts.items():
        r = {}
        names = list(b["ml"])
        if len(names) == 2:
            r["ml_first"] = names[0]
            r["ml"] = consensus(devig(b["ml"][names[0]], b["ml"][names[1]]))
        p = b["props"]
        if "GTD" in p and "ITD" in p:
            r["gtd"] = consensus(devig(p["GTD"], p["ITD"]))
        for line in ("1.5", "2.5", "3.5", "4.5"):
            if f"O{line}" in p and f"U{line}" in p:
                r[f"over_{line}"] = consensus(devig(p[f"O{line}"], p[f"U{line}"]))
        res[key] = r
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("props_txt")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = summarize(read(a.props_txt))
    def f(x):
        return "  --  " if not x or x.get("median") is None else f"{100 * x['median']:5.1f}%"
    print(f"{'bout':42s} {'ML 1st':>7s} {'GTD':>7s} {'O1.5':>7s} {'O2.5':>7s} {'O4.5':>7s}  books(GTD)")
    for k, r in res.items():
        g = r.get("gtd") or {}
        print(f"{k[:42]:42s} {f(r.get('ml')):>7s} {f(r.get('gtd')):>7s} {f(r.get('over_1.5')):>7s} "
              f"{f(r.get('over_2.5')):>7s} {f(r.get('over_4.5')):>7s}  {','.join(g.get('books', []))}"
              f"{' (Kambi pair = 1 view)' if KAMBI <= set(g.get('books', [])) else ''}")
    no_props = [k for k, r in res.items() if "gtd" not in r]
    if no_props:
        print("no GTD market yet:", "; ".join(no_props))
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
