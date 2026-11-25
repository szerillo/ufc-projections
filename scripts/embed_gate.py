#!/usr/bin/env python3
"""Merge gate for fight embeds (Sean, Nov 25 2026): the full embed verifier must be clean only for UPCOMING cards.
A card is upcoming when its first-fight date (cards.yml first_fight_utc, UTC) is today or later AND its event file
(form/data/events/<date>-*.json, date within a day) is not past "upcoming" (final / awaiting_results = fought).
Fought cards are skipped: their embeds drift from the odds and model once results land, so they cannot block a merge.
Unknown slug or no date = FAIL (closed).

  python3 -I scripts/embed_gate.py --slug SLUG [--today YYYY-MM-DD] [--root DIR] [--verify-cmd CMD] [--query]
--query: print "upcoming" or "fought" and exit 0 (merge_main uses it to skip the embed rebuild on fought cards).
--verify-cmd: verifier command (default: python3 scripts/verify_fight_embeds.py --slug SLUG); tests pass a stub.
"""
import argparse, datetime as dt, glob, json, os, re, subprocess, sys

CLEAN = re.compile(r"^TOTAL: (\d+)/\1 numbers verified; 0 mismatches/assertion failures", re.M)


def card_date(root, slug):
    txt = open(os.path.join(root, "cards.yml"), encoding="utf-8").read()
    for block in re.split(r"\n(?=- )", txt):
        if re.search(r'^\s*-?\s*slug:\s*"?%s"?\s*$' % re.escape(slug), block, re.M):
            m = re.search(r'first_fight_utc:\s*"?(\d{4}-\d{2}-\d{2})', block)
            return dt.date.fromisoformat(m.group(1)) if m else None
    return None


def fought(root, d):
    """True when an event file within a day of d is no longer 'upcoming'."""
    for p in glob.glob(os.path.join(root, "form", "data", "events", "*.json")):
        try:
            ed = dt.date.fromisoformat(os.path.basename(p)[:10])
        except ValueError:
            continue
        if abs((ed - d).days) <= 1:
            st = json.load(open(p, encoding="utf-8")).get("status")
            if st and st != "upcoming":
                return True
    return False


def classify(root, slug, today):
    d = card_date(root, slug)
    if d is None:
        return None, None
    return ("fought" if d < today or fought(root, d) else "upcoming"), d


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--today", default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--verify-cmd")
    ap.add_argument("--query", action="store_true")
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today)
    kind, d = classify(a.root, a.slug, today)
    if kind is None:
        print(f"EMBED GATE FAIL: {a.slug} has no first_fight_utc in cards.yml (unknown card, failing closed)")
        return 1
    if a.query:
        print(kind)
        return 0
    if kind == "fought":
        print(f"EMBED GATE SKIP: {a.slug} ({d}) is a fought card; its embeds drift once results land, so they do not block the merge")
        return 0
    cmd = a.verify_cmd or f"python3 scripts/verify_fight_embeds.py --slug {a.slug}"
    out = subprocess.run(cmd, shell=True, cwd=a.root, capture_output=True, text=True)
    sys.stdout.write("\n".join((out.stdout or "").strip().splitlines()[-3:]) + "\n")
    if out.returncode != 0 or not CLEAN.search(out.stdout or ""):
        print(f"EMBED GATE FAIL: {a.slug} ({d}) is upcoming and its embed verifier is not clean")
        return 1
    print(f"EMBED GATE PASS: {a.slug} ({d}) upcoming, verifier clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
