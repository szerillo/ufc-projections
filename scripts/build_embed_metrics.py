#!/usr/bin/env python3
"""Per-fighter metrics for one card's embeds (Block 59d), every UFC fight before the card counted (no minimum).

    python3 -I scripts/build_embed_metrics.py --event form/data/events/<slug>.json --cache .form_cache --out form/data/embed_metrics/<card>.json

Source: UFCStats CSVs only (Greco1899/scrape_ufc_stats: ufc_fight_stats, ufc_fight_results, ufc_event_details), the
same data as the site's fighter database.
Per fighter:
  target   share of significant strikes landed to head / body / legs; head, body, leg landed minus absorbed per minute
  rounds   per round 1..5: sig. strikes landed per minute and landed minus absorbed per minute, fights reaching it, and
           share of those rounds won: a round that ends in a finish goes to the finisher; any other round is scored with the
           site's decision-scoring model (labs.json scoring.coef), ties count half
  r45      rounds 4-5 vs rounds 1-3 (only fighters who have been to round 4): output kept and differential change
  ko       UFC KO/TKO wins and losses, knockdowns scored and absorbed
  power    fights where the fighter scored a knockdown or won by KO/TKO on the feet (ground-and-pound finishes with no
           knockdown do not count; finish position from the UFCStats finish detail); dropped = knocked down, or lost by
           KO/TKO anywhere (ground included; doctor and injury stoppages left out)
  power_w  recency-weighted power / dropped share (latest fight weight 1, a fight 3 back weight 0.5); last5 counts
  grap     our grappling: takedowns landed per 15, TD accuracy, TD defence, share of fight time in control (for and
           against), submission attempts per 15
  outcomes UFC wins and losses by KO/TKO, submission, decision
Division baseline (UFC fights since 2020 in the fight's weight class, 100+ fights): share of fighter-appearances with a
power event; the same share is the "got dropped" baseline.
"""
import argparse, csv, json, re, unicodedata, datetime as dt
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
fold = lambda s: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower())


def secs(t):
    m, s = str(t).split(":"); return int(m) * 60 + int(s)


GROUND = re.compile(r"From |On Ground|On The Ground|Upkick")
STAND = re.compile(r"At Distance|In Clinch|Flying|Spinning")


def standing_ko(r):
    """KO/TKO finished on the feet: UFCStats finish detail says At Distance / In Clinch / flying or spinning strike, and not a ground position."""
    d = r["DETAILS"] or ""
    return "KO/TKO" in r["METHOD"] and "Doctor" not in r["METHOD"] and bool(STAND.search(d)) and not GROUND.search(d)


def ko_loss(r):
    """Any KO/TKO finish except doctor stoppages and injuries: counts against durability wherever it happened."""
    return "KO/TKO" in r["METHOD"] and "Doctor" not in r["METHOD"] and "njury" not in (r["DETAILS"] or "")


def bucket(r):
    m = r["METHOD"]
    return "ko" if "KO/TKO" in m else "sub" if "Submission" in m else "dec" if "Decision" in m else None


SOS = json.loads((REPO / "form/data/labs.json").read_text())["sos"]   # beta100 (strikes/min per 100 Elo of opponent) and mean
HALF = 0.5 ** (1 / 3)   # per-fight decay: a fight 3 back counts half as much as the latest


def ctrl(t):
    m = re.match(r"(\d+):(\d+)", str(t or "")); return int(m.group(1)) * 60 + int(m.group(2)) if m else 0


COEF = {c["k"]: c["b"] for c in json.loads((REPO / "form/data/labs.json").read_text())["scoring"]["coef"]}


def rscore(x):
    """Round score from the site's decision-scoring model (labs.json scoring.coef): head, body, leg strikes, knockdowns,
    takedowns, control minutes, submission attempts."""
    return (COEF["head"] * of(x["HEAD"])[0] + COEF["body"] * of(x["BODY"])[0] + COEF["leg"] * of(x["LEG"])[0]
            + COEF["kd"] * int(float(x["KD"] or 0)) + COEF["td"] * of(x["TD"])[0] + COEF["ctrl"] * ctrl(x["CTRL"]) / 60
            + COEF["sub"] * int(float(x["SUB.ATT"] or 0)))


def of(x):   # "20 of 47" -> (20, 47)
    m = re.match(r"(\d+) of (\d+)", str(x or "")); return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--event", required=True); ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True); a = ap.parse_args()
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
    # division baseline (UFC fights since 2020, by weight class): share of fighter-appearances with a "power event"
    # = scored a knockdown, or won by KO/TKO on the feet. Every event has a victim, so the same share is the "got dropped" baseline.
    base = defaultdict(lambda: [0, 0, 0])
    for (e, b), r in res.items():
        d_ = date.get(e)
        if not d_ or d_ < "2020-01-01" or d_ >= cut: continue
        byr = rows.get((e, b))
        if not byr: continue
        wc = re.sub(r"^(UFC )?(Interim )?|( Title)? Bout$", "", r["WEIGHTCLASS"].strip()).strip()
        names = [x.strip() for x in b.split(" vs. ")]
        if len(names) != 2: continue
        kd = {n_: sum(int(float(v["KD"] or 0)) for (rd, fi), v in byr.items() if fi == n_) for n_ in names}
        sk = standing_ko(r) and r["OUTCOME"] in ("W/L", "L/W")
        winner = names[0] if r["OUTCOME"] == "W/L" else names[1] if r["OUTCOME"] == "L/W" else None
        kl = ko_loss(r) and winner is not None
        for n_ in names:
            base[wc][0] += 1; base[wc][1] += (kd[n_] > 0) or (sk and winner == n_)
            other = names[1] if n_ == names[0] else names[0]
            base[wc][2] += (kd[other] > 0) or (kl and winner == other)
    out = {"event": ev["slug"], "date": cut, "built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "sources": {"ufcstats": "Greco1899/scrape_ufc_stats CSVs"}, "fighters": {},
           "division_power_share": {wc: round(k / n, 4) for wc, (n, k, _) in base.items() if n >= 100},
           "division_dropped_share": {wc: round(d / n, 4) for wc, (n, _, d) in base.items() if n >= 100}}
    for f in ev["fights"]:
        for sd in ("a", "b"):
            name = f[sd]["name"]; me = canon(name)
            R = [0.0] * 6; L = [0] * 6; A = [0] * 6; N = [0] * 6        # per round: seconds, landed, absorbed, fights reaching
            WON = [0.0] * 6                                               # per round: rounds won (finish = won/lost; else scoring model)
            tgt = {"head": [0, 0], "body": [0, 0], "leg": [0, 0]}         # landed, absorbed
            kd_for = kd_ag = ko_w = ko_l = nf = 0; secs_tot = 0
            gp = dict(tdl=0, tda=0, otdl=0, otda=0, cf=0, ca=0, sa=0); hist = []; flog = []
            ff = {x_["d"]: x_ for x_ in (json.loads((REPO / "form/data/fighters" / f"{f[sd]['slug']}.json").read_text())["fights"] if f[sd].get("slug") and (REPO / "form/data/fighters" / f"{f[sd]['slug']}.json").exists() else [])}
            pw = dr = 0; oc = {"w": {"ko": 0, "sub": 0, "dec": 0}, "l": {"ko": 0, "sub": 0, "dec": 0}}
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
                decided = r_["OUTCOME"] in ("W/L", "L/W")
                if "KO/TKO" in r_["METHOD"] and decided:
                    if win: ko_w += 1
                    else: ko_l += 1
                if decided and bucket(r_): oc["w" if win else "l"][bucket(r_)] += 1
                kdf = sum(int(float(v["KD"] or 0)) for (rd, fi), v in byr.items() if fi == mi)
                kda = sum(int(float(v["KD"] or 0)) for (rd, fi), v in byr.items() if fi == op)
                sk = decided and standing_ko(r_)
                kl = decided and not win and ko_loss(r_)
                pw += (kdf > 0) or (sk and win); dr += (kda > 0) or kl
                hist.append((d_, int((kdf > 0) or (sk and win)), int((kda > 0) or kl)))
                fx = ff.get(d_) or {}
                ent = {"d": d_, "o": op, "es": fx.get("es"), "n": fx.get("n"), "r": "W" if decided and win else "L" if decided else "D",
                       "oe": fx.get("oe"), "secs": 0, "sl": 0, "sa": 0, "cf": 0, "ca": 0, "tdl": 0, "tdo": 0, "rw": []}
                flog.append(ent)
                for rd in range(1, last_r + 1):
                    if rd > 5: break
                    x, y = byr.get((rd, mi)), byr.get((rd, op))
                    if not x or not y: continue
                    s_ = last_s if rd == last_r else 300
                    if rd == last_r and decided and "Decision" not in r_["METHOD"]: rw_ = 1.0 if win else 0.0
                    else:
                        sc = rscore(x) - rscore(y); rw_ = 1.0 if sc > 0 else 0.0 if sc < 0 else 0.5
                    WON[rd] += rw_
                    ent["rw"].append([rd, rw_, of(x["SIG.STR."])[0] - of(y["SIG.STR."])[0]])
                    ent["secs"] += s_; ent["sl"] += of(x["SIG.STR."])[0]; ent["sa"] += of(y["SIG.STR."])[0]
                    ent["cf"] += ctrl(x["CTRL"]); ent["ca"] += ctrl(y["CTRL"]); ent["tdl"] += of(x["TD"])[0]; ent["tdo"] += of(y["TD"])[0]
                    R[rd] += s_; N[rd] += 1; L[rd] += of(x["SIG.STR."])[0]; A[rd] += of(y["SIG.STR."])[0]; secs_tot += s_
                    kd_for += int(float(x["KD"] or 0)); kd_ag += int(float(y["KD"] or 0))
                    a_, b_ = of(x["TD"]), of(y["TD"])
                    gp["tdl"] += a_[0]; gp["tda"] += a_[1]; gp["otdl"] += b_[0]; gp["otda"] += b_[1]
                    gp["cf"] += ctrl(x["CTRL"]); gp["ca"] += ctrl(y["CTRL"]); gp["sa"] += int(float(x["SUB.ATT"] or 0))
                    for k_, col in (("head", "HEAD"), ("body", "BODY"), ("leg", "LEG")):
                        tgt[k_][0] += of(x[col])[0]; tgt[k_][1] += of(y[col])[0]
            mins = secs_tot / 60
            land = sum(v[0] for v in tgt.values())
            rec = {"name": name, "ufc_fights": nf, "minutes": round(mins, 1),
                   "target": {k_: (round(v[0] / land, 4) if land else None) for k_, v in tgt.items()},
                   "target_diff": {k_: (round((v[0] - v[1]) / mins, 3) if mins else None) for k_, v in tgt.items()},
                   "rounds": [{"r": rd, "fights": N[rd], "landed_pm": round(L[rd] / (R[rd] / 60), 3) if R[rd] else None,
                               "diff_pm": round((L[rd] - A[rd]) / (R[rd] / 60), 3) if R[rd] else None,
                               "won": round(WON[rd] / N[rd], 4) if N[rd] else None} for rd in range(1, 6)],
                   "ufc_ko_wins": ko_w, "ufc_ko_losses": ko_l, "power_fights": pw, "dropped_fights": dr, "outcomes": oc, "kd_for": kd_for, "kd_against": kd_ag}
            # recency weighting: most recent UFC fight counts 1, each fight further back counts less (half weight 3 fights back)
            hist.sort(reverse=True); wts = [HALF ** i for i in range(len(hist))]; ws = sum(wts)
            rec["power_w"] = round(sum(w * h[1] for w, h in zip(wts, hist)) / ws, 4) if ws else None
            rec["dropped_w"] = round(sum(w * h[2] for w, h in zip(wts, hist)) / ws, 4) if ws else None
            rec["last5"] = {"fights": len(hist[:5]), "power": sum(h[1] for h in hist[:5]), "dropped": sum(h[2] for h in hist[:5])}
            rec["grap"] = {"td15": round(gp["tdl"] / mins * 15, 3) if mins else None, "td_acc": round(gp["tdl"] / gp["tda"], 4) if gp["tda"] else None,
                           "tdd": round(1 - gp["otdl"] / gp["otda"], 4) if gp["otda"] else None,
                           "ctrl": round(gp["cf"] / secs_tot, 4) if secs_tot else None, "ctrl_ag": round(gp["ca"] / secs_tot, 4) if secs_tot else None,
                           "sub15": round(gp["sa"] / mins * 15, 3) if mins else None}
            # per-fight log (newest first) for the dot strips and the round drill-down
            flog.sort(key=lambda e_: e_["d"], reverse=True); rec["fights"] = flog
            # consistency: fights they out-landed the opponent in; fights they won the grappling in (more control time, or more
            # takedowns when control is level), counting only fights with 60+ s of control or a takedown on either side
            rec["out_landed"] = {"k": sum(1 for e_ in flog if e_["sl"] > e_["sa"]), "n": sum(1 for e_ in flog if e_["secs"])}
            gf = [e_ for e_ in flog if e_["cf"] + e_["ca"] >= 60 or e_["tdl"] + e_["tdo"] > 0]
            rec["grap_won"] = {"k": sum(1 for e_ in gf if (e_["cf"] - e_["ca"] > 0) or (e_["cf"] == e_["ca"] and e_["tdl"] > e_["tdo"])), "n": len(gf)}
            # schedule-adjusted strike differential, as Labs (labs.json sos): sd - beta * (time-weighted opponent Elo - mean),
            # opponent Elo at fight time from the fighter file, fights of 3+ minutes only
            ow = [(e_["oe"], e_["secs"]) for e_ in flog if e_["oe"] and e_["secs"] >= 180]
            sdv = sum(e_["sl"] - e_["sa"] for e_ in flog) / (secs_tot / 60) if secs_tot else None
            if ow and sdv is not None:
                moe = sum(a_ * b_ for a_, b_ in ow) / sum(b_ for _, b_ in ow)
                rec["sos"] = {"sd": round(sdv, 3), "opp_elo": round(moe, 1), "adj_sd": round(sdv - SOS["beta100"] / 100 * (moe - SOS["mean"]), 3)}
            e13 = sum(R[1:4]) / 60; e45 = sum(R[4:6]) / 60
            if e45 > 0 and e13 > 0:
                rec["r45"] = {"fights": N[4], "landed_pm_13": round(sum(L[1:4]) / e13, 3), "landed_pm_45": round(sum(L[4:6]) / e45, 3),
                              "diff_pm_13": round((sum(L[1:4]) - sum(A[1:4])) / e13, 3), "diff_pm_45": round((sum(L[4:6]) - sum(A[4:6])) / e45, 3)}
            out["fighters"][name] = rec
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True))
    print(a.out, len(out["fighters"]), "fighters;", sum(1 for x in out["fighters"].values() if x["ufc_fights"]), "with UFC rows")


if __name__ == "__main__":
    main()
