#!/usr/bin/env python3
"""Tests for dk_5r_o45.py on a synthetic git repo (fake DraftKings totals with set commit times; no real prices).
Checks: entry = last feed commit before the card's first bout (a later commit is ignored); close = last commit before the bout's
own start; a 3.5 line does not qualify; the 50% cut; settlement (decision over, R5 2:31 over, R5 2:30 under, R4 under, NC void);
the unit rule on minus and plus prices; grade never rewrites a graded line; score is interim before 40 bets and gives each
registered reading on synthetic 40-bet logs; manual entry for a bout the feed lacks.
Run: python3 -I audits/forward_tests/5r_o45_dk/test_dk_5r_o45.py (from the repo root)."""
import json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
S = os.path.join(HERE, "dk_5r_o45.py"); d = tempfile.mkdtemp(); fails = 0
def ok(name, c):
    global fails; print(("PASS " if c else "FAIL ") + name); fails += not c
# scratch repo with the scripts the tool imports
os.makedirs(f"{d}/scripts"); os.makedirs(f"{d}/data"); os.makedirs(f"{d}/form/data")
for f in ("card_overrides.py", "fighter_names.py"):
    if os.path.exists(f"{REPO}/scripts/{f}"): shutil.copy(f"{REPO}/scripts/{f}", f"{d}/scripts/{f}")
if os.path.exists(f"{REPO}/form/data/name_aliases.json"): shutil.copy(f"{REPO}/form/data/name_aliases.json", f"{d}/form/data/")
g = lambda *a, env=None: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, check=True, env={**os.environ, **(env or {})})
g("init", "-q", "-b", "main"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
def feed(main_o, main_u, co_line, co_o, co_u):
    def fight(a, b, line, o, u):
        return {"fighter_a": {"name": a}, "fighter_b": {"name": b}, "markets": {"total_rounds": [
            {"label": "Over", "books": {"draftkings": {"line": line, "cost": o}}}, {"label": "Under", "books": {"draftkings": {"line": line, "cost": u}}}]}}
    return {"updated_at": "x", "fights": [fight("Al Main", "Bo Main", 4.5, main_o, main_u), fight("Cy Co", "Di Co", co_line, co_o, co_u)]}
def commit(doc, when):
    json.dump(doc, open(f"{d}/data/test_odds.json", "w")); g("add", "-A")
    g("commit", "-q", "-m", when, env={"GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when})
commit(feed(-130, 105, 3.5, -150, 120), "2026-12-05T14:30:00+00:00")   # entry snapshot (before the 15:00 first bout)
commit(feed(-150, 120, 3.5, -160, 130), "2026-12-05T15:30:00+00:00")   # after the first bout: must not be the entry
commit(feed(-170, 135, 4.5, -110, -110), "2026-12-05T20:30:00+00:00")  # last before the main event: the close
ev = {"date": "2026-12-05", "fights": [
    {"a": {"name": "Al Main"}, "b": {"name": "Bo Main"}, "sched": 5, "start": "2026-12-05 21:00:00", "result": {"kind": "win", "winner": "a", "method": "Decision - Unanimous", "round": 5, "time": "5:00"}},
    {"a": {"name": "Cy Co"}, "b": {"name": "Di Co"}, "sched": 5, "start": "2026-12-05 20:00:00", "result": {"kind": "win", "winner": "b", "method": "KO/TKO", "round": 5, "time": "2:31"}},
    {"a": {"name": "Ed Three"}, "b": {"name": "Fy Three"}, "sched": 3, "start": "2026-12-05 15:00:00", "result": {"kind": "win", "winner": "a", "method": "KO/TKO", "round": 1, "time": "1:00"}}]}
json.dump(ev, open(f"{d}/ev.json", "w"))
run = lambda *a: subprocess.run([sys.executable, "-I", S, *a], cwd=d, capture_output=True, text=True)
r = run("extract", "--slug", "test", "--event", "ev.json", "--log", "log.jsonl", "--ref", "main")
L = [json.loads(l) for l in open(f"{d}/log.jsonl")]; M = next(l for l in L if l["bout"].startswith("Al")); C = next(l for l in L if l["bout"].startswith("Cy"))
ok("only the two five-round bouts are logged", len(L) == 2)
ok("entry = last commit before the first bout (-130 / +105), not the 15:30 commit", M["dk_over_entry"] == -130 and M["dk_under_entry"] == 105)
ok("main event qualifies (no-vig over 55%)", M["qualifies"] is True)
ok("close = last commit before the bout's own start (-170 / +135)", M["dk_over_close"] == -170 and M["dk_under_close"] == 135)
ok("co-main at a 3.5 line does not qualify and is noted", C["qualifies"] is False and C["note"] == "line not 4.5 (3.5)")
r2 = run("extract", "--slug", "test", "--event", "ev.json", "--log", "log.jsonl", "--ref", "main")
ok("a second extract does not log a bout twice", len(open(f"{d}/log.jsonl").read().splitlines()) == 2 and "already logged" in r2.stdout)
run("grade", "--event", "ev.json", "--log", "log.jsonl")
L = [json.loads(l) for l in open(f"{d}/log.jsonl")]; M = next(l for l in L if l["bout"].startswith("Al"))
ok("decision = over; minus price to win 1u: +1.00 on 1.30 risked", M["went_over"] is True and M["units"] == 1.0 and abs(M["risked"] - 1.30) < 1e-9)
sys.path.insert(0, HERE); sys.argv = ["x", "score", "--log", "none"]
import importlib.util; spec = importlib.util.spec_from_file_location("dk", S); dk = importlib.util.module_from_spec(spec)
sys.argv = ["x"]; src = open(S).read().split("\nap = argparse")[0]; ns = {}; exec(compile(src, S, "exec"), ns)
wo, un = ns["went_over"], ns["units"]
ok("R5 2:31 KO = over", wo({"kind": "win", "method": "KO/TKO", "round": 5, "time": "2:31"}) is True)
ok("R5 2:30 KO = under", wo({"kind": "win", "method": "KO/TKO", "round": 5, "time": "2:30"}) is False)
ok("R4 sub = under", wo({"kind": "win", "method": "Submission", "round": 4, "time": "4:59"}) is False)
ok("no contest = void", wo({"kind": "nc", "method": "Overturned", "round": 2, "time": "1:00"}) is None)
ok("plus price risks 1u: win +1.20, loss -1.00", un(120, True) == (1.2, 1.0) and un(120, False) == (-1.0, 1.0))
before = open(f"{d}/log.jsonl").read(); run("grade", "--event", "ev.json", "--log", "log.jsonl")
ok("grade never rewrites a graded line", open(f"{d}/log.jsonl").read() == before)
r = run("score", "--log", "log.jsonl", "--today", "2026-12-06")
ok("score is interim with 1 bet", "interim, not scored (1 of 40 bets)" in r.stdout)
def synth(n_win, price=-120, clv_close=-130, clv_under=110):
    rows = []
    for i in range(40):
        w = i < n_win
        rows.append({"card_date": "2027-01-01", "bout": f"b{i}", "dk_line": 4.5, "dk_over_entry": price, "dk_under_entry": 100, "entry_seen_at": "x",
                     "entry_source": "t", "dk_over_close": clv_close, "dk_under_close": clv_under, "close_seen_at": "x", "qualifies": True,
                     "result_rounds": "x", "went_over": w, "units": un(price, w)[0], "risked": un(price, w)[1], "note": ""})
    open(f"{d}/s.jsonl", "w").write("".join(json.dumps(x) + "\n" for x in rows))
    return run("score", "--log", "s.jsonl", "--today", "2027-02-01").stdout
ok("40 bets, strong ROI and positive CLV -> SUPPORTED", "-> SUPPORTED" in synth(34))
ok("40 bets, losing -> NOT SUPPORTED", "-> NOT SUPPORTED" in synth(18))
ok("40 bets, ROI > 0 but negative CLV (close -100 / -120) -> NOT SHOWN", "-> NOT SHOWN" in synth(34, clv_close=-100, clv_under=-120))
r = run("manual", "--log", "log.jsonl", "--card-date", "2026-12-05", "--bout", "Gy Man vs Hu Man", "--over", "-125", "--under", "+100", "--seen-at", "2026-12-05T14:00:00Z", "--source", "DK page")
ok("manual DK page entry logs a qualifying line", json.loads(open(f"{d}/log.jsonl").read().splitlines()[-1])["qualifies"] is True)
print(f"{18 - fails}/18 pass"); sys.exit(1 if fails else 0)
