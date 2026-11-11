#!/usr/bin/env python3
"""Turn collector read-backs (scripts/collect/*.js) into the Markov source files + engine blocks.

  python3 scripts/inputs_to_blocks.py --dir <inputs/slug> --slug ufc334 --bp ufc_334

Reads from --dir:
  raw_ufcstats_kd.txt   lines "Name|us(8 csv)|kd(10 csv)|record|note" from ufcstats.js
  sherdog.json          {"Name": {pre_ufc fields..., career_ko_pct, career_sub_pct}} from sherdog.js
  fights_raw.json       {"A vs B": {"wc","rounds","f1","f2"}} built from oddsbreaker.js (A side = card order)
  careerctx.json        optional hand terms {"Name": {"momentum","layoff_penalty","prospect_boost"}}
Writes <slug>_ufcstats.txt, <slug>_kdstats.txt, <slug>_sherdog.txt, data_blocks.py.

SYN rule for matchups Oddsbreaker lacks (fixed 2026-11-11): UFC record, minutes, age, stance, win and
method shares from UFCStats + fight logs; SLpM/SApM = UFCStats career; TD acc/def from UFCStats;
TD per 5 = TD avg / 3; sub att per 5 = sub avg / 3; distance 75 / clinch-ground 25, control 50%,
TD faced 1.0, sub def 50%, sub faced 0.5 as fixed defaults. Label every SYN row.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import markov_blocks as mb  # noqa: E402

U = ["slpm", "str_acc", "sapm", "str_def", "td_avg", "td_acc", "td_def", "sub_avg"]
K = ["kd_per15", "kd_abs_per15", "career_dec_rate", "finish_rate", "been_finished_rate", "off_ko_loss", "age", "ufc_fights", "sub_loss_rate", "sub_att_per15"]
PRE = ["pre_bouts", "pre_wins", "pre_losses", "pre_ko_losses", "pre_sub_losses", "pre_finish_rate", "regional_5r_2plus"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--bp")
    ap.add_argument("--women", nargs="*", default=[])
    a = ap.parse_args()
    D = Path(a.dir)
    sher = json.load(open(D / "sherdog.json")) if (D / "sherdog.json").exists() else {}
    hand = json.load(open(D / "careerctx.json")) if (D / "careerctx.json").exists() else {}
    ufc, kd, ctx, notes = {}, {}, {}, {}
    for line in open(D / "raw_ufcstats_kd.txt", encoding="utf-8"):
        n, u, k, rec, note = line.rstrip("\n").split("|")[:5]
        ufc[n] = dict(zip(U, [float(x) for x in u.split(",")]))
        d = dict(zip(K, [None if x == "" else float(x) for x in k.split(",")]))
        d["off_ko_loss"], d["ufc_fights"] = bool(d["off_ko_loss"]), int(d["ufc_fights"])
        d["gender"] = "F" if n in a.women else "M"
        if d.get("finish_rate") is None:
            d.pop("finish_rate", None)          # 0-win fighter: key out, never None (regress() crash)
        s = sher.get(n)
        if s and d["ufc_fights"] <= 3:
            d["pre_ufc"] = {k2: s[k2] for k2 in PRE}
            d["sub_loss_rate"] = round((s["pre_sub_losses"] + 1) / (s["pre_losses"] + 4), 3)  # UFC losses are 0 for this group today; add them if not
        if s and "career_ko_pct" in s:
            ctx.setdefault(n, {}).update(career_ko_pct=s["career_ko_pct"], career_sub_pct=s["career_sub_pct"])
        if n in hand:
            ctx.setdefault(n, {}).update(hand[n])
        kd[n], notes[n] = d, (rec, note)
    fr = json.load(open(D / "fights_raw.json"))
    mo = {}
    if a.bp:
        bp = Path(__file__).resolve().parents[1] / "data" / f"{a.bp}_odds.json"
        for key in fr:
            A, B = key.split(" vs ")
            m = mb.market_for(bp, A, B)
            if m:
                mo[key] = m
    with open(D / f"{a.slug}_ufcstats.txt", "w") as f:
        for n, v in ufc.items():
            f.write(f'"{n}": {json.dumps(v)}  # {notes[n][0]}\n')
    with open(D / f"{a.slug}_kdstats.txt", "w") as f:
        for n, v in kd.items():
            f.write(f'"{n}": {json.dumps({k: v[k] for k in v if k != "pre_ufc"})}  # {notes[n][1]}\n')
    with open(D / f"{a.slug}_sherdog.txt", "w") as f:
        for n, v in sher.items():
            f.write(f'"{n}": {json.dumps(v)}\n')
    blocks = {"fights_raw": fr, "ufc_stats": ufc, "kd_stats": kd, "market_odds": mo, "career_context": ctx}
    (D / "data_blocks.py").write_text(mb.blocks_py(blocks), encoding="utf-8")
    print(f"{len(ufc)} fighters, {len(fr)} fights, {len(mo)} priced, {len(ctx)} with career_context")


if __name__ == "__main__":
    main()
