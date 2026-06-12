"""
UFC live-odds ingestor — BettingPros API → normalized JSON.

Usage:
  python fetch_odds.py --card "UFC Freedom 250" --out data/freedom_250_odds.json

Cron strategy (see workflow): the controller decides whether to invoke this
script on each tick. The script itself is a single-shot pull.

The BettingPros key is lifted from their public web bundle (same auth their
site uses). If the key rotates, grab the new one from:
  https://www.bettingpros.com/dist/assets/api-*.js  →  grep for x-api-key

Markets covered:
  237 — Moneyline
  238 — Fight Ending (KO/SUB/DEC at the fight level)
  239 — Method of Victory (per-fighter KO/SUB/DEC)
  240 — Fight Distance (YES = goes the distance / NO = ends inside)
  241 — Total Rounds (over/under)

Books we surface:
  0  = consensus (BP's blended line, with no-vig win% baked in)
  10 = FanDuel
  12 = DraftKings
  19 = BetMGM
  30 = Caesars
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import urllib.request
import urllib.parse
import urllib.error

API_BASE = "https://api.bettingpros.com/v3"
API_KEY = os.environ.get("BETTINGPROS_API_KEY", "CHi8Hy5CEE4khd46XNYL23dCFX96oUdw6qOt1Dnh")

MARKETS = {
    237: "moneyline",
    238: "fight_ending",
    239: "method_of_victory",
    240: "fight_distance",
    241: "total_rounds",
}

BOOKS = {
    0: "consensus",
    10: "fanduel",
    12: "draftkings",
    19: "betmgm",
    30: "caesars",
}


def _request(path: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params)
    url = f"{API_BASE}{path}?{qs}"
    req = urllib.request.Request(
        url,
        headers={
            "x-api-key": API_KEY,
            "User-Agent": "ufc-projections-odds-ingest/1.0",
            "Accept": "application/json",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                wait = 2 ** attempt
                print(f"  retry {attempt + 1} after {wait}s on HTTP {e.code}", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("exhausted retries")


def find_card_events(card_name: str, location: str = "NY") -> list[dict]:
    """Return all events whose comp_name matches the given card name."""
    res = _request("/events", {"sport": "UFC", "location": location})
    events = res.get("events", [])
    matches = [
        e for e in events
        if (e.get("comp_name") or "").strip().lower().startswith(card_name.strip().lower())
    ]
    matches.sort(key=lambda e: e.get("scheduled") or "")
    return matches


def _extract_book_lines(selection: dict) -> dict:
    """Pull cost + computed no-vig % per book we care about."""
    out: dict[str, dict] = {}
    for b in selection.get("books") or []:
        bid = b.get("id")
        if bid not in BOOKS:
            continue
        lines = b.get("lines") or []
        if not lines:
            continue
        ln = lines[0]
        out[BOOKS[bid]] = {
            "cost": ln.get("cost"),
            "line": ln.get("line"),
            "updated": ln.get("updated"),
            "no_vig_pct": (ln.get("metrics") or {}).get("pm_win_pct"),
        }
    return out


def fetch_market(event_id: int, market_id: int, location: str = "NY") -> list[dict]:
    """Pull a single (event_id × market_id) and normalize."""
    res = _request(
        "/offers",
        {
            "sport": "UFC",
            "location": location,
            "market_id": market_id,
            "event_id": event_id,
            "include": "selections",
        },
    )
    offers = res.get("offers", [])
    out: list[dict] = []
    for o in offers:
        for s in o.get("selections") or []:
            out.append({
                "label": s.get("label"),
                "short_label": s.get("short_label"),
                "selection": s.get("selection") or "",
                "opening_cost": (s.get("opening_line") or {}).get("cost"),
                "books": _extract_book_lines(s),
            })
    return out


def assemble_fight(event: dict) -> dict:
    """Pull all 5 markets for one event and shape into the fight blob."""
    parts = event.get("participants") or []
    a = parts[0] if len(parts) > 0 else {}
    b = parts[1] if len(parts) > 1 else {}
    fight: dict[str, Any] = {
        "event_id": event["id"],
        "scheduled_utc": event.get("scheduled"),
        "weight_class": event.get("weight_class"),
        "fighter_a": {
            "name": a.get("name"),
            "short": (a.get("competitor") or {}).get("short_name"),
            "bp_id": a.get("id"),
        },
        "fighter_b": {
            "name": b.get("name"),
            "short": (b.get("competitor") or {}).get("short_name"),
            "bp_id": b.get("id"),
        },
        "status": event.get("status"),
        "markets": {},
    }
    for mid, slug in MARKETS.items():
        try:
            fight["markets"][slug] = fetch_market(event["id"], mid)
        except Exception as exc:
            fight["markets"][slug] = []
            print(f"  ! event {event['id']} market {mid}: {exc}", file=sys.stderr)
    return fight


def build_card(card_name: str, location: str = "NY") -> dict:
    events = find_card_events(card_name, location)
    if not events:
        raise SystemExit(f"No events matched card name {card_name!r}")
    print(f"Matched {len(events)} fights for {card_name}", file=sys.stderr)

    fights = []
    for ev in events:
        fight_num = len(fights) + 1
        a_name = (ev.get("participants") or [{}])[0].get("name", "?")
        b_name = (ev.get("participants") or [{}, {}])[1].get("name", "?") if len(ev.get("participants") or []) > 1 else "?"
        print(f"  [{fight_num}/{len(events)}] event {ev['id']} {a_name} vs {b_name}", file=sys.stderr)
        fights.append({"n": fight_num, **assemble_fight(ev)})

    return {
        "card": card_name,
        "venue": (events[0].get("venue") or {}).get("name"),
        "updated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "source": "bettingpros",
        "books_included": list(BOOKS.values()),
        "fights": fights,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True, help='e.g. "UFC Freedom 250"')
    ap.add_argument("--out", required=True, help="path to write odds.json")
    ap.add_argument("--location", default="NY", help="BettingPros location code")
    args = ap.parse_args()

    payload = build_card(args.card, args.location)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
