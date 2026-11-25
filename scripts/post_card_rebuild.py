#!/usr/bin/env python3
"""Post-card rebuild (Sean approved Nov 25 2026): the day after a card, fought cards leave the upcoming slot.
Idempotent; touches only cards dated before today that still say "upcoming".

1 form/data/events/<date>-*.json: results from --results (UFCStats, "date|kind|winner|loser|method|round|time" per line;
  kind win or draw, winner first) are written into each bout's "result"; status -> "final" when every bout has a result,
  else "awaiting_results" (never "upcoming" again).
2 form/data/index.json: past entries leave "upcoming" and go to the top of "events".
3 data/manifest.json: past Markov cards still "upcoming" -> "graded".
Without --results it only fixes status (the scheduled workflow runs it that way; results come with the next full build).

  python3 -I scripts/post_card_rebuild.py [--today YYYY-MM-DD] [--root DIR] [--results FILE] [--dry-run]
"""
import argparse, datetime as dt, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guard_card_status import same

METHOD = {"U-DEC": "Decision - Unanimous", "S-DEC": "Decision - Split", "M-DEC": "Decision - Majority", "SUB": "Submission",
          "KO/TKO": "KO/TKO", "DQ": "DQ", "Overturned": "Overturned", "CNC": "Could Not Continue"}


def dump(p, d, dry, indent=None):
    """Keep each file's existing layout: events and index are compact, manifest is indent=1."""
    if not dry:
        with open(p, "w", encoding="utf-8") as fh:
            if indent is None:
                json.dump(d, fh, ensure_ascii=fh.name.endswith("index.json"), separators=(",", ":"))
            else:
                json.dump(d, fh, ensure_ascii=True, indent=indent)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--results")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    R, today = a.root, dt.date.fromisoformat(a.today)
    res = []
    if a.results:
        for ln in open(a.results, encoding="utf-8"):
            if ln.strip() and not ln.startswith("#"):
                d, kind, w, l, m, rd, t = ln.rstrip("\n").split("|")
                res.append(dict(date=d, kind=kind, w=w, l=l, method=METHOD.get(m, m), round=int(rd), time=t))
    changed = []
    for p in sorted(glob.glob(os.path.join(R, "form", "data", "events", "*.json"))):
        try:
            d = dt.date.fromisoformat(os.path.basename(p)[:10])
        except ValueError:
            continue
        ev = json.load(open(p, encoding="utf-8"))
        if ev.get("status") != "upcoming" or d >= today:
            continue
        n_new = 0
        for f in ev.get("fights", []):
            A, B = f["a"]["name"], f["b"]["name"]
            for r in res:
                if r["date"] != str(d):
                    continue
                if same(r["w"], A) and same(r["l"], B): win = "a"
                elif same(r["w"], B) and same(r["l"], A): win = "b"
                else: continue
                old = f.get("result") or {}
                f["result"] = {**old, "winner": None if r["kind"] == "draw" else win, "kind": r["kind"], "method": r["method"],
                               "round": r["round"], "time": r["time"], "source": "UFCStats event page (post_card_rebuild)"}
                n_new += 1
        done = all(f.get("result") for f in ev.get("fights", []))
        ev["status"] = "final" if done else "awaiting_results"
        dump(p, ev, a.dry_run)
        changed.append(f"event {os.path.basename(p)}: {n_new}/{len(ev.get('fights', []))} results written, status -> {ev['status']}")
    ip = os.path.join(R, "form", "data", "index.json")
    idx = json.load(open(ip, encoding="utf-8"))
    past = [u for u in idx.get("upcoming", []) if u.get("date") and dt.date.fromisoformat(u["date"]) < today]
    if past:
        idx["upcoming"] = [u for u in idx["upcoming"] if u not in past]
        known = {e.get("slug") for e in idx.get("events", [])}
        idx["events"] = sorted([u for u in past if u.get("slug") not in known] + idx.get("events", []), key=lambda e: e.get("date", ""), reverse=True)
        dump(ip, idx, a.dry_run)
        changed += [f"index.json: {u['slug']} moved from upcoming to events" for u in past]
    mp = os.path.join(R, "data", "manifest.json")
    man = json.load(open(mp, encoding="utf-8"))
    hit = [c for c in man.get("cards", []) if c.get("status") == "upcoming" and c.get("date") and dt.date.fromisoformat(c["date"]) < today]
    for c in hit:
        c["status"] = "graded"
        changed.append(f"manifest: {c['slug']} -> graded")
    if hit:
        dump(mp, man, a.dry_run, indent=1)
    print(f"post-card rebuild ({today}{', dry run' if a.dry_run else ''}): {len(changed)} change(s)")
    for c in changed:
        print("  " + c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
