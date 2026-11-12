#!/usr/bin/env python3
"""Independent recompute of form/data/embed_metrics/<card>.json from the raw UFCStats CSVs (Block 59i, Kirk check 4).

    python3 -I scripts/verify_embed_metrics.py --event form/data/events/<slug>.json --cache .form_cache --metrics form/data/embed_metrics/<card>.json

Written separately from build_embed_metrics.py, from the definitions in the embed keys, so a bug in the metrics builder
(the file verify_fight_embeds.py trusts) shows up here. Works fight first: one record per UFC bout per fighter, then sums.
Exit 1 on any mismatch. Fields checked: every per-fighter number an embed displays, plus the division baselines.
"""
import argparse, csv, json, re, sys, unicodedata, datetime as dt
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOL = 0.0006


def key(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in s if ch.isalpha())


def landed(cell):
    m = re.match(r"\s*(\d+)\s+of\s+(\d+)", cell or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def clock(cell):
    m = re.match(r"\s*(\d+):(\d\d)", cell or "")
    return 60 * int(m.group(1)) + int(m.group(2)) if m else 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--event"); ap.add_argument("--cache"); ap.add_argument("--metrics"); a = ap.parse_args()
    ev = json.load(open(a.event)); M = json.load(open(a.metrics)); D = Path(a.cache); cut = ev["date"]
    alias = {key(k): v for k, v in json.load(open(REPO / "form/data/name_aliases.json")).items() if not k.startswith("_")}
    ck = lambda s: key(alias.get(key(s), s))
    labs = json.load(open(REPO / "form/data/labs.json")); W = {c["k"]: c["b"] for c in labs["scoring"]["coef"]}; SOS = labs["sos"]
    when = {}
    for r in csv.DictReader(open(D / "ufc_event_details.csv", encoding="utf-8")):
        when[r["EVENT"].strip()] = dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    result = {(r["EVENT"].strip(), r["BOUT"].strip()): r for r in csv.DictReader(open(D / "ufc_fight_results.csv", encoding="utf-8"))}
    stats = {}
    for r in csv.DictReader(open(D / "ufc_fight_stats.csv", encoding="utf-8")):
        m = re.fullmatch(r"Round (\d+)", (r["ROUND"] or "").strip())
        if m: stats.setdefault((r["EVENT"].strip(), r["BOUT"].strip()), {})[(int(m.group(1)), r["FIGHTER"].strip())] = r

    def score(row):
        return (W["head"] * landed(row["HEAD"])[0] + W["body"] * landed(row["BODY"])[0] + W["leg"] * landed(row["LEG"])[0]
                + W["kd"] * int(float(row["KD"] or 0)) + W["td"] * landed(row["TD"])[0] + W["ctrl"] * clock(row["CTRL"]) / 60
                + W["sub"] * int(float(row["SUB.ATT"] or 0)))

    def bouts(name):
        """One record per prior UFC bout for this fighter, built straight from the CSV rows."""
        me = ck(name); out = []
        for (e, b), rr in stats.items():
            d = when.get(e)
            if not d or d >= cut: continue
            names = {fi for (_, fi) in rr}; mine = [x for x in names if ck(x) == me]
            if len(mine) != 1 or len(names) != 2 or (e, b) not in result: continue
            me_n = mine[0]; op = (names - {me_n}).pop(); res = result[(e, b)]
            first = b.split(" vs. ")[0].strip() == me_n; oc = res["OUTCOME"].strip()
            decided = oc in ("W/L", "L/W"); won = decided and ((oc == "W/L") == first)
            lr, lt = int(res["ROUND"]), clock(res["TIME"]); meth, det = res["METHOD"], res["DETAILS"] or ""
            rec = dict(d=d, op=op, decided=decided, won=won, meth=meth, det=det, rounds=[])
            for rd in range(1, min(lr, 5) + 1):
                x, y = rr.get((rd, me_n)), rr.get((rd, op))
                if not x or not y: continue
                secs = lt if rd == lr else 300
                if rd == lr and decided and "Decision" not in meth: rw = 1.0 if won else 0.0
                else:
                    sx, sy = score(x), score(y); rw = 1.0 if sx > sy else (0.0 if sx < sy else 0.5)
                rec["rounds"].append(dict(rd=rd, secs=secs, rw=rw, L=landed(x["SIG.STR."])[0], A=landed(y["SIG.STR."])[0],
                    tgt={t: (landed(x[t.upper()])[0], landed(y[t.upper()])[0]) for t in ("head", "body", "leg")},
                    ohead=landed(y["HEAD"]), kdf=int(float(x["KD"] or 0)), kda=int(float(y["KD"] or 0)), td=landed(x["TD"]), otd=landed(y["TD"]),
                    cf=clock(x["CTRL"]), ca=clock(y["CTRL"]), sub=int(float(x["SUB.ATT"] or 0))))
            out.append(rec)
        return out

    standing = lambda r: ("KO/TKO" in r["meth"] and "Doctor" not in r["meth"] and re.search(r"At Distance|In Clinch|Flying|Spinning", r["det"])
                          and not re.search(r"From |On Ground|On The Ground|Upkick", r["det"]))
    koloss = lambda r: "KO/TKO" in r["meth"] and "Doctor" not in r["meth"] and "njury" not in r["det"]
    bad = []; checked = 0

    def cmp(nm, path, want, got):
        nonlocal checked
        checked += 1
        if want is None and got is None: return
        tol = 0.0051 if path.endswith("mins") else TOL * max(1, abs(float(want))) if want is not None else TOL   # mins are stored to 2 dp
        if want is None or got is None or abs(float(want) - float(got)) > tol:
            bad.append(f"{nm}: {path} recomputed {want} vs file {got}")

    def at(obj, path):
        for k in path.split("."):
            if obj is None: return None
            obj = obj[int(k)] if isinstance(obj, list) else obj.get(k)
        return obj

    for f in ev["fights"]:
        for s in ("a", "b"):
            nm = f[s]["name"]; G = M["fighters"].get(nm)
            if G is None: bad.append(f"{nm}: missing from metrics file"); continue
            B = bouts(nm); R_ = [r for b in B for r in b["rounds"]]
            T = sum(r["secs"] for r in R_); mins = T / 60
            cmp(nm, "ufc_fights", len(B), G.get("ufc_fights"))
            land = sum(r["tgt"][t][0] for r in R_ for t in ("head", "body", "leg"))
            for t in ("head", "body", "leg"):
                cmp(nm, f"target.{t}", sum(r["tgt"][t][0] for r in R_) / land if land else None, at(G, f"target.{t}"))
                cmp(nm, f"target_diff.{t}", sum(r["tgt"][t][0] - r["tgt"][t][1] for r in R_) / mins if mins else None, at(G, f"target_diff.{t}"))
            for rd in range(1, 6):
                X = [r for r in R_ if r["rd"] == rd]; sx = sum(r["secs"] for r in X)
                cmp(nm, f"rounds.{rd-1}.fights", len(X), at(G, f"rounds.{rd-1}.fights"))
                cmp(nm, f"rounds.{rd-1}.mins", sx / 60, at(G, f"rounds.{rd-1}.mins"))
                cmp(nm, f"rounds.{rd-1}.diff_pm", sum(r["L"] - r["A"] for r in X) / (sx / 60) if sx else None, at(G, f"rounds.{rd-1}.diff_pm"))
                cmp(nm, f"rounds.{rd-1}.landed_pm", sum(r["L"] for r in X) / (sx / 60) if sx else None, at(G, f"rounds.{rd-1}.landed_pm"))
                cmp(nm, f"rounds.{rd-1}.won", sum(r["rw"] for r in X) / len(X) if X else None, at(G, f"rounds.{rd-1}.won"))
            e45 = sum(r["secs"] for r in R_ if r["rd"] >= 4); e13 = sum(r["secs"] for r in R_ if r["rd"] <= 3)
            if e45 and e13:
                cmp(nm, "r45.landed_pm_45", sum(r["L"] for r in R_ if r["rd"] >= 4) / (e45 / 60), at(G, "r45.landed_pm_45"))
                cmp(nm, "r45.landed_pm_13", sum(r["L"] for r in R_ if r["rd"] <= 3) / (e13 / 60), at(G, "r45.landed_pm_13"))
                cmp(nm, "r45.diff_pm_45", sum(r["L"] - r["A"] for r in R_ if r["rd"] >= 4) / (e45 / 60), at(G, "r45.diff_pm_45"))
            dec_ = [b for b in B if b["decided"]]
            dsec = [((max(r["rd"] for r in b["rounds"]) - 1) * 300 + [r for r in b["rounds"] if r["rd"] == max(r2["rd"] for r2 in b["rounds"])][0]["secs"]) for b in dec_ if b["rounds"]]
            cmp(nm, "pace.n", len(dec_), at(G, "pace.n"))
            cmp(nm, "pace.min", sum(dsec) / len(dsec) / 60 if dsec else None, at(G, "pace.min"))
            cmp(nm, "pace.r1", sum(1 for b in dec_ if b["rounds"] and max(r["rd"] for r in b["rounds"]) == 1 and "Decision" not in b["meth"]) / len(dec_) if dec_ else None, at(G, "pace.r1"))
            ohl = sum(r["ohead"][0] for r in R_); oha = sum(r["ohead"][1] for r in R_)
            cmp(nm, "hdef", 1 - ohl / oha if oha else None, G.get("hdef"))
            # power / dropped per bout, newest first for the recency weights
            ev_ = sorted(((b["d"], int(sum(r["kdf"] for r in b["rounds"]) > 0 or (b["decided"] and b["won"] and bool(standing(b)))),
                           int(sum(r["kda"] for r in b["rounds"]) > 0 or (b["decided"] and not b["won"] and koloss(b)))) for b in B), reverse=True)
            cmp(nm, "power_fights", sum(x[1] for x in ev_), G.get("power_fights")); cmp(nm, "dropped_fights", sum(x[2] for x in ev_), G.get("dropped_fights"))
            wts = [0.5 ** (i / 3) for i in range(len(ev_))]
            if ev_:
                cmp(nm, "power_w", sum(w * x[1] for w, x in zip(wts, ev_)) / sum(wts), G.get("power_w"))
                cmp(nm, "dropped_w", sum(w * x[2] for w, x in zip(wts, ev_)) / sum(wts), G.get("dropped_w"))
            cmp(nm, "last5.power", sum(x[1] for x in ev_[:5]), at(G, "last5.power")); cmp(nm, "last5.dropped", sum(x[2] for x in ev_[:5]), at(G, "last5.dropped"))
            cmp(nm, "last5.fights", len(ev_[:5]), at(G, "last5.fights"))
            for w_ in ("w", "l"):
                for m_, pat in (("ko", "KO/TKO"), ("sub", "Submission"), ("dec", "Decision")):
                    cmp(nm, f"outcomes.{w_}.{m_}", sum(1 for b in B if b["decided"] and (b["won"] == (w_ == "w")) and pat in b["meth"]), at(G, f"outcomes.{w_}.{m_}"))
            tdl = sum(r["td"][0] for r in R_); tda = sum(r["td"][1] for r in R_); otl = sum(r["otd"][0] for r in R_); ota = sum(r["otd"][1] for r in R_)
            cmp(nm, "grap.td15", tdl / mins * 15 if mins else None, at(G, "grap.td15"))
            cmp(nm, "grap.td_acc", tdl / tda if tda else None, at(G, "grap.td_acc"))
            cmp(nm, "grap.tdd", 1 - otl / ota if ota else None, at(G, "grap.tdd"))
            cmp(nm, "grap.ctrl", sum(r["cf"] for r in R_) / T if T else None, at(G, "grap.ctrl"))
            cmp(nm, "grap.ctrl_ag", sum(r["ca"] for r in R_) / T if T else None, at(G, "grap.ctrl_ag"))
            cmp(nm, "grap.sub15", sum(r["sub"] for r in R_) / mins * 15 if mins else None, at(G, "grap.sub15"))
            GA = json.load(open(REPO / "data/embeds/grappling_adjust.json"))
            if f[s].get("slug") and B:
                oe2 = {x["d"]: x.get("oe") for x in json.load(open(REPO / "form/data/fighters" / f"{f[s]['slug']}.json"))["fights"]}
                bs = [(sum(r["cf"] for r in b["rounds"]), sum(r["ca"] for r in b["rounds"]), sum(r["secs"] for r in b["rounds"]), oe2.get(b["d"])) for b in B]
                tw = sum(x[2] for x in bs if x[2])
                if tw:
                    cmp(nm, "grap.net_ctrl", sum(x[0] - x[1] for x in bs) / tw, at(G, "grap.net_ctrl"))
                    cmp(nm, "grap.adj_net_ctrl", sum(((x[0] - x[1]) / x[2] - (GA["gamma_per100"] * (x[3] - GA["strength_mean"]) / 100 if x[3] else 0)) * x[2] for x in bs if x[2]) / tw, at(G, "grap.adj_net_ctrl"))
            per = [dict(L=sum(r["L"] for r in b["rounds"]), A=sum(r["A"] for r in b["rounds"]), s=sum(r["secs"] for r in b["rounds"]),
                        cf=sum(r["cf"] for r in b["rounds"]), ca=sum(r["ca"] for r in b["rounds"]),
                        t1=sum(r["td"][0] for r in b["rounds"]), t2=sum(r["otd"][0] for r in b["rounds"])) for b in B]
            cmp(nm, "out_landed.k", sum(1 for p in per if p["s"] and p["L"] > p["A"]), at(G, "out_landed.k"))
            cmp(nm, "out_landed.n", sum(1 for p in per if p["s"]), at(G, "out_landed.n"))
            gq = [p for p in per if p["cf"] + p["ca"] >= 60 or p["t1"] + p["t2"] > 0]
            cmp(nm, "grap_won.n", len(gq), at(G, "grap_won.n"))
            cmp(nm, "grap_won.k", sum(1 for p in gq if p["cf"] > p["ca"] or (p["cf"] == p["ca"] and p["t1"] > p["t2"])), at(G, "grap_won.k"))
            # opponent-adjusted diff: opponent strength from the fighter file (by date), weight = bout seconds, bouts of 3+ min
            if f[s].get("slug"):
                oe = {x["d"]: x.get("oe") for x in json.load(open(REPO / "form/data/fighters" / f"{f[s]['slug']}.json"))["fights"]}
                wsum = sum(p["s"] for p, b in zip(per, B) if oe.get(b["d"]) and p["s"] >= 180)
                if wsum and T:
                    mo = sum(oe[b["d"]] * p["s"] for p, b in zip(per, B) if oe.get(b["d"]) and p["s"] >= 180) / wsum
                    raw = sum(p["L"] - p["A"] for p in per) / (T / 60)
                    cmp(nm, "sos.adj_sd", raw - SOS["beta100"] / 100 * (mo - SOS["mean"]), at(G, "sos.adj_sd"))
            # the drill-down rows: strikes +/- for each fight and round, matched by date and round
            for i_, fx in enumerate(G.get("fights") or []):
                b = next((b for b in B if b["d"] == fx["d"]), None)
                if b is None: bad.append(f"{nm}: drill-down fight {fx['d']} not in the CSV"); continue
                for j_, (rd, rw, dff) in enumerate(fx["rw"]):
                    r = next((r for r in b["rounds"] if r["rd"] == rd), None)
                    cmp(nm, f"fights.{i_}.rw.{j_}.2", (r["L"] - r["A"]) if r else None, dff); cmp(nm, f"fights.{i_}.rw.{j_}.1", r["rw"] if r else None, rw)
    # division baselines, for the weight classes on this card
    wcs = {re.sub(r"^(UFC )?(Interim )?", "", f.get("wc") or "") for f in ev["fights"]}
    tally = {}
    for (e, b), res in result.items():
        d = when.get(e)
        if not d or d < "2020-01-01" or d >= cut or (e, b) not in stats: continue
        wc = re.sub(r"( Title)? Bout$", "", re.sub(r"^(UFC )?(Interim )?", "", res["WEIGHTCLASS"].strip())).strip()
        if wc not in wcs: continue
        sides = [x.strip() for x in b.split(" vs. ")]
        if len(sides) != 2: continue
        oc = res["OUTCOME"].strip(); win = sides[0] if oc == "W/L" else sides[1] if oc == "L/W" else None
        kd = {n_: sum(int(float(v["KD"] or 0)) for (rd, fi), v in stats[(e, b)].items() if fi == n_) for n_ in sides}
        rr = dict(meth=res["METHOD"], det=res["DETAILS"] or "")
        t = tally.setdefault(wc, [0, 0, 0])
        for n_ in sides:
            o_ = sides[1] if n_ == sides[0] else sides[0]
            t[0] += 1; t[1] += (kd[n_] > 0) or (win == n_ and bool(standing(rr))); t[2] += (kd[o_] > 0) or (win == o_ and koloss(rr))
    for wc, (n_, p_, d_) in tally.items():
        if n_ >= 100:
            cmp("division " + wc, "power_share", p_ / n_, M["division_power_share"].get(wc)); cmp("division " + wc, "dropped_share", d_ / n_, M["division_dropped_share"].get(wc))
    # debutants' tale of the tape against the raw UFCStats fighter list
    tott = {}
    for r in csv.DictReader(open(D / "ufc_fighter_tott.csv", encoding="utf-8")): tott.setdefault(ck(r["FIGHTER"]), r)
    for f in ev["fights"]:
        for s in ("a", "b"):
            b_ = (M["fighters"].get(f[s]["name"]) or {}).get("bio")
            if not b_: continue
            r = tott.get(ck(f[s]["name"])); checked += 1
            want = (re.sub(r"' ", "'", r["HEIGHT"]) if r and r["HEIGHT"] != "--" else None, r["REACH"].rstrip('"') if r and r["REACH"] != "--" else None,
                    dt.datetime.strptime(r["DOB"], "%b %d, %Y").strftime("%Y-%m-%d") if r and r["DOB"] not in ("", "--") else None)
            if (b_.get("ht"), b_.get("reach"), b_.get("dob")) != want: bad.append(f"{f[s]['name']}: debut bio {b_} vs UFCStats {want}")
    print(f"verify_embed_metrics: {checked} values recomputed from the CSVs, {len(bad)} mismatches")
    for x in bad[:40]: print("  MISMATCH", x)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
