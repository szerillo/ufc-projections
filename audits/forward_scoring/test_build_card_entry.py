#!/usr/bin/env python3
"""Tests for build_card_entry.py on a synthetic repo (a main branch with the card's event file, odds feed and cards.yml, and an
audit-locks branch with the walkout lock + MANIFEST, all with set commit times).
  OK      lock committed 14:40Z, first bout 15:00Z -> entry written with the git times, sha and export; CARD ENTRY OK
  L4      cards.yml says the first fight is 14:30Z (earlier than the event file) -> LATE, entry written with late: true, exit 1
  L4      the odds feed's scheduled_utc is the earliest source -> used and named
  L2      lock changed after it was added -> refused, no entry
  L3      MANIFEST line missing, and MANIFEST sha mismatch -> refused
  L1      no lock on audit-locks -> refused
  L5      lock missing a column the harness reads -> refused; CRLF line endings -> refused
  RERUN   building the same date twice keeps one entry; the template placeholder is dropped
  HARNESS the built entry is read by forward_score.py verify and counted by score
Run: python3 -I audits/forward_scoring/test_build_card_entry.py (from the repo root)."""
import csv, hashlib, io, json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
B = os.path.join(HERE, "build_card_entry.py"); FS = os.path.join(HERE, "forward_score.py")
fails = 0
def ok(name, c, extra=""):
    global fails; print(("PASS " if c else "FAIL ") + name + ("" if c else "\n" + extra)); fails += not c
H = ["pk", "date", "event", "tab", "row", "tag", "dog", "fav", "K code", "Tap C", "Junk D", "Tip E", "dog open F", "dog listed G (sheet)",
     "dog CLOSE (consensus)", "Markov J", "model Q", "flag AA", "dog price (D)", "fav price (I)", "T0 snap kind", "T0 params"]
P = "rules v4.9; B41=0.5; B42=0.1086; B43=0.15; B44=0.075; B45=0.15; B46 (80%+ price floor)=-500; women=-0.04 (Q)"
def lock_csv(cols=H):
    rows = [["1", "12/5/2026", "X", "Main Card", "2", "185", "Dan Dog", "Fred Fav", "", "", "", "", "0.40", "", "", "", "0.33", "ok", "200", "-240", "first_walkout", P],
            ["1", "12/5/2026", "X", "Prelims", "2", "155", "Ned Dog", "Gus Fav", "", "", "", "", "0.38", "", "", "", "0.37", "ok", "150", "-170", "first_walkout", P]]
    buf = io.StringIO(); w = csv.writer(buf); w.writerow(cols); w.writerows([[r[H.index(c)] for c in cols] for r in rows])
    return buf.getvalue() + "\n#PropSnap\npk\n"

def make(lock=True, late_yml=False, feed_first=None, relock=False, manifest="ok", cols=H, crlf=False):
    d = tempfile.mkdtemp()
    g = lambda *a, t=None: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, check=True,
                                          env={**os.environ, **({"GIT_COMMITTER_DATE": t, "GIT_AUTHOR_DATE": t} if t else {})})
    g("init", "-q", "-b", "main"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    for sub in ("scripts", "form/data/events", "data", "audits/forward_scoring"): os.makedirs(f"{d}/{sub}", exist_ok=True)
    for f in ("fighter_names.py", "sheet_v47.py", "card_overrides.py"):
        if os.path.exists(f"{REPO}/scripts/{f}"): shutil.copy(f"{REPO}/scripts/{f}", f"{d}/scripts/{f}")
    if os.path.exists(f"{REPO}/form/data/name_aliases.json"): shutil.copy(f"{REPO}/form/data/name_aliases.json", f"{d}/form/data/")
    ev = {"date": "2026-12-05", "fights": [
        {"n": 2, "a": {"name": "Fred Fav"}, "b": {"name": "Dan Dog"}, "start": "2026-12-05 21:00:00", "result": {"kind": "win", "winner": "b"}},
        {"n": 1, "a": {"name": "Ned Dog"}, "b": {"name": "Gus Fav"}, "start": "2026-12-05 15:00:00", "result": {"kind": "win", "winner": "b"}}]}
    json.dump(ev, open(f"{d}/form/data/events/2026-12-05-test-card.json", "w"))
    feed = {"updated_at": "x", "fights": [{"fighter_a": {"name": "Ned Dog"}, "fighter_b": {"name": "Gus Fav"}, "scheduled_utc": feed_first or "2026-12-05 15:10:00"}]}
    json.dump(feed, open(f"{d}/data/t_odds.json", "w"))
    open(f"{d}/cards.yml", "w").write(f'- name: "X"\n  slug: "t"\n  first_fight_utc: "{"2026-12-05T14:30:00+00:00" if late_yml else "2026-12-05T15:00:00+00:00"}"\n')
    json.dump([{"date": "2026-12-05", "lock": "x", "event": "form/data/events/2026-12-05-<card>.json"}], open(f"{d}/audits/forward_scoring/cards_forward.json", "w"))
    g("add", "-A"); g("commit", "-q", "-m", "main", t="2026-12-01T00:00:00+00:00")
    g("checkout", "-q", "-b", "audit-locks")
    if lock:
        os.makedirs(f"{d}/analysis/snap_locks", exist_ok=True)
        body = lock_csv(cols).replace("\r\n", "\n"); body = body.replace("\n", "\r\n") if crlf else body
        open(f"{d}/analysis/snap_locks/2026-12-05.csv", "w", newline="").write(body)
        sha = hashlib.sha256(body.encode()).hexdigest()
        man = {"ok": f"{sha}  analysis/snap_locks/2026-12-05.csv\n", "bad": f"{'0' * 64}  analysis/snap_locks/2026-12-05.csv\n", "none": "abc  other.txt\n"}[manifest]
        open(f"{d}/analysis/MANIFEST.txt", "w").write(man)
        g("add", "-A"); g("commit", "-q", "-m", "lock", t="2026-12-05T14:40:00+00:00")
        if relock:
            open(f"{d}/analysis/snap_locks/2026-12-05.csv", "a").write("edited\n"); g("add", "-A"); g("commit", "-q", "-m", "edit", t="2026-12-05T22:00:00+00:00")
    g("checkout", "-q", "main")
    return d

def build(d, extra=()):
    return subprocess.run([sys.executable, "-I", B, "--date", "2026-12-05", "--slug", "t", "--audit-ref", "audit-locks", "--main-ref", "main",
                           "--cards", "audits/forward_scoring/cards_forward.json", "--cache", f"{d}/_cache", *extra], cwd=d, capture_output=True, text=True)

d = make(); r = build(d); C = json.load(open(f"{d}/audits/forward_scoring/cards_forward.json"))
e = C[-1] if C else {}
ok("OK: CARD ENTRY OK, exit 0", r.returncode == 0 and "CARD ENTRY OK" in r.stdout, r.stdout + r.stderr)
ok("OK: lock time = audit-locks commit time, first bout = earliest start (event file 15:00Z)",
   e.get("lock_commit_utc") == "2026-12-05T14:40:00Z" and e.get("first_bout_utc") == "2026-12-05T15:00:00Z" and e.get("late") is False, json.dumps(e))
ok("OK: export written outside the repo tree with the recorded sha", os.path.exists(e.get("lock", "")) and hashlib.sha256(open(e["lock"], "rb").read()).hexdigest() == e.get("lock_sha256"))
ok("RERUN: template placeholder dropped, one entry for the date", len(C) == 1)
build(d); ok("RERUN: building twice keeps one entry", len(json.load(open(f"{d}/audits/forward_scoring/cards_forward.json"))) == 1)
p = subprocess.run([sys.executable, "-I", FS, "verify", "--lock", e["lock"], "--event", e["event"], "--commit-time", e["lock_commit_utc"]], cwd=d, capture_output=True, text=True)
ok("HARNESS: forward_score verify reads the entry's lock and event", "lock committed before first bout: YES" in p.stdout, p.stdout + p.stderr)
json.dump([], open(f"{d}/close.json", "w")); os.makedirs(f"{d}/arch", exist_ok=True)
p = subprocess.run([sys.executable, "-I", FS, "score", "--cards", "audits/forward_scoring/cards_forward.json", "--close", "close.json", "--archive", "arch"], cwd=d, capture_output=True, text=True)
ok("HARNESS: forward_score score counts the built card", "COUNTS" in p.stdout, p.stdout + p.stderr)
d = make(late_yml=True); r = build(d); C = json.load(open(f"{d}/audits/forward_scoring/cards_forward.json"))
ok("L4: cards.yml 14:30Z earlier than the lock -> LATE, exit 1, entry written late", r.returncode == 1 and "LATE LOCK" in r.stdout and C[-1].get("late") is True and C[-1]["first_bout_source"] == "cards.yml", r.stdout)
d = make(feed_first="2026-12-05 14:50:00"); r = build(d); C = json.load(open(f"{d}/audits/forward_scoring/cards_forward.json"))
ok("L4: the feed's 14:50Z start is the earliest source, named, lock still before it", r.returncode == 0 and C[-1]["first_bout_source"] == "odds feed" and C[-1]["first_bout_utc"] == "2026-12-05T14:50:00Z", r.stdout)
d = make(relock=True); r = build(d)
ok("L2: lock changed after it was added -> refused, no entry", r.returncode == 1 and "L2 FAIL" in r.stdout and "entry written" not in r.stdout, r.stdout)
d = make(manifest="none"); r = build(d); ok("L3: no MANIFEST line -> refused", r.returncode == 1 and "has no line" in r.stdout, r.stdout)
d = make(manifest="bad"); r = build(d); ok("L3: MANIFEST sha mismatch -> refused", r.returncode == 1 and "MANIFEST sha" in r.stdout, r.stdout)
d = make(lock=False); r = build(d); ok("L1: no lock on audit-locks -> refused", r.returncode == 1 and "L1 FAIL" in r.stdout, r.stdout)
d = make(cols=[c for c in H if c != "model Q"]); r = build(d); ok("L5: lock missing 'model Q' -> refused", r.returncode == 1 and "missing columns" in r.stdout, r.stdout)
d = make(crlf=True); r = build(d); ok("L5: CRLF line endings -> refused", r.returncode == 1 and "CRLF" in r.stdout, r.stdout)
print(f"{15 - fails}/15 pass"); sys.exit(1 if fails else 0)
