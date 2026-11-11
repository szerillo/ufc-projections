#!/usr/bin/env python3
"""Build the five V4.1b engine data blocks for a card, run the engine, and replay-check.

Sources (in order of authority):
  * the site's stored fighter data, form/data/fighters/*.json (UFCStats per-fight totals)
      -> ufc_stats, kd_stats (KD recipe: prior UFC fights only, per 15 min), age, gender
  * markov/inputs/<card>/oddsbreaker.txt   Oddsbreaker positional rows ("A (Name): ~string")
      -> fights_raw. Pulled through Chrome or pasted once; the site cannot rebuild every
         Oddsbreaker field (SLpM variant, TD/5, positional %), so this file is required.
  * markov/inputs/<card>/sherdog.json      {"Name": {pre_ufc dict}}  optional
  * markov/inputs/<card>/context.json      {"Name": {momentum, career_ko_pct, ...}}  optional
  * markov/inputs/<card>/overrides.json    {"ufc_stats"|"kd_stats": {"Name": {...}}}  optional,
      for DWCS bouts the site's UFCStats source does not carry
  * data/<bp_slug>_odds.json               consensus ML -> market_odds (output comparison only;
                                            the engine is market-blind)

THIN SAMPLE: a fighter with 3 or fewer UFC fights on file and no sherdog.json entry is
listed in the run report and badged on the site until the Sherdog data is entered.

The engine itself is NOT in this public repo. Point ENGINE_PATH at a local copy of
ufc_v4_engine.py (V4.1b template). Engine logic is never edited here: only the five
data dict literals are replaced.

  python3 scripts/markov_blocks.py build  --card ufc-334 --event form/data/events/<slug>.json --bp ufc_334 --date 2026-11-14
  python3 scripts/markov_blocks.py replay --saved path/to/waldo_data_block.py --date 2026-11-07
"""
import argparse, datetime as dt, json, os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from card_overrides import same  # noqa: E402

FIGHTERS = REPO / "form" / "data" / "fighters"
BLOCKS = ("fights_raw", "ufc_stats", "kd_stats", "market_odds", "career_context")


def slug(n):
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")


def fighter_file(name):
    p = FIGHTERS / f"{slug(name)}.json"
    return json.load(open(p)) if p.exists() else None


def prior(d, date):
    return [f for f in (d or {}).get("fights", []) if f["d"] < date]


def r2(x, n=2):
    return round(x, n)


def ufc_stats_for(name, date):
    d = fighter_file(name)
    F = [f for f in prior(d, date) if "s" in f]
    mins = sum(f["secs"] or 0 for f in F) / 60
    if not F or mins <= 0:
        return None
    t = [sum(f["s"][i] for f in F) for i in range(14)]
    return {"slpm": r2(t[0] / mins), "str_acc": r2(t[0] / t[1]) if t[1] else 0.0, "sapm": r2(t[2] / mins),
            "str_def": r2(1 - t[2] / t[3]) if t[3] else 0.0, "td_avg": r2(t[6] / mins * 15), "td_acc": r2(t[6] / t[7]) if t[7] else 0.0,
            "td_def": r2(1 - t[8] / t[9]) if t[9] else 0.0, "sub_avg": r2(t[12] / mins * 15, 1)}


def kd_stats_for(name, date, wc):
    d = fighter_file(name)
    F = prior(d, date)
    mins = sum(f["secs"] or 0 for f in F) / 60
    S = [f["s"] for f in F if "s" in f]
    t = [sum(x[i] for x in S) for i in range(14)] if S else [0] * 14
    W = [f for f in F if f["r"] == "W"]
    L = [f for f in F if f["r"] == "L"]
    fin = lambda f: "KO" in f["m"] or "Sub" in f["m"]
    dob = ((d or {}).get("bio") or {}).get("dob")
    age = r2((dt.date.fromisoformat(date) - dt.date.fromisoformat(dob)).days / 365.25, 1) if dob else None
    out = {"kd_per15": r2(t[4] / mins * 15) if mins else 0.0, "kd_abs_per15": r2(t[5] / mins * 15) if mins else 0.0,
           "career_dec_rate": r2(sum("Decision" in f["m"] for f in F) / len(F), 3) if F else 0.0,
           "finish_rate": r2(sum(fin(f) for f in W) / len(W), 3) if W else None,
           "been_finished_rate": r2(sum(fin(f) for f in L) / len(L), 3) if L else 0.0,
           "off_ko_loss": bool(F and F[0]["r"] == "L" and "KO" in F[0]["m"]),
           "age": age, "gender": "F" if (wc or "").startswith("Women") else "M", "ufc_fights": len(F),
           "sub_loss_rate": r2(sum("Sub" in f["m"] for f in L) / len(F), 3) if F else 0.0,
           "sub_att_per15": r2(t[12] / mins * 15, 1) if mins else 0.0}
    if out["finish_rate"] is None:
        del out["finish_rate"]  # 0-win fighter: leave the key out (finish_rate None crashes regress())
    return out


def parse_oddsbreaker(path):
    """'=== Fight N: A vs B (...) ===' then 'A (..): string' / 'B (..): string'."""
    out, cur = {}, None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"=== Fight \d+: (.+?) vs (.+?) \(", line)
        if m:
            cur = (m.group(1).strip(), m.group(2).strip())
            out[cur] = {}
            continue
        m = re.match(r"([AB]) \([^)]*\):\s*(\S.*)$", line.strip())
        if m and cur:
            out[cur]["f1" if m.group(1) == "A" else "f2"] = m.group(2).strip()
    return out


def market_for(bp_file, a, b):
    if not bp_file or not Path(bp_file).exists():
        return None
    for f in json.load(open(bp_file)).get("fights", []):
        an, bn = f["fighter_a"]["name"], f["fighter_b"]["name"]
        if not ((same(an, a) and same(bn, b)) or (same(an, b) and same(bn, a))):
            continue
        px = {}
        for sel in (f.get("markets") or {}).get("moneyline", []):
            c = ((sel.get("books") or {}).get("consensus") or {}).get("cost")
            px[sel.get("label")] = c
        pa = next((v for k, v in px.items() if same(k or "", a)), None)
        pb = next((v for k, v in px.items() if same(k or "", b)), None)
        if pa is not None and pb is not None:
            return {"f1": pa, "f2": pb}
    return None


def build(card, event_doc, bp_file, date, inputs_dir):
    ev = json.load(open(event_doc))
    inp = Path(inputs_dir)
    ob = parse_oddsbreaker(inp / "oddsbreaker.txt") if (inp / "oddsbreaker.txt").exists() else {}
    sher = json.load(open(inp / "sherdog.json")) if (inp / "sherdog.json").exists() else {}
    ctx = json.load(open(inp / "context.json")) if (inp / "context.json").exists() else {}
    ovr = json.load(open(inp / "overrides.json")) if (inp / "overrides.json").exists() else {}
    B = {k: {} for k in BLOCKS}
    report = {"missing_oddsbreaker": [], "thin_sample": [], "no_site_data": [], "no_market": []}
    for f in ev["fights"]:
        a, b = f["a"]["name"], f["b"]["name"]
        key = f"{a} vs {b}"
        rounds = f.get("sched") or (5 if f.get("title") else 3)
        row = next((v for (x, y), v in ob.items() if same(x, a) and same(y, b)), None)
        if row is None:
            row = next(({"f1": v.get("f2"), "f2": v.get("f1")} for (x, y), v in ob.items() if same(x, b) and same(y, a)), None)
        if row and row.get("f1") and row.get("f2"):
            B["fights_raw"][key] = {"wc": f["wc"], "rounds": rounds, "f1": row["f1"], "f2": row["f2"]}
        else:
            report["missing_oddsbreaker"].append(key)
        for nm in (a, b):
            us = ufc_stats_for(nm, date)
            if us:
                B["ufc_stats"][nm] = us
            else:
                report["no_site_data"].append(nm)
            kd = kd_stats_for(nm, date, f["wc"])
            pre = next((v for k, v in sher.items() if same(k, nm)), None)
            if pre:
                kd["pre_ufc"] = pre
            elif kd["ufc_fights"] <= 3:
                report["thin_sample"].append(nm)
            B["kd_stats"][nm] = kd
            for blk in ("ufc_stats", "kd_stats"):
                o = next((v for k, v in (ovr.get(blk) or {}).items() if same(k, nm)), None)
                if o:
                    B[blk].setdefault(nm, {}).update(o)
            c = next((v for k, v in ctx.items() if same(k, nm)), None)
            if c:
                B["career_context"][nm] = c
        mo = market_for(bp_file, a, b)
        if mo:
            B["market_odds"][key] = mo
        else:
            report["no_market"].append(key)
    return B, report


def blocks_py(B):
    return "\n".join(f"{k} = {json.dumps(B[k], indent=4, ensure_ascii=False).replace('true', 'True').replace('false', 'False').replace('null', 'None')}\n"
                     for k in BLOCKS)


def splice(engine_src, B):
    """Replace each top-level `name = {...}` literal in the engine template; logic untouched."""
    src = engine_src
    for k in BLOCKS:
        m = re.search(rf"^{k} = \{{.*?^\}}\n", src, re.S | re.M)
        if not m:
            raise SystemExit(f"engine template has no top-level {k} block")
        lit = json.dumps(B[k], indent=4, ensure_ascii=False).replace("true", "True").replace("false", "False").replace("null", "None")
        src = src[:m.start()] + f"{k} = {lit}\n" + src[m.end():]
    return src


def load_saved(path):
    src = open(path, encoding="utf-8").read()
    ns = {}
    for k in BLOCKS:
        m = re.search(rf"^{k} = \{{.*?^\}}\n", src, re.S | re.M)
        if m:
            exec(m.group(0), ns)
    return {k: ns.get(k, {}) for k in BLOCKS}


def compare(built, saved):
    """Field-level diff of built vs saved blocks. Exact equality is the switch-over gate."""
    rep = {}
    for k in BLOCKS:
        tot = same_n = 0
        diffs = []
        for name, sv in saved[k].items():
            bv = next((v for n2, v in built[k].items() if same(n2.split(" vs ")[0], name.split(" vs ")[0]) and
                       (" vs " not in name or same(n2.split(" vs ")[-1], name.split(" vs ")[-1]))), None)
            fields = sv.items() if isinstance(sv, dict) else [("value", sv)]
            for fk, fv in fields:
                tot += 1
                gv = (bv or {}).get(fk) if isinstance(bv, dict) else None
                ok = gv == fv or (isinstance(fv, float) and isinstance(gv, (int, float)) and abs(gv - fv) < 1e-9)
                same_n += ok
                if not ok:
                    diffs.append((name, fk, fv, gv))
        rep[k] = {"fields": tot, "exact": same_n, "diffs": diffs}
    return rep


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--card", required=True)
    b.add_argument("--event", required=True)
    b.add_argument("--bp")
    b.add_argument("--date", required=True)
    b.add_argument("--out", default=str(REPO / "markov" / "runs"))
    b.add_argument("--run", action="store_true", help="splice into ENGINE_PATH and run it")
    r = sub.add_parser("replay")
    r.add_argument("--saved", required=True, help="hand-built data block or sim .py of a past card")
    r.add_argument("--event", required=True)
    r.add_argument("--date", required=True)
    r.add_argument("--inputs", required=True)
    r.add_argument("--bp")
    r.add_argument("--json-out")
    a = ap.parse_args()

    if a.cmd == "build":
        inputs = REPO / "markov" / "inputs" / a.card
        bp = REPO / "data" / f"{a.bp}_odds.json" if a.bp else None
        B, report = build(a.card, a.event, bp, a.date, inputs)
        out = Path(a.out) / a.card
        out.mkdir(parents=True, exist_ok=True)
        (out / "data_blocks.py").write_text(blocks_py(B), encoding="utf-8")
        (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(json.dumps(report, indent=1))
        if a.run:
            eng = os.environ.get("ENGINE_PATH")
            if not eng or not Path(eng).exists():
                raise SystemExit("ENGINE_PATH not set: the engine is kept out of this public repo")
            if report["missing_oddsbreaker"]:
                raise SystemExit("Oddsbreaker rows missing; engine not run: " + "; ".join(report["missing_oddsbreaker"]))
            sim = out / "sim_v41b.py"
            sim.write_text(splice(Path(eng).read_text(encoding="utf-8"), B), encoding="utf-8")
            env = dict(os.environ, PYTHONHASHSEED=os.environ.get("PYTHONHASHSEED", "0"))
            with open(out / "sim_v41b_output.txt", "w") as fh:
                subprocess.run([sys.executable, str(sim)], stdout=fh, check=True, env=env)
            print("engine output:", out / "sim_v41b_output.txt")
    else:
        saved = load_saved(a.saved)
        bp = REPO / "data" / f"{a.bp}_odds.json" if a.bp else None
        B, report = build("replay", a.event, bp, a.date, a.inputs)
        rep = compare(B, saved)
        gate = all(v["exact"] == v["fields"] for k, v in rep.items() if k != "market_odds")
        for k, v in rep.items():
            print(f"{k:15s} {v['exact']}/{v['fields']} exact")
        print("GATE (all blocks but market_odds exact):", "PASS" if gate else "FAIL")
        if a.json_out:
            Path(a.json_out).write_text(json.dumps({"gate": gate, "blocks": rep, "report": report}, indent=1, default=str))
        sys.exit(0 if gate else 1)


if __name__ == "__main__":
    main()
