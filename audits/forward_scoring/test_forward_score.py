#!/usr/bin/env python3
"""Tests for forward_score.py on a synthetic 3-bout card (lock CSV + site event file). Run from the repo root:
python3 -I audits/forward_scoring/test_forward_score.py (exit 0 = all pass).
Card: A dog Dan Dog +200 vs Fred Fav -240, open dog 0.40, walkout close 0.31 (drift 9 pts), sheet flag drifting veto, DOG WINS.
      B dog Ned Dog +150 vs Gus Fav -170, open 0.38, close 0.37 (drift 1 pt), flag ok, dog loses.
      C dog Lou Long +800 vs Max Heavy -1200 (80%+ favorite shorter than -500), favorite LOSES so the dog wins; women's bout (tag w125).
Checks: result join and orientation, T3 buckets and units, T6 both sizings, v4.9 BET/PASS split, worst single loss,
the late-lock rule, T2 interim on one card, and T1/T4 refusing to score without their archive inputs."""
import csv, io, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); FS = os.path.join(HERE, "forward_score.py")
d = tempfile.mkdtemp()
H = ["pk", "date", "event", "tab", "row", "tag", "dog", "fav", "K code", "Tap C", "Junk D", "Tip E", "dog open F", "dog listed G (sheet)",
     "dog CLOSE (consensus)", "Markov J", "model Q", "flag AA", "dog price (D)", "fav price (I)", "T0 snap kind", "T0 params"]
P = "rules v4.9; B41=0.5; B42=0.1086; B43=0.15; B44=0.075; B45=0.15; B46 (80%+ price floor)=-500; women=-0.04 (Q)"
rows = [["1", "12/5/2026", "X", "Main Card", "2", "185", "Dan Dog", "Fred Fav", "", "", "", "", "0.40", "", "0.31", "0.45", "", "no dog bet (drifting)", "200", "-240", "first_walkout", P],
        ["1", "12/5/2026", "X", "Main Card", "3", "155", "Ned Dog", "Gus Fav", "", "", "", "", "0.38", "", "0.37", "", "", "ok", "150", "-170", "first_walkout", P],
        ["1", "12/5/2026", "X", "Prelims", "2", "w125", "Lou Long", "Max Heavy", "", "", "", "", "0.10", "", "0.08", "", "", "ok", "800", "-1200", "first_walkout", P]]
buf = io.StringIO(); w = csv.writer(buf); w.writerow(H); w.writerows(rows)
open(f"{d}/lock.csv", "w").write(buf.getvalue() + "\n#PropSnap\npk\n")
ev = {"date": "2026-12-05", "fights": [
    {"n": 3, "a": {"name": "Fred Fav"}, "b": {"name": "Dan Dog"}, "result": {"kind": "win", "winner": "b"}, "start": "2026-12-05 21:00:00"},
    {"n": 2, "a": {"name": "Ned Dog"}, "b": {"name": "Gus Fav"}, "result": {"kind": "win", "winner": "b"}, "start": "2026-12-05 20:00:00"},
    {"n": 1, "a": {"name": "Lou Long"}, "b": {"name": "Max Heavy"}, "result": {"kind": "win", "winner": "a"}, "start": "2026-12-05 15:00:00"}]}
json.dump(ev, open(f"{d}/ev.json", "w"))
json.dump([], open(f"{d}/close.json", "w")); os.makedirs(f"{d}/arch")
def run(commit):
    json.dump([{"date": "2026-12-05", "lock": f"{d}/lock.csv", "event": f"{d}/ev.json", "lock_commit_utc": commit, "first_bout_utc": "2026-12-05T15:00:00Z"}], open(f"{d}/cards.json", "w"))
    return subprocess.run([sys.executable, "-I", FS, "score", "--cards", f"{d}/cards.json", "--close", f"{d}/close.json", "--archive", f"{d}/arch"],
                          capture_output=True, text=True)
fails = 0
def check(name, cond):
    global fails; print(("PASS " if cond else "FAIL ") + name); fails += not cond
r = run("2026-12-05T14:40:00Z"); o = r.stdout
if r.returncode: print(r.stderr[-2000:])
check("card counts when the lock precedes the first bout", "COUNTS" in o)
check("T3 vetoed bucket: Dan Dog won at +200 risking 1u -> +2.00", "vetoed (sheet flag 'no dog bet (drifting)'): n=1 won 1 units +2.00" in o)
check("T3 drifting by 3+ pts: only Dan Dog (9 pts); Lou Long drift 2 pts is not", "drifting by T3 (3+ pts): n=1 won 1 units +2.00" in o)
check("T3 other dogs: Ned Dog lost (-1) and Lou Long won at +800 (+8) -> +7.00", "other dogs: n=2 won 1 units +7.00" in o)
check("T6 A to-win 1u: Max Heavy -1200 lost -> -12.00 and worst loss -12.00", "A to-win 1u, all 80%+: bets 1, record 0-1, units -12.00, risked 12.00, worst single loss -12.00" in o)
check("T6 B risk cap 2u -> -2.00", "B risk cap 2u, all 80%+: bets 1, record 0-1, units -2.00, risked 2.00, worst single loss -2.00" in o)
check("T6 v4.9 floor: -1200 is a PASS, so no BET-only line", "[PASS (v4.9 floor)]" in o and "v4.9 BET only" not in o)
check("T1 with an empty close set refuses to score part (c)", "cannot pool part (c); T1 not scored" in o)
check("T2 interim on one card", "T2 interim, not scored" in o)
check("T4 refuses to fit on a too-small training base", "training base too small to fit" in o)
r2 = run("2026-12-05T15:30:00Z")
check("late lock: card does not count", "does not count (late lock)" in r2.stdout and "no counted forward card yet" in r2.stdout)
print(f"{11 - fails}/11 pass"); sys.exit(1 if fails else 0)
