#!/usr/bin/env python3
"""Tests for scripts/guard_card_status.py, re-creating C4's three cases (Nov 25 2026) on synthetic data:
T1 stale: a past card still 'upcoming' in manifest, index and its event file -> 3 G1 failures.
T2 planted: a Dec 5 card carrying Prochazka vs Stirling, Stirling fought 14 days before, bout not on the official list
   -> G2 and G3 fail.
T3 control: Blachowicz vs Prochazka on the list, no recent fight -> passes.
T4 missing official list with --require-official -> fails; without the flag -> passes.
Run: python3 -I scripts/test_guard_card_status.py (exit 0 = all pass)."""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, "guard_card_status.py")


def mk(stale, bout, recent, official):
    r = tempfile.mkdtemp()
    for d in ("data", "data/official", "form/data/events", "form/data/fighters"):
        os.makedirs(os.path.join(r, d), exist_ok=True)
    json.dump({"cards": [{"slug": "nov21", "date": "2026-11-21", "status": "upcoming" if stale else "graded"}]}, open(f"{r}/data/manifest.json", "w"))
    json.dump({"upcoming": ([{"slug": "2026-11-21-x", "date": "2026-11-21"}] if stale else []) + [{"slug": "2026-12-05-y", "date": "2026-12-05"}], "events": []},
              open(f"{r}/form/data/index.json", "w"))
    json.dump({"status": "upcoming" if stale else "final", "fights": [{"a": {"name": "Jiri Prochazka", "slug": "jiri-prochazka"}, "b": {"name": "Navajo Stirling", "slug": "navajo-stirling"}}]},
              open(f"{r}/form/data/events/2026-11-21-x.json", "w"))
    A, B = bout
    json.dump({"status": "upcoming", "fights": [{"a": {"name": A, "slug": A.lower().replace(" ", "-")}, "b": {"name": B, "slug": B.lower().replace(" ", "-")}}]},
              open(f"{r}/form/data/events/2026-12-05-y.json", "w"))
    json.dump({"slug": "navajo-stirling", "fights": [{"d": "2026-11-21"}] if recent else [{"d": "2026-06-01"}]}, open(f"{r}/form/data/fighters/navajo-stirling.json", "w"))
    json.dump({"slug": "jiri-prochazka", "fights": [{"d": "2026-06-01"}]}, open(f"{r}/form/data/fighters/jiri-prochazka.json", "w"))
    if official:
        open(f"{r}/data/official/2026-12-05.txt", "w").write("# UFC.com event page\nIsrael Adesanya vs Shara Magomedov\nJan Błachowicz vs Jiří Procházka\n")
    if not recent and not stale:   # control: no event file carries the planted fighters' recent bout
        os.remove(f"{r}/form/data/events/2026-11-21-x.json")
    return r


def run(r, *extra):
    p = subprocess.run([sys.executable, "-I", G, "--today", "2026-11-25", "--root", r, "--official-dir", f"{r}/data/official", *extra], capture_output=True, text=True)
    return p.returncode, p.stdout


cases = []
rc, out = run(mk(True, ("Israel Adesanya", "Shara Magomedov"), False, True))
cases.append(("T1 stale card: 3 G1 failures", rc == 1 and out.count("G1 stale card") == 3, out))
rc, out = run(mk(False, ("Jiri Prochazka", "Navajo Stirling"), True, True))
cases.append(("T2 planted fought bout: G2 and G3 fail", rc == 1 and "G2 already fought: Navajo Stirling" in out and "G3 not official: Jiri Prochazka vs Navajo Stirling" in out, out))
rc, out = run(mk(False, ("Jan Blachowicz", "Jiri Prochazka"), False, True))
cases.append(("T3 control on the list, no recent fight: passes", rc == 0, out))
rc, out = run(mk(False, ("Jan Blachowicz", "Jiri Prochazka"), False, False), "--require-official")
cases.append(("T4a missing official list with --require-official fails", rc == 1 and "no official UFC.com list" in out, out))
rc, out = run(mk(False, ("Jan Blachowicz", "Jiri Prochazka"), False, False))
cases.append(("T4b missing list without the flag passes", rc == 0, out))
bad = 0
for name, ok, out in cases:
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
    if not ok:
        print(out)
print(f"{len(cases) - bad}/{len(cases)} passed")
sys.exit(1 if bad else 0)
