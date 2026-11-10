#!/usr/bin/env python3
"""Labs data: reads the built Fight Form JSON (form/data) plus the cached UFCStats round stats and writes
form/data/labs.json (studies) and form/data/labs_fights.json (compact rows for the query tool).
Run after build_form.py:  python3 scripts/build_labs.py"""
import csv, json, re, glob, math, datetime as dt
from collections import defaultdict
from pathlib import Path
import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parents[1]
D = REPO / "form" / "data"
CACHE = REPO / ".form_cache"
DIVS = ["Strawweight", "Flyweight", "Bantamweight", "Featherweight", "Lightweight", "Welterweight", "Middleweight",
        "Light Heavyweight", "Heavyweight", "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight"]
APEX_PPV = {250, 252, 255, 256, 258, 259, 260}
VEGAS_NOT_APEX = {"2023-03-11": "The Theater at Virgin Hotels", "2023-09-16": "T-Mobile Arena"}
ALTITUDE = ("Mexico City", "Denver", "Salt Lake City")


def of(s):
    m = re.match(r"\s*(\d+)\s+of\s+(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def mmss(s):
    m = re.match(r"\s*(\d+):(\d+)", s or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0


def inches(h):
    m = re.match(r"(\d+)'(\d+)", h or "")
    return int(m.group(1)) * 12 + int(m.group(2)) if m else None


def mclass(m):
    return "DEC" if "Decision" in m else "SUB" if "Sub" in m else "KO" if "KO" in m else "OTH"


def payout(american):
    return american / 100 if american > 0 else 100 / -american


def is_apex(name, loc, date):
    if not loc.startswith("Las Vegas") or date < "2020-05-30":
        return False
    # Venue log checked against Wikipedia "List of UFC events" (read 2026-11-10): every Las Vegas card since
    # 2020-05-30 was at the APEX except numbered cards other than the seven pandemic-era ones, and two Fight Nights.
    if date in VEGAS_NOT_APEX:
        return False
    m = re.match(r"UFC (\d+)", name)
    return (int(m.group(1)) in APEX_PPV) if m else True


def rnd(x, d=3):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), d)


def main():
    bios = {}
    for p in glob.glob(str(D / "fighters" / "*.json")):
        j = json.load(open(p))
        bios[j["slug"]] = j.get("bio") or {}
    events = [json.load(open(p)) for p in sorted(glob.glob(str(D / "events" / "*.json")))]
    events = [e for e in events if e.get("status") == "final"]
    events.sort(key=lambda e: e["date"])

    # raw round stats with attempts
    raw = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    rawr = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for r in csv.DictReader(open(CACHE / "ufc_fight_stats.csv", encoding="utf-8")):
        f = (r["FIGHTER"] or "").strip()
        if not f:
            continue
        t = raw[(r["EVENT"].strip(), r["BOUT"].strip())][f]
        try:
            t["kd"] += int(float(r["KD"] or 0))
        except ValueError:
            pass
        for k, col in (("sig", "SIG.STR."), ("td", "TD"), ("head", "HEAD"), ("body", "BODY"), ("leg", "LEG"), ("dist", "DISTANCE"), ("clinch", "CLINCH"), ("ground", "GROUND")):
            l, a = of(r[col]); t[k + "_l"] += l; t[k + "_a"] += a
        try:
            t["sub"] += int(float(r["SUB.ATT"] or 0))
        except ValueError:
            pass
        t["ctrl"] += mmss(r["CTRL"])
        rn = re.search(r"(\d+)", r["ROUND"] or "")
        if rn:
            rr = rawr[(r["EVENT"].strip(), r["BOUT"].strip())][f][int(rn.group(1))]
            rr["sl"], rr["sa"] = of(r["SIG.STR."]); rr["tl"], rr["ta"] = of(r["TD"]); rr["ctrl"] = mmss(r["CTRL"])
            try:
                rr["kd"] = int(float(r["KD"] or 0))
            except ValueError:
                rr["kd"] = 0
            for k_, col in (("head", "HEAD"), ("body", "BODY"), ("leg", "LEG"), ("dist", "DISTANCE"), ("clinch", "CLINCH"), ("ground", "GROUND")):
                rr[k_] = of(r[col])[0]
            rr["tot"] = of(r["TOTAL STR."])[0]
            try:
                rr["sub"] = int(float(r["SUB.ATT"] or 0))
            except ValueError:
                rr["sub"] = 0
    rrkey = {(en, frozenset(x.strip() for x in bout.split(" vs. "))): v for (en, bout), v in rawr.items()}
    rawkey = {}
    for (en, bout), v in raw.items():
        rawkey[(en, frozenset(x.strip() for x in bout.split(" vs. ")))] = v

    F = []  # flat fights
    for e in events:
        top = max((f["n"] for f in e["fights"]), default=0)
        apex = is_apex(e["name"], e.get("location") or "", e["date"])
        for f in e["fights"]:
            r = f.get("result") or {}
            if not r.get("kind"):
                continue
            secs = None
            if r.get("round") and r.get("time"):
                secs = (r["round"] - 1) * 300 + mmss(r["time"])
            od = f.get("odds") or {}
            cl, op = od.get("close"), od.get("open")
            st = rawkey.get((e["name"], frozenset([f["a"]["name"], f["b"]["name"]])))
            F.append({"e": e, "f": f, "date": e["date"], "yr": int(e["date"][:4]), "wc": re.sub(r"^Interim ", "", f.get("wc") or ""), "sched": f.get("sched"),
                      "pos": top - f["n"] + 1, "apex": apex, "a": f["a"], "b": f["b"], "kind": r["kind"], "w": r.get("winner"),
                      "m": mclass(r.get("method") or ""), "method": r.get("method") or "", "secs": secs, "cl": cl, "op": op,
                      "ra": (st or {}).get(f["a"]["name"]), "rb": (st or {}).get(f["b"]["name"]),
                      "rr": rrkey.get((e["name"], frozenset([f["a"]["name"], f["b"]["name"]]))), "ref": r.get("ref") or "", "details": r.get("details") or "", "rnd": r.get("round")})
    dec = [x for x in F if x["kind"] == "win"]

    def study(rows):
        """rows: (fight, side) = the side being tracked. Win rate over all rows; market + ROI over rows with a close."""
        n = len(rows); w = sum(1 for x, s in rows if x["w"] == s)
        o = [(x, s) for x, s in rows if x["cl"] and x["cl"].get("ma") is not None and x["cl"].get("mb") is not None]
        imp = [x["cl"]["p"] if s == "a" else 1 - x["cl"]["p"] for x, s in o]
        pnl = [payout(x["cl"]["ma" if s == "a" else "mb"]) if x["w"] == s else -1 for x, s in o]
        ow = sum(1 for x, s in o if x["w"] == s)
        return {"n": n, "w": w, "wp": rnd(w / n) if n else None, "on": len(o), "ow": ow, "owp": rnd(ow / len(o)) if o else None,
                "imp": rnd(sum(imp) / len(imp)) if o else None, "roi": rnd(sum(pnl) / len(pnl)) if o else None}

    out = {"built": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", "n_fights": len(F), "n_odds": sum(1 for x in F if x["cl"])}

    # ---- biggest upsets (closing consensus)
    ups = []
    for x in dec:
        if not x["cl"]:
            continue
        pw = x["cl"]["p"] if x["w"] == "a" else 1 - x["cl"]["p"]
        win, lose = (x["a"], x["b"]) if x["w"] == "a" else (x["b"], x["a"])
        ups.append({"d": x["date"], "es": x["e"]["slug"], "n": x["f"]["n"], "w": win["name"], "l": lose["name"], "p": rnd(pw),
                    "ml": x["cl"]["ma" if x["w"] == "a" else "mb"], "lml": x["cl"]["mb" if x["w"] == "a" else "ma"], "m": x["m"], "r": x["f"]["result"].get("round"), "wc": x["wc"]})
    ups.sort(key=lambda u: u["p"])
    out["upsets"] = ups[:40]
    byyr = defaultdict(list)
    for u in ups:
        byyr[u["d"][:4]].append(u)
    out["upsets_by_year"] = [{"yr": y, "n": len(v), "dogs": sum(1 for u in v if u["p"] < 0.5), "big": sum(1 for u in v if u["p"] < 0.25)} for y, v in sorted(byyr.items())]

    # ---- physical gaps
    def age(slug, date):
        dob = (bios.get(slug) or {}).get("dob")
        return (dt.date.fromisoformat(date) - dt.date.fromisoformat(dob)).days / 365.25 if dob else None

    def gap_study(val, buckets, since="2010-01-01"):
        res = []
        for lab, lo, hi in buckets:
            rows = []
            for x in dec:
                if x["date"] < since:
                    continue
                va, vb = val(x["a"]["slug"], x), val(x["b"]["slug"], x)
                if va is None or vb is None or va == vb:
                    continue
                g = abs(va - vb)
                if lo <= g < hi:
                    rows.append((x, "a" if va > vb else "b"))
            s = study(rows); s["label"] = lab; res.append(s)
        return res
    AG = [("under 2 yrs", 0, 2), ("2–4", 2, 4), ("4–6", 4, 6), ("6–8", 6, 8), ("8–10", 8, 10), ("10+", 10, 99)]
    older = gap_study(lambda s, x: age(s, x["date"]), AG)
    for s in older:  # flip to the younger fighter
        for a, b in (("w", "n"), ("ow", "on")):
            s[a] = s[b] - s[a]
        s["wp"] = rnd(s["w"] / s["n"]) if s["n"] else None
        s["owp"] = rnd(s["ow"] / s["on"]) if s["on"] else None
        s["imp"] = rnd(1 - s["imp"]) if s["imp"] is not None else None
        s.pop("roi")
    # ROI on the younger side needs its own pass
    for s, (lab, lo, hi) in zip(older, AG):
        rows = []
        for x in dec:
            if x["date"] < "2010-01-01":
                continue
            va, vb = age(x["a"]["slug"], x["date"]), age(x["b"]["slug"], x["date"])
            if va is None or vb is None or va == vb or not (lo <= abs(va - vb) < hi):
                continue
            rows.append((x, "a" if va < vb else "b"))
        s["roi"] = study(rows)["roi"]
    out["age_gap"] = older
    out["reach_gap"] = gap_study(lambda s, x: float((bios.get(s) or {}).get("reach")) if (bios.get(s) or {}).get("reach") else None,
                                 [("1 in", 1, 2), ("2 in", 2, 3), ("3 in", 3, 4), ("4 in", 4, 5), ("5 in", 5, 6), ("6+ in", 6, 99)])
    out["height_gap"] = gap_study(lambda s, x: inches((bios.get(s) or {}).get("ht")),
                                  [("1 in", 1, 2), ("2 in", 2, 3), ("3 in", 3, 4), ("4 in", 4, 5), ("5+ in", 5, 99)])
    # age bands (fighter's own age) vs market
    bands = [("under 25", 0, 25), ("25–27", 25, 28), ("28–30", 28, 31), ("31–33", 31, 34), ("34–36", 34, 37), ("37+", 37, 99)]
    ab = []
    for lab, lo, hi in bands:
        rows = []
        for x in dec:
            if x["date"] < "2010-01-01":
                continue
            for s in "ab":
                a_ = age(x[s]["slug"], x["date"])
                if a_ is not None and lo <= a_ < hi:
                    rows.append((x, s))
        st = study(rows); st["label"] = lab; ab.append(st)
    out["age_band"] = ab

    # ---- situational spots (chronological history)
    hist = defaultdict(list)
    sit = defaultdict(list)
    for x in F:
        info = {}
        for s in "ab":
            h = hist[x[s]["slug"]]
            lastd = h[-1]["date"] if h else None
            info[s] = {"debut": not h, "lay": (dt.date.fromisoformat(x["date"]) - dt.date.fromisoformat(lastd)).days if lastd else None,
                       "ko_loss": bool(h) and h[-1]["lost"] and h[-1]["m"] == "KO", "stance": (bios.get(x[s]["slug"]) or {}).get("stance")}
        if x["kind"] == "win" and x["date"] >= "2010-01-01":
            for s, o in (("a", "b"), ("b", "a")):
                i, j = info[s], info[o]
                if i["debut"] and not j["debut"]: sit["UFC debut vs. a UFC veteran"].append((x, s))
                if i["lay"] and i["lay"] >= 400 and j["lay"] and j["lay"] < 250: sit["400+ day layoff vs. opponent active inside 250 days"].append((x, s))
                if i["ko_loss"] and not j["ko_loss"] and not j["debut"]: sit["Coming off a KO/TKO loss"].append((x, s))
                if i["stance"] == "Southpaw" and j["stance"] == "Orthodox": sit["Southpaw vs. orthodox"].append((x, s))
                if i["lay"] and i["lay"] <= 60 and j["lay"] and j["lay"] > 60: sit["Quick turnaround (60 days or fewer)"].append((x, s))
        for s in "ab":
            hist[x[s]["slug"]].append({"date": x["date"], "lost": x["kind"] == "win" and x["w"] != s, "m": x["m"]})
    out["situational"] = [dict(study(v), label=k) for k, v in sit.items()]
    # card position: favourites by slot
    pos = []
    for lab, fn in (("Main event", lambda x: x["pos"] == 1), ("Co-main to 5th from top", lambda x: 2 <= x["pos"] <= 5), ("6th from top and lower", lambda x: x["pos"] >= 6),
                    ("Five-round fights", lambda x: x["sched"] == 5), ("Title fights", lambda x: x["f"].get("title"))):
        rows = [(x, "a" if x["cl"]["p"] >= 0.5 else "b") for x in dec if x["cl"] and fn(x)]
        s = study(rows); s["label"] = lab; s["dist"] = rnd(sum(1 for x, _ in rows if x["m"] == "DEC") / len(rows)) if rows else None; pos.append(s)
    out["position"] = pos

    # ---- divisional baselines
    def agg(rows):
        n = len(rows)
        if not n:
            return None
        k = sum(1 for x in rows if x["m"] == "KO"); s = sum(1 for x in rows if x["m"] == "SUB"); d = sum(1 for x in rows if x["m"] == "DEC")
        st = [x for x in rows if x["ra"] and x["rb"] and x["secs"]]
        mins = sum(x["secs"] for x in st) / 60 or 1
        tot = lambda key: sum(x["ra"][key] + x["rb"][key] for x in st)
        return {"n": n, "fin": rnd((k + s) / n), "ko": rnd(k / n), "sub": rnd(s / n), "dec": rnd(d / n),
                "min": rnd(sum(x["secs"] for x in rows if x["secs"]) / 60 / max(1, sum(1 for x in rows if x["secs"])), 2),
                "slpm": rnd(tot("sig_l") / 2 / mins, 2), "td15": rnd(tot("td_l") / 2 / mins * 15, 2), "kd15": rnd(tot("kd") / 2 / mins * 15, 3),
                "ctrl": rnd(tot("ctrl") / 60 / mins, 3), "head": rnd(tot("head_l") / max(1, tot("sig_l"))), "dist": rnd(tot("dist_l") / max(1, tot("sig_l")))}
    last = dt.date.fromisoformat(events[-1]["date"])
    d12, d36 = (last - dt.timedelta(days=365)).isoformat(), (last - dt.timedelta(days=1095)).isoformat()
    divs = []
    for wc in DIVS + ["All"]:
        rows = [x for x in dec if (wc == "All" or x["wc"] == wc)]
        divs.append({"wc": wc, "r12": agg([x for x in rows if x["date"] > d12]), "r36": agg([x for x in rows if x["date"] > d36]),
                     "years": {str(y): agg([x for x in rows if x["yr"] == y]) for y in range(2015, last.year + 1)}})
    out["divisions"] = divs
    out["asof"] = last.isoformat()

    # ---- APEX vs full-size cage (rule-based venue flag; see note on the page)
    base = {wc: agg([x for x in dec if x["wc"] == wc and x["date"] >= "2020-05-30"]) for wc in DIVS}
    oct_ = []
    for y in range(2020, last.year + 1):
        row = {"yr": y}
        for lab, fl in (("apex", True), ("big", False)):
            rows = [x for x in dec if x["yr"] == y and x["date"] >= "2020-05-30" and x["apex"] == fl]
            a = agg(rows)
            exp = [base[x["wc"]]["fin"] for x in rows if x["wc"] in base and base[x["wc"]]]
            row[lab] = a and {"n": a["n"], "fin": a["fin"], "ko": a["ko"], "sub": a["sub"], "exp": rnd(sum(exp) / len(exp)) if exp else None, "ev": len({x["e"]["slug"] for x in rows})}
        oct_.append(row)
    allr = {}
    for lab, fl in (("apex", True), ("big", False)):
        rows = [x for x in dec if x["date"] >= "2020-05-30" and x["apex"] == fl]
        a = agg(rows); exp = [base[x["wc"]]["fin"] for x in rows if x["wc"] in base and base[x["wc"]]]
        allr[lab] = {"n": a["n"], "fin": a["fin"], "ko": a["ko"], "sub": a["sub"], "exp": rnd(sum(exp) / len(exp)), "ev": len({x["e"]["slug"] for x in rows})}
    out["octagon"] = {"years": oct_, "all": allr}

    # ---- custom fighter metrics
    T = defaultdict(lambda: defaultdict(float)); meta = {}
    for x in F:
        if not (x["ra"] and x["rb"] and x["secs"]):
            continue
        for s, o in (("a", "b"), ("b", "a")):
            me, op = x["r" + s], x["r" + o]; t = T[x[s]["slug"]]
            t["secs"] += x["secs"]; t["n"] += 1
            for k in ("kd", "ctrl", "sig_l", "sig_a", "td_l", "td_a", "head_l", "head_a", "body_l", "body_a", "leg_l", "leg_a", "dist_l", "dist_a", "clinch_l", "ground_l"):
                t[k] += me[k]; t["o_" + k] += op[k]
            meta[x[s]["slug"]] = {"name": x[s]["name"], "last": x["date"], "wc": x["wc"]}
    cut = (last - dt.timedelta(days=730)).isoformat()
    div = lambda a, b: (a / b) if b else None
    mets = []
    lg = defaultdict(float)
    for slug, t in T.items():
        for k, v in t.items():
            lg[k] += v
        if t["n"] < 5 or meta[slug]["last"] < cut:
            continue
        m = t["secs"] / 60
        mets.append({"s": slug, "nm": meta[slug]["name"], "wc": meta[slug]["wc"], "n": int(t["n"]), "min": rnd(m, 0),
                     "ctd": rnd(div(t["ctrl"], t["td_l"]), 0) if t["td_l"] >= 5 else None,             # control seconds per takedown landed
                     "octd": rnd(div(t["o_ctrl"], t["o_td_l"]), 0) if t["o_td_l"] >= 5 else None,     # opponent control per takedown conceded
                     "kd15": rnd(t["kd"] / m * 15, 2), "kda15": rnd(t["o_kd"] / m * 15, 2),
                     "kdr": rnd(div(t["kd"] * 100, t["head_l"]), 2), "chin": rnd(div(t["o_kd"] * 100, t["o_head_l"]), 2),
                     "hdef": rnd(1 - t["o_head_l"] / t["o_head_a"]) if t["o_head_a"] else None,
                     "bdef": rnd(1 - t["o_body_l"] / t["o_body_a"]) if t["o_body_a"] >= 40 else None,
                     "ldef": rnd(1 - t["o_leg_l"] / t["o_leg_a"]) if t["o_leg_a"] >= 40 else None,
                     "dd": rnd((t["dist_l"] - t["o_dist_l"]) / m, 2), "hd": rnd((t["head_l"] - t["o_head_l"]) / m, 2),
                     "bd": rnd((t["body_l"] - t["o_body_l"]) / m, 2), "ld": rnd((t["leg_l"] - t["o_leg_l"]) / m, 2),
                     "mix": [rnd(div(t["head_l"], t["sig_l"]) or 0, 2), rnd(div(t["body_l"], t["sig_l"]) or 0, 2), rnd(div(t["leg_l"], t["sig_l"]) or 0, 2)],
                     "dshare": rnd(div(t["dist_l"], t["sig_l"]), 2)})
    lm = lg["secs"] / 60
    out["metrics"] = mets
    out["metrics_league"] = {"ctd": rnd(lg["ctrl"] / lg["td_l"], 0), "kd15": rnd(lg["kd"] / lm * 15, 2), "kdr": rnd(lg["kd"] * 100 / lg["head_l"], 2),
                             "hdef": rnd(1 - lg["head_l"] / lg["head_a"]), "bdef": rnd(1 - lg["body_l"] / lg["body_a"]), "ldef": rnd(1 - lg["leg_l"] / lg["leg_a"])}

    # ---- how decisions are scored: logistic on stat differentials, no intercept, both orientations
    FE = [("head", "head_l", "Head strike"), ("body", "body_l", "Body strike"), ("leg", "leg_l", "Leg strike"), ("kd", "kd", "Knockdown"),
          ("td", "td_l", "Takedown"), ("ctrl", "ctrl", "Minute of control"), ("sub", "sub", "Submission attempt")]
    dfs = [x for x in dec if x["m"] == "DEC" and x["ra"] and x["rb"] and x["date"] >= "2010-01-01"]
    def vec(x):
        return [(x["ra"][k] - x["rb"][k]) / (60 if n == "ctrl" else 1) for n, k, _ in FE]
    X = np.array([vec(x) for x in dfs], float); y = np.array([1.0 if x["w"] == "a" else 0.0 for x in dfs])
    X2 = np.vstack([X, -X]); y2 = np.concatenate([y, 1 - y])
    b = np.zeros(X.shape[1])
    for _ in range(40):
        p = 1 / (1 + np.exp(-X2 @ b)); W = p * (1 - p) + 1e-9
        b += np.linalg.solve(X2.T @ (X2 * W[:, None]) + 1e-6 * np.eye(len(b)), X2.T @ (y2 - p))
    pa = 1 / (1 + np.exp(-X @ b)); pw = np.where(y == 1, pa, 1 - pa)
    luck = defaultdict(lambda: [0.0, 0, 0]); rows = []
    for x, p_a, p_w in zip(dfs, pa, pw):
        for s, pp in (("a", p_a), ("b", 1 - p_a)):
            L = luck[x[s]["slug"]]; L[0] += (1.0 if x["w"] == s else 0.0) - pp; L[1] += 1; L[2] = max(L[2], 0)
        win, lose = (x["a"], x["b"]) if x["w"] == "a" else (x["b"], x["a"])
        rows.append({"d": x["date"], "es": x["e"]["slug"], "n": x["f"]["n"], "w": win["name"], "l": lose["name"], "p": rnd(float(p_w)), "split": "Split" in x["method"] or "Majority" in x["method"], "sched": x["sched"]})
    un = [r["p"] for r in rows if not r["split"]]; sp = [r["p"] for r in rows if r["split"]]
    active = {m["s"] for m in mets}
    lk = [{"s": s, "nm": meta[s]["name"], "luck": rnd(v[0], 2), "n": v[1]} for s, v in luck.items() if s in active and v[1] >= 4]
    out["scoring"] = {"n": len(dfs), "acc": rnd(float((pw > 0.5).mean())), "coef": [{"k": n, "label": lab, "b": rnd(float(c), 4), "head_eq": rnd(float(c / b[0]), 1)} for (n, _, lab), c in zip(FE, b)],
                      "unan": {"n": len(un), "p": rnd(sum(un) / len(un)), "agree": rnd(sum(1 for v in un if v > .5) / len(un))},
                      "split": {"n": len(sp), "p": rnd(sum(sp) / len(sp)), "agree": rnd(sum(1 for v in sp if v > .5) / len(sp))},
                      "against": sorted(rows, key=lambda r: r["p"])[:30],
                      "lucky": sorted(lk, key=lambda r: -r["luck"])[:20], "unlucky": sorted(lk, key=lambda r: r["luck"])[:20]}


    # ================= cardio: round 1 vs round 3, fights where round 3 was completed
    def r3done(x):
        return x["rr"] and x["rnd"] and (x["m"] == "DEC" or x["rnd"] >= 4) and all(k in x["rr"].get(x[s]["name"], {}) for s in "ab" for k in (1, 2, 3))
    C = defaultdict(lambda: defaultdict(float)); halves = defaultdict(lambda: [[], []]); wf = []
    def cvec(x, s, o):
        me, op = x["rr"][x[s]["name"]], x["rr"][x[o]["name"]]
        return {"a1": me[1]["sa"], "a3": me[3]["sa"], "a2": me[2]["sa"], "d1": me[1]["sl"] - op[1]["sl"], "d2": me[2]["sl"] - op[2]["sl"], "d3": me[3]["sl"] - op[3]["sl"],
                "t1": me[1]["ta"], "t3": me[3]["ta"], "c1": me[1]["ctrl"], "c3": me[3]["ctrl"], "l1": me[1]["sl"], "l3": me[3]["sl"]}
    for x in F:
        if x["kind"] != "win" and x["kind"] != "draw":
            continue
        if not r3done(x):
            continue
        va, vb = cvec(x, "a", "b"), cvec(x, "b", "a")
        pa_, pb_ = C[x["a"]["slug"]], C[x["b"]["slug"]]
        if pa_["n"] >= 3 and pb_["n"] >= 3:   # walk-forward check
            sa_ = (pa_["d3"] - pa_["d1"]) / pa_["n"]; sb_ = (pb_["d3"] - pb_["d1"]) / pb_["n"]
            if abs(sa_ - sb_) >= 3:
                better = "a" if sa_ > sb_ else "b"; v = va if better == "a" else vb
                wf.append({"imp": v["d3"] - v["d1"], "r3": v["d3"], "lost1": v["d1"] < 0, "gap": abs(sa_ - sb_)})
        for s, v in (("a", va), ("b", vb)):
            c = C[x[s]["slug"]]
            for k, val in v.items():
                c[k] += val
            c["n"] += 1
            h = halves[x[s]["slug"]]; h[int(c["n"]) % 2].append((v["d3"] - v["d1"], v["a3"] / v["a1"] if v["a1"] else None))
            meta.setdefault(x[s]["slug"], {"name": x[s]["name"], "last": x["date"], "wc": x["wc"]})
    def crow(slug):
        c = C.get(slug)
        if not c or c["n"] < 3:
            return None
        n = c["n"]
        return {"s": slug, "nm": meta[slug]["name"], "wc": meta[slug]["wc"], "n": int(n), "a1": rnd(c["a1"] / n / 5, 2), "a3": rnd(c["a3"] / n / 5, 2),
                "out": rnd(c["a3"] / c["a1"], 3) if c["a1"] else None, "d1": rnd(c["d1"] / n, 1), "d2": rnd(c["d2"] / n, 1), "d3": rnd(c["d3"] / n, 1), "sw": rnd((c["d3"] - c["d1"]) / n, 1),
                "t1": rnd(c["t1"] / n, 2), "t3": rnd(c["t3"] / n, 2), "c1": rnd(c["c1"] / n, 0), "c3": rnd(c["c3"] / n, 0)}
    tot = defaultdict(float)
    for c in C.values():
        for k, v in c.items():
            tot[k] += v
    def corr(idx):
        xs, ys = [], []
        for h in halves.values():
            if len(h[0]) >= 3 and len(h[1]) >= 3:
                a = [v[idx] for v in h[0] if v[idx] is not None]; b = [v[idx] for v in h[1] if v[idx] is not None]
                if a and b:
                    xs.append(sum(a) / len(a)); ys.append(sum(b) / len(b))
        return rnd(float(np.corrcoef(xs, ys)[0, 1]), 2), len(xs)
    up = []
    try:
        idx = json.load(open(D / "index.json"))
        for u in idx.get("upcoming", [])[:1]:
            ue = json.load(open(D / "events" / (u["slug"] + ".json")))
            for f in sorted(ue["fights"], key=lambda f: -f["n"]):
                up.append({"n": f["n"], "es": ue["slug"], "a": crow(f["a"]["slug"]) or {"nm": f["a"]["name"], "s": f["a"]["slug"]}, "b": crow(f["b"]["slug"]) or {"nm": f["b"]["name"], "s": f["b"]["slug"]}})
            out_up_name = ue["name"]
    except Exception as ex:
        print("upcoming cardio skipped:", ex); out_up_name = None
    crows = [crow(s) for s in C if C[s]["n"] >= 4 and meta[s]["last"] >= cut]
    out["cardio"] = {"rows": [r for r in crows if r], "league": {"out": rnd(tot["a3"] / tot["a1"], 3), "a1": rnd(tot["a1"] / tot["n"] / 5, 2), "a3": rnd(tot["a3"] / tot["n"] / 5, 2),
                     "t1": rnd(tot["t1"] / tot["n"], 2), "t3": rnd(tot["t3"] / tot["n"], 2), "c1": rnd(tot["c1"] / tot["n"], 0), "c3": rnd(tot["c3"] / tot["n"], 0)},
                     "rel_sw": corr(0), "rel_out": corr(1), "upcoming": up, "upcoming_name": out_up_name,
                     "wf": {"n": len(wf), "improved": rnd(sum(1 for w in wf if w["imp"] > 0) / len(wf)) if wf else None, "won3": rnd(sum(1 for w in wf if w["r3"] > 0) / len(wf)) if wf else None,
                            "lost1_n": sum(1 for w in wf if w["lost1"]), "lost1_won3": rnd(sum(1 for w in wf if w["lost1"] and w["r3"] > 0) / max(1, sum(1 for w in wf if w["lost1"])))}}
    base_l1 = [x for x in F if r3done(x)]
    l1 = [(x, s, o) for x in base_l1 for s, o in (("a", "b"), ("b", "a")) if x["rr"][x[s]["name"]][1]["sl"] < x["rr"][x[o]["name"]][1]["sl"]]
    out["cardio"]["base_lost1_won3"] = rnd(sum(1 for x, s, o in l1 if x["rr"][x[s]["name"]][3]["sl"] > x["rr"][x[o]["name"]][3]["sl"]) / len(l1))

    # ================= referees
    since15 = [x for x in dec if x["date"] >= "2015-01-01"]
    bw = {wc: agg([x for x in since15 if x["wc"] == wc]) for wc in DIVS}
    refs = defaultdict(list)
    for x in since15:
        if x["ref"]:
            refs[x["ref"]].append(x)
    R = []
    for nm_, rows in refs.items():
        if len(rows) < 60:
            continue
        a = agg(rows); ex = [bw[x["wc"]] for x in rows if bw.get(x["wc"])]
        ko = [x for x in rows if x["m"] == "KO" and x["secs"]]
        R.append({"nm": nm_, "n": a["n"], "last": max(x["date"] for x in rows), "fin": a["fin"], "ko": a["ko"], "sub": a["sub"], "dec": a["dec"],
                  "xko": rnd(sum(e["ko"] for e in ex) / len(ex)), "xsub": rnd(sum(e["sub"] for e in ex) / len(ex)), "xfin": rnd(sum(e["fin"] for e in ex) / len(ex)),
                  "kot": rnd(sum(x["secs"] for x in ko) / len(ko) / 60, 2) if ko else None,
                  "main": sum(1 for x in rows if x["pos"] == 1), "title": sum(1 for x in rows if x["f"].get("title"))})
    out["refs"] = sorted(R, key=lambda r: -r["n"])

    # ================= judges
    pmodel = {id(x): float(p) for x, p in zip(dfs, pa)}
    J = defaultdict(lambda: defaultdict(float)); pool = defaultdict(float); orient_ok = orient_n = 0
    for x in dfs:
        cards = re.findall(r"([A-Za-z'’\.\- ]+?)\s+(\d+)\s*-\s*(\d+)\s*\.", x["details"])
        if len(cards) != 3:
            continue
        cards = [(n.strip().title(), int(p), int(q)) for n, p, q in cards]
        col0 = sum(1 for _, p, q in cards if p > q); col1 = sum(1 for _, p, q in cards if q > p)
        if col0 == col1:
            continue
        wcol = 0 if col0 > col1 else 1
        orient_n += 1; orient_ok += 1 if (wcol == 0) == (x["w"] == "a") else 0
        ws = x["w"]; ls = "b" if ws == "a" else "a"
        pw_ = pmodel[id(x)] if ws == "a" else 1 - pmodel[id(x)]
        sd = {s: x["r" + s]["sig_l"] for s in "ab"}; cd = {s: x["r" + s]["ctrl"] for s in "ab"}
        clash = None  # one fighter out-landed, the other out-controlled by a minute or more
        for s, o in (("a", "b"), ("b", "a")):
            if sd[s] > sd[o] and cd[o] - cd[s] >= 60:
                clash = o   # the control fighter
        for n_, p, q in cards:
            mine, theirs = (p, q) if wcol == 0 else (q, p)   # winner's points first
            side = ws if mine > theirs else ls if theirs > mine else None
            j = J[n_]; j["n"] += 1; j["last"] = max(j["last"] or 0, int(x["date"].replace("-", "")))
            if side is None:
                j["draw"] += 1; continue
            j["dis"] += side != ws
            j["stat"] += (side == ws) == (pw_ > 0.5); j["statn"] += 1
            if x["sched"] == 3:
                j["n3"] += 1; j["wide"] += abs(mine - theirs) >= 4
            if clash:
                j["cl"] += 1; j["clc"] += side == clash; pool["cl"] += 1; pool["clc"] += side == clash
            pool["n"] += 1; pool["dis"] += side != ws; pool["n3"] += x["sched"] == 3; pool["wide"] += (x["sched"] == 3 and abs(mine - theirs) >= 4); pool["stat"] += (side == ws) == (pw_ > 0.5)
    JR = [{"nm": n_, "n": int(j["n"]), "last": str(int(j["last"])), "dis": rnd(j["dis"] / j["n"]), "stat": rnd(j["stat"] / j["statn"]) if j["statn"] else None,
           "wide": rnd(j["wide"] / j["n3"]) if j["n3"] >= 30 else None, "cl": int(j["cl"]), "ctrl": rnd(j["clc"] / j["cl"]) if j["cl"] >= 15 else None}
          for n_, j in J.items() if j["n"] >= 40]
    out["judges"] = {"rows": sorted(JR, key=lambda r: -r["n"]), "pool": {"n": int(pool["n"]), "dis": rnd(pool["dis"] / pool["n"]), "wide": rnd(pool["wide"] / pool["n3"]), "ctrl": rnd(pool["clc"] / pool["cl"]), "stat": rnd(pool["stat"] / pool["n"]), "cl": int(pool["cl"])},
                     "orient": rnd(orient_ok / orient_n)}

    # ================= weight-class moves + late-booked fights (added to the situational list)
    MEN = DIVS[1:9]; WOM = ["Women's Strawweight", "Women's Flyweight", "Women's Bantamweight", "Women's Featherweight"]
    def widx(wc):
        return MEN.index(wc) if wc in MEN else WOM.index(wc) if wc in WOM else None
    lastwc = {}; mv = defaultdict(list)
    for x in F:
        i = widx(x["wc"]); info = {}
        for s in "ab":
            p = lastwc.get(x[s]["slug"])
            info[s] = None if (p is None or i is None) else ("up" if i > p else "down" if i < p else "same")
        if x["kind"] == "win" and x["date"] >= "2010-01-01":
            for s, o in (("a", "b"), ("b", "a")):
                if info[s] in ("up", "down") and info[o] == "same":
                    mv["First fight after moving %s a weight class" % info[s]].append((x, s))
        if i is not None:
            for s in "ab":
                lastwc[x[s]["slug"]] = i
    out["situational"] += [dict(study(v), label=k) for k, v in sorted(mv.items())]
    late = []
    byev = defaultdict(list)
    for x in dec:
        od = x["f"].get("odds") or {}
        if od.get("open") and od.get("start"):
            ld = (dt.datetime.fromisoformat(od["start"].replace("Z", "")) - dt.datetime.fromisoformat(od["open"]["t"].replace("Z", ""))).total_seconds() / 86400
            byev[x["e"]["slug"]].append((x, ld))
    norm_ = []
    for rows in byev.values():
        med = sorted(l for _, l in rows)[len(rows) // 2]
        for x, l in rows:
            (late if (l <= 6 and med - l >= 5) else norm_).append(x)
    def favstudy(rows, lab):
        s = study([(x, "a" if x["cl"]["p"] >= 0.5 else "b") for x in rows if x["cl"]]); s["label"] = lab
        s["fin"] = rnd(sum(1 for x in rows if x["m"] != "DEC") / len(rows)) if rows else None; return s
    out["late"] = [favstudy(late, "Line first posted 6 days or fewer before the fight, 5+ days after the rest of the card"), favstudy(norm_, "All other fights")]

    # ================= venue log (Las Vegas since the APEX opened) + altitude
    with open(REPO / "data" / "venues_vegas.csv", "w", newline="") as fh:
        w_ = csv.writer(fh); w_.writerow(["date", "event", "venue", "source"])
        for e in events:
            if (e.get("location") or "").startswith("Las Vegas") and e["date"] >= "2020-05-30":
                m_ = re.match(r"UFC (\d+)", e["name"])
                v = VEGAS_NOT_APEX.get(e["date"]) or ("UFC/Meta APEX" if is_apex(e["name"], e["location"], e["date"]) else ("Sphere" if m_ and m_.group(1) == "306" else "T-Mobile Arena"))
                w_.writerow([e["date"], e["name"], v, "Wikipedia: List of UFC events (2026-11-10)"])
    alt_rows = [x for x in dec if x["date"] >= "2015-01-01" and any(c in (x["e"].get("location") or "") for c in ALTITUDE)]
    def pace(rows):
        q = [x for x in rows if r3done(x)]
        a1 = sum(x["rr"][x[s]["name"]][1]["sa"] for x in q for s in "ab"); a3 = sum(x["rr"][x[s]["name"]][3]["sa"] for x in q for s in "ab")
        return {"n": len(q), "kept": rnd(a3 / a1) if a1 else None}
    altset = {id(x) for x in alt_rows}
    rest = [x for x in dec if x["date"] >= "2015-01-01" and id(x) not in altset]
    def venue_row(rows, lab):
        a = agg(rows); ex = [bw[x["wc"]]["fin"] for x in rows if bw.get(x["wc"])]
        fav = study([(x, "a" if x["cl"]["p"] >= 0.5 else "b") for x in rows if x["cl"]])
        return {"label": lab, "n": a["n"], "fin": a["fin"], "exp": rnd(sum(ex) / len(ex)), "ko": a["ko"], "sub": a["sub"], "pace": pace(rows), "ev": len({x["e"]["slug"] for x in rows}), "fav": fav}
    out["altitude"] = [venue_row(alt_rows, "Altitude (Mexico City, Denver, Salt Lake City)"), venue_row(rest, "Everywhere else")]
    since20 = [x for x in dec if x["date"] >= "2020-05-30"]
    out["octagon"]["fav"] = [venue_row([x for x in since20 if x["apex"]], "APEX"), venue_row([x for x in since20 if not x["apex"]], "Full-size cage")]

    # ================= live-betting baselines: what round 1 tells you
    live = []
    past1 = [x for x in dec if x["rr"] and x["rnd"] and (x["rnd"] >= 2) and all(1 in x["rr"].get(x[s]["name"], {}) for s in "ab") and x["date"] >= "2015-01-01"]
    def lrow(lab, pick):
        rows = [(x, s) for x in past1 for s in "ab" if pick(x, s, "b" if s == "a" else "a")]
        if not rows:
            return
        w_ = sum(1 for x, s in rows if x["w"] == s)
        o = [(x, s) for x, s in rows if x["cl"]]
        pre = sum((x["cl"]["p"] if s == "a" else 1 - x["cl"]["p"]) for x, s in o) / len(o) if o else None
        ow = sum(1 for x, s in o if x["w"] == s) / len(o) if o else None
        dog = [(x, s) for x, s in o if (x["cl"]["p"] if s == "a" else 1 - x["cl"]["p"]) < 0.5]
        live.append({"label": lab, "n": len(rows), "wp": rnd(w_ / len(rows)), "on": len(o), "pre": rnd(pre), "owp": rnd(ow),
                     "dog_n": len(dog), "dog_wp": rnd(sum(1 for x, s in dog if x["w"] == s) / len(dog)) if dog else None,
                     "dog_pre": rnd(sum((x["cl"]["p"] if s == "a" else 1 - x["cl"]["p"]) for x, s in dog) / len(dog)) if dog else None})
    R1 = lambda x, s: x["rr"][x[s]["name"]][1]
    lrow("Out-landed the opponent in round 1 (any margin)", lambda x, s, o: R1(x, s)["sl"] > R1(x, o)["sl"])
    lrow("Out-landed by 10+ in round 1", lambda x, s, o: R1(x, s)["sl"] - R1(x, o)["sl"] >= 10)
    lrow("Out-landed by 20+ in round 1", lambda x, s, o: R1(x, s)["sl"] - R1(x, o)["sl"] >= 20)
    lrow("Scored a knockdown in round 1 (fight continued)", lambda x, s, o: R1(x, s).get("kd", 0) > 0 and R1(x, o).get("kd", 0) == 0)
    lrow("Landed a takedown and 2+ min of control in round 1", lambda x, s, o: R1(x, s)["tl"] > 0 and R1(x, s)["ctrl"] >= 120)
    lrow("3+ min of control in round 1", lambda x, s, o: R1(x, s)["ctrl"] >= 180)
    lrow("Out-landed in round 1 but gave up 2+ min of control", lambda x, s, o: R1(x, s)["sl"] > R1(x, o)["sl"] and R1(x, o)["ctrl"] >= 120)
    out["live"] = {"rows": live, "n": len(past1),
                   "dist2": rnd(sum(1 for x in past1 if x["m"] == "DEC") / len(past1)),
                   "dist3": rnd(sum(1 for x in past1 if x["m"] == "DEC" and x["rnd"] >= 3) / max(1, sum(1 for x in past1 if x["rnd"] >= 3))),
                   "dist2_5": rnd(sum(1 for x in past1 if x["m"] == "DEC" and x["sched"] == 5) / max(1, sum(1 for x in past1 if x["sched"] == 5)))}
    # two-round state in three-round fights
    two = [x for x in dec if x["sched"] == 3 and r3done(x) and x["date"] >= "2015-01-01"]
    def rw(x, s, o, k):
        a_, b_ = x["rr"][x[s]["name"]][k], x["rr"][x[o]["name"]][k]
        return a_["sl"] > b_["sl"]
    up2 = [(x, s) for x in two for s, o in (("a", "b"), ("b", "a")) if rw(x, s, o, 1) and rw(x, s, o, 2)]
    lost3 = [(x, s) for x, s in up2 if not rw(x, s, "b" if s == "a" else "a", 3)]
    split = [(x, s) for x in two for s, o in (("a", "b"), ("b", "a")) if rw(x, s, o, 3) and (rw(x, s, o, 1) != rw(x, s, o, 2))]
    out["live"]["states"] = [{"label": "Out-landed the opponent in rounds 1 and 2, fight went the distance", "n": len(up2), "wp": rnd(sum(1 for x, s in up2 if x["w"] == s) / len(up2))},
                             {"label": "…and then was out-landed in round 3", "n": len(lost3), "wp": rnd(sum(1 for x, s in lost3 if x["w"] == s) / len(lost3))},
                             {"label": "Rounds 1 and 2 split on strikes, out-landed the opponent in round 3", "n": len(split), "wp": rnd(sum(1 for x, s in split if x["w"] == s) / len(split))}]

    # ================= more spots: streaks, experience, rematches
    st2 = defaultdict(list); H = defaultdict(list); met = {}
    for x in F:
        info = {}
        for s in "ab":
            h = H[x[s]["slug"]]; ws = ls = 0
            for r_ in reversed(h):
                if r_ == "W" and ls == 0: ws += 1
                elif r_ == "L" and ws == 0: ls += 1
                else: break
            info[s] = {"ws": ws, "ls": ls, "n": len(h)}
        key = frozenset([x["a"]["slug"], x["b"]["slug"]])
        if x["kind"] == "win" and x["date"] >= "2010-01-01":
            for s, o in (("a", "b"), ("b", "a")):
                i, j = info[s], info[o]
                if i["ws"] >= 3 and j["ws"] < 3: st2["On a 3+ fight UFC win streak (opponent is not)"].append((x, s))
                if i["ws"] >= 5: st2["On a 5+ fight UFC win streak"].append((x, s))
                if i["ls"] >= 2 and j["ls"] < 2: st2["On a 2+ fight UFC losing streak (opponent is not)"].append((x, s))
                if i["n"] >= 10 and 1 <= j["n"] <= 3: st2["10+ UFC fights vs. an opponent with 1–3"].append((x, s))
                if key in met and met[key] == x[s]["slug"]: st2["Rematch: won the previous meeting"].append((x, s))
        if x["kind"] == "win":
            met[key] = x[x["w"]]["slug"]
            H[x["a"]["slug"]].append("W" if x["w"] == "a" else "L"); H[x["b"]["slug"]].append("W" if x["w"] == "b" else "L")
        else:
            H[x["a"]["slug"]].append("D"); H[x["b"]["slug"]].append("D")
    out["situational"] += [dict(study(v), label=k) for k, v in st2.items()]
    # chin and cardio as pre-fight spots (walk-forward)
    st3 = defaultdict(list); KO = defaultdict(int); SW = defaultdict(lambda: [0.0, 0])
    for x in F:
        if x["kind"] == "win" and x["date"] >= "2010-01-01":
            for s_, o_ in (("a", "b"), ("b", "a")):
                if KO[x[s_]["slug"]] >= 2 and KO[x[o_]["slug"]] == 0: st3["2+ prior UFC KO/TKO losses vs. an opponent with none"].append((x, s_))
                if KO[x[s_]["slug"]] >= 3: st3["3+ prior UFC KO/TKO losses"].append((x, s_))
                a_, b_ = SW[x[s_]["slug"]], SW[x[o_]["slug"]]
                if a_[1] >= 3 and b_[1] >= 3 and a_[0] / a_[1] - b_[0] / b_[1] >= 5:
                    st3["Better late-round history (R1→R3 swing 5+ ahead of opponent)"].append((x, s_))
                    if x["sched"] == 5: st3["…same, in five-round fights"].append((x, s_))
        if x["kind"] == "win" and x["m"] == "KO":
            KO[x["b" if x["w"] == "a" else "a"]["slug"]] += 1
        if r3done(x):
            for s_, o_ in (("a", "b"), ("b", "a")):
                v_ = cvec(x, s_, o_); SW[x[s_]["slug"]][0] += v_["d3"] - v_["d1"]; SW[x[s_]["slug"]][1] += 1
    out["situational"] += [dict(study(v), label=k) for k, v in st3.items()]
    for k_, v_ in st3.items():
        if k_.startswith("2+ prior"):
            out["chin"] = {"n": len(v_), "ko_loss": rnd(sum(1 for x, s_ in v_ if x["m"] == "KO" and x["w"] != s_) / len(v_)),
                           "base": rnd(sum(1 for x in dec if x["m"] == "KO" and x["date"] >= "2010-01-01") / 2 / sum(1 for x in dec if x["date"] >= "2010-01-01"))}

    try:
        import labs_rounds
        out["rounds"] = labs_rounds.build(F, CACHE, rnd, D)
    except Exception as ex:
        import traceback; traceback.print_exc(); print("round-level judging skipped:", ex)

    json.dump(out, open(D / "labs.json", "w"), separators=(",", ":"))
    print("altitude", out["altitude"]); print("octfav", [(r["label"], r["n"], r["fin"], r["exp"], r["fav"]["owp"], r["fav"]["imp"], r["fav"]["roi"], r["pace"]) for r in out["octagon"]["fav"]])
    print("live", out["live"]); print("spots2", [(s["label"], s["n"], s["wp"], s["on"], s["owp"], s["imp"], s["roi"]) for s in out["situational"][-5:]])
    print("cardio", len(out["cardio"]["rows"]), out["cardio"]["league"], "rel", out["cardio"]["rel_sw"], out["cardio"]["rel_out"], "wf", out["cardio"]["wf"], "base", out["cardio"]["base_lost1_won3"])
    print("refs", len(out["refs"]), out["refs"][:2]); print("judges", len(JR), out["judges"]["pool"], "orient", out["judges"]["orient"], out["judges"]["rows"][:2])
    print("late", out["late"]); print("moves", out["situational"][-2:])

    # ---- compact rows for the query tool (fights with a closing line)
    q = []
    for x in dec:
        if not x["cl"] or x["cl"].get("ma") is None or x["cl"].get("mb") is None:
            continue
        fs = "a" if x["cl"]["p"] >= 0.5 else "b"; ds = "b" if fs == "a" else "a"
        pf = x["cl"]["p"] if fs == "a" else 1 - x["cl"]["p"]
        po = None
        if x["op"]:
            po = x["op"]["p"] if fs == "a" else 1 - x["op"]["p"]
        q.append([x["date"], x["e"]["slug"], x["f"]["n"], x[fs]["name"], x[ds]["name"], x["wc"], x["sched"], x["pos"], rnd(pf, 4), rnd(po, 4),
                  x["cl"]["m" + fs], x["cl"]["m" + ds], 1 if x["w"] == fs else 0, x["m"], 1 if x["apex"] else 0, x["f"]["result"].get("round")])
    json.dump({"cols": ["d", "es", "n", "fav", "dog", "wc", "sched", "pos", "pf", "po", "mf", "md", "fw", "m", "apex", "r"], "rows": q}, open(D / "labs_fights.json", "w"), separators=(",", ":"))
    print("labs:", len(F), "fights,", len(q), "query rows,", len(mets), "fighters,", len(dfs), "decisions; scoring acc", out["scoring"]["acc"])
    print([(c["label"], c["head_eq"]) for c in out["scoring"]["coef"]])
    print("apex", out["octagon"]["all"]); print("age", [(s["label"], s["n"], s["wp"], s["roi"]) for s in out["age_gap"]])
    print("reach", [(s["label"], s["n"], s["wp"], s["roi"]) for s in out["reach_gap"]]); print("ups", out["upsets"][:3])
    print("sit", [(s["label"], s["n"], s["wp"], s["on"], s["imp"], s["roi"]) for s in out["situational"]])


if __name__ == "__main__":
    main()
