#!/usr/bin/env python3
"""Refresh only the line-history ("odds") block of one event file from the sharp-tracker Odds API archive (Block 59k).

    python3 -I scripts/refresh_event_odds.py --event form/data/events/<slug>.json [--cache .form_cache] [--no-download]

Why: the event file's odds block is written by build_form.py, which also needs the private model-sheet ID, so it is not
run on a schedule and the line history froze at its last run (Nov 10 18:05 UTC for UFC 334). The archive itself keeps
updating. This script reuses build_form.py's own loader and summariser (same matching, same no-vig median), touches no
sheet data, and changes nothing else in the event file. Prints what changed per fight.
"""
import argparse, datetime as dt, importlib.util, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))   # build_form imports form_model from scripts/
spec = importlib.util.spec_from_file_location("build_form", REPO / "scripts/build_form.py")
BF = importlib.util.module_from_spec(spec); spec.loader.exec_module(BF)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--event", required=True); ap.add_argument("--cache", default=str(REPO / ".form_cache"))
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--archive", help="local checkout of szerillo/sharp-tracker (used instead of downloading; the GitHub API can be blocked)")
    a = ap.parse_args()
    cache = Path(a.cache); evp = Path(a.event); ev = json.loads(evp.read_text())
    if a.archive:
        import shutil
        src = Path(a.archive) / "data"
        for rel in ["oddsapi/compact/mma.jsonl.gz", "mma/oddsapi_live.jsonl"]:
            (cache / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src / rel, cache / rel)
        (cache / "oddsapi" / "mma").mkdir(parents=True, exist_ok=True)
        for fp in (src / "oddsapi" / "mma").glob("*.json.gz"): shutil.copy2(fp, cache / "oddsapi" / "mma" / fp.name)
    elif not a.no_download:
        for rel in ["oddsapi/compact/mma.jsonl.gz", "mma/oddsapi_live.jsonl"]:
            BF.fetch(BF.ST_RAW + rel, cache / rel, timeout=300)
        # the dated 2026 snapshot files hold the early lines (openers); same list build_form.py downloads
        import urllib.request
        req = urllib.request.Request(BF.ST_API_TREE, headers={"User-Agent": "mma-fight-form-build/1.0"})
        for t in json.load(urllib.request.urlopen(req, timeout=60)).get("tree", []):
            dest = cache / "oddsapi" / "mma" / t["path"]
            if not dest.exists(): BF.fetch(BF.ST_RAW + "oddsapi/mma/" + t["path"], dest)
    n_snap = len(list((cache / "oddsapi" / "mma").glob("*.json.gz")))
    if n_snap == 0: sys.exit("no dated snapshot files in the cache: openers would be wrong; refusing to write")
    by_id = BF.load_odds(cache); idx = BF.index_odds(by_id); d = dt.date.fromisoformat(ev["date"])
    newest = max((s["t"] for v in by_id.values() for s in v), default=None)
    print(f"archive newest snapshot {newest}")
    for f in ev["fights"]:
        old = f.get("odds") or {}
        eid, fl = BF.find_odds(idx, by_id, f["a"]["name"], f["b"]["name"], d)
        o = BF.summarize_odds(by_id[eid], fl, a_name=f["a"]["name"]) if eid else None
        if o:
            f["odds"] = BF.public_odds(o)   # Consensus_US_PREREG: published current line from US-regulated books only
        oc, nc = (old.get("close") or {}), ((o or {}).get("close") or {})
        print(f"  {f['n']:>2} {f['a']['name']} vs {f['b']['name']}: close {oc.get('t', '-')} p={oc.get('p', '-')} -> {nc.get('t', 'no match, kept old')} p={nc.get('p', '-')}")
    evp.write_text(json.dumps(ev, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main()
