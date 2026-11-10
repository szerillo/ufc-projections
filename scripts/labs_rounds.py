"""Round-level judging study. Needs a private pull of round-by-round scorecards saved at
.form_cache/mmadecisions.json (not committed: the compilation belongs to MMADecisions.com).
Only derived aggregates are written to the site."""
import json, re, unicodedata
from collections import defaultdict
import numpy as np

FE = [("head", "Head strike"), ("body", "Body strike"), ("leg", "Leg strike"), ("kd", "Knockdown"), ("tl", "Takedown"),
      ("ctrlm", "Minute of control"), ("sub", "Submission attempt"), ("nonsig", "Non-significant strike")]
COUNTRY = {"USA": "USA", "England": "United Kingdom", "Scotland": "United Kingdom", "Wales": "United Kingdom", "UAE": "United Arab Emirates"}


def nz(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s.replace("-", " ")).split()


def fit(X, y):
    X2 = np.vstack([X, -X]); y2 = np.concatenate([y, 1 - y]); b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-np.clip(X2 @ b, -30, 30))); W = p * (1 - p) + 1e-9
        b += np.linalg.solve(X2.T @ (X2 * W[:, None]) + 1e-4 * np.eye(len(b)), X2.T @ (y2 - p))
    return b


def build(F, cache, rnd, D=None):
    raw = json.load(open(cache / "mmadecisions.json"))
    pool = [x for x in F if x["date"] >= "2015-12-01" and x["rr"]]
    def nzd(s):
        s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
        return set(re.sub(r"[^a-z0-9 ]", " ", s.replace("-", " ")).split())
    used = set()
    def find(d):
        if not d["j"]:
            return None
        a, b = nz(d["j"][0][1]), nz(d["j"][0][2])
        evt = nzd(d["ev"]); best = None
        for x in pool:
            if id(x) in used:
                continue
            if d.get("y"):
                if x["yr"] != d["y"]:
                    continue
            elif x["date"] < "2023-12-15":
                continue
            na, nb = nz(x["a"]["name"]), nz(x["b"]["name"])
            for flip, (p, q) in enumerate(((na, nb), (nb, na))):
                if a and b and all(w in p for w in a) and all(w in q for w in b):
                    sc = len(evt & nzd(x["e"]["name"]))
                    if best is None or sc > best[0]:
                        best = (sc, x, bool(flip))
        if best:
            used.add(id(best[1]))
        return best
    rows = []; fights = []; unmatched = 0
    J = defaultdict(lambda: defaultdict(float)); P = defaultdict(float)
    for d in raw:
        m = find(d)
        if not m:
            unmatched += 1; continue
        _, x, flip = m
        A, B = ("b", "a") if flip else ("a", "b")       # A = scorecard's first column
        ra, rb = x["rr"].get(x[A]["name"], {}), x["rr"].get(x[B]["name"], {})
        cards = [(j[0], [tuple(int(v) for v in s.split("-")) for s in j[3].split()]) for j in d["j"]]
        nr = min(len(c[1]) for c in cards)
        tot = [(sum(s[0] for s in c[1]), sum(s[1] for s in c[1])) for c in cards]
        wa = sum(1 for t in tot if t[0] > t[1]); wb = sum(1 for t in tot if t[1] > t[0])
        winner = A if wa > wb else B if wb > wa else None
        med = d.get("m") or {}
        sa_, sb_ = nz(d["j"][0][1])[-1:], nz(d["j"][0][2])[-1:]
        ma = sum(v for k, v in med.items() if nz(k.split(" ", 1)[1])[-1:] == sa_); mb = sum(v for k, v in med.items() if nz(k.split(" ", 1)[1])[-1:] == sb_)
        born = re.search(r"TALE OF THE TAPE \S+ \S+ (.*?) BORN (.*?) \d+ AGE", d.get("tape") or "")
        fights.append({"x": x, "A": A, "B": B, "winner": winner, "ma": ma, "mb": mb, "mn": sum(med.values()), "born": born.groups() if born else None, "split": 0 < min(wa, wb), "tot": tot, "cards": cards, "id": d.get("id")})
        for r in range(1, nr + 1):
            if r not in ra or r not in rb:
                continue
            f = {k: ra[r].get(k, 0) - rb[r].get(k, 0) for k in ("head", "body", "leg", "kd", "tl", "sub", "sl", "tot", "ctrl")}
            f["ctrlm"] = f["ctrl"] / 60; f["nonsig"] = f["tot"] - f["sl"]
            sc = [c[1][r - 1] for c in cards]
            va = sum(1 for s in sc if s[0] > s[1]); vb = sum(1 for s in sc if s[1] > s[0])
            if va == vb:
                continue
            maj = 1 if va > vb else 0
            rows.append({"f": f, "y": maj, "unan": min(va, vb) == 0, "r": r, "nr": nr, "x": x, "A": A, "B": B,
                         "sc": [(c[0].title(), s) for c, s in zip(cards, sc)], "st": (ra[r], rb[r])})
            clash = None
            if f["sl"] > 0 and f["ctrl"] <= -60: clash = 0      # A out-landed, B controlled -> control side is B (y=0)
            if f["sl"] < 0 and f["ctrl"] >= 60: clash = 1
            for (nm, _), s in zip(cards, sc):
                j = J[nm.title()]; j["n"] += 1; P["n"] += 1
                side = 1 if s[0] > s[1] else 0 if s[1] > s[0] else None
                wide = abs(s[0] - s[1]) >= 2
                j["wide"] += wide; P["wide"] += wide
                if side is None:
                    continue
                j["dis"] += side != maj; P["dis"] += side != maj
                if clash is not None:
                    j["cl"] += 1; j["clc"] += side == clash; P["cl"] += 1; P["clc"] += side == clash
    X = np.array([[r["f"][k] for k, _ in FE] for r in rows], float); y = np.array([r["y"] for r in rows], float)
    b = fit(X, y); p = 1 / (1 + np.exp(-X @ b)); pw = np.where(y == 1, p, 1 - p)
    un = np.array([r["unan"] for r in rows])
    # round-by-round expected decisions: fight luck = actual - P(win) from simulating rounds independently
    byf = defaultdict(list)
    for r, pp in zip(rows, p):
        byf[id(r["x"])].append(pp)
    def pwin(ps):   # P(A wins more rounds than B), 10-9 rounds only
        dist = {0: 1.0}
        for q in ps:
            nd = defaultdict(float)
            for k, v in dist.items():
                nd[k + 1] += v * q; nd[k - 1] += v * (1 - q)
            dist = nd
        return sum(v for k, v in dist.items() if k > 0) + 0.5 * dist.get(0, 0)
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()).strip("-")
    perfight = defaultdict(dict); jlog = defaultdict(list)
    rp = defaultdict(dict)
    for r, pp in zip(rows, p):
        rp[id(r["x"])][r["r"]] = float(pp)
    for ft in fights:
        x = ft["x"]; flip = ft["A"] == "b"
        cards = []
        for nm, scs in ft["cards"]:
            sc = [(s[1], s[0]) if flip else s for s in scs]   # orient to our fighter a - fighter b
            ta, tb = sum(s[0] for s in sc), sum(s[1] for s in sc)
            side = "a" if ta > tb else "b" if tb > ta else None
            cards.append([nm.title(), " ".join("%d-%d" % s for s in sc), ta, tb])
            jlog[nm.title()].append([x["date"], x["e"]["slug"], x["f"]["n"], x["a"]["name"], x["b"]["name"], "%d-%d" % (ta, tb),
                                     x["w"], 1 if (side and x["w"] and side != x["w"]) else 0, x["wc"]])
        pr = rp.get(id(x), {})
        probs = [rnd((1 - pr[k]) if flip else pr[k], 2) if k in pr else None for k in range(1, len(ft["cards"][0][1]) + 1)]
        born = None
        if ft["born"]:
            born = [ft["born"][1], ft["born"][0]] if flip else list(ft["born"])
        perfight[x["e"]["slug"]][x["f"]["n"]] = {"j": cards, "med": [ft["mb"], ft["ma"]] if flip else [ft["ma"], ft["mb"]], "mn": ft["mn"], "p": probs, "born": born, "id": ft["id"]}
    if D is not None:
        for es, fs in perfight.items():
            fp = D / "events" / (es + ".json")
            ev = json.load(open(fp))
            for f in ev["fights"]:
                if f["n"] in fs:
                    f["cards"] = fs[f["n"]]
            json.dump(ev, open(fp, "w"), separators=(",", ":"))
        json.dump({slug(k): {"nm": k, "rows": sorted(v, key=lambda r: r[0], reverse=True)} for k, v in jlog.items() if len(v) >= 5}, open(D / "judges.json", "w"), separators=(",", ":"))
    against = []; home = defaultdict(lambda: [0, 0.0, 0]); media_rob = []
    for ft in fights:
        x = ft["x"]; ps = byf.get(id(x))
        if not ps or ft["winner"] is None:
            continue
        pa = pwin(ps); pw_ = pa if ft["winner"] == ft["A"] else 1 - pa
        win, lose = x[ft["winner"]], x[ft["B"] if ft["winner"] == ft["A"] else ft["A"]]
        rec = {"d": x["date"], "es": x["e"]["slug"], "n": x["f"]["n"], "w": win["name"], "l": lose["name"], "p": rnd(pw_), "split": ft["split"],
               "med": [ft["ma"], ft["mb"]] if ft["winner"] == ft["A"] else [ft["mb"], ft["ma"]]}
        against.append(rec)
        if ft["mn"] >= 5 and rec["med"][1] > rec["med"][0]:
            media_rob.append(rec)
        if ft["born"]:
            loc = (x["e"].get("location") or "").split(",")[-1].strip()
            for side, bn in ((ft["A"], ft["born"][0]), (ft["B"], ft["born"][1])):
                c = bn.split(",")[-1].strip(); c = COUNTRY.get(c, c)
                oth = ft["born"][1] if side == ft["A"] else ft["born"][0]
                oc = oth.split(",")[-1].strip(); oc = COUNTRY.get(oc, oc)
                if c == loc and oc != loc:
                    k = "USA" if loc == "USA" else "Outside the USA"
                    for kk in (k, "All"):
                        h = home[kk]; h[0] += 1; h[1] += pa if side == ft["A"] else 1 - pa; h[2] += ft["winner"] == side
    # ---------- outliers
    def rrec(r, pp, extra=None):
        x = r["x"]; a_, b_ = r["st"]; got = r["A"] if r["y"] == 1 else r["B"]; oth = r["B"] if r["y"] == 1 else r["A"]
        g, o = (a_, b_) if r["y"] == 1 else (b_, a_)
        mmss_ = lambda s: "%d:%02d" % (s // 60, s % 60)
        d = {"d": x["date"], "es": x["e"]["slug"], "n": x["f"]["n"], "r": r["r"], "w": x[got]["name"], "l": x[oth]["name"], "p": rnd(pp if r["y"] == 1 else 1 - pp),
             "st": "sig. strikes %d–%d · control %s–%s · takedowns %d–%d%s" % (g["sl"], o["sl"], mmss_(g["ctrl"]), mmss_(o["ctrl"]), g["tl"], o["tl"], (" · knockdowns %d–%d" % (g.get("kd", 0), o.get("kd", 0))) if (g.get("kd", 0) or o.get("kd", 0)) else "")}
        if extra:
            d.update(extra)
        return d
    out_rounds = sorted([rrec(r, pp) for r, pp in zip(rows, p) if r["unan"] and (pp if r["y"] == 1 else 1 - pp) < 0.2], key=lambda d: d["p"])[:30]
    lone = []; lone8 = []; jout = defaultdict(lambda: [0, 0])
    for r, pp in zip(rows, p):
        sides = [(nm, 1 if s[0] > s[1] else 0 if s[1] > s[0] else None, abs(s[0] - s[1]) >= 2, s) for nm, s in r["sc"]]
        for nm, sd, wide, s in sides:
            if sd is None:
                continue
            others = [o for o in sides if o[0] != nm]
            pj = pp if sd == 1 else 1 - pp
            if sd != r["y"] and all(o[1] == r["y"] for o in others):
                jout[nm][0] += 1
                if pj < 0.25:
                    jout[nm][1] += 1
                    x = r["x"]; mine = r["A"] if sd == 1 else r["B"]
                    lone.append(rrec(r, pp, {"j": nm, "js": slug(nm), "for": x[mine]["name"], "pj": rnd(pj)}))
            if wide and not any(o[2] for o in others):
                x = r["x"]; mine = r["A"] if sd == 1 else r["B"]
                lone8.append(rrec(r, pp, {"j": nm, "js": slug(nm), "for": x[mine]["name"], "pj": rnd(pj), "sc": "%d-%d" % (max(s), min(s)), "agree": all(o[1] == sd for o in others)}))
    lone.sort(key=lambda d: d["pj"]); lone8.sort(key=lambda d: d["d"], reverse=True)
    disputes = []
    for ft in fights:
        x = ft["x"]; flip = ft["A"] == "b"
        mar = [(t_[1] - t_[0]) if flip else (t_[0] - t_[1]) for t_ in ft["tot"]]
        if max(mar) > 0 and min(mar) < 0:
            disputes.append({"d": x["date"], "es": x["e"]["slug"], "n": x["f"]["n"], "a": x["a"]["name"], "b": x["b"]["name"], "w": x["w"], "spread": max(mar) - min(mar),
                             "cards": [[c[0].title(), ("%d-%d" % ((t_[1], t_[0]) if flip else t_))] for c, t_ in zip(ft["cards"], ft["tot"])],
                             "med": [ft["mb"], ft["ma"]] if flip else [ft["ma"], ft["mb"]]})
    disputes.sort(key=lambda d: (-d["spread"], d["d"]), reverse=False)
    # ---------- per-judge criteria: each judge's own weights, shrunk toward the pool
    jrows = defaultdict(list)
    for i, r in enumerate(rows):
        for nm, s in r["sc"]:
            if s[0] != s[1]:
                jrows[nm].append((i, 1.0 if s[0] > s[1] else 0.0))
    crit = []
    for nm, lst in jrows.items():
        if len(lst) < 450:
            continue
        Xi = X[[i for i, _ in lst]]; yi = np.array([v for _, v in lst])
        X2 = np.vstack([Xi, -Xi]); y2 = np.concatenate([yi, 1 - yi]); bj = b.copy(); lam = 6.0 / (b ** 2)
        for _ in range(40):
            pq = 1 / (1 + np.exp(-np.clip(X2 @ bj, -30, 30))); W = pq * (1 - pq) + 1e-9
            bj += np.linalg.solve(X2.T @ (X2 * W[:, None]) + np.diag(lam), X2.T @ (y2 - pq) - lam * (bj - b))
        pj_ = 1 / (1 + np.exp(-Xi @ bj))
        crit.append({"nm": nm, "s": slug(nm), "n": len(lst), "m": {k: rnd(float(bj[i] / b[i]), 2) for i, (k, _) in enumerate(FE)},
                     "acc": rnd(float(((pj_ > .5) == (yi == 1)).mean())), "lone": jout[nm][0], "lone_bad": jout[nm][1]})
    crit.sort(key=lambda c: -c["n"])
    # ---------- calibration
    conf = np.maximum(p, 1 - p); hit = (p > .5) == (y == 1); cal = []
    for lo, hi in ((.5, .6), (.6, .7), (.7, .8), (.8, .9), (.9, .97), (.97, 1.01)):
        mk = (conf >= lo) & (conf < hi)
        if mk.sum():
            cal.append({"lab": "%d–%d%%" % (lo * 100, min(100, hi * 100)), "n": int(mk.sum()), "pred": rnd(float(conf[mk].mean())), "act": rnd(float(hit[mk].mean())), "split": rnd(float((~un[mk]).mean()))})
    extra = {"out_rounds": out_rounds, "lone": lone[:30], "lone8": lone8[:30], "lone8_n": len(lone8), "disputes": disputes[:30], "disputes_n": len(disputes), "crit": crit, "cal": cal,
             "raw": [{"label": lab, "b": rnd(float(c), 4)} for (_, lab), c in zip(FE, b)]}
    JR = [{"nm": n, "s": slug(n), "n": int(j["n"]), "dis": rnd(j["dis"] / j["n"]), "wide": rnd(j["wide"] / j["n"]), "cl": int(j["cl"]), "ctrl": rnd(j["clc"] / j["cl"]) if j["cl"] >= 12 else None}
          for n, j in J.items() if j["n"] >= 60]
    byr = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["nr"] == 3:
            byr[r["r"]][0] += 1; byr[r["r"]][1] += not r["unan"]
    return {"n_fights": len(fights), "n_rounds": len(rows), "unmatched": unmatched, "acc": rnd(float((pw > .5).mean())), "acc_unan": rnd(float((pw[un] > .5).mean())), "acc_split": rnd(float((pw[~un] > .5).mean())),
            "split_share": rnd(float((~un).mean())), "coef": [{"label": lab, "head_eq": rnd(float(c / b[0]), 2)} for (_, lab), c in zip(FE, b)],
            "pool": {"n": int(P["n"]), "dis": rnd(P["dis"] / P["n"]), "wide": rnd(P["wide"] / P["n"]), "ctrl": rnd(P["clc"] / P["cl"]) if P["cl"] else None, "cl": int(P["cl"])},
            "judges": sorted(JR, key=lambda r: -r["n"]), "by_round": [{"r": k, "n": v[0], "split": rnd(v[1] / v[0])} for k, v in sorted(byr.items())],
            "against": sorted(against, key=lambda r: r["p"])[:25], "media": sorted(media_rob, key=lambda r: r["med"][0] - r["med"][1])[:25],
            "media_n": sum(1 for f in fights if f["mn"] >= 5), "media_dis": len(media_rob),
            **extra,
            "home": [{"label": k, "n": v[0], "exp": rnd(v[1] / v[0]), "act": rnd(v[2] / v[0])} for k, v in home.items() if v[0] >= 20]}
