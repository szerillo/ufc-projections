#!/usr/bin/env python3
"""Which of two copies of a BettingPros odds file is newer? (Kirk round 26 C, used by main_guard.py and merge_main.sh)

Round 22-25 compared the two "updated_at" strings as text. That breaks on a timestamp written with an offset or fractional
seconds ("...T13:30:00-05:00" sorts before "...T18:09:02Z" although it is later), and it trusts updated_at even if the bot
stamped the file before writing newer data. Now:
  1 both updated_at values must parse as timezone-aware times; they are compared as times, not text;
  2 the data must agree, price by price: for every (bout, market, selection, book) present in BOTH files, the newer file's
    "updated" may not be older than the other file's (round 27 B: a book or market the bot dropped is simply not compared, so a
    legitimately dropped line no longer refuses; a stale file still does). No price in common: no answer.
Anything else: no answer, and the caller refuses.

  python3 scripts/odds_newer.py A.json B.json   -> prints A or B, or exits 1 with the reason
"""
import datetime as dt, json, sys


def _ts(s):
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None: raise ValueError(f"updated_at has no time zone: {s}")
    return t


def _data_newest(d):
    best = None
    for f in d.get("fights", []):
        for lst in (f.get("markets") or {}).values():
            for e in lst or []:
                for b in (e.get("books") or {}).values():
                    u = b.get("updated")
                    if u and (best is None or u > best): best = u   # same writer, same "YYYY-MM-DD HH:MM:SS" format in both files
    return best


def _prices(d):
    out = {}
    for f in d.get("fights", []):
        fk = "|".join(sorted([(f.get("fighter_a") or {}).get("name", ""), (f.get("fighter_b") or {}).get("name", "")]))
        for mk, lst in (f.get("markets") or {}).items():
            for e in lst or []:
                for bk, b in (e.get("books") or {}).items():
                    if b.get("updated"): out[(fk, mk, e.get("label"), e.get("selection"), bk)] = b["updated"]
    return out


def newer(a, b):
    ta, tb = _ts(a["updated_at"]), _ts(b["updated_at"])
    if ta == tb: raise ValueError(f"same updated_at {ta.isoformat()}")
    first, other = ("A", "B") if ta > tb else ("B", "A")
    pa, pb = _prices(a), _prices(b); common = set(pa) & set(pb)
    if not common: raise ValueError("the two files share no price to compare")
    pn, po = (pa, pb) if first == "A" else (pb, pa)
    back = sorted(k for k in common if pn[k] < po[k])
    if back:
        k = back[0]; raise ValueError(f"updated_at says {first} is newer, but {len(back)} of {len(common)} shared prices are older in it (e.g. {k[0]} {k[1]} {k[2]} {k[4]}: {pn[k]} vs {po[k]})")
    da, db = _data_newest(a), _data_newest(b)
    return first, ta, tb, da, db


if __name__ == "__main__":
    try:
        w, ta, tb, da, db = newer(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
        print(w); print(f"  updated_at A {ta.isoformat()} B {tb.isoformat()}; newest book price A {da} B {db}", file=sys.stderr)
    except Exception as e:
        print(f"cannot tell which odds file is newer: {e}", file=sys.stderr); sys.exit(1)
