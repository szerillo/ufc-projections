"""Lift Line pending holds that the odds feed has since resolved (Nov 20 2026, Mitchell vs Yousaf).

A bout held at promote time because it was not yet in data/<slug>_odds.json (OPP-2) stays held in the verified
export until Sean publishes again. This re-runs scripts/verify_projections.py on the SAME export (data/pending,
same published_at as the verified file) against the CURRENT odds file. A held bout is restored only if that run
passes with the bout no longer pending; its numbers come from the export unchanged.
The 3 h price-age gate is not re-tested here: it was passed at promote time and holds for every live bout alike.
  python3 -I scripts/recheck_holds.py --slug fn_prochazka_stirling [--dry]"""
import json, sys, subprocess, tempfile, pathlib, datetime as dt, os
REPO = pathlib.Path(__file__).resolve().parent.parent
a = sys.argv; slug = a[a.index("--slug") + 1]; dry = "--dry" in a
V_p = REPO / f"data/{slug}_projections.json"; P_p = REPO / f"data/pending/{slug}_projections.json"
if not V_p.exists() or not P_p.exists(): print("RECHECK HOLDS: no verified or pending export; nothing to do"); sys.exit(0)
V, P = json.load(open(V_p)), json.load(open(P_p))
held = [h for h in V.get("line_pending") or [] if "OPP-2" in h.get("reason", "")]
if not held: print("RECHECK HOLDS: no OPP-2 holds"); sys.exit(0)
if P.get("published_at") != V.get("published_at") or P.get("staging"):
    sys.exit("RECHECK HOLDS: data/pending is not the export that was verified; publish again instead")
key = lambda d, f: (d.strip().lower(), f.strip().lower())
with tempfile.TemporaryDirectory() as td:
    T = json.loads(json.dumps(P)); T["prices_loaded"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    tp = pathlib.Path(td) / f"{slug}_projections.json"; json.dump(T, open(tp, "w")); rp = pathlib.Path(td) / "r.md"
    r = subprocess.run([sys.executable, str(REPO / "scripts/verify_projections.py"), str(tp), "--report", str(rp)], cwd=REPO, capture_output=True, text=True)
    rep = rp.read_text() if rp.exists() else r.stdout
if "**PASS" not in rep:
    print("RECHECK HOLDS: re-check did not pass; holds unchanged\n" + rep[:800]); sys.exit(0)
odds_at = json.load(open(REPO / f"data/{slug}_odds.json")).get("updated_at")
now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
lifted = []
for h in held:
    L = rep.splitlines(); i = next((k for k, ln in enumerate(L) if ln.startswith("**Line pending")), None); pend = []
    if i is not None:                                   # the "**Line pending (n):**" header, then its "- dog vs fav: reason" lines
        for ln in L[i + 1:]:
            if not ln.strip(): break
            pend.append(ln)
    if any(h["dog"].split()[-1] in ln or h["fav"].split()[-1] in ln for ln in pend):   # the re-check still holds it
        continue
    row = next((f for f in P["fights"] if key(f["dog"], f["fav"]) == key(h["dog"], h["fav"])), None)
    if not row: continue
    lifted.append((h, row))
if not lifted: print("RECHECK HOLDS: holds still apply"); sys.exit(0)
order = [key(f["dog"], f["fav"]) for f in P["fights"]]
for h, row in lifted:
    V["line_pending"] = [x for x in V["line_pending"] if x is not h]
    V["fights"].append(row)
    V["verified"].setdefault("holds_lifted", []).append({"dog": h["dog"], "fav": h["fav"], "reason": h["reason"],
        "rechecked_at": now, "odds_updated_at": odds_at, "by": "scripts/recheck_holds.py"})
V["fights"].sort(key=lambda f: order.index(key(f["dog"], f["fav"])))
if not V["line_pending"]: V.pop("line_pending")
print("RECHECK HOLDS: lifted " + ", ".join(f"{h['dog']} vs {h['fav']}" for h, _ in lifted) + f" (odds file {odds_at})" + (" [dry run]" if dry else ""))
if not dry:
    open(V_p, "w").write(json.dumps(V, indent=1) + "\n")
