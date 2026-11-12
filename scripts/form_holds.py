#!/usr/bin/env python3
"""Kirk round 28: hold (pull) numbers from the public site until the post-334 bio refresh.

  python3 -I scripts/form_holds.py apply   # idempotent; first run records the pulled values in audits/round28/hold_values.json
  python3 -I scripts/form_holds.py check   # exit 1 and list any held field that still carries a value

What a hold does, per form/data/form_holds.json (which names fights, fields and rows, never values):
  form_line: event file fight -> form.p = null, the Form Line angles built from p (fl5, fl10, fl10_dog) removed, form.held = text
  bio:       fighter file      -> bio[key] = null, bio[key + "_held"] = text
  labs:      labs.json rows    -> every number in the row = null, row.held = text
The pages and embeds print the held text where the number was. The pulled values go only to the audit record, which the
verifier reads to search the site for any leftover copy (scripts/verify_fight_embeds.py hold_check)."""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; FD = REPO / "form/data"
HOLDS = FD / "form_holds.json"; REC = REPO / "audits/round28/hold_values.json"
FL_ANGLES = ("fl5", "fl10", "fl10_dog")
LAB_NUM = ("n", "w", "wp", "on", "ow", "owp", "imp", "roi")

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def dump(p, d, compact): p.write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False) if compact else json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")

def problems(root=REPO):
    fd = root / "form/data"; H = load(fd / "form_holds.json"); bad = []
    for slug, ns in H["form_line"]["events"].items():
        ev = load(fd / "events" / f"{slug}.json")
        for n in ns:
            f = next((x for x in ev["fights"] if x["n"] == n), None)
            if not f: bad.append(f"{slug} fight {n}: not in the event file"); continue
            fm = f.get("form") or {}
            if fm.get("p") is not None: bad.append(f"{slug} fight {n}: form.p still {fm['p']}")
            if any(k in (fm.get("ang") or {}) for k in FL_ANGLES): bad.append(f"{slug} fight {n}: Form Line angle still listed")
            if fm.get("held") != H["form_line"]["text"]: bad.append(f"{slug} fight {n}: held text missing")
    for slug, keys in H["bio"]["fighters"].items():
        b = load(fd / "fighters" / f"{slug}.json").get("bio") or {}
        for k in keys:
            if b.get(k) not in (None, ""): bad.append(f"{slug}: bio.{k} still {b[k]}")
            if b.get(k + "_held") != H["bio"]["text"]: bad.append(f"{slug}: bio.{k}_held missing")
    L = load(fd / "labs.json")
    for sec, labels in H["labs"]["rows"].items():
        for lab in labels:
            r = next((x for x in L[sec] if x.get("label") == lab), None)
            if not r: bad.append(f"labs {sec} {lab}: row missing"); continue
            if any(r.get(k) is not None for k in LAB_NUM): bad.append(f"labs {sec} {lab}: numbers still present")
            if r.get("held") != H["labs"]["text"]: bad.append(f"labs {sec} {lab}: held text missing")
    return bad

def apply():
    H = load(HOLDS); rec = load(REC) if REC.exists() else {"form_line": {}, "bio": {}, "labs": {}}; changed = []
    for slug, ns in H["form_line"]["events"].items():
        p = FD / "events" / f"{slug}.json"; ev = load(p); hit = False
        for f in ev["fights"]:
            if f["n"] not in ns: continue
            fm = f["form"]; key = f"{slug}#{f['n']}"
            if fm.get("p") is not None:
                rec["form_line"].setdefault(key, {"p": fm["p"], "ang": {k: v for k, v in (fm.get("ang") or {}).items() if k in FL_ANGLES}})
                fm["p"] = None; hit = True
            for k in FL_ANGLES:
                if k in (fm.get("ang") or {}): fm["ang"].pop(k); hit = True
            if fm.get("held") != H["form_line"]["text"]: fm["held"] = H["form_line"]["text"]; hit = True
        if hit: dump(p, ev, True); changed.append(str(p.relative_to(REPO)))
    for slug, keys in H["bio"]["fighters"].items():
        p = FD / "fighters" / f"{slug}.json"; d = load(p); b = d["bio"]; hit = False
        for k in keys:
            if b.get(k) not in (None, ""): rec["bio"].setdefault(f"{slug}.{k}", b[k]); b[k] = None; hit = True
            if b.get(k + "_held") != H["bio"]["text"]: b[k + "_held"] = H["bio"]["text"]; hit = True
        if hit: dump(p, d, True); changed.append(str(p.relative_to(REPO)))
    p = FD / "labs.json"; L = load(p); hit = False
    for sec, labels in H["labs"]["rows"].items():
        for r in L[sec]:
            if r.get("label") not in labels: continue
            if any(r.get(k) is not None for k in LAB_NUM):
                rec["labs"].setdefault(f"{sec}.{r['label']}", {k: r.get(k) for k in LAB_NUM}); hit = True
                for k in LAB_NUM:
                    if k in r: r[k] = None
            if r.get("held") != H["labs"]["text"]: r["held"] = H["labs"]["text"]; hit = True
    if hit: dump(p, L, True); changed.append(str(p.relative_to(REPO)))
    REC.parent.mkdir(parents=True, exist_ok=True); dump(REC, rec, False)
    print("holds applied:", changed or "nothing to change (already held)")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "apply": apply()
    b = problems()
    for x in b: print("HOLD FAIL:", x)
    print(f"holds: {len(b)} problems"); sys.exit(1 if b else 0)
