"""Kirk round 21 call 1: Friday republish then a Saturday republish 17 h later (Fri 7:30 pm ET -> Sat 12:30 pm ET).
The archive ends now (Thu), so the two anchors are shifted onto real archive time: T1 = archive_newest - 17 h ('Friday'),
T2 = archive_newest ('Saturday'). Same 17 h gap, same 24 h window rule (build_line_history.listed_check, unchanged).
Case F: on Friday Sean pastes, for every cell, the best US-regulated price seen in the window (what listed_price_report
shows). Case S1: Saturday republish with NO new paste (same Listed prices, new published_at). Case S2: Saturday republish after
re-pasting from a fresh report. Scratch only: reads the cache and the event file, writes nothing in the repo."""
import json, sys, datetime as dt, pathlib, copy
sys.path.insert(0, "/tmp/e5/scripts"); import build_line_history as BL, build_form as BF
by = BF.load_odds(pathlib.Path("/tmp/e5/.form_cache")); idx = BF.index_odds(by)
ev = json.load(open("/tmp/e5/form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json")); d = dt.date.fromisoformat(ev["date"])
newest = max(s["t"] for v in by.values() for s in v)
T2 = dt.datetime.fromisoformat(newest[:19]).replace(tzinfo=dt.timezone.utc); T1 = T2 - dt.timedelta(hours=17)
iso = lambda t: t.isoformat()[:19] + "Z"
print(f"archive newest {newest}; T1 ('Fri 7:30 pm ET') = {iso(T1)}; T2 ('Sat 12:30 pm ET') = {iso(T2)}; window {BL.LISTED_WINDOW_H} h")
fights = []
for f in ev["fights"]:
    an, bn = f["a"]["name"], f["b"]["name"]; eid, fl = BF.find_odds(idx, by, an, bn, d)
    if eid: fights.append((f["n"], an, bn, eid, fl))
def run(listed, until):
    out = {}
    for n, an, bn, eid, fl in fights:
        la, lb = listed.get((n, "a")), listed.get((n, "b"))
        r, win = BL.listed_check(by[eid], fl, an, la if la is not None else -10000, lb if lb is not None else -10000, iso(until))
        out[n] = r
    return out, win
# Friday: Sean pastes the best regulated price in the Friday window for every cell
probe, win1 = run({}, T1)
L1 = {(n, sd): (v["best_regulated"][0] if v["best_regulated"] else None) for n, r in probe.items() for sd, v in r.items()}
F, _ = run(L1, T1); S1, win2 = run(L1, T2)
print(f"Friday window {win1}; Saturday window {win2} (re-anchored to the new published_at)")
nof = [(n, sd) for n, r in F.items() for sd, v in r.items() if not v["ok"]]
nos = [(n, sd, L1[(n, sd)], r[sd]["best_regulated"]) for n, r in S1.items() for sd in r if not r[sd]["ok"]]
print(f"Case F  (Friday, pasted from report): NO cells {len(nof)} {nof}")
print(f"Case S1 (Saturday republish, no new paste): NO cells {len(nos)}")
for x in nos: print("   bout", x[0], x[1], "listed", x[2], "-> best regulated in Saturday window", x[3])
L2 = {(n, sd): (v["best_regulated"][0] if v["best_regulated"] else None) for n, r in S1.items() for sd, v in r.items()}
S2, _ = run(L2, T2)
print(f"Case S2 (Saturday, re-pasted from a fresh report): NO cells {sum(1 for r in S2.values() for v in r.values() if not v['ok'])}")
print("Price movement inside the 17 h: cells whose best regulated price changed:",
      sum(1 for n, r in S1.items() for sd in r if r[sd]["best_regulated"] and F[n][sd]["best_regulated"] and r[sd]["best_regulated"][0] != F[n][sd]["best_regulated"][0]))
