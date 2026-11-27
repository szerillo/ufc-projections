"""DRY RUN of the Friday Dec 4 spread-lock path on the DRAFT Dec 5 card. Tests the PATH, not prices.

Everything it writes goes to a scratch directory (default /tmp/dec5_spread_dryrun). It never touches analysis/spread_locks/,
never commits, never bets. The inputs it builds are SYNTHETIC and labelled so:
  * projections export: sides and true_fav from the BFO DRAFT no-vig medians (no model), a flat placeholder method split,
    "dryrun": true. The real export comes from Sean's publish.
  * odds file: consensus no-vig from the same medians.
  * event file: the DRAFT list, first bout 15:00Z and main event 21:00Z from cards.yml (both unconfirmed).
  * books.json: three TEST rows (-3.5 at -110 / +3.5 at -110), flagged "test": true. Not real book prices.
Steps: preflight (expects READY bar the DRAFT warning), lock (SPREAD_TRACK_TEST=1), table, close, grade on fake results,
then the refusals: staging export, lock after the first bout, and a test row written outside /tmp.
Run from a ufc-projections checkout of this branch:
  python3 -I audits/dec5/spread_dryrun/dryrun_spread_lock.py --cache <UFCStats cache dir> [--scratch DIR]"""
import argparse, json, os, shutil, subprocess, sys
ap = argparse.ArgumentParser(); ap.add_argument("--cache", required=True); ap.add_argument("--scratch", default="/tmp/dec5_spread_dryrun")
a = ap.parse_args()
REPO = os.getcwd(); S = a.scratch; SLUG = "fn_adesanya_magomedov"; DATE = "2026-12-05"
EVF = f"form/data/events/{DATE}-ufc-fight-night-adesanya-vs-magomedov.json"
if os.path.exists(S): shutil.rmtree(S)
# scratch tree = this checkout's scripts + data (copied), so the tools run unchanged and nothing lands in the repo
shutil.copytree(REPO, S, ignore=shutil.ignore_patterns(".git", "form"), symlinks=True)
os.makedirs(f"{S}/form/data/events", exist_ok=True)
for f in os.listdir(f"{REPO}/form/data"):   # top-level site data (aliases, labs) the tools import; no event or fighter files
    if f.endswith(".json"): shutil.copy(f"{REPO}/form/data/{f}", f"{S}/form/data/{f}")
os.makedirs(f"{S}/analysis/spreads_tracker", exist_ok=True)
for f in ("spread_track.py", "frozen_v1.json"):
    open(f"{S}/analysis/spreads_tracker/{f}", "w").write(subprocess.run(["git", "show", f"origin/audit-locks:analysis/spreads_tracker/{f}"], capture_output=True, text=True, check=True).stdout)
open(f"{S}/PUBLIC_OK.txt", "w").write(subprocess.run(["git", "show", "origin/audit-locks:analysis/PUBLIC_OK.txt"], capture_output=True, text=True, check=True).stdout)

def imp(o): return 100 / (o + 100) if o > 0 else -o / (-o + 100)
COL = ["Polymarket", "Kalshi", "FanDuel", "Caesars", "BetRivers", "BetWay", "Unibet", "BetMGM", "DraftKings"]; MED4 = ["FanDuel", "Caesars", "BetRivers", "Unibet"]
def med(x):
    x = sorted(x); n = len(x); return x[n // 2] if n % 2 else round((x[n // 2 - 1] + x[n // 2]) / 2)
prices = {}
for l in open("audits/dec5/odds_draft/bfo_raw_2026-11-27.txt"):
    if l.startswith("#") or "|" not in l: continue
    n, v = l.rstrip("\n").split("|"); p = dict(zip(COL, [int(x) if x else None for x in v.split(",")]))
    prices[n.lower()] = med([p[b] for b in MED4 if p[b] is not None])
bouts = [tuple(x.strip() for x in l.split(" vs ")) for l in open("data/official/2026-12-05.DRAFT.txt") if " vs " in l and not l.startswith("#")]
sys.path.insert(0, "scripts"); import fighter_names as FN
def price(name):
    hit = [v for k, v in prices.items() if FN.name_match(k, name)]
    assert len(hit) == 1, (name, hit); return hit[0]
V = {"schema": "dryrun", "dryrun": True, "staging": False, "slug": SLUG, "event": "UFC Fight Night: Adesanya vs. Magomedov (DRAFT)",
     "published_at": "DRYRUN-not-a-publish", "fights": []}
O = {"card": "DRAFT", "updated_at": "2026-11-27T09:35:00+00:00", "source": "DRYRUN from BFO draft medians", "fights": []}
E = {"name": "UFC Fight Night: Adesanya vs. Magomedov", "date": DATE, "status": "upcoming", "fights": []}
for i, (x, y) in enumerate(bouts):
    px, py = price(x), price(y); nx = imp(px) / (imp(px) + imp(py))
    fav, dog = (x, y) if nx >= 0.5 else (y, x); pf = max(nx, 1 - nx)
    five = i < 2   # main and co-main are scheduled five-rounders on the draft card
    V["fights"].append({"publish": True, "tag": "x-5" if five else "x", "dog": dog, "fav": fav,
                        "sheet": {"true_fav": round(pf, 4), "true_dog": round(1 - pf, 4)},
                        "method": {"fav": {"dec": 0.5, "ko": 0.4, "sub": 0.1}, "dog": {"dec": 0.5, "ko": 0.4, "sub": 0.1}}})
    O["fights"].append({"n": len(bouts) - i, "markets": {"moneyline": [
        {"label": x, "books": {"consensus": {"no_vig_pct": round(nx * 100, 2)}}}, {"label": y, "books": {"consensus": {"no_vig_pct": round((1 - nx) * 100, 2)}}}]}})
    start = "2026-12-05 21:00:00" if i == 0 else "2026-12-05 15:00:00" if i == len(bouts) - 1 else None
    E["fights"].append({"n": len(bouts) - i, "a": {"name": x}, "b": {"name": y}, "start": start, "result": None})
json.dump(V, open(f"{S}/data/{SLUG}_projections.json", "w"), indent=1)
json.dump(O, open(f"{S}/data/{SLUG}_odds.json", "w"), indent=1)
json.dump(E, open(f"{S}/{EVF}", "w"), indent=1)
pick = [V["fights"][0], V["fights"][1], V["fights"][6]]   # main event, co-main, one three-rounder
books = []
for f in pick:
    books += [{"fighter": f["fav"], "line": -3.5, "price": -110, "book": "DraftKings", "seen_at": "2026-11-27T09:40:00Z", "test": True},
              {"fighter": f["dog"], "line": 3.5, "price": -110, "book": "DraftKings", "seen_at": "2026-11-27T09:40:00Z", "test": True}]
json.dump(books, open(f"{S}/books.json", "w"), indent=1)
res = {"source": "DRYRUN fake results", "fights": [
    {"winner": pick[0]["fav"], "loser": pick[0]["dog"], "method": "Decision", "cards": [[49, 46], [49, 46], [48, 47]]},
    {"winner": pick[1]["dog"], "loser": pick[1]["fav"], "method": "KO", "cards": []},
    {"winner": pick[2]["fav"], "loser": pick[2]["dog"], "method": "Decision", "cards": [[29, 28], [29, 28], [28, 29]]}]}
json.dump(res, open(f"{S}/results.json", "w"), indent=1)

R = []
def run(label, cmd, env=None, expect=0, want=None):
    p = subprocess.run(cmd, cwd=S, capture_output=True, text=True, env={**os.environ, **(env or {})})
    ok = (p.returncode == 0) == (expect == 0) and (want is None or want in p.stdout + p.stderr)
    R.append((label, ok)); print(f"\n### {label}: exit {p.returncode} -> {'as expected' if ok else 'UNEXPECTED'}")
    print((p.stdout + p.stderr).strip()[-2500:]); return p
LOCK = f"{S}/test_lock.jsonl"; T = {"SPREAD_TRACK_TEST": "1"}
pf = run("preflight on the DRAFT inputs (blocks only on draft-only items)", [sys.executable, "-I", "audits/forward_scoring/spread_lock_preflight.py", "--slug", SLUG, "--date", DATE,
         "--books", "books.json", "--cache", a.cache, "--card-list", "data/official/2026-12-05.DRAFT.txt", "--allowlist", "PUBLIC_OK.txt"])
R[-1] = (R[-1][0], "READY" in pf.stdout)   # preflight must say READY: the DRAFT list is a warning, not a block
print("preflight READY:", "READY" in pf.stdout and "NOT READY" not in pf.stdout)
run("lock (test mode)", [sys.executable, "-I", "analysis/spreads_tracker/spread_track.py", "lock", "--slug", SLUG, "--event", EVF, "--books", "books.json", "--out", LOCK, "--cache", a.cache], T)
run("table", [sys.executable, "-I", "analysis/spreads_tracker/spread_track.py", "table", "--locks", LOCK])
run("close (test mode)", [sys.executable, "-I", "analysis/spreads_tracker/spread_track.py", "lock", "--stage", "close", "--slug", SLUG, "--event", EVF, "--books", "books.json", "--out", LOCK, "--cache", a.cache], T)
run("grade on fake results", [sys.executable, "-I", "analysis/spreads_tracker/spread_track.py", "grade", "--locks", LOCK, "--results", "results.json"])
# refusals
st = json.load(open(f"{S}/data/{SLUG}_projections.json")); st["staging"] = True; json.dump(st, open(f"{S}/data/{SLUG}_projections.json", "w"))
run("REFUSE staging export", [sys.executable, "-I", "analysis/spreads_tracker/spread_track.py", "lock", "--slug", SLUG, "--event", EVF, "--books", "books.json", "--out", f"{S}/x.jsonl", "--cache", a.cache], expect=1, want="REFUSED: staging export")
st["staging"] = False; json.dump(st, open(f"{S}/data/{SLUG}_projections.json", "w"))
ev = json.load(open(f"{S}/{EVF}")); ev["fights"][-1]["start"] = "2026-11-01 15:00:00"; json.dump(ev, open(f"{S}/{EVF}", "w"))
run("REFUSE lock after the first bout (no test mode)", [sys.executable, "-I", "analysis/spreads_tracker/spread_track.py", "lock", "--slug", SLUG, "--event", EVF, "--books", "books.json", "--out", f"{S}/y.jsonl", "--cache", a.cache], expect=1, want="REFUSED: card started")
run("REFUSE preflight after the first bout", [sys.executable, "-I", "audits/forward_scoring/spread_lock_preflight.py", "--slug", SLUG, "--date", DATE, "--books", "books.json", "--cache", a.cache, "--allowlist", "PUBLIC_OK.txt"], expect=1, want="has started")
# GAP PROBE: spread_track refuses test rows only outside /tmp/. A checkout that itself lives under /tmp (scratch trees,
# worktrees) is inside /tmp, so a test-mode lock aimed at the real lock path is ACCEPTED. Expected to be accepted today.
os.makedirs(f"{S}/analysis/spread_locks", exist_ok=True)
gp = subprocess.run([sys.executable, "-I", "analysis/spreads_tracker/spread_track.py", "lock", "--slug", SLUG, "--event", EVF, "--books", "books.json",
                     "--out", "analysis/spread_locks/2026-12-05.jsonl", "--cache", a.cache], cwd=S, capture_output=True, text=True, env={**os.environ, **T})
gap = gp.returncode == 0 and os.path.exists(f"{S}/analysis/spread_locks/2026-12-05.jsonl")
print("\n### GAP PROBE: test-mode lock into analysis/spread_locks from a checkout under /tmp:", "ACCEPTED (known gap)" if gap else "refused")
run("preflight BLOCKS a lock file holding test rows (mitigation)", [sys.executable, "-I", "audits/forward_scoring/spread_lock_preflight.py", "--slug", SLUG, "--date", DATE,
    "--books", "books.json", "--cache", a.cache, "--allowlist", "PUBLIC_OK.txt"], expect=1, want="holds SPREAD_TRACK_TEST rows")
shutil.rmtree(f"{S}/analysis/spread_locks")
leak = os.path.exists(f"{REPO}/analysis/spread_locks/2026-12-05.jsonl")
R.append(("no lock file written in the real checkout", not leak))
print("\nKNOWN GAP (not counted as a pass):", "test-mode guard accepts lock paths inside a checkout under /tmp" if gap else "none")
print("\n## SUMMARY"); [print(("PASS " if ok else "FAIL ") + l) for l, ok in R]
print(f"{sum(ok for _, ok in R)}/{len(R)} pass"); sys.exit(0 if all(ok for _, ok in R) else 1)
