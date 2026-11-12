#!/usr/bin/env python3
"""Which of two copies of a BettingPros odds file is newer? (Kirk round 26 C, used by main_guard.py and merge_main.sh)

Round 22-25 compared the two "updated_at" strings as text. That breaks on a timestamp written with an offset or fractional
seconds ("...T13:30:00-05:00" sorts before "...T18:09:02Z" although it is later), and it trusts updated_at even if the bot
stamped the file before writing newer data. Now:
  1 both updated_at values must parse as timezone-aware times; they are compared as times, not text;
  2 the newest per-book "updated" inside each file must not contradict that order (the newer file may not hold older data).
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


def newer(a, b):
    ta, tb = _ts(a["updated_at"]), _ts(b["updated_at"])
    if ta == tb: raise ValueError(f"same updated_at {ta.isoformat()}")
    first, other = ("A", "B") if ta > tb else ("B", "A")
    da, db = _data_newest(a), _data_newest(b)
    dn, do = (da, db) if first == "A" else (db, da)
    if dn and do and dn < do:
        raise ValueError(f"updated_at says {first} is newer ({max(ta, tb).isoformat()}), but its newest book price ({dn}) is older than the other file's ({do})")
    return first, ta, tb, da, db


if __name__ == "__main__":
    try:
        w, ta, tb, da, db = newer(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
        print(w); print(f"  updated_at A {ta.isoformat()} B {tb.isoformat()}; newest book price A {da} B {db}", file=sys.stderr)
    except Exception as e:
        print(f"cannot tell which odds file is newer: {e}", file=sys.stderr); sys.exit(1)
