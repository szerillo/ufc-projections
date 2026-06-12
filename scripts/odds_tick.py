"""
Cadence controller — decides on each cron tick whether to actually invoke
fetch_odds.py, and whether the card is even active.

Tiered schedule:
    > 48h to card           every 12h
    48h → 24h               every 6h
    24h → 6h                every 2h
    6h → first fight        every 1h
    first fight → main      every 30 min, per-fight (skip fights in progress)
    main bell + 5 min       stop (assume card is over)

Per-fight rule:
    A fight is "live" if now >= scheduled - 5 min. We stop trying to refresh
    that bout's lines and snapshot the last good pull as its closing line.
    The script writes a sidecar `data/{card}_closing.json` capturing this.

Inputs:
    - cards.yml at repo root listing active cards + their main-event UTC time.
      (Anything past main + 30 min is considered finished and skipped.)

Exit codes:
    0  ran an ingest (fresh odds committed)
    1  skipped — not inside any fetch window (workflow exits clean)
    2  fatal error (workflow should fail)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
CARDS_FILE = REPO / "cards.yml"
DATA_DIR = REPO / "data"

# Tiered cadence: (max hours to card, min minutes between fetches)
TIERS = [
    (6, 60),        # 0–6h before card start: hourly
    (24, 120),      # 6–24h: every 2 hours
    (48, 360),      # 24–48h: every 6 hours
    (10_000, 720),  # > 48h: every 12 hours
]
# When inside the card (first fight has started but main hasn't ended),
# cap the refresh at this many minutes (your "never tighter than 30 min" rule)
IN_CARD_MIN_MINUTES = 30

# Buffer after main-event scheduled time before we stop polling entirely
POST_MAIN_BUFFER_MIN = 30
# Treat a fight as "live" this many minutes before its scheduled bell
PRE_FIGHT_FREEZE_MIN = 5


def now_utc() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)


def load_cards() -> list[dict]:
    if not CARDS_FILE.exists():
        sys.exit(f"cards.yml not found at {CARDS_FILE}")
    with CARDS_FILE.open() as f:
        return yaml.safe_load(f) or []


def latest_pull_ts(out_path: Path) -> dt.datetime | None:
    if not out_path.exists():
        return None
    try:
        data = json.loads(out_path.read_text())
        ts = data.get("updated_at")
        if ts:
            return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        pass
    # Fall back to mtime
    return dt.datetime.fromtimestamp(out_path.stat().st_mtime, tz=dt.timezone.utc)


def required_min_minutes(hours_to_start: float, inside_card: bool) -> int:
    """Return minimum minutes between fetches given the current state."""
    if inside_card:
        return IN_CARD_MIN_MINUTES
    for max_h, mins in TIERS:
        if hours_to_start <= max_h:
            return mins
    return TIERS[-1][1]


def freeze_in_progress_fights(out_path: Path, now: dt.datetime) -> None:
    """Mark fights whose scheduled bell has been reached as `status: live`
    so the widget knows to display their last-good lines."""
    if not out_path.exists():
        return
    data = json.loads(out_path.read_text())
    changed = False
    for f in data.get("fights", []):
        sched_str = f.get("scheduled_utc")
        if not sched_str:
            continue
        sched = dt.datetime.fromisoformat(sched_str.replace(" ", "T") + "+00:00")
        cutoff = sched - dt.timedelta(minutes=PRE_FIGHT_FREEZE_MIN)
        if now >= cutoff and f.get("status") != "live":
            f["status"] = "live"
            f["frozen_at"] = now.isoformat()
            changed = True
    if changed:
        data["updated_at"] = now.isoformat()
        out_path.write_text(json.dumps(data, indent=2))


def run_ingest(card_name: str, out_path: Path) -> int:
    cmd = [
        sys.executable,
        str(REPO / "scripts" / "fetch_odds.py"),
        "--card", card_name,
        "--out", str(out_path),
    ]
    print(f"  $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO)
    return proc.returncode


def process_card(card: dict, now: dt.datetime) -> bool:
    """Returns True if we ran an ingest, False if we skipped."""
    name = card["name"]
    slug = card["slug"]
    first_bell = dt.datetime.fromisoformat(card["first_fight_utc"]).astimezone(dt.timezone.utc)
    main_bell = dt.datetime.fromisoformat(card["main_event_utc"]).astimezone(dt.timezone.utc)
    out_path = DATA_DIR / f"{slug}_odds.json"

    # Past the card?
    if now >= main_bell + dt.timedelta(minutes=POST_MAIN_BUFFER_MIN + 30):
        print(f"[{name}] past main event + buffer — skipping")
        return False

    inside_card = first_bell <= now < main_bell + dt.timedelta(minutes=POST_MAIN_BUFFER_MIN)
    hours_to_start = max(0.0, (first_bell - now).total_seconds() / 3600.0)
    min_minutes = required_min_minutes(hours_to_start, inside_card)

    last = latest_pull_ts(out_path)
    elapsed_min = ((now - last).total_seconds() / 60.0) if last else None

    print(f"[{name}] first_bell={first_bell} main_bell={main_bell}")
    print(f"[{name}] now={now} h-to-start={hours_to_start:.2f} inside_card={inside_card} required={min_minutes}min last-pull-mins-ago={elapsed_min}")

    if elapsed_min is not None and elapsed_min < min_minutes:
        print(f"[{name}] still within window — skipping")
        # Even if we skip the API call, freeze any newly-live fights
        freeze_in_progress_fights(out_path, now)
        return False

    rc = run_ingest(name, out_path)
    if rc != 0:
        print(f"[{name}] ingest failed rc={rc}", file=sys.stderr)
        return False

    freeze_in_progress_fights(out_path, now)
    return True


def main() -> None:
    now = now_utc()
    cards = load_cards()
    if not cards:
        print("No cards configured in cards.yml — exit clean")
        sys.exit(1)

    ran_anything = False
    for card in cards:
        try:
            if process_card(card, now):
                ran_anything = True
        except Exception as exc:
            print(f"[{card.get('name', '?')}] error: {exc}", file=sys.stderr)
            # Don't fail the whole workflow for one card — keep going
            continue

    sys.exit(0 if ran_anything else 1)


if __name__ == "__main__":
    main()
