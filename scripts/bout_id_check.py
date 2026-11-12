#!/usr/bin/env python3
"""One bout, one number (Block 54). Every public surface that numbers UFC card bouts must give a bout the same number.

    python3 -I scripts/bout_id_check.py --event form/data/events/<event>.json --odds data/<slug>_odds.json \
        [--page <slug>_fight_form.html] [--embed embed.html --embed-key <slug>] [--keys extra.json]

Surfaces: the site event file (fight-page URLs #/fight/<event>/<n>), the BettingPros odds file the live overlay reads,
the card page's FIGHTS, the embed builder roster, and any extra key list ({"14": "Ciryl Gane vs Josh Hokit", ...}, e.g.
a visual layer's keys). Bouts are matched by fighter names (scripts/fighter_names.py; surnames for the embed roster).
RED (exit 1) when a bout gets two different numbers, or a key names a bout that is not on the card.
Block 55: the site event file's n is a URL id (#/fight/<event>/<n>), kept stable so shared and Labs links keep opening
the same bout. It is checked for identity only (each id names exactly one bout on the card), not for number agreement.
The site shows the card number (13 = main event) from bout order, not from n.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fighter_names as FN  # noqa: E402

nm = lambda x: x["name"] if isinstance(x, dict) else x


def same(a, b, A, B) -> bool:
    if FN.bout_slots(a, b, A, B):
        return True
    # surname-only rosters: a surname matches a full name if it is its last token, its letters joined (Alateng Heili),
    # or one edit away in 5+ letters (the feed spells Radtke "Radke")
    def sur(x, full):
        t, T = FN.tokens(x), FN.tokens(full)
        if not t or not T: return False
        s, L = t[-1], T[-1]
        return s == L or s == "".join(T) or "".join(t) == "".join(T) or (min(len(s), len(L)) >= 5 and FN._edit1(s, L))
    return (sur(a, A) and sur(b, B)) or (sur(a, B) and sur(b, A))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", required=True); ap.add_argument("--odds", required=True)
    ap.add_argument("--page"); ap.add_argument("--embed"); ap.add_argument("--embed-key"); ap.add_argument("--keys")
    a = ap.parse_args()
    S = {"site event file (URL ids)": [(f["n"], nm(f["a"]), nm(f["b"])) for f in json.loads(Path(a.event).read_text())["fights"]],
         "odds file": [(f["n"], f["fighter_a"]["name"], f["fighter_b"]["name"]) for f in json.loads(Path(a.odds).read_text())["fights"]]}
    if a.page:
        page = Path(a.page).read_text()
        S["card page"] = [(int(n), x, y) for n, x, y in re.findall(r'n: (\d+), card:.*?\n\s+a: \{ name: "([^"]+)".*?\n\s+b: \{ name: "([^"]+)"', page)]
    if a.embed:
        emb = Path(a.embed).read_text(); blk = emb[emb.index(f"{a.embed_key}: ["):]; blk = blk[:blk.index("],")]
        S["embed builder"] = [(int(n), m.split(" vs ")[0], m.split(" vs ")[1]) for n, m in re.findall(r'n: (\d+), matchup: "([^"]+)"', blk)]
    if a.keys:
        S["extra keys"] = [(int(k), v.split(" vs ")[0], v.split(" vs ")[1]) for k, v in json.loads(Path(a.keys).read_text()).items()]
    base = S["odds file"]
    bad, n = [], 0
    for surf, rows in S.items():
        for num, x, y in rows:
            n += 1
            hit = [bn for bn, A, B in base if same(x, y, A, B)]
            if not hit:
                bad.append(f"{surf}: {num} = {x} vs {y} is not a bout on the card (odds file)")
                continue
            if len(hit) != 1:
                bad.append(f"{surf}: {num} = {x} vs {y} matches {len(hit)} bouts on the card")
            if surf.endswith("(URL ids)"):
                continue
            for other, orows in S.items():
                if other.endswith("(URL ids)"):
                    continue
                for on, A, B in orows:
                    if other != surf and same(x, y, A, B) and on != num:
                        bad.append(f"{x} vs {y}: {surf} says {num}, {other} says {on}")
    bad = sorted(set(bad))
    print(f"bout IDs: {n} bout numbers on {len(S)} surfaces, {len(bad)} disagreements")
    for x in bad[:40]: print("  -", x)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
