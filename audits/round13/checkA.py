import sys, json, importlib.util, pathlib, datetime as dt, statistics, collections
repo = pathlib.Path("/tmp/e5"); sys.path.insert(0, str(repo / "scripts"))
sp = importlib.util.spec_from_file_location("bf", repo / "scripts/build_form.py"); BF = importlib.util.module_from_spec(sp); sp.loader.exec_module(BF)
by = BF.load_odds(repo / ".form_cache"); idx = BF.index_odds(by)
rows = json.load(open("earlier_start_rows.json"))
c = collections.Counter(); spreads = {"after_E2": [], "after_E3_only": [], "control_pre": []}; mins = []
for d, a, b, oc, nc, cut, e1 in rows:
    if not oc: continue
    dd = dt.date.fromisoformat(d); eid, fl = BF.find_odds(idx, by, a, b, dd); sn = by[eid]
    e2 = BF._utc(BF.bp_start(a, b, dd)); tc = BF._utc(oc["t"]); cu = BF._utc(cut)
    snap = next(s for s in sn if s["t"] == oc["t"])
    us = []
    for bk, m in snap["books"].items():
        if bk in BF.US_REGULATED and m.get("h2h"):
            h, w = m["h2h"]; f2 = BF.name_match(a, snap["away"]) > BF.name_match(a, snap["home"])
            p = BF.novig(*((w, h) if f2 else (h, w)))
            if p is not None: us.append(p)
    sp_ = (max(us) - min(us)) * 100 if len(us) >= 2 else None
    if tc < cu:
        c["close before cut (clean)"] += 1
        if sp_ is not None: spreads["control_pre"].append(sp_)
        continue
    k = "after_E2" if e2 and tc >= e2 else "after_E3_only"
    c[k] += 1; mins.append((tc - cu).total_seconds() / 60)
    if sp_ is not None: spreads[k].append(sp_)
print("v24 published closes:", sum(1 for r in rows if r[3]), dict(c))
print("minutes from cut to the v24 close snapshot: median %.0f, max %.0f" % (statistics.median(mins), max(mins)))
for k, v in spreads.items():
    v.sort(); print(f"US-book spread at the close snapshot, {k}: n {len(v)}, median {statistics.median(v):.1f} pts, share over 15 pts {sum(x>15 for x in v)/len(v):.1%}")
