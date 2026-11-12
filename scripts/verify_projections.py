#!/usr/bin/env python3
"""Verify a sheet-published projections file before it goes live.

The UFC Model sheet's "Publish to site" menu writes data/pending/<slug>_projections.json.
This script recomputes every published fight's moneyline block with scripts/sheet_v47.py
from the inputs carried in the file and compares it with the numbers the sheet exported.

    python3 -I scripts/verify_projections.py data/pending/ufc_334_projections.json [--promote] [--report out.md]

PASS (exit 0): every number within 0.0001 pts, flag code and recommendation text identical incl. late tag (when exported), method shares
and GTD sane. With --promote the file is copied to data/<slug>_projections.json with a
"verified" block added. FAIL (exit 1): nothing is promoted, the live file is left as it was.
Exit 2: the file can't be read or is malformed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sheet_v47 as S  # noqa: E402
import fighter_names as FN  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TOL = 1e-6           # 0.0001 percentage points. Block 45: the mirror reproduces the sheet's getValues bit for bit on all
                     # 13 UFC 334 fights (largest gap 0; 5e-11 when inputs come from a 10-digit xlsx export), so 0.1 pts was 20 million x too loose
TOL_PTS = TOL * 100
MAX_PRICE_AGE_H = 3  # pre-registered Nov 11 (Block 44): prices must be refreshed within 3 h of the check
NUM_KEYS = [("listed", "listed"), ("H", "markov_shifted"), ("Q", "q"), ("true_dog", "true_dog"),
            ("true_fav", "true_fav"), ("dog_edge", "dog_edge"), ("fav_edge", "fav_edge"), ("drift", "drift")]
SLUG_RE = re.compile(r"^[a-z0-9_]+$")
# Values the last check() compared against a recomputation or a source (replaces the hand-picked "48/48" render count, Block 48)
COMPARED = {"n": 0}


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


def _lead_price(s) -> int | None:
    m = re.match(r"\s*([+-]?\d+)", str(s or ""))
    return int(m.group(1)) if m else None


def opponent_errs(doc: dict, fights: list, odds_doc: dict | None) -> list[str]:
    """Opponent-match guard, pre-registered Block 46 (OPP-1, OPP-2). A price is only trusted if it came from this bout."""
    errs = []
    bouts = None
    if odds_doc is None:
        errs.append(f"odds file data/{doc.get('slug')}_odds.json missing or unreadable, so no fight can be matched to a real bout (OPP-2)")
    else:
        bouts = [((b.get("fighter_a") or {}).get("name", ""), (b.get("fighter_b") or {}).get("name", "")) for b in odds_doc.get("fights") or []]
    for f in fights:
        tag = f"{f.get('dog')} vs {f.get('fav')}"
        ps, inp = f.get("price_source"), f.get("inputs") or {}
        if not isinstance(ps, dict):
            errs.append(f"{tag}: price_source missing, so the price cannot be tied to this bout (publish with the current script) (OPP-1)")
        else:
            for side in ("dog", "fav"):
                COMPARED["n"] += 2
                if not FN.strict_match(str(ps.get(side) or ""), str(f.get(side) or "")):
                    errs.append(f"{tag}: price taken from Feed row {ps.get('order')} '{ps.get('dog')} vs {ps.get('fav')}', "
                                f"whose {side} is not {f.get(side)} (OPP-1)")
                want = _lead_price(ps.get("best_" + side)) if str(ps.get("best_" + side) or "").strip() else _lead_price(ps.get("cons_" + side))
                got = inp.get(side + "_odds")
                if want is None or not isinstance(got, (int, float)) or int(got) != want:
                    errs.append(f"{tag}: {side} price {got} is not the Feed row's price {want} (OPP-1)")
        COMPARED["n"] += bouts is not None
        if bouts is not None and not any(FN.bout_slots(str(f.get("dog") or ""), str(f.get("fav") or ""), a, b) for a, b in bouts):
            errs.append(f"{tag}: no such bout in data/{doc.get('slug')}_odds.json (OPP-2)")
    return errs


def split_pending(doc: dict, errs: list[str]) -> tuple[list[str], list[dict]]:
    """Line pending (pre-registered Block 47, LP-1/LP-2): a fight whose only errors are opponent-guard errors is held back
    as line_pending instead of failing the file. Any other error, a missing odds file, or every fight pending stays red."""
    tags = {f"{f.get('dog')} vs {f.get('fav')}": f for f in doc.get("fights") or []}
    hard, held = [], {}
    for e in errs:
        tag = next((t for t in tags if e.startswith(t + ": ")), None)
        if tag is not None and "(OPP-" in e:
            held.setdefault(tag, []).append(e[len(tag) + 2:])
        else:
            hard.append(e)
    if held and len(held) == len(tags):
        hard.append(f"every fight failed the opponent guard ({len(held)} of {len(tags)}), so nothing would be published (LP)")
    return hard, [{"dog": tags[t].get("dog"), "fav": tags[t].get("fav"), "reason": "; ".join(r)} for t, r in held.items()]


def price_age_h(doc: dict, now: dt.datetime | None = None) -> float | None:
    s = doc.get("prices_loaded")
    if not s:
        return None
    t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if t.tzinfo is None:   # a stamp without an offset could be any time zone: refuse it rather than guess (Block 45)
        raise ValueError(f"prices_loaded {s!r} has no time zone offset")
    return ((now or dt.datetime.now(dt.timezone.utc)) - t).total_seconds() / 3600


def load_odds(slug: str) -> dict | None:
    try:
        return json.loads((REPO / "data" / f"{slug}_odds.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def check(doc: dict, path: Path, now: dt.datetime | None = None, odds_doc: dict | None | str = "auto") -> list[str]:
    errs: list[str] = []
    COMPARED["n"] = 0
    try:
        age = price_age_h(doc, now)
    except ValueError as ex:
        age = -1.0
        errs.append(f"{ex}: publish with the current script (it writes UTC, e.g. 2026-11-13T04:30:00.000Z)")
    if age == -1.0:
        pass
    elif age is None:
        errs.append("no prices_loaded stamp (publish with the current script, after UFC > Refresh prices)")
    elif age > MAX_PRICE_AGE_H:
        errs.append(f"prices were loaded {age:.1f} h ago (limit {MAX_PRICE_AGE_H} h): run UFC > Refresh prices, then publish again")
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
            COMPARED["n"] += 1
            d = abs(r[rk] - float(out[ok]))
            if d > TOL:
                errs.append(f"{tag}: {ok} sheet {float(out[ok])*100:.2f} vs recomputed {r[rk]*100:.2f} ({d*100:.2f} pts)")
        COMPARED["n"] += ("flag" in out) + ("rec" in out)
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
    # method split and fight GTD: recomputed from the file's own method_inputs with the tab formulas (Block 44)
    params = doc.get("params") or {}
    for f in fights:
        tag = f"{f.get('dog')} vs {f.get('fav')}"
        if f.get("method") is None and f.get("gtd") is None:
            continue
        mi = f.get("method_inputs")
        L = (f.get("sheet") or {}).get("true_dog")
        if not isinstance(mi, dict) or not isinstance(L, (int, float)):
            errs.append(f"{tag}: method_inputs missing, so the method split and GTD cannot be checked (publish with the current script)")
            continue
        r = S.method_gtd(float(L), {**mi, "b41": params.get("b41"), "b45": params.get("b45")})
        for side in ("dog", "fav"):
            for k in ("dec", "ko", "sub"):
                v = ((f.get("method") or {}).get(side) or {}).get(k)
                COMPARED["n"] += v is not None
                if v is not None and abs(float(v) - r[side][k]) > TOL:
                    errs.append(f"{tag}: {side} {k} sheet {float(v)*100:.2f} vs recomputed {r[side][k]*100:.2f}")
        COMPARED["n"] += f.get("gtd") is not None
        if f.get("gtd") is not None and abs(float(f["gtd"]) - r["gtd"]) > TOL:
            errs.append(f"{tag}: GTD sheet {float(f['gtd'])*100:.2f} vs recomputed {r['gtd']*100:.2f}")
    # opponent-match guard (Block 46): the price must come from this bout, and the bout must exist in the odds feed
    errs += opponent_errs(doc, fights, load_odds(str(doc.get("slug"))) if odds_doc == "auto" else odds_doc)
    # the params block must agree with the per-fight inputs the numbers were checked against (Block 43 seed test)
    ps = (doc.get("params") or {}).get("shift")
    for f in fights:
        fs = (f.get("inputs") or {}).get("shift")
        if ps is not None and fs is not None and abs(float(ps) - float(fs)) > 1e-9:
            errs.append(f"{f.get('dog')} vs {f.get('fav')}: inputs shift {fs} differs from params shift {ps}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--promote", action="store_true")
    ap.add_argument("--report")
    ap.add_argument("--now", help="TEST ONLY: ISO time to use as the clock for the price-age rule. The workflow never sets it (Block 58)")
    a = ap.parse_args()
    now = dt.datetime.fromisoformat(a.now.replace("Z", "+00:00")) if a.now else None
    path = Path(a.path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as ex:  # noqa: BLE001
        print(f"FAIL: cannot read {path}: {ex}")
        return 2
    n = len(doc.get("fights") or [])
    # Already live: this exact file was verified and promoted before (a manual re-run, or a later push that re-checks every
    # pending file). Re-checking it would only add the price-age rule against a clock that kept moving (Block 45).
    live = REPO / "data" / f"{doc.get('slug', '')}_projections.json"
    if live.exists():
        try:
            cur = json.loads(live.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cur = None
        src_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if isinstance(cur, dict) and ({k: v for k, v in cur.items() if k != "verified"} == doc
                                      or (cur.get("verified") or {}).get("source_sha256") == src_sha):
            msg = (f"## Projections check: {path.name}\n\n**Already live.** This file was verified at "
                   f"{(cur.get('verified') or {}).get('at')} and is what the page shows; nothing to check or promote.\n")
            print(msg)
            if a.report:
                Path(a.report).write_text(msg, encoding="utf-8")
            return 0
    errs, pending = split_pending(doc, check(doc, path, now=now))
    lines = [f"## Projections check: {path.name}", "", f"Published {doc.get('published_at')} · {n} fight(s) · tolerance {TOL_PTS:g} pts", ""]
    if errs:
        lines += ["**FAIL. Not promoted; the live file is unchanged.**", ""] + [f"- {e}" for e in errs]
    else:
        lines += [f"**PASS.** Every number matches scripts/sheet_v47.py within {TOL_PTS:g} pts; flags and recs identical; every price ties to its own bout (Feed row and odds feed). **Values compared: {COMPARED['n']}, mismatched: 0.**"]
        if pending:
            lines += ["", f"**Line pending ({len(pending)}):** shown on the page as \"Line pending\", no numbers:"] + \
                     [f"- {x['dog']} vs {x['fav']}: {x['reason']}" for x in pending]
    report = "\n".join(lines) + "\n"
    print(report)
    if a.report:
        Path(a.report).write_text(report, encoding="utf-8")
    if errs:
        return 1
    if a.promote:
        if pending:
            held = {(x["dog"], x["fav"]) for x in pending}
            doc["fights"] = [f for f in doc["fights"] if (f.get("dog"), f.get("fav")) not in held]
            doc["line_pending"] = pending
        doc["verified"] = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                           "by": "scripts/verify_projections.py", "tolerance_pts": TOL_PTS, "fights": len(doc["fights"]),
                           "line_pending": len(pending), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        live = REPO / "data" / f"{doc['slug']}_projections.json"
        live.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(f"promoted -> {live.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
