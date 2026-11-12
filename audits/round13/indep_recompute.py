"""Independent recompute of every published close under the earlier-start rule (own cut and own median; builder used only to
load the archive and match bouts)."""
import sys, json, glob, importlib.util, pathlib, datetime as dt, statistics
repo = pathlib.Path("/tmp/e5"); sys.path.insert(0, str(repo / "scripts"))
sp = importlib.util.spec_from_file_location("bf", repo / "scripts/build_form.py"); BF = importlib.util.module_from_spec(sp); sp.loader.exec_module(BF)
by = BF.load_odds(repo / ".form_cache"); idx = BF.index_odds(by)
REG = {"draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "circasports"}
P = lambda x: dt.datetime.fromisoformat(str(x).replace("Z", "+00:00").replace(" ", "T")).replace(tzinfo=dt.timezone.utc)
bp = []
for fp in glob.glob(str(repo / "data/*_odds.json")):
    for f in json.load(open(fp))["fights"]:
        if f.get("scheduled_utc"): bp.append((P(f["scheduled_utc"]), f["fighter_a"]["name"], f["fighter_b"]["name"]))
n = bad = nclose = 0
for fp in sorted(glob.glob(str(repo / "form/data/events/*.json"))):
    ev = json.load(open(fp)); d = dt.date.fromisoformat(ev["date"])
    for f in ev["fights"]:
        o = f.get("odds")
        if not o: continue
        a, b = f["a"]["name"], f["b"]["name"]; eid, _ = BF.find_odds(idx, by, a, b, d); sn = by[eid]; n += 1
        e1 = P(sn[-1]["start"]); ests = [e1] + [P(s["start"]) for s in sn if e1 - dt.timedelta(hours=12) <= P(s["start"]) <= e1]
        ests += [t for t, x, y in bp if abs((t.date() - d).days) <= 1 and BF.pair_match(a, b, x, y)[0] >= 1]
        if f.get("start"): ests.append(P(f["start"]))
        cut = min(ests); last = None
        for s in sn:
            if P(s["t"]) >= cut or s["t"] < o["open"]["t"]: continue
            ps = []
            for bk, m in s["books"].items():
                if bk in REG and m.get("h2h"):
                    h, w = m["h2h"]; fl = BF.name_match(a, s["away"]) > BF.name_match(a, s["home"])
                    x, y = (w, h) if fl else (h, w); ps.append((1 / x) / (1 / x + 1 / y))
            if ps: last = (s["t"], statistics.median(ps))
        c = o.get("close")
        if (last is None) != (c is None) or (last and (c["t"][:19] != last[0][:19] or abs(c["p"] - last[1]) > 0.0006)):
            bad += 1; print("MISMATCH", ev["date"], a, b, c and (c["t"], c["p"]), last)
        nclose += c is not None
print(f"independent recompute: {n} published blocks, {nclose} with a close, {bad} mismatches")
