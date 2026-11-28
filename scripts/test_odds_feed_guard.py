#!/usr/bin/env python3
"""Tests for scripts/odds_feed_guard.py and its friday_refresh.sh hook (step 1b), on the Dec 5 DRAFT card
(fixture scripts/fixtures/dec5_odds_feed_DRAFT.json, 14 bouts; the list is embedded below so the test needs no card file).
Each case corrupts one thing in a copy of the fixture and checks the guard's verdict and the reason it gives.
  baseline                         PASS
  STALE    6 h old, no time zone, 3 h in the future, unreadable; and 3.9 h old still PASSES
  MISSING  a bout dropped from the feed; one side's consensus price blank; a bout duplicated in the feed
  EXTRA    a cancelled bout still in the feed FAILS; the same bout listed in card_overrides "cancel" PASSES with a note
  SURNAME  Mairon Santos's price filed under Riley vs Gabriel Santos FAILS; a surname-only "Santos" label FAILS;
           the feed's "Junyong Park" spelling of JunYong Park PASSES
  DRAFT    a .DRAFT.txt list without --allow-draft is refused (exit 2)
  OVERRIDE a reason lets a bad feed through, says OVERRIDDEN and logs one line; an empty reason does not; a good feed with a
           reason is unchanged and not logged
  HOOK     step 1b of friday_refresh.sh, run alone: good feed passes, bad feed stops it, ALLOW_BAD_ODDS_FEED lets it through + logs
Run: python3 -I scripts/test_odds_feed_guard.py (exit 0 = all pass)."""
import copy, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
G = os.path.join(HERE, "odds_feed_guard.py"); FIX = json.load(open(os.path.join(HERE, "fixtures", "dec5_odds_feed_DRAFT.json")))
NOW = "2026-11-27T10:00:00Z"; SLUG = "fn_adesanya_magomedov"
d = tempfile.mkdtemp(); fails = 0
CARD = ["Israel Adesanya vs Shara Magomedov", "Ian Machado Garry vs Yaroslav Amosov", "Serghei Spivac vs Mario Pinto", "Levan Chokheli vs Islam Dulatov",
        "Mairon Santos vs Akbar Abdullaev", "Magomed Tuchalov vs Ion Cutelaba", "Bruno Silva vs Jafel Filho", "Uran Satybaldiev vs Ivan Gnizditskiy",
        "Marco Tulio vs JunYong Park", "Pavel Andrusca vs Mahammadali Osmanli", "Modestino Rodrigues vs Matthieu Duclos", "Abdul Hussein vs Hecher Sosa",
        "Luke Riley vs Gabriel Santos", "Mateusz Rebecki vs Elves Brener"]   # the Dec 5 DRAFT list as of 2026-11-27 (branch dec5-precard)
OFF = os.path.join(d, "2026-12-05.DRAFT.txt"); open(OFF, "w").write("# DRAFT test copy\n" + "\n".join(CARD) + "\n")


def run(mut=None, overrides=None, extra=(), official=None):
    official = official or OFF
    doc = copy.deepcopy(FIX)
    if mut: mut(doc)
    json.dump(doc, open(f"{d}/odds.json", "w"))
    json.dump(overrides or {}, open(f"{d}/ovr.json", "w"))
    p = subprocess.run([sys.executable, "-I", G, "--odds", f"{d}/odds.json", "--official", official, "--slug", SLUG, "--allow-draft",
                        "--overrides", f"{d}/ovr.json", "--now", NOW, *extra], capture_output=True, text=True)
    return p.returncode, p.stdout


def case(name, want_rc, want_text, **kw):
    global fails
    rc, out = run(**kw)
    ok = rc == want_rc and (want_text is None or want_text in out)
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"\n   rc {rc}, output:\n{out}")); fails += not ok


def fight(doc, who):
    return next(f for f in doc["fights"] if who in (f["fighter_a"]["name"], f["fighter_b"]["name"]))


def setf(k, v): return lambda doc: doc.__setitem__(k, v)


case("baseline: clean draft feed passes", 0, "DRAFT ODDS FEED GUARD PASS")
case("STALE: updated_at 6 h old", 1, "STALE: updated_at 2026-11-27T04:00:00+00:00 is 6.0 h old", mut=setf("updated_at", "2026-11-27T04:00:00+00:00"))
case("STALE: 3.9 h old is inside the 4 h limit", 0, "PASS", mut=setf("updated_at", "2026-11-27T06:06:00+00:00"))
case("STALE: no time zone", 1, "has no time zone", mut=setf("updated_at", "2026-11-27T09:35:00"))
case("STALE: 3 h in the future", 1, "is in the future", mut=setf("updated_at", "2026-11-27T13:00:00Z"))
case("STALE: unreadable", 1, "STALE: updated_at unreadable", mut=setf("updated_at", None))
case("MISSING: bout dropped from the feed", 1, "MISSING: Abdul Hussein vs Hecher Sosa has no feed fight",
     mut=lambda doc: doc["fights"].remove(fight(doc, "Abdul Hussein")))
case("MISSING: one side has no consensus price", 1, "MISSING: no consensus moneyline price for Shara Magomedov",
     mut=lambda doc: fight(doc, "Shara Magomedov")["markets"]["moneyline"][1]["books"]["consensus"].__setitem__("cost", None))
case("MISSING: bout duplicated in the feed", 1, "has 2 feed fights (duplicate)",
     mut=lambda doc: doc["fights"].append(copy.deepcopy(fight(doc, "Luke Riley"))))
canc = {"fighter_a": {"name": "Rodolfo Vieira"}, "fighter_b": {"name": "Marc-Andre Barriault"}, "status": "scheduled",
        "markets": {"moneyline": [{"label": "Rodolfo Vieira", "books": {"consensus": {"cost": -150}}}, {"label": "Marc-Andre Barriault", "books": {"consensus": {"cost": 125}}}]}}
case("EXTRA: cancelled bout still in the feed", 1, "EXTRA: feed fight Rodolfo Vieira vs Marc-Andre Barriault is on no official bout",
     mut=lambda doc: doc["fights"].append(copy.deepcopy(canc)))
case("EXTRA: same bout listed in card_overrides cancel passes with a note", 0, "dropped by card_overrides cancel: Rodolfo Vieira vs Marc-Andre Barriault",
     mut=lambda doc: doc["fights"].append(copy.deepcopy(canc)), overrides={SLUG: {"cancel": [["Marc-Andre Barriault", "Rodolfo Vieira"]]}})
def cross(doc):   # Mairon Santos's price row filed under Riley vs Gabriel Santos (same-surname mix-up)
    gs = fight(doc, "Gabriel Santos")["markets"]["moneyline"]
    gs[[i for i, s in enumerate(gs) if s["label"] == "Gabriel Santos"][0]]["label"] = "Mairon Santos"
case("SURNAME: Mairon Santos price under Riley vs Gabriel Santos", 1, "SURNAME: price for 'Mairon Santos' sits under Luke Riley vs Gabriel Santos", mut=cross)
case("SURNAME: surname-only label 'Santos'", 1, "SURNAME: label 'Santos'",
     mut=lambda doc: fight(doc, "Mairon Santos")["markets"]["moneyline"][0].__setitem__("label", "Santos"))
case("SURNAME: feed spelling 'Junyong Park' for JunYong Park passes", 0, "PASS",
     mut=lambda doc: [s.__setitem__("label", "Junyong Park") for s in fight(doc, "JunYong Park")["markets"]["moneyline"] if s["label"] == "JunYong Park"])
p = subprocess.run([sys.executable, "-I", G, "--odds", os.path.join(HERE, "fixtures", "dec5_odds_feed_DRAFT.json"), "--official", OFF, "--slug", SLUG, "--now", NOW], capture_output=True, text=True)
ok = p.returncode == 2 and "REFUSED: the official list is a DRAFT" in p.stdout
print(("PASS " if ok else "FAIL ") + "DRAFT: list refused without --allow-draft"); fails += not ok

# ---- override switch (Sean, Nov 27, option A) ----
LOG = f"{d}/overrides.log"
stale = setf("updated_at", "2026-11-27T04:00:00+00:00")
case("OVERRIDE: bad feed with a reason passes, says OVERRIDDEN", 0, "ODDS FEED GUARD OVERRIDDEN (1 failure(s) let through: bot down, prices checked by hand)",
     mut=stale, extra=("--override", "bot down, prices checked by hand", "--override-log", LOG))
rec = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
ok = len(rec) == 1 and rec[0]["reason"] == "bot down, prices checked by hand" and rec[0]["slug"] == SLUG and rec[0]["fails"][0].startswith("STALE")
print(("PASS " if ok else "FAIL ") + "OVERRIDE: one log line with time, slug, reason and the failures"); fails += not ok
case("OVERRIDE: empty reason does not override", 1, "ODDS FEED GUARD FAIL (1)", mut=stale, extra=("--override", "  ", "--override-log", LOG))
case("OVERRIDE: good feed with a reason is unchanged and not logged", 0, "not logged", extra=("--override", "just in case", "--override-log", LOG))
ok = len(open(LOG).read().splitlines()) == 1
print(("PASS " if ok else "FAIL ") + "OVERRIDE: log still has exactly one line"); fails += not ok

# ---- the friday_refresh.sh hook (step 1b), run on its own in a scratch tree ----
line = next(l for l in open(os.path.join(REPO, "scripts", "friday_refresh.sh")) if l.startswith('step "1b odds feed guard"'))
t = tempfile.mkdtemp()
for sub in ("scripts", "data/official", "form/data/events"): os.makedirs(f"{t}/{sub}", exist_ok=True)
for f in ("odds_feed_guard.py", "card_overrides.py", "odds_newer.py", "fighter_names.py"):
    if os.path.exists(os.path.join(HERE, f)): import shutil; shutil.copy(os.path.join(HERE, f), f"{t}/scripts/{f}")
open(f"{t}/data/official/2026-12-05.txt", "w").write("\n".join(CARD) + "\n")
json.dump({"date": "2026-12-05", "fights": []}, open(f"{t}/form/data/events/ev.json", "w"))
def hook(doc, env):
    json.dump(doc, open(f"{t}/data/{SLUG}_odds.json", "w"))
    script = 'set -euo pipefail; SLUG="%s"; EVENT="form/data/events/ev.json"; step(){ echo "== $*"; }\n%s' % (SLUG, line)
    return subprocess.run(["bash", "-c", script], cwd=t, capture_output=True, text=True, env={**os.environ, **env})
import datetime as _dt
fresh = copy.deepcopy(FIX); fresh["updated_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
bad = copy.deepcopy(fresh); bad["fights"] = [f for f in bad["fights"] if "Abdul Hussein" not in (f["fighter_a"]["name"], f["fighter_b"]["name"])]
env0 = {k: v for k, v in os.environ.items() if k != "ALLOW_BAD_ODDS_FEED"}
r = hook(fresh, {}); ok = r.returncode == 0 and "ODDS FEED GUARD PASS" in r.stdout
print(("PASS " if ok else "FAIL ") + "HOOK: good feed passes step 1b unchanged" + ("" if ok else "\n" + r.stdout + r.stderr)); fails += not ok
r = hook(bad, {"ALLOW_BAD_ODDS_FEED": ""}); ok = r.returncode != 0 and "MISSING: Abdul Hussein vs Hecher Sosa" in r.stdout
print(("PASS " if ok else "FAIL ") + "HOOK: bad feed stops the refresh at step 1b" + ("" if ok else "\n" + r.stdout + r.stderr)); fails += not ok
r = hook(bad, {"ALLOW_BAD_ODDS_FEED": "Hussein bout pulled, waiting on UFC.com"})
lg = f"{t}/audits/odds_guard/overrides.log"
ok = r.returncode == 0 and "OVERRIDDEN" in r.stdout and os.path.exists(lg) and "Hussein bout pulled" in open(lg).read()
print(("PASS " if ok else "FAIL ") + "HOOK: ALLOW_BAD_ODDS_FEED lets it through and logs it" + ("" if ok else "\n" + r.stdout + r.stderr)); fails += not ok
N = 23
print(f"{N - fails}/{N} pass"); sys.exit(1 if fails else 0)
