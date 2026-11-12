#!/usr/bin/env python3
"""Sean's projection on the site comes from the sheet's "Publish to site" export.

Source order for one event (cards.yml slug, e.g. ufc_334):
  1. data/<slug>_projections.json          verified copy (promoted by the projections workflow, if present)
  2. data/pending/<slug>_projections.json  the export exactly as the sheet published it
  3. no export: keep whatever the build already attached (the build's own sheet pull, src "sheet",
     or a widget's USER_PROJECTIONS, src "widget"). That is the fallback, never mixed with 1/2.

What is taken from the export, per fight (oriented onto the event file's a/b sides):
  win %          sheet.true_dog / sheet.true_fav
  method split   method.dog / method.fav  (DEC / KO / SUB share of that fighter's wins; method % = win % x share)
  GTD            gtd
  sheet inputs   inputs.* (listed prices, open, Markov J, Tap / Junk / Tip, shift) and sheet.flag / rec / edges

Every fight gets f["proj_src"] in {"publish", "sheet", "widget", None}; the event doc gets
doc["proj_source"] = {"src", "file", "published_at", "fights": {src: count}}.

Used by build_form.py (upcoming loop) and as a script to patch an already built event file in place:
    python3 scripts/publish_source.py --slug ufc_334 --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import card_overrides  # noqa: E402  (one fighter-name rule for card corrections and this attach)

REPO = Path(__file__).resolve().parent.parent
# keys of f["sheet"] the export does not carry; they stay from the build's older sheet pull and are listed per fight
NOT_IN_EXPORT = ("momentum", "play", "ou_play", "o25_listed", "o25_model", "hold", "best")


def export_path(slug, repo=REPO):
    for p in (repo / "data" / f"{slug}_projections.json", repo / "data" / "pending" / f"{slug}_projections.json"):
        if p.exists():
            return p
    return None


def load_export(slug, repo=REPO):
    p = export_path(slug, repo)
    if not p:
        return None, None
    return json.load(open(p)), p


def find_row(export, an, bn):
    for r in (export or {}).get("fights", []):
        if r.get("publish") is False:
            continue
        if card_overrides.bout_is(r["dog"], r["fav"], an, bn):
            return r
    return None


def _pct(x):
    return None if x is None else round(x * 100, 6)


def model_from_row(r, a_dog):
    """f["model"] block (percent units, like the rest of the site) from one export row."""
    S, M = r["sheet"], r["method"]
    ra, rb = ("dog", "fav") if a_dog else ("fav", "dog")
    inp = r.get("inputs") or {}
    ml = {"dog": inp.get("dog_odds"), "fav": inp.get("fav_odds")}

    def side(role):
        p = S["true_" + role]
        m = M[role]
        return {"win": _pct(p), "dec": _pct(p * m["dec"]), "ko": _pct(p * m["ko"]), "sub": _pct(p * m["sub"]), "ml": ml[role]}
    rec_text = S.get("rec")
    rec = None
    if rec_text and rec_text.upper().startswith("BET"):
        txt = card_overrides._norm(rec_text)
        hit_d = card_overrides._norm(r["dog"]).split()[-1] in txt
        hit_f = card_overrides._norm(r["fav"]).split()[-1] in txt
        role = "dog" if hit_d and not hit_f else "fav" if hit_f and not hit_d else None
        rec = None if role is None else ("a" if (role == "dog") == a_dog else "b")
    return {"a": side(ra), "b": side(rb), "gtd": _pct(r.get("gtd")), "rec": rec, "rec_text": rec_text, "src": "publish"}


def sheet_from_row(r, a_dog, params, old=None, published_at=None):
    """f["sheet"] block (0-1 units, oriented to side a like build_form.sheet_obj) from one export row."""
    S, M, inp = r["sheet"], r["method"], r.get("inputs") or {}
    sd = (lambda x: None if x is None else (x if a_dog else 1 - x))
    ra, rb = ("dog", "fav") if a_dog else ("fav", "dog")
    meth = lambda role: [M[role]["dec"], M[role]["ko"], M[role]["sub"]]
    old = old or {}
    so = {
        "dog": "a" if a_dog else "b",
        "tap": sd(inp.get("tap")), "junk": sd(inp.get("junk")), "tip": sd(inp.get("tip")),
        "open": sd(inp.get("open_dog")), "listed": sd(S.get("listed")), "markov": sd(inp.get("markov")),
        "model": S["true_dog"] if a_dog else S["true_fav"],
        "flag": S.get("flag"), "rec": S.get("rec"),
        "gtd": r.get("gtd"), "gtd_listed": r.get("gtd_listed"),
        "tag": r.get("tag") or old.get("tag", ""),
        "k": "" if inp.get("ctx") is None else str(inp.get("ctx")), "w": 1 if inp.get("women") else 0,
        "par": [params.get("b45", 0.15), inp.get("shift", params.get("shift", 0.0)) or 0.0, params.get("b43", 0.15), params.get("b44", 0.075)],
        "ml": {"a": inp.get("dog_odds") if a_dog else inp.get("fav_odds"), "b": inp.get("fav_odds") if a_dog else inp.get("dog_odds")},
        "edge": {"a": S.get("dog_edge") if a_dog else S.get("fav_edge"), "b": S.get("fav_edge") if a_dog else S.get("dog_edge")},
        "meth": {"a": meth(ra), "b": meth(rb)},
        "src": "publish", "published_at": published_at,
    }
    if (r.get("markov_dec") or {}).get(ra) is not None:
        so["markov_dec_side"] = {"a": r["markov_dec"][ra], "b": r["markov_dec"][rb]}
    kept = [k for k in NOT_IN_EXPORT if old.get(k) not in (None, "", [], {})]
    for k in kept:
        so[k] = old[k]
    if kept:
        so["from_build_pull"] = kept
    return so


def apply(doc, slug, repo=REPO, export=None, export_file=None):
    """Attach the export to every fight it covers; mark the source on every fight and on the doc."""
    if export is None:
        export, p = load_export(slug, repo)
        export_file = str(p.relative_to(repo)) if p else None
    counts = {}
    for f in doc["fights"]:
        an, bn = f["a"]["name"], f["b"]["name"]
        r = find_row(export, an, bn) if export else None
        if r is not None:
            a_dog = card_overrides.same(r["dog"], an)
            f["model"] = model_from_row(r, a_dog)
            f["sheet"] = sheet_from_row(r, a_dog, export.get("params") or {}, f.get("sheet"), export.get("published_at"))
            if r.get("tag"):
                f["sched"] = 5 if str(r["tag"]).endswith("-5") else 3
            f["proj_src"] = "publish"
        else:
            m = f.get("model")
            f["proj_src"] = None if not m else ("sheet" if m.get("src") == "sheet" else "widget")
        counts[str(f["proj_src"])] = counts.get(str(f["proj_src"]), 0) + 1
    doc["proj_source"] = {"src": "publish" if counts.get("publish") else ("sheet" if counts.get("sheet") else ("widget" if counts.get("widget") else None)),
                          "file": export_file if export else None,
                          "published_at": (export or {}).get("published_at"),
                          "export_source": (export or {}).get("source"),
                          "fights": counts}
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--event", required=True)
    a = ap.parse_args()
    doc = apply(json.load(open(a.event)), a.slug)
    json.dump(doc, open(a.event, "w"), separators=(",", ":"))
    print(a.event, doc["proj_source"])


if __name__ == "__main__":
    main()
