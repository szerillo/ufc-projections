#!/usr/bin/env python3
"""Verify a sheet-published projections file before it goes live.

The UFC Model sheet's "Publish to site" menu writes data/pending/<slug>_projections.json.
This script recomputes every published fight's moneyline block with scripts/sheet_v47.py
from the inputs carried in the file and compares it with the numbers the sheet exported.

    python3 -I scripts/verify_projections.py data/pending/ufc_334_projections.json [--promote] [--report out.md]

PASS (exit 0): every number within 0.1 pts, flag code and recommendation text identical incl. late tag (when exported), method shares
and GTD sane. With --promote the file is copied to data/<slug>_projections.json with a
"verified" block added. FAIL (exit 1): nothing is promoted, the live file is left as it was.
Exit 2: the file can't be read or is malformed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sheet_v47 as S  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TOL = 0.001          # 0.1 percentage points, on 0-1 probabilities
NUM_KEYS = [("listed", "listed"), ("H", "markov_shifted"), ("Q", "q"), ("true_dog", "true_dog"),
            ("true_fav", "true_fav"), ("dog_edge", "dog_edge"), ("fav_edge", "fav_edge"), ("drift", "drift")]
SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def flag_code(s: str | None) -> str:
    s = (s or "").strip()
    for pre, code in (("DEBUTANT", "D"), ("SHARPS", "SHARPS"), ("no dog bet (drifting)", "DRIFT"),
                      ("public on dog", "PUBLIC"), ("public lean", "PUBLIC_LEAN"), ("ok", "OK")):
        if s.startswith(pre):
            return code
    return "?" + s


def rec_norm(s: str | None) -> str:
    # Whitespace only. The late tag is compared word for word: an earlier version stripped it to
    # present/absent, which let a wrong tag wording or percent pass (audit block 35 falsifier).
    return re.sub(r"\s+", " ", (s or "-").strip())


def check(doc: dict, path: Path) -> list[str]:
    errs: list[str] = []
    slug = doc.get("slug", "")
    if doc.get("schema") != 1:
        errs.append(f"schema is {doc.get('schema')!r}, expected 1")
    if not SLUG_RE.match(slug) or not path.name.startswith(slug + "_"):
        errs.append(f"slug {slug!r} does not match file name {path.name}")
    fights = doc.get("fights") or []
    if not fights:
        errs.append("no fights in file")
    seen = set()
    for i, f in enumerate(fights):
        tag = f"{f.get('dog')} vs {f.get('fav')}"
        if (f.get("dog"), f.get("fav")) in seen:
            errs.append(f"{tag}: listed twice")
        seen.add((f.get("dog"), f.get("fav")))
        if f.get("publish") is not True:
            errs.append(f"{tag}: publish flag is not true (only checked fights may be exported)")
        inp, out = f.get("inputs") or {}, f.get("sheet") or {}
        for k in ("dog_odds", "fav_odds"):
            if not isinstance(inp.get(k), (int, float)) or abs(inp[k]) < 100:
                errs.append(f"{tag}: input {k} missing or not an American price ({inp.get(k)!r})")
        if errs and errs[-1].startswith(tag + ": input"):
            continue
        r = S.row({**inp, "dog": f["dog"], "fav": f["fav"]})
        for rk, ok in NUM_KEYS:
            if out.get(ok) is None:
                errs.append(f"{tag}: sheet value {ok} missing")
                continue
            d = abs(r[rk] - float(out[ok]))
            if d > TOL:
                errs.append(f"{tag}: {ok} sheet {float(out[ok])*100:.2f} vs recomputed {r[rk]*100:.2f} ({d*100:.2f} pts)")
        if "flag" in out and flag_code(out.get("flag")) != flag_code(r["flag"]):
            errs.append(f"{tag}: flag sheet {out.get('flag')!r} vs recomputed {r['flag']!r}")
        if "rec" in out and rec_norm(out.get("rec")) != rec_norm(r["rec"]):
            errs.append(f"{tag}: rec sheet {out.get('rec')!r} vs recomputed {r['rec']!r}")
        m = f.get("method") or {}
        for side in ("dog", "fav"):
            sh = m.get(side) or {}
            vals = [sh.get(k) for k in ("dec", "ko", "sub")]
            if any(v is None for v in vals):
                continue  # method shares are optional (blank until the sheet has them)
            if any(not 0 <= float(v) <= 1 for v in vals) or abs(sum(map(float, vals)) - 1) > 0.01:
                errs.append(f"{tag}: {side} method shares {vals} not in [0,1] or not summing to 1")
        g = f.get("gtd")
        if g is not None and not 0 <= float(g) <= 1:
            errs.append(f"{tag}: GTD {g} outside [0,1]")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--promote", action="store_true")
    ap.add_argument("--report")
    a = ap.parse_args()
    path = Path(a.path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as ex:  # noqa: BLE001
        print(f"FAIL: cannot read {path}: {ex}")
        return 2
    errs = check(doc, path)
    n = len(doc.get("fights") or [])
    lines = [f"## Projections check: {path.name}", "", f"Published {doc.get('published_at')} · {n} fight(s) · tolerance 0.1 pts", ""]
    if errs:
        lines += ["**FAIL. Not promoted; the live file is unchanged.**", ""] + [f"- {e}" for e in errs]
    else:
        lines += ["**PASS.** Every number matches scripts/sheet_v47.py within 0.1 pts; flags and recs identical."]
    report = "\n".join(lines) + "\n"
    print(report)
    if a.report:
        Path(a.report).write_text(report, encoding="utf-8")
    if errs:
        return 1
    if a.promote:
        doc["verified"] = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                           "by": "scripts/verify_projections.py", "tolerance_pts": 0.1, "fights": n}
        live = REPO / "data" / f"{doc['slug']}_projections.json"
        live.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(f"promoted -> {live.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
