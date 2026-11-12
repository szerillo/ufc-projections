#!/usr/bin/env python3
"""Read-only Kalshi KXUFCFIGHT snapshot for the dormant fallback (Kalshi_Fallback_PREREG, sha 4b6d292e).
    python3 -I scripts/fetch_kalshi_ufc.py --out data/embeds/kalshi_<slug>.json
Per open market: title, yes bid/ask, and the time of its last trade. No keys needed (public market data)."""
import argparse, json, time, urllib.request, datetime as dt
B = "https://api.elections.kalshi.com/trade-api/v2"
def get(u):
    for i in range(6):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ufc-embeds"}), timeout=30))
        except Exception: time.sleep(3 + 3 * i)
    raise SystemExit("kalshi read failed: " + u)
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
ms = get(f"{B}/markets?series_ticker=KXUFCFIGHT&status=open&limit=500").get("markets", []); out = {"read_at": dt.datetime.now(dt.timezone.utc).isoformat()[:19] + "Z", "markets": []}
for m in ms:
    tr = get(f"{B}/markets/trades?ticker={m['ticker']}&limit=1").get("trades", []); time.sleep(0.6)
    out["markets"].append({"ticker": m["ticker"], "event": m["event_ticker"], "name": m.get("yes_sub_title") or m["title"].replace(" wins", ""),
                           "bid": float(m.get("yes_bid_dollars") or 0), "ask": float(m.get("yes_ask_dollars") or 0), "last_trade": tr[0]["created_time"][:19] + "Z" if tr else None})
json.dump(out, open(a.out, "w"), indent=1); print(f"kalshi: {len(out['markets'])} markets read at {out['read_at']}")
