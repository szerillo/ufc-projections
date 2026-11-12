#!/usr/bin/env python3
"""Block 57: Labs next-card rows must be the current card. For every upcoming card in form/data/index.json, each Labs
"upcoming" row (cardio, props, sd_edge) must name two fighters who are on that card's event file in the same bout, with
the same number, and every bout on the card must have a row. RED (exit 1) on a cancelled or replaced fighter's name, a
wrong number or a missing bout. Fix: python3 -I scripts/build_labs.py --upcoming-only

    python3 -I scripts/labs_card_check.py [--root DIR]      (DIR = a site checkout; default this repo)
"""
import argparse, json, re, sys, unicodedata
from pathlib import Path

fold = lambda s: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1])); a = ap.parse_args()
    D = Path(a.root) / "form" / "data"
    idx, labs = json.loads((D / "index.json").read_text()), json.loads((D / "labs.json").read_text())
    red = 0
    for u in idx.get("upcoming", [])[:1]:   # Labs builds its next-card rows from the first upcoming card only
        ev = json.loads((D / "events" / f"{u['slug']}.json").read_text())
        on_card = {fold(f[s]["name"]) for f in ev["fights"] for s in "ab"}
        bout = {frozenset((fold(f["a"]["name"]), fold(f["b"]["name"]))): f["n"] for f in ev["fights"]}
        for sec in ("cardio", "props", "sd_edge"):
            rows = (labs.get(sec) or {}).get("upcoming") or []
            nm = lambda x: x.get("nm") if isinstance(x, dict) else x
            stale, wrong_n, seen = [], [], set()
            for r in rows:
                if r.get("es") != ev["slug"]:
                    stale.append(f"#{r.get('n')} is for another card ({r.get('es')})"); continue
                A, B = nm(r["a"]), nm(r["b"])
                gone = [x for x in (A, B) if fold(x) not in on_card]
                if gone:
                    stale.append(f"#{r['n']} {A} vs {B}: not on the card: {', '.join(gone)}"); continue
                k = frozenset((fold(A), fold(B)))
                if k not in bout:
                    stale.append(f"#{r['n']} {A} vs {B}: not a bout on the card"); continue
                seen.add(k)
                if bout[k] != r["n"]:
                    wrong_n.append(f"#{r['n']} {A} vs {B}: card number is {bout[k]}")
            missing = [f"{ev['fights'][i]['a']['name']} vs {ev['fights'][i]['b']['name']}" for i, k in enumerate(
                frozenset((fold(f["a"]["name"]), fold(f["b"]["name"]))) for f in ev["fights"]) if k not in seen]
            bad = len(stale) + len(wrong_n) + len(missing); red += bad
            print(f"{sec}: {len(rows)} rows, {len(stale)} stale (fighter not on the card), {len(wrong_n)} wrong number, {len(missing)} bouts missing")
            for x in stale + wrong_n + ["missing: " + m for m in missing]:
                print("   ", x)
    print("RESULT:", "RED" if red else "GREEN", f"({red} problems)")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
