"""Print how many minutes of 'live' odds coverage are still needed right now.

Live window per card in cards.yml: from LEAD_H hours before the first bell to the
main event bell + 35 minutes. Prints 0 when no card is in its window. Used by
.github/workflows/odds_live.yml, which keeps one job alive through the window and
calls scripts/odds_tick.py every few minutes (odds_tick still enforces the cadence).

Why: GitHub runs the */30 schedule in odds.yml only about every 5 hours on this repo
(100 runs Oct 21 - Nov 11 against 1,028 scheduled ticks), so card-night closes were
hours stale.
"""
import datetime as dt
import sys
from pathlib import Path

import yaml

LEAD_H = 6
TAIL_MIN = 35
REPO = Path(__file__).resolve().parents[1]


def minutes_left(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    best = 0
    for c in yaml.safe_load((REPO / "cards.yml").read_text()) or []:
        fb = dt.datetime.fromisoformat(c["first_fight_utc"]).replace(tzinfo=dt.timezone.utc)
        mb = dt.datetime.fromisoformat(c["main_event_utc"]).replace(tzinfo=dt.timezone.utc)
        start, end = fb - dt.timedelta(hours=LEAD_H), mb + dt.timedelta(minutes=TAIL_MIN)
        if start <= now < end:
            best = max(best, int((end - now).total_seconds() // 60) + 1)
    return best


if __name__ == "__main__":
    if len(sys.argv) > 1:   # test hook: --at 2026-11-14T22:00:00
        print(minutes_left(dt.datetime.fromisoformat(sys.argv[2]).replace(tzinfo=dt.timezone.utc)))
    else:
        print(minutes_left())
