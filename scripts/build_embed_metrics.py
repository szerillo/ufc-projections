#!/usr/bin/env python3
"""Per-fighter metrics for one card's embeds (Block 59d), every UFC fight before the card counted (no minimum).

    python3 -I scripts/build_embed_metrics.py --event form/data/events/<slug>.json --cache .form_cache \
        --career data/embeds/<card>_career.json --out form/data/embed_metrics/<card>.json

Sources: UFCStats CSVs (Greco1899/scrape_ufc_stats: ufc_fight_stats, ufc_fight_results, ufc_event_details) for the UFC
rows, and the Sherdog career pull (data/embeds/<card>_career.json) for whole-career KO wins and losses.
Per fighter:
  target   share of significant strikes landed to head / body / legs; head, body, leg landed minus absorbed per minute
  rounds   per round 1..5: sig. strikes landed per minute and landed minus absorbed per minute, and fights reaching it
  r45      rounds 4-5 vs rounds 1-3 (only fighters who have been to round 4): output kept and differential change
  ko       UFC KO/TKO wins and losses, knockdowns scored and absorbed; career KO wins and losses from Sherdog
Division baseline (UFC fights since 2020 in the fight's weight class): KO/TKO finishes as a share of fight appearances
for the winner side (= half the KO finish rate), which is what "KO'd opponents in X% of fights" compares to.
"""
import argparse, csv, json, re, unicodedata, datetime as dt
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
fold = lambda s: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower())


def secs(t):
    m, s = str(t).split(":"); return int(m) * 60 + int(s)


def of(x):   # "20 of 47" -> (20, 47)
    m = re.match(r"(\d+) of (\d+)", str(x or "")); return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--event", required=True); ap.add_argument("--cache", required=True)
    ap.add_argument("--career", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
    ev = json.loads(Path(a.event).read_text()); D = Path(a.cache); cut = ev["date"]
    alias = {fold(k): v for k, v in json.loads((REPO / "form/data/name_aliases.json").read_text()).items() if not k.startswith("_")}
    canon = lambda s: fold(alias.get(fold(s), s))
    date = {r["EVENT"].strip(): dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").date().isoformat() for r in csv.DictReader(open(D / "ufc_event_details.csv", encoding="utf-8"))}
    res = {}
    for r in csv.DictReader(open(D / "ufc_fight_results.csv", encoding="utf-8")):
        res[(r["EVENT"].strip(), r["BOUT"].strip())] = r
    rows = defaultdict(dict)   # (event, bout) -> {(round, fighter): row}
    for r in csv.DictReader(open(D / "ufc_fight_stats.csv", encoding="utf-8")):
        m = re.match(r"Round (\d+)", r["ROUND"] or "")
        if m: rows[(r["EVENT"].strip(), r["BOUT"].strip())][(int(m.group(1)), r["FIGHTER"].strip())] = r
    # division baseline: KO/TKO finishes since 2020, by weight class
    base = defaultdict(lambda: [0, 0])
    for (e, b), r in res.items():
        d_ = date.get(e)
        if not d_ or d_ < "2020-01-01" or d_ >= cut: continue
        wc = re.sub(r"^(UFC )?(Interim )?|( Title)? Bout$", "", r["WEIGHTCLASS"].strip()).strip()
        base[wc][0] += 1; base[wc][1] += "KO/TKO" in r["METHOD"]
    out = {"event": ev["slug"], "date": cut, "built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "sources": {"ufcstats": "Greco1899/scrape_ufc_stats CSVs", "career": a.career}, "fighters": {},
           "division_ko_share": {wc: round(k / n / 2, 4) for wc, (n, k) in base.items() if n >= 50}}
    career = json.loads(Path(a.career).read_text())["fighters"]
    for f in ev["fights"]:
        for sd in ("a", "b"):
            name = f[sd]["name"]; me = canon(name)
            R = [0.0] * 6; L = [0] * 6; A = [0] * 6; N = [0] * 6        # per round: seconds, landed, absorbed, fights reaching
            tgt = {"head": [0, 0], "body": [0, 0], "leg": [0, 0]}         # landed, absorbed
            kd_for = kd_ag = ko_w = ko_l = nf = 0; secs_tot = 0
            for (e, b), byr in rows.items():
                d_ = date.get(e)
                if not d_ or d_ >= cut: continue
                fighters = {fi for (_, fi) in byr}
                mine = [fi for fi in fighters if canon(fi) == me]
                if len(mine) != 1: continue
                mi = mine[0]; op = next((fi for fi in fighters if fi != mi), None)
                r_ = res.get((e, b))
                if not r_ or not op: continue
                nf += 1; last_r = int(r_["ROUND"]); last_s = secs(r_["TIME"])
                win = (r_["OUTCOME"].split("/")[0] == "W") == (b.split(" vs. ")[0].strip() == mi)
                if "KO/TKO" in r_["METHOD"] and r_["OUTCOME"] in ("W/L", "L/W"):
                    if win: ko_w += 1
                    else: ko_l += 1
                for rd in range(1, last_r + 1):
                    if rd > 5: break
                    x, y = byr.get((rd, mi)), byr.get((rd, op))
                    if not x or not y: continue
                    s_ = last_s if rd == last_r else 300
                    R[rd] += s_; N[rd] += 1; L[rd] += of(x["SIG.STR."])[0]; A[rd] += of(y["SIG.STR."])[0]; secs_tot += s_
                    kd_for += int(float(x["KD"] or 0)); kd_ag += int(float(y["KD"] or 0))
                    for k_, col in (("head", "HEAD"), ("body", "BODY"), ("leg", "LEG")):
                        tgt[k_][0] += of(x[col])[0]; tgt[k_][1] += of(y[col])[0]
            mins = secs_tot / 60
            land = sum(v[0] for v in tgt.values())
            rec = {"name": name, "ufc_fights": nf, "minutes": round(mins, 1),
                   "target": {k_: (round(v[0] / land, 4) if land else None) for k_, v in tgt.items()},
                   "target_diff": {k_: (round((v[0] - v[1]) / mins, 3) if mins else None) for k_, v in tgt.items()},
                   "rounds": [{"r": rd, "fights": N[rd], "landed_pm": round(L[rd] / (R[rd] / 60), 3) if R[rd] else None,
                               "diff_pm": round((L[rd] - A[rd]) / (R[rd] / 60), 3) if R[rd] else None} for rd in range(1, 6)],
                   "ufc_ko_wins": ko_w, "ufc_ko_losses": ko_l, "kd_for": kd_for, "kd_against": kd_ag}
            e13 = sum(R[1:4]) / 60; e45 = sum(R[4:6]) / 60
            if e45 > 0 and e13 > 0:
                rec["r45"] = {"fights": N[4], "landed_pm_13": round(sum(L[1:4]) / e13, 3), "landed_pm_45": round(sum(L[4:6]) / e45, 3),
                              "diff_pm_13": round((sum(L[1:4]) - sum(A[1:4])) / e13, 3), "diff_pm_45": round((sum(L[4:6]) - sum(A[4:6])) / e45, 3)}
            c = career.get(name)
            if c and not c.get("err"):
                rec["career"] = {k_: c[k_] for k_ in ("fights", "wins", "losses", "ko_wins", "ko_losses", "sherdog") if k_ in c}
            out["fighters"][name] = rec
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True))
    print(a.out, len(out["fighters"]), "fighters;", sum(1 for x in out["fighters"].values() if x["ufc_fights"]), "with UFC rows")


if __name__ == "__main__":
    main()
