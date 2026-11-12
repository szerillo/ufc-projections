"""Earlier_Start_PREREG (sha 5c667602): recompute every published odds block under the earlier-start cut and patch it.
Only blocks that equal the v24-rule recompute are patched (hand-kept blocks are reported, not touched).
usage: python3 apply_earlier_start.py REPO [--write]"""
import sys, json, glob, importlib.util, pathlib, datetime as dt, statistics
repo = pathlib.Path(sys.argv[1]); write = "--write" in sys.argv
sys.path.insert(0, str(repo / "scripts"))
sp = importlib.util.spec_from_file_location("bf", repo / "scripts/build_form.py"); BF = importlib.util.module_from_spec(sp); sp.loader.exec_module(BF)
by = BF.load_odds(repo / ".form_cache"); idx = BF.index_odds(by)
real_cut = BF.start_cut

def pub(eid, fl, a, b, d, old_rule):
    BF.start_cut = (lambda snaps, sched=None: None) if old_rule else real_cut
    o = BF.summarize_odds(by[eid], fl, a_name=a, sched=BF.bp_start(a, b, d))
    BF.start_cut = real_cut
    return BF.public_odds(o)

rows = []; kept = 0; patched_files = 0; opener_after = 0; nblocks = 0
for fp in sorted(glob.glob(str(repo / "form/data/events/*.json"))):
    ev = json.load(open(fp)); d = dt.date.fromisoformat(ev["date"]); ch = False
    for f in ev["fights"]:
        cur = f.get("odds")
        if not cur:
            continue
        nblocks += 1
        a, b = f["a"]["name"], f["b"]["name"]
        eid, fl = BF.find_odds(idx, by, a, b, d)
        if not eid:
            kept += 1; continue
        old = pub(eid, fl, a, b, d, True)
        if json.dumps(old, sort_keys=True) != json.dumps(cur, sort_keys=True):
            kept += 1; continue
        new = pub(eid, fl, a, b, d, False)
        cut = real_cut(by[eid], BF.bp_start(a, b, d))
        if cut and BF._utc(new["open"]["t"]) >= cut:
            opener_after += 1
        oc, nc = cur.get("close"), new.get("close")
        rows.append((ev["date"], a, b, oc, nc, cut.strftime("%Y-%m-%dT%H:%M") if cut else None, by[eid][-1]["start"]))
        if new != cur:
            f["odds"] = new; ch = True
    if ch and write:
        pathlib.Path(fp).write_text(json.dumps(ev, separators=(",", ":"), ensure_ascii=False)); patched_files += 1

same = [r for r in rows if r[3] == r[4]]
lost = [r for r in rows if r[3] and not r[4]]
moved = [r for r in rows if r[3] and r[4] and r[3] != r[4]]
dpts = sorted(abs(r[4]["p"] - r[3]["p"]) * 100 for r in moved)
print(f"published odds blocks: {nblocks}; recomputed: {len(rows)}; not equal to v24 recompute (left alone): {kept}")
print(f"close unchanged: {len(same)}; close moved to an earlier snapshot: {len(moved)}; close lost (opener only): {len(lost)}; opener after cut: {opener_after}")
if dpts:
    q = lambda p: dpts[min(len(dpts) - 1, int(p * len(dpts)))]
    print(f"change in close, pts (moved only): median {statistics.median(dpts):.2f}, p95 {q(0.95):.2f}, max {dpts[-1]:.2f}; over 1 pt: {sum(x>1 for x in dpts)}; over 3: {sum(x>3 for x in dpts)}")
    allp = dpts + [0.0] * len(same)
    print(f"over all recomputed blocks: median {statistics.median(allp):.2f}")
print("largest:")
for r in sorted(moved, key=lambda r: -abs(r[4]["p"] - r[3]["p"]))[:5]:
    print(f"  {r[0]} {r[1]} vs {r[2]}: {r[3]['p']} ({r[3]['nb']} US, {r[3]['t'][:16]}) -> {r[4]['p']} ({r[4]['nb']} US, {r[4]['t'][:16]}), cut {r[5]}, archive start {r[6]}, {abs(r[4]['p']-r[3]['p'])*100:.1f} pts")
for r in lost:
    print(f"  LOST: {r[0]} {r[1]} vs {r[2]}: close {r[3]['t'][:16]}, cut {r[5]}")
json.dump([[r[0], r[1], r[2], r[3], r[4], r[5], r[6]] for r in rows], open(pathlib.Path(__file__).with_name("earlier_start_rows.json"), "w"))
if write: print(f"files patched: {patched_files}")
