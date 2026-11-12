#!/usr/bin/env python3
"""Option (a), Block 56: after a verified promote, copy each bout's sheet rec from data/<card>_projections.json into the
site event file, in the same commit. Bouts are matched by both fighters' names after form/data/name_aliases.json
(exact keys, no fuzzy matching). A bout on the site with no published row gets no rec ("-").

    python3 -I scripts/sync_event_recs.py data/ufc_334_projections.json [--event form/data/events/<slug>.json]
Exit 1 if a published bout matches zero or two site bouts (nothing is written then).
"""
import argparse, json, re, sys, unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
fold = lambda s: re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())).strip()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("proj"); ap.add_argument("--event")
    a = ap.parse_args()
    P = json.loads(Path(a.proj).read_text())
    al = {k: v for k, v in json.loads((REPO / "form/data/name_aliases.json").read_text()).items() if not k.startswith("_")}
    canon = lambda s: fold(al.get(fold(s), s)).replace(" ", "")
    ev_path = Path(a.event) if a.event else next(p for p in (REPO / "form/data/events").glob("*.json")
                                                 if json.loads(p.read_text()).get("bp_file") == f"data/{P['slug']}_odds.json")
    ev = json.loads(ev_path.read_text())
    key = lambda x, y: frozenset((canon(x), canon(y)))
    site = {key(f["a"]["name"], f["b"]["name"]): f for f in ev["fights"]}
    pub, bad = {}, []
    for r in P["fights"]:
        if not r.get("publish"):
            continue
        k = key(r["dog"], r["fav"])
        if k not in site:
            bad.append(f"{r['dog']} vs {r['fav']}: no site bout")
        pub[k] = (r.get("sheet") or {}).get("rec") or "-"
    if bad:
        print("RED, nothing written:", *bad, sep="\n  "); return 1
    changed = 0
    for k, f in site.items():
        rec = pub.get(k, "-")
        so = f.setdefault("sheet", {}); m = f.get("model")
        old = so.get("rec")
        so["rec"] = rec; so["rec_src"] = P.get("published_at")
        if m is None or m.get("src") == "sheet":
            m = m or {}; f["model"] = m
            side = None
            if rec.upper().startswith("BET"):
                body = fold(rec.split("(")[0].split("[")[0])
                ha, hb = fold(f["a"]["name"]).split()[-1] in body.split(), fold(f["b"]["name"]).split()[-1] in body.split()
                side = "a" if ha and not hb else "b" if hb and not ha else None
            m["rec"], m["rec_text"], m["src"] = side, rec, "sheet"
        changed += old != rec
        if old != rec:
            print(f"  {f['a']['name']} vs {f['b']['name']}: {old!r} -> {rec!r}")
    ev_path.write_text(json.dumps(ev, separators=(",", ":"), ensure_ascii=False))
    print(f"recs synced from {a.proj} (published {P.get('published_at')}): {changed} changed, {len(site)} bouts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
