"""Patch UFCStats-derived fields (per-fight stats, url, result ref/details) from a sheet-less rebuild into the
live event files, keeping every sheet/model/odds/start field from main. Usage: patch_events.py NEWDIR MAINJSON... (in place)"""
import json, sys, unicodedata
norm = lambda s: unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
newdir, files = sys.argv[1], sys.argv[2:]
for p in files:
    live = json.load(open(p)); new = json.load(open(f"{newdir}/{p.split('/')[-1]}"))
    idx = {frozenset((norm(f["a"]["name"]), norm(f["b"]["name"]))): f for f in new["fights"]}
    n = 0
    for f in live["fights"]:
        g = idx.get(frozenset((norm(f["a"]["name"]), norm(f["b"]["name"]))))
        assert g, ("no match", f["a"]["name"], f["b"]["name"])
        flip = norm(g["a"]["name"]) != norm(f["a"]["name"])
        r, gr = f.get("result") or {}, g.get("result") or {}
        st = g.get("stats")
        if flip:  # rebuild lists the corner the other way round: swap stats and the winner side
            st = st and {"a": st["b"], "b": st["a"]}
            gr = dict(gr, winner={"a": "b", "b": "a"}.get(gr.get("winner"), gr.get("winner")))
        assert (r.get("winner"), r.get("method"), str(r.get("round"))) == (gr.get("winner"), gr.get("method"), str(gr.get("round"))), ("result mismatch", f["a"]["name"], r, gr)
        f["stats"] = st; f["url"] = f.get("url") or g.get("url")
        for k in ("ref", "details"):
            if gr.get(k) is not None: r[k] = gr[k]
        f["result"] = r; n += 1
    json.dump(live, open(p, "w"), separators=(",", ":"), ensure_ascii=False)
    print(p, n, "fights patched")
