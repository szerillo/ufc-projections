#!/usr/bin/env python3
"""Card status guard (spec: C4, Stale_Card_Root_Cause_and_Guard_2026-11-25; Sean approved wiring Nov 25 2026).
Read-only. Exit 1 on any failure; blocks friday_refresh go-live and merge_main.

G1 stale card: nothing dated before today may be "upcoming" (data/manifest.json cards, form/data/events/*.json,
   form/data/index.json "upcoming").
G2 already fought: on an upcoming event, a fighter with a UFC bout in the 30 days before the card date, or on/after it,
   fails. Sources: form/data/fighters/<slug>.json fights[].d, and every other event file's bouts (so a card fought but
   not yet merged into fighter files still counts).
G3 not official: every bout on an upcoming event must be on the official UFC.com card list: data/official/<event date>.txt
   (or --official FILE), one "A vs B" per line copied from the UFC.com event page. Match is accent-, case- and
   order-insensitive with a last-name fallback. --require-official: a missing list fails.

  python3 -I scripts/guard_card_status.py [--today YYYY-MM-DD] [--root DIR] [--official FILE] [--official-dir DIR]
                                          [--require-official]
"""
import argparse, datetime as dt, glob, json, os, re, sys, unicodedata


TRANS = str.maketrans({"ł": "l", "ø": "o", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe", "ı": "i", "ð": "d", "þ": "th"})


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "").lower().translate(TRANS))
    return re.sub(r"[^a-z ]", " ", "".join(c for c in s if not unicodedata.combining(c))).split()


def same(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    return a == b or "".join(a) == "".join(b) or (a[-1] == b[-1] and a[0][0] == b[0][0])


def load(p):
    return json.load(open(p, encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--official")
    ap.add_argument("--official-dir")
    ap.add_argument("--require-official", action="store_true")
    a = ap.parse_args(argv)
    R, today = a.root, dt.date.fromisoformat(a.today)
    fails = []
    # ---- G1
    man = os.path.join(R, "data", "manifest.json")
    if os.path.exists(man):
        for c in load(man).get("cards", []):
            if c.get("status") == "upcoming" and c.get("date") and dt.date.fromisoformat(c["date"]) < today:
                fails.append(f"G1 stale card: manifest {c['slug']} ({c['date']}) is still 'upcoming'")
    idx = os.path.join(R, "form", "data", "index.json")
    if os.path.exists(idx):
        for u in load(idx).get("upcoming", []):
            if u.get("date") and dt.date.fromisoformat(u["date"]) < today:
                fails.append(f"G1 stale card: index.json upcoming slot holds {u['slug']} ({u['date']})")
    events = {}
    for p in sorted(glob.glob(os.path.join(R, "form", "data", "events", "*.json"))):
        try:
            d = dt.date.fromisoformat(os.path.basename(p)[:10])
        except ValueError:
            continue
        ev = load(p); events[p] = (d, ev)
        if ev.get("status") == "upcoming" and d < today:
            fails.append(f"G1 stale card: event {os.path.basename(p)} is still 'upcoming'")
    # ---- G2 + G3 on upcoming events dated today or later
    fights_of = {}
    for p in glob.glob(os.path.join(R, "form", "data", "fighters", "*.json")):
        f = load(p); fights_of[f.get("slug") or os.path.basename(p)[:-5]] = [x.get("d") for x in f.get("fights", []) if x.get("d")]
    upcoming = [(p, d, ev) for p, (d, ev) in events.items() if ev.get("status") == "upcoming" and d >= today]
    for p, d, ev in upcoming:
        name = os.path.basename(p)
        lo = d - dt.timedelta(days=30)
        for b in ev.get("fights", []):
            for side in ("a", "b"):
                fr = b.get(side) or {}
                hits = [x for x in fights_of.get(fr.get("slug"), []) if dt.date.fromisoformat(x) >= lo]
                for q, (d2, ev2) in events.items():
                    if q == p or not (lo <= d2):
                        continue
                    if any(same((g.get(s2) or {}).get("name"), fr.get("name")) or ((g.get(s2) or {}).get("slug") and (g.get(s2) or {}).get("slug") == fr.get("slug"))
                           for g in ev2.get("fights", []) for s2 in ("a", "b")):
                        hits.append(f"{d2} ({os.path.basename(q)[11:-5]})")
                if hits:
                    fails.append(f"G2 already fought: {fr.get('name')} on {name} has a UFC bout within 30 days before {d} or after it: {sorted(set(map(str, hits)))[:3]}")
        off = a.official or (os.path.join(a.official_dir, f"{d}.txt") if a.official_dir else None)
        if off and os.path.exists(off):
            pairs = [re.split(r"\s+vs\.?\s+", ln.strip(), flags=re.I) for ln in open(off, encoding="utf-8") if " vs" in ln.lower() and not ln.startswith("#")]
            pairs = [x for x in pairs if len(x) == 2]
            for b in ev.get("fights", []):
                A, B = (b.get("a") or {}).get("name"), (b.get("b") or {}).get("name")
                if not any((same(A, x) and same(B, y)) or (same(A, y) and same(B, x)) for x, y in pairs):
                    fails.append(f"G3 not official: {A} vs {B} on {name} is not on the official list {os.path.basename(off)}")
        elif a.require_official:
            fails.append(f"G3 not official: no official UFC.com list for {name} (expected {off or 'data/official/' + str(d) + '.txt'})")
    print(f"card guard ({today}): {len(upcoming)} upcoming event(s) checked; {len(fails)} failure(s)")
    for f in fails:
        print("  " + f)
    print("CARD GUARD " + ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
