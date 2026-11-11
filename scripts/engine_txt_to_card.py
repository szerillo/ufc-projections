#!/usr/bin/env python3
"""Raw V4.1b engine output (sim_v41b_output.txt) -> Duration Model card JSON.

Builds a FULL card (finish split, SS mean/median, TD ladder, P(KD), dec share, round
distribution, spreads) straight from the engine's printed blocks, so an automated run
can publish without a hand-written MD. Optional inputs:
  --market  JSON {"A vs B": {"f1": ml, "f2": ml}}           market ML (sides fav/dog)
  --gtd     JSON {"A vs B": de-vigged GTD %}                 market GTD from the props pull
  --blocks  data_blocks.py from markov_blocks.py             tape (ufc_stats) + THIN flags

Flags are NOT generated. The rule is "8+ points AND a fighter-specific mechanism"; a
mechanism is a human line, so 8+ point gaps are listed under "flag_candidates" (not
rendered on the site) for review, never as flags.
"""
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

NUM = r"(-?[\d.]+)"


def implied(ml):
    ml = float(ml)
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def parse(txt):
    fights = []
    blocks = re.split(r"\n=+\n(?=  \S.* vs .*\n)", txt)
    for b in blocks:
        m = re.match(r"  (.+?) vs (.+?)\n  (.+?) \| (\d)R \|", b)
        if not m or "ARCHIVE\t" not in b:
            continue
        A, B, wc, rounds = m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), int(m.group(4))
        g = lambda pat, s=b: re.search(pat, s)
        f = {"A": A, "B": B, "wc": wc, "rounds": rounds}
        f["thin"] = [n.strip() for n in (g(r"THIN SAMPLE: (.+?) \(") .group(1).split(",") if g(r"THIN SAMPLE: (.+?) \(") else [])]
        f["p_dec"] = float(g(r"P\(DECISION\): " + NUM).group(1))
        f["rounds_pct"] = [float(x) for x in re.findall(r"R\d: " + NUM + "%", g(r"Finish by round:(.+)").group(1))]
        for side, name in (("a", A), ("b", B)):
            mm = g(r"P\(" + re.escape(name) + r" finishes\): " + NUM + r"%\s+\(KO " + NUM + r"% / Sub " + NUM + "%")
            f[side + "_fin"], f[side + "_ko"], f[side + "_sub"] = (float(mm.group(i)) for i in (1, 2, 3))
            ss = g(re.escape(name) + r": mean " + NUM + r" / median " + NUM)
            f[side + "_ss"] = (float(ss.group(1)), float(ss.group(2)))
            td = g(r"TAKEDOWNS " + re.escape(name) + r": proj " + NUM + r"\s+P\(>=1\) (\d+)%\s+P\(>=2\) (\d+)%\s+P\(>=3\) (\d+)%")
            f[side + "_td"] = (float(td.group(1)), int(td.group(2)), int(td.group(3)), int(td.group(4)))
        kd = g(r"P\(SCORES A KD\): .+? (\d+)%\s+\|\s+.+? (\d+)%")
        f["a_kd"], f["b_kd"] = int(kd.group(1)), int(kd.group(2))
        f["exp_min"] = float(g(r"EXPECTED MINUTES: " + NUM).group(1))
        sp = g(r"P\(fav -3\.5\) = " + NUM)
        sp9 = g(r"P\(fav -9\.5, \dR\) = P\(fav finishes\) = " + NUM)
        f["spread"] = {"fav_minus35": float(sp.group(1)) if sp else None, "fav_minus95": float(sp9.group(1)) if sp9 else None, "convention": "per-card"}
        mk = g(r"market \(de-vig\): .+? " + NUM + r"% / .+? " + NUM + "%")
        f["mkt_a"] = float(mk.group(1)) if mk else None
        ar = g(r"ARCHIVE\t.+?\t" + NUM + r"\t" + NUM)
        f["a_shrunk"], f["a_raw"] = float(ar.group(1)), float(ar.group(2))
        f["archive_line"] = g(r"ARCHIVE\t(.+)").group(1).strip()
        fights.append(f)
    return fights


def card(fights, slug, title, date, market=None, gtd=None, ufc_stats=None):
    out = {"slug": slug, "title": title, "date": date, "venue": None, "engine_version": "V4.1b",
           "notes": ["Built automatically from the raw engine output (markov.yml). Flags need a human mechanism line; see flag_candidates."],
           "archive_tsv": "\n".join(f["archive_line"] for f in fights), "fights": [],
           "duration_flags": [], "ml_flags": [], "prop_notes": [], "vetoes": [], "flag_candidates": []}
    for i, f in enumerate(fights, 1):
        key = f"{f['A']} vs {f['B']}"
        mo = (market or {}).get(key)
        a_sh, a_raw = f["a_shrunk"], f["a_raw"]
        sides = (None, None)
        if mo:
            pa = implied(mo["f1"]) / (implied(mo["f1"]) + implied(mo["f2"]))
            sides = ("fav", "dog") if pa >= 0.5 else ("dog", "fav")
            if float(mo["f1"]) < 0 and float(mo["f2"]) < 0:
                sides = ("pickem", "pickem")  # both sides minus money (site convention)
        fighters = []
        for s, name, win_sh, win_raw, odds, side in (("a", f["A"], a_sh, a_raw, mo and mo["f1"], sides[0]),
                                                      ("b", f["B"], round(100 - a_sh, 1), round(100 - a_raw, 1), mo and mo["f2"], sides[1])):
            fin = f[s + "_fin"]
            x = {"name": name, "side": side, "market_odds": odds, "model_win_shrunk": win_sh, "model_win_raw": win_raw,
                 "dec_share_of_wins": round(max(0.0, win_sh - fin) / win_sh * 100) if win_sh else None,
                 "finish_pct": fin, "finish_ko": f[s + "_ko"], "finish_sub": f[s + "_sub"],
                 "ss_mean": f[s + "_ss"][0], "ss_median": f[s + "_ss"][1],
                 "td_proj": f[s + "_td"][0], "td_p1": f[s + "_td"][1], "td_p2": f[s + "_td"][2], "td_p3": f[s + "_td"][3],
                 "p_kd": f[s + "_kd"], "p_kd_clamped": f[s + "_kd"] >= 40, "badges": ["THIN SAMPLE"] if name in f["thin"] else []}
            us = (ufc_stats or {}).get(name)
            if us:
                x["tape"] = {k: us.get(k) for k in ("slpm", "sapm", "str_acc", "str_def", "td_avg", "td_acc", "td_def", "sub_avg")}
            fighters.append(x)
        mg = (gtd or {}).get(key)
        dur = {"p_dec": f["p_dec"], "market_gtd_devig": mg, "gap": round(f["p_dec"] - mg, 1) if mg is not None else None,
               "round_dist": f["rounds_pct"], "exp_minutes": f["exp_min"]}
        out["fights"].append({"order": i, "bout": key, "weight_class": f["wc"], "rounds": f["rounds"], "is_main_event": i == 1,
                              "duration": dur, "spread": f["spread"], "result": None, "fighters": fighters})
        if mg is not None and abs(f["p_dec"] - mg) >= 8:
            out["flag_candidates"].append({"fight_order": i, "type": "duration", "gap": round(f["p_dec"] - mg, 1)})
        if f["mkt_a"] is not None and abs(a_sh - f["mkt_a"]) >= 8:
            out["flag_candidates"].append({"fight_order": i, "type": "ml", "gap_a": round(a_sh - f["mkt_a"], 1)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txt")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--market")
    ap.add_argument("--gtd")
    ap.add_argument("--blocks")
    ap.add_argument("--out")
    a = ap.parse_args()
    us = None
    if a.blocks:
        import markov_blocks as mb
        us = mb.load_saved(a.blocks)["ufc_stats"]
    c = card(parse(Path(a.txt).read_text(encoding="utf-8")), a.slug, a.title, a.date,
             json.load(open(a.market)) if a.market else None, json.load(open(a.gtd)) if a.gtd else None, us)
    s = json.dumps(c, indent=1, ensure_ascii=False)
    Path(a.out).write_text(s, encoding="utf-8") if a.out else print(s)
    print(len(c["fights"]), "fights;", len(c["flag_candidates"]), "flag candidates", file=sys.stderr)


if __name__ == "__main__":
    main()
