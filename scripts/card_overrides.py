#!/usr/bin/env python3
"""Real-card corrections for upcoming UFC events (data/card_overrides.json).

The BettingPros feed keeps cancelled bouts, misses replacements and has no
title flag, so a hand edit of form/data/events/*.json is wiped by the next
build_form.py run. This module is the one place those corrections live:

  * build_form.py calls apply_feed() on the feed fights before it builds an
    upcoming event, and apply_doc() on the finished event doc.
  * Run as a script it patches an already built event file + index.json in
    place (same code path), for when a full rebuild is not possible:

    python3 scripts/card_overrides.py --slug ufc_334 \
        --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json \
        --index form/data/index.json --fighters form/data/fighters --check

Nothing here invents numbers: a replaced bout loses its old odds/model/sheet
blocks and only gets name, slug, Elo and fight count from the fighter file.
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OVR_PATH = REPO / "data" / "card_overrides.json"
STALE_KEYS = ("bp", "odds", "form", "model", "sheet", "markov", "props")


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower().replace("-", " ")).strip()


def same(a, b):
    """Same fighter? Handles Charlie Radke ~ Charles Radtke, Christopher ~ Chris."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = na.split(), nb.split()
    if len(ta) == 1 or len(tb) == 1:  # mononyms (Alatengheili)
        return ta[-1] == tb[-1] or difflib.SequenceMatcher(None, na.replace(" ", ""), nb.replace(" ", "")).ratio() >= 0.9
    last = difflib.SequenceMatcher(None, ta[-1], tb[-1]).ratio()
    first = ta[0] == tb[0] or ta[0].startswith(tb[0][:4]) or tb[0].startswith(ta[0][:4]) \
        or difflib.SequenceMatcher(None, ta[0], tb[0]).ratio() >= 0.6
    return last >= 0.83 and first


def bout_is(a, b, x, y):
    return (same(a, x) and same(b, y)) or (same(a, y) and same(b, x))


def load(slug, path=OVR_PATH):
    if not path.exists():
        return None
    return (json.load(open(path)) or {}).get(slug)


# ---------------------------------------------------------------- feed level
def apply_feed(slug, fights, path=OVR_PATH):
    """BettingPros feed fights (fighter_a/fighter_b dicts). Returns a new list."""
    o = load(slug, path)
    if not o:
        return fights
    out = []
    for f in fights:
        an, bn = f["fighter_a"]["name"], f["fighter_b"]["name"]
        if any(bout_is(an, bn, x, y) for x, y in o.get("cancel", [])):
            continue
        f = json.loads(json.dumps(f))
        for r in o.get("replace", []):
            for me, opp in (("fighter_a", "fighter_b"), ("fighter_b", "fighter_a")):
                if same(f[me]["name"], r["out"]) and same(f[opp]["name"], r["opp"]):
                    f[me] = {"name": r["in"]}
                    # the feed's prices describe the old matchup
                    for k in [k for k in f if k not in ("n", "fighter_a", "fighter_b", "weight_class", "scheduled_utc", "status")]:
                        f.pop(k, None)
        out.append(f)
    return out


# ---------------------------------------------------------------- doc level
def _fighter_ref(name, fighters_dir):
    p = Path(fighters_dir) / (re.sub(r"[^a-z0-9]+", "-", _norm(name)).strip("-") + ".json") if fighters_dir else None
    if p and p.exists():
        d = json.load(open(p))
        return {"name": d.get("name") or name, "slug": d.get("slug"), "elo": d.get("elo"), "nf": len(d.get("fights") or [])}
    return {"name": name, "slug": None, "elo": None, "nf": 0}


def apply_doc(slug, doc, fighters_dir=None, path=OVR_PATH):
    """Built event doc (form/data/events/*.json). Mutates and returns it."""
    o = load(slug, path)
    if not o:
        return doc
    fights = [f for f in doc["fights"]
              if not any(bout_is(f["a"]["name"], f["b"]["name"], x, y) for x, y in o.get("cancel", []))]
    for f in fights:
        for r in o.get("replace", []):
            for me, opp in (("a", "b"), ("b", "a")):
                if same(f[me]["name"], r["out"]) and same(f[opp]["name"], r["opp"]):
                    f[me] = _fighter_ref(r["in"], fighters_dir)
                    for k in STALE_KEYS:
                        f.pop(k, None)
        is_title = any(bout_is(f["a"]["name"], f["b"]["name"], x, y) for x, y in o.get("title", []))
        f["title"] = bool(is_title)
        if is_title:
            f["sched"] = 5
    order = [tuple(s.split("|")) for s in o.get("order", [])]
    if order:
        def rank(f):
            for i, (x, y) in enumerate(order):
                if bout_is(f["a"]["name"], f["b"]["name"], x, y):
                    return i
            return len(order) + 100  # unknown bouts sink to the bottom, flagged by check()
        fights.sort(key=rank)
    if fights:
        fights[0]["sched"] = 5
    doc["fights"] = fights
    doc["overrides"] = o.get("source")
    return doc


def apply_index(index, doc):
    for u in index.get("upcoming", []):
        if u.get("slug") == doc["slug"]:
            u["nf"] = len(doc["fights"])
            f0 = doc["fights"][0]
            u["main"] = f"{f0['a']['name']} vs {f0['b']['name']}"
    return index


def n_main(fights):
    n = len(fights)
    return min(n, (5 if any(f.get("title") for f in fights) else 6) if n >= 12 else 5)


def check(slug, doc, index=None, path=OVR_PATH):
    o = load(slug, path) or {}
    errs = []
    ns = [f["n"] for f in doc["fights"]]
    if len(ns) != len(set(ns)):
        errs.append("duplicate n")
    if index:
        u = next((u for u in index.get("upcoming", []) if u.get("slug") == doc["slug"]), None)
        if not u or u["nf"] != len(doc["fights"]):
            errs.append("index nf mismatch")
    for x, y in o.get("cancel", []):
        if any(bout_is(f["a"]["name"], f["b"]["name"], x, y) for f in doc["fights"]):
            errs.append(f"cancelled bout still listed: {x} vs {y}")
    for r in o.get("replace", []):
        if any(same(f[s]["name"], r["out"]) for f in doc["fights"] for s in "ab"):
            errs.append(f"replaced fighter still listed: {r['out']}")
    order = [tuple(s.split("|")) for s in o.get("order", [])]
    if order:
        got = [(f["a"]["name"], f["b"]["name"]) for f in doc["fights"]]
        if len(got) != len(order) or not all(bout_is(a, b, x, y) for (a, b), (x, y) in zip(got, order)):
            errs.append("order differs from overrides")
    seg = o.get("segments")
    if seg and n_main(doc["fights"]) != seg.get("main"):
        errs.append(f"site will show {n_main(doc['fights'])} main card bouts, real card has {seg.get('main')} (app.js heuristic)")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--event", required=True)
    ap.add_argument("--index")
    ap.add_argument("--fighters", default=str(REPO / "form" / "data" / "fighters"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    doc = apply_doc(a.slug, json.load(open(a.event)), a.fighters)
    json.dump(doc, open(a.event, "w"), separators=(",", ":"))
    idx = None
    if a.index:
        idx = apply_index(json.load(open(a.index)), doc)
        json.dump(idx, open(a.index, "w"), separators=(",", ":"))
    for i, f in enumerate(doc["fights"]):
        seg = "main" if i < n_main(doc["fights"]) else "prelim"
        print(f"{i+1:2d} n={f['n']:<2} {seg:6s} {f['a']['name']} vs {f['b']['name']}  {f['wc']}  {f['sched']}R{'  TITLE' if f['title'] else ''}")
    if a.check:
        errs = check(a.slug, doc, idx)
        print("CHECK:", "OK" if not errs else "; ".join(errs))
        sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
