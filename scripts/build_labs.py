#!/usr/bin/env python3
"""Labs data: reads the built Fight Form JSON (form/data) plus the cached UFCStats round stats and writes
form/data/labs.json (studies) and form/data/labs_fights.json (compact rows for the query tool).
Run after build_form.py:  python3 scripts/build_labs.py"""
import csv, json, re, glob, math, datetime as dt
from collections import defaultdict
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[1]
D = REPO / "form" / "data"
CACHE = REPO / ".form_cache"
DIVS = ["Strawweight", "Flyweight", "Bantamweight", "Featherweight", "Lightweight", "Welterweight", "Middleweight",
        "Light Heavyweight", "Heavyweight", "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight"]
APEX_PPV = {250, 252, 255, 256, 258, 259, 260}


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
                      "ra": (st or {}).get(f["a"]["name"]), "rb": (st or {}).get(f["b"]["name"])})
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

    json.dump(out, open(D / "labs.json", "w"), separators=(",", ":"))

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
