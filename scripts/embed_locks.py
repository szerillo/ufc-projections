#!/usr/bin/env python3
"""Fingerprint locks for files the embed builder AND the checker both read (Kirk round 9, C).

    python3 -I scripts/embed_locks.py check  --slug ufc_334            # exit 1 and list what changed
    python3 -I scripts/embed_locks.py bless  --slug ufc_334 --reason "UFC 334 Friday labs rebuild" [--who Kirk]

Locked files have no independent source the checker can recompute them from. Files with an independent source are not
locked: line history (raw odds archive), the stats file (UFCStats CSVs), the odds feed (archive side check), the sheet export
(it is the source; export age gate). The event file is locked minus its odds block, which the Friday refresh rewrites and the checker recomputes from the raw archive.
A bless writes the new fingerprints with who, why and old -> new into data/embeds/locks.json; it refuses to run inside the
Friday refresh or the rehearsal (EMBED_PIPELINE=1), so a pipeline run can never re-bless its own inputs.
"""
import argparse, datetime as dt, hashlib, json, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; LOCKS = REPO / "data/embeds/locks.json"
def event_file(slug):
    idx = json.loads((REPO / "form/data/index.json").read_text())
    for u in idx.get("upcoming", []):
        p = REPO / "form/data/events" / f'{u["slug"]}.json'
        if p.exists() and json.loads(p.read_text()).get("bp_file") == f"data/{slug}_odds.json": return p
def view(p):
    b = p.read_bytes()
    if "/events/" in str(p):
        d = json.loads(b)
        for f in d.get("fights", []):
            f.pop("odds", None)   # Kirk round 10 A: only the odds block is left out (the Friday refresh rewrites it; the checker recomputes it from the archive)
        b = json.dumps(d, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(b).hexdigest()
def files(slug):
    ev = event_file(slug); d = json.loads(ev.read_text())
    out = ["data/card_overrides.json", "embed.html", "form/data/labs.json", "form/data/index.json", "data/embeds/spot_tests.json", str(ev.relative_to(REPO))]
    out += sorted(f"form/data/fighters/{f[s]['slug']}.json" for f in d["fights"] for s in "ab" if f[s].get("slug") and (REPO / f"form/data/fighters/{f[s]['slug']}.json").exists())
    return out
def current(slug): return {f: view(REPO / f) for f in files(slug)}
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["check", "bless"]); ap.add_argument("--slug", default="ufc_334")
    ap.add_argument("--reason"); ap.add_argument("--who", default="Kirk"); a = ap.parse_args()
    L = json.loads(LOCKS.read_text()) if LOCKS.exists() else {"locks": {}, "history": []}
    cur = current(a.slug); pinned = L["locks"].get(a.slug, {})
    changed = {f: (pinned.get(f), h) for f, h in cur.items() if pinned.get(f) != h}
    if a.cmd == "check":
        for f, (o, n) in changed.items(): print(f"  LOCK: {f} {'not pinned' if o is None else 'changed since it was blessed'} ({(o or '-')[:12]} -> {n[:12]})")
        print(f"LOCKS: {len(cur)} files, {len(changed)} changed"); sys.exit(1 if changed else 0)
    if os.environ.get("EMBED_PIPELINE") == "1" or os.environ.get("GITHUB_ACTIONS") == "true": sys.exit("refusing to bless inside a pipeline run: bless by hand, with a reason")
    if not a.reason or len(a.reason) < 10: sys.exit("a bless needs --reason (what changed and why it is legitimate)")
    for f, (o, n) in changed.items(): print(f"  bless {f}: {(o or '-')[:12]} -> {n[:12]}")
    L["locks"][a.slug] = cur
    at_ = dt.datetime.now(dt.timezone.utc).isoformat()[:19] + "Z"
    # Kirk round 18 call 3 (Strip_Names_PREREG sha 74d582e1): who and why go to _audit/locks_history.json (not served by the
    # site's Jekyll build); the served locks.json keeps only when, which card and what changed
    L["history"].append({"at": at_, "slug": a.slug, "changed": {f: [o, n] for f, (o, n) in changed.items()}})
    AUD = REPO / "_audit" / "locks_history.json"; AUD.parent.mkdir(exist_ok=True)
    H = json.loads(AUD.read_text()) if AUD.exists() else {"history": []}
    H["history"].append({"at": at_, "slug": a.slug, "who": a.who, "reason": a.reason}); AUD.write_text(json.dumps(H, indent=1))
    LOCKS.write_text(json.dumps(L, indent=1)); print(f"blessed {len(changed)} file(s); history entries: {len(L['history'])}")
if __name__ == "__main__": main()
