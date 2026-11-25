#!/usr/bin/env python3
"""Tests for scripts/embed_gate.py (Sean, Nov 25 2026): a fought card with mismatches passes; an upcoming card with a
mismatch fails; an upcoming clean card passes; an unknown card fails closed; a card dated today but already graded is
fought. Run: python3 -I scripts/test_embed_gate.py  (exit 0 = all pass)."""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "embed_gate.py")
BAD = "echo 'TOTAL: 1668/1883 numbers verified; 215 mismatches/assertion failures'"
GOOD = "echo 'TOTAL: 1883/1883 numbers verified; 0 mismatches/assertion failures'"


def root():
    r = tempfile.mkdtemp()
    os.makedirs(os.path.join(r, "form", "data", "events"))
    open(os.path.join(r, "cards.yml"), "w").write(
        '- name: "Past card"\n  slug: "past_card"\n  first_fight_utc: "2026-11-21T15:00:00"\n'
        '- name: "Next card"\n  slug: "next_card"\n  first_fight_utc: "2026-12-05T15:00:00"\n'
        '- name: "Graded today"\n  slug: "graded_today"\n  first_fight_utc: "2026-11-25T01:00:00"\n')
    for name, st in (("2026-11-21-past.json", "upcoming"), ("2026-12-05-next.json", "upcoming"), ("2026-11-25-gt.json", "final")):
        json.dump({"status": st, "fights": []}, open(os.path.join(r, "form", "data", "events", name), "w"))
    return r


def run(r, slug, cmd):
    p = subprocess.run([sys.executable, "-I", GATE, "--slug", slug, "--today", "2026-11-25", "--root", r, "--verify-cmd", cmd],
                       capture_output=True, text=True)
    return p.returncode, p.stdout.strip().splitlines()[-1]


CASES = [("fought card with 215 mismatches passes (skipped)", "past_card", BAD, 0),
         ("upcoming card with a mismatch fails", "next_card", BAD, 1),
         ("upcoming card, clean verifier, passes", "next_card", GOOD, 0),
         ("unknown card fails closed", "no_such_card", GOOD, 1),
         ("card dated today but graded counts as fought", "graded_today", BAD, 0)]

r = root(); bad = 0
for name, slug, cmd, want in CASES:
    rc, last = run(r, slug, cmd)
    ok = rc == want; bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}: {name} (exit {rc}, want {want}) | {last}")
print(f"{len(CASES) - bad}/{len(CASES)} passed")
sys.exit(1 if bad else 0)
