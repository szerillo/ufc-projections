#!/usr/bin/env python3
"""Tests for scripts/odds_feed_guard.py on the Dec 5 DRAFT card (fixture scripts/fixtures/dec5_odds_feed_DRAFT.json, 14 bouts).
Each case corrupts one thing in a copy of the fixture and checks the guard's verdict and the reason it gives.
  baseline                         PASS
  STALE    6 h old, no time zone, 3 h in the future, unreadable; and 3.9 h old still PASSES
  MISSING  a bout dropped from the feed; one side's consensus price blank; a bout duplicated in the feed
  EXTRA    a cancelled bout still in the feed FAILS; the same bout listed in card_overrides "cancel" PASSES with a note
  SURNAME  Mairon Santos's price filed under Riley vs Gabriel Santos FAILS; a surname-only "Santos" label FAILS;
           the feed's "Junyong Park" spelling of JunYong Park PASSES
  DRAFT    a .DRAFT.txt list without --allow-draft is refused (exit 2)
Run: python3 -I scripts/test_odds_feed_guard.py (exit 0 = all pass)."""
import copy, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
G = os.path.join(HERE, "odds_feed_guard.py"); FIX = json.load(open(os.path.join(HERE, "fixtures", "dec5_odds_feed_DRAFT.json")))
OFF = os.path.join(REPO, "data", "official", "2026-12-05.DRAFT.txt"); NOW = "2026-11-27T10:00:00Z"; SLUG = "fn_adesanya_magomedov"
d = tempfile.mkdtemp(); fails = 0


def run(mut=None, overrides=None, extra=(), official=OFF):
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
print(f"{15 - fails}/15 pass"); sys.exit(1 if fails else 0)
