#!/usr/bin/env python3
"""
MMA Fight Form — figures, baseline model and backtests.

  * Form Figure: one number per performance (result + in-fight dominance, adjusted
    for the opponent's own figure rating coming in).
  * Form Line: a stats-only win probability, and a goes-the-distance probability,
    both fit walk-forward (a fight's number only uses fights from earlier years).
  * Research: closing-line calibration, price-band ROI, steam, situational angles,
    totals, and the Form Line graded against the close.

Everything is numpy only. Called from build_form.py; `python3 scripts/form_model.py`
prints the research summary.
"""
from __future__ import annotations
import datetime as dt, math, re
from collections import defaultdict
import numpy as np

OPPC = 0.7          # opponent adjustment: points per point of opponent figure rating above 50
import os
FIG_PRIOR = float(os.environ.get("FIG_PRIOR", 2.5))
PRIOR_MIN = 20.0    # minutes of league-average performance blended into every rate
LEAGUE = dict(slpm=3.9, td15=1.4, ctrl=0.16, kd15=0.25, sub15=0.6)
FEATS = ["elo", "fig", "fig3", "slpm", "sapm", "td15", "otd15", "ctrl", "octrl", "kd15", "okd15", "sub15", "acc", "def",
         "tdacc", "tdd", "w3", "age", "reach", "ht", "lay", "offko", "n", "streak", "kol", "finr", "south", "age35", "debut"]
GFEATS = ["base", "dec_a", "dec_b", "fin_a", "fin_b", "kd", "sub", "pace", "five", "women", "elo_gap"]


def norm(name):
    import unicodedata
    s = unicodedata.normalize("NFD", name or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s.replace("-", " ").replace("'", ""))
    return re.sub(r"\s+", " ", s).strip()


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def fit_logit(X, y, l2=1.0, iters=50, free=0):
    """Ridge logistic by Newton steps. The first `free` columns are not penalised (intercepts)."""
    n, d = X.shape
    b = np.zeros(d)
    pen = np.ones(d) * l2
    pen[:free] = 1e-6
    for _ in range(iters):
        p = sigmoid(X @ b)
        W = p * (1 - p) + 1e-9
        g = X.T @ (p - y) + pen * b
        H = (X * W[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(H, g)
        b -= step
        if np.abs(step).max() < 1e-7:
            break
    return b


def inches(ht):
    m = re.match(r"(\d+)'(\d+)", ht or "")
    return int(m.group(1)) * 12 + int(m.group(2)) if m else None


# ------------------------------------------------------------------ dominance + figure
def _dom_row(a, b, secs):
    m = max(secs / 60, 1)
    tot = a["sl"] + b["sl"]
    return [(a["sl"] - b["sl"]) / m, (a["sl"] - b["sl"]) / max(tot, 10), a["kd"] - b["kd"], (a["tl"] - b["tl"]) / m * 5,
            (a["ctrl"] - b["ctrl"]) / max(secs, 1), a["sub"] - b["sub"], (a["head"] - b["head"]) / m]


def fit_dominance(fights):
    X, y = [], []
    for f in fights:
        if f["kind"] != "win" or not f["sa"] or not f["sb"] or not f["secs"]:
            continue
        r = _dom_row(f["sa"], f["sb"], f["secs"])
        s = 1 if f["winner"] == "a" else 0
        X.append(r); y.append(s); X.append([-v for v in r]); y.append(1 - s)
    X, y = np.array(X), np.array(y)
    sd = X.std(0)
    return fit_logit(X / sd, y, l2=1.0), sd


def result_score(f, side):
    if f["kind"] == "draw":
        return 0.5
    if f["kind"] == "nc":
        return None
    won = f["winner"] == side
    m = f["method"]
    if "KO" in m or "Sub" in m:
        early = 1 - min(1, (f["secs"] or 900) / (300 * (f["sched"] or 3)))
        v = 0.85 + 0.15 * early
    elif "Split" in m or "Majority" in m:
        v = 0.58
    else:
        v = 0.72
    return v if won else 1 - v


# ------------------------------------------------------------------ as-of summaries
def summarize(h, date):
    secs = sum(x["secs"] for x in h)
    m = secs / 60
    PM = PRIOR_MIN

    def rate(k, lg):
        return (sum(x[k] for x in h) + lg * PM) / (m + PM)

    d = {"n": len(h), "min": m}
    d["slpm"] = rate("sl", LEAGUE["slpm"]); d["sapm"] = rate("osl", LEAGUE["slpm"])
    d["td15"] = rate("tl", LEAGUE["td15"] / 15) * 15; d["otd15"] = rate("otl", LEAGUE["td15"] / 15) * 15
    d["ctrl"] = (sum(x["ctrl"] for x in h) + LEAGUE["ctrl"] * PM * 60) / (secs + PM * 60)
    d["octrl"] = (sum(x["octrl"] for x in h) + LEAGUE["ctrl"] * PM * 60) / (secs + PM * 60)
    d["kd15"] = rate("kd", LEAGUE["kd15"] / 15) * 15; d["okd15"] = rate("okd", LEAGUE["kd15"] / 15) * 15
    d["sub15"] = rate("sub", LEAGUE["sub15"] / 15) * 15
    sa = sum(x["sa"] for x in h); osa = sum(x["osa"] for x in h); ta = sum(x["ta"] for x in h); ota = sum(x["ota"] for x in h)
    d["acc"] = (sum(x["sl"] for x in h) + .45 * 40) / (sa + 40); d["def"] = 1 - (sum(x["osl"] for x in h) + .45 * 40) / (osa + 40)
    d["tdacc"] = (sum(x["tl"] for x in h) + .38 * 5) / (ta + 5); d["tdd"] = 1 - (sum(x["otl"] for x in h) + .38 * 5) / (ota + 5)
    last = h[-3:]
    d["w3"] = (sum(x["won"] for x in last) + 0.5) / (len(last) + 1)
    figs = [(x["fig"], 0.5 ** ((date - x["date"]).days / 730)) for x in h if x["fig"] is not None]
    d["fig"] = (sum(f * w for f, w in figs) + 50.0 * FIG_PRIOR) / (sum(w for _, w in figs) + FIG_PRIOR) if figs else 50.0
    l3 = [f for f, _ in figs[-3:]]
    d["fig3"] = (sum(l3) + 50) / (len(l3) + 1) if l3 else 50.0
    d["lay"] = (date - h[-1]["date"]).days if h else None
    d["last_fig"] = h[-1]["fig"] if h else None
    d["last_lbs"] = h[-1].get("lbs") if h else None
    d["offko"] = 1 if h and h[-1]["lost_ko"] else 0
    d["offloss"] = 1 if h and h[-1]["won"] == 0 else 0
    d["kol"] = sum(x["lost_ko"] for x in h)
    st = 0
    for x in reversed(h):
        if x["won"] == 1:
            st += 1
        else:
            break
    d["streak"] = st
    wins = sum(1 for x in h if x["won"] == 1); losses = sum(1 for x in h if x["won"] == 0)
    d["finr"] = (sum(x["fin_w"] for x in h) + 0.5) / (wins + 1)
    d["decr"] = (sum(x["dec"] for x in h) + 0.5 * 2) / (len(h) + 2)
    d["finl"] = (sum(x["fin_l"] for x in h) + 0.5) / (losses + 1)
    d["wins"], d["losses"] = wins, losses
    d["ko_w"] = sum(x.get("ko_w", 0) for x in h); d["sub_w"] = sum(x.get("sub_w", 0) for x in h)
    d["ko_l"] = sum(x["lost_ko"] for x in h); d["sub_l"] = sum(x.get("sub_l", 0) for x in h)
    return d


def _vec(A, B):
    v = []
    for k in FEATS:
        if k == "south":
            v.append((1 if A["stance"] == "Southpaw" else 0) - (1 if B["stance"] == "Southpaw" else 0)); continue
        if k == "age35":
            v.append(max(0, (A.get("age") or 30) - 34) - max(0, (B.get("age") or 30) - 34)); continue
        if k == "debut":
            v.append((1 if A["n"] == 0 else 0) - (1 if B["n"] == 0 else 0)); continue
        a, b = A.get(k), B.get(k)
        if k == "lay":
            a, b = a or 400, b or 400
            v.append(math.log(max(a, 30) / 180) - math.log(max(b, 30) / 180)); continue
        if a is None or b is None:
            v.append(0.0); continue
        if k == "elo":
            v.append((a - b) / 100)
        elif k in ("fig", "fig3"):
            v.append((a - b) / 10)
        elif k == "n":
            v.append(math.log1p(a) - math.log1p(b))
        else:
            v.append(a - b)
    return v


def _gvec(A, B, base, sched, wc):
    return [math.log(base / (1 - base)), A["decr"], B["decr"], A["finr"] + A["finl"], B["finr"] + B["finl"],
            A["kd15"] + A["okd15"] + B["kd15"] + B["okd15"], A["sub15"] + B["sub15"], A["slpm"] + A["sapm"] + B["slpm"] + B["sapm"],
            1.0 if sched == 5 else 0.0, 1.0 if wc.startswith("Women") else 0.0, abs((A.get("elo") or 1500) - (B.get("elo") or 1500)) / 100]


WLB = [("Light Heavyweight", 205), ("Heavyweight", 265), ("Strawweight", 115), ("Flyweight", 125), ("Bantamweight", 135),
       ("Featherweight", 145), ("Lightweight", 155), ("Welterweight", 170), ("Middleweight", 185)]


def wc_lbs(wc):
    for k, v in WLB:
        if k in (wc or ""):
            return v
    return None


def mclass(f):
    """0 KO/TKO, 1 submission, 2 decision; None for anything else."""
    if f["kind"] != "win":
        return None
    m = f["method"]
    if "Decision" in m:
        return 2
    if "Sub" in m:
        return 1
    if "KO" in m:
        return 0
    return None


def _mvec(W, L, base, five=0.0):
    """Features for P(method | W beats L). base = division [ko, sub, dec] shares."""
    PW = 3.0
    kw = (W["ko_w"] + base[0] * PW) / (W["wins"] + PW); sw = (W["sub_w"] + base[1] * PW) / (W["wins"] + PW)
    kl = (L["ko_l"] + base[0] * PW) / (L["losses"] + PW); sl = (L["sub_l"] + base[1] * PW) / (L["losses"] + PW)
    return [base[0], base[1], kw, sw, kl, sl, W["kd15"], L["okd15"], W["sub15"], W["td15"], W["ctrl"], L["tdd"], W["slpm"] - W["sapm"],
            L["def"], (W.get("age") or 30) - 30, (L.get("age") or 30) - 30, five, 1.0 if (W.get("lbs") or 0) >= 205 else 0.0]


def fit_softmax(X, y, k=3, l2=1.0, iters=400, lr=0.5):
    n, d = X.shape
    B = np.zeros((d, k))
    Y = np.eye(k)[y]
    for _ in range(iters):
        Z = X @ B
        Z -= Z.max(1, keepdims=True)
        P = np.exp(Z); P /= P.sum(1, keepdims=True)
        G = X.T @ (P - Y) / n + l2 * B / n
        G[0] = (X.T @ (P - Y) / n)[0]
        B -= lr * G
    return B


def softmax_p(x, B):
    z = x @ B
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def is_dec(f):
    return f["kind"] == "draw" or (f["kind"] == "win" and "Decision" in f["method"])


# ------------------------------------------------------------------ main enrichment
class FormModel:
    def __init__(self, events, bio):
        self.events, self.bio = events, bio
        self.fights = sorted([f for e in events.values() for f in e["fights"]], key=lambda f: (f["date"], f["n"]))
        self.hist = defaultdict(list)
        self.wc_hist = defaultdict(list)  # weight class -> list of (date, decided)
        self.m_hist = defaultdict(list)   # weight class -> list of (date, method class)
        self.dom_b, self.dom_sd = fit_dominance(self.fights)
        self._pass1()
        self._fit_walk_forward()

    def dom_p(self, f, side):
        a, b = (f["sa"], f["sb"]) if side == "a" else (f["sb"], f["sa"])
        if not a or not b or not f["secs"]:
            return None
        return float(sigmoid((np.array(_dom_row(a, b, f["secs"])) / self.dom_sd) @ self.dom_b))

    def fighter_state(self, name, date, elo=None):
        b = self.bio.get(norm(name)) or {}
        s = summarize(self.hist[name], date)
        dob = b.get("dob")
        s["age"] = (date - dt.date.fromisoformat(dob)).days / 365.25 if dob else None
        s["reach"] = float(b["reach"]) if b.get("reach") else None
        s["ht"] = inches(b.get("ht"))
        s["stance"] = b.get("stance") or ""
        s["elo"] = elo
        return s

    def wc_base(self, wc, date, sched=3):
        wc = (wc or "").replace("Interim ", "")
        rows = [d for (t, d, s5) in self.wc_hist[wc] if (date - t).days <= 365 * 5 and (date - t).days > 0 and s5 == (sched == 5)]
        allr = [d for (t, d, s5) in self.wc_hist["*"] if (date - t).days <= 365 * 5 and (date - t).days > 0]
        g = (sum(allr) + 5) / (len(allr) + 10)
        return (sum(rows) + g * 30) / (len(rows) + 30)

    def m_base(self, wc, date):
        def shares(rows, prior, pw):
            c = [prior[i] * pw for i in range(3)]
            for t, mc in rows:
                if 0 < (date - t).days <= 365 * 5:
                    c[mc] += 1
            tot = sum(c)
            return [x / tot for x in c]
        g = shares(self.m_hist["*"], [0.32, 0.19, 0.49], 10)
        return shares(self.m_hist[(wc or "").replace("Interim ", "")], g, 30)

    def _pass1(self):
        for f in self.fights:
            A = self.fighter_state(f["a"], f["date"], f.get("elo_a")); B = self.fighter_state(f["b"], f["date"], f.get("elo_b"))
            f["_A"], f["_B"] = A, B
            f["_base"] = self.wc_base(f["wc"], f["date"], f["sched"] or 3)
            f["_mbase"] = self.m_base(f["wc"], f["date"])
            for side, me_s, op_s in (("a", A, B), ("b", B, A)):
                o = "b" if side == "a" else "a"
                rs = result_score(f, side)
                fig = None
                if rs is not None:
                    dp = self.dom_p(f, side)
                    fig = 100 * (0.5 * rs + 0.5 * (dp if dp is not None else rs)) + OPPC * (op_s["fig"] - 50)
                f["fig_" + side] = None if fig is None else round(fig, 1)
            if f["kind"] == "nc":
                continue
            dec = 1 if is_dec(f) else 0
            # Kirk round 12 (Form_Fix_PREREG sha d78b86a2): interim title bouts count in their division, as m_hist already does
            self.wc_hist[f["wc"].replace("Interim ", "")].append((f["date"], dec, f["sched"] == 5)); self.wc_hist["*"].append((f["date"], dec, f["sched"] == 5))
            mc = mclass(f)
            if mc is not None:
                self.m_hist[f["wc"].replace("Interim ", "")].append((f["date"], mc)); self.m_hist["*"].append((f["date"], mc))
            for side in "ab":
                o = "b" if side == "a" else "a"
                me, op = f["s" + side], f["s" + o]
                won = 1 if f["winner"] == side else (0.5 if f["kind"] == "draw" else 0)
                fin = ("KO" in f["method"]) or ("Sub" in f["method"])
                g = lambda d, k: d[k] if d else 0
                self.hist[f[side]].append(dict(
                    date=f["date"], won=won, secs=(f["secs"] or 0) if me else 0, sl=g(me, "sl"), sa=g(me, "sa"), osl=g(op, "sl"), osa=g(op, "sa"),
                    tl=g(me, "tl"), ta=g(me, "ta"), otl=g(op, "tl"), ota=g(op, "ta"), ctrl=g(me, "ctrl"), octrl=g(op, "ctrl"),
                    kd=g(me, "kd"), okd=g(op, "kd"), sub=g(me, "sub"), fig=f["fig_" + side],
                    lost_ko=1 if (won == 0 and "KO" in f["method"]) else 0, fin_w=1 if (won == 1 and fin) else 0,
                    fin_l=1 if (won == 0 and fin) else 0, dec=dec, lbs=wc_lbs(f["wc"]),
                    ko_w=1 if (won == 1 and "KO" in f["method"]) else 0, sub_w=1 if (won == 1 and "Sub" in f["method"]) else 0,
                    sub_l=1 if (won == 0 and "Sub" in f["method"]) else 0))

    def _train(self, rows, l2=20.0):
        X = np.array([r[0] for r in rows]); y = np.array([r[1] for r in rows])
        sd = X.std(0) + 1e-9
        b = fit_logit(np.vstack([X / sd, -X / sd]), np.concatenate([y, 1 - y]), l2=l2)
        return b, sd

    def _train_g(self, rows, l2=5.0):
        X = np.array([r[0] for r in rows]); y = np.array([r[1] for r in rows])
        mu, sd = X.mean(0), X.std(0) + 1e-9
        Z = np.hstack([np.ones((len(X), 1)), (X - mu) / sd])
        return fit_logit(Z, y, l2=l2, free=1), mu, sd

    def _fit_walk_forward(self):
        W, G = [], []
        for f in self.fights:
            if f["date"].year < 2010:
                continue
            if f["kind"] == "win":
                W.append((_vec(f["_A"], f["_B"]), 1 if f["winner"] == "a" else 0, f))
            if f["kind"] != "nc" and f["sched"] in (3, 5):
                G.append((_gvec(f["_A"], f["_B"], f["_base"], f["sched"], f["wc"]), 1 if is_dec(f) else 0, f))
        last_year = max(f["date"].year for f in self.fights)
        for Y in range(2015, last_year + 1):
            tr = [r for r in W if r[2]["date"].year < Y]; te = [r for r in W if r[2]["date"].year == Y]
            if tr and te:
                b, sd = self._train(tr)
                for x, _, f in te:
                    f["fl"] = float(sigmoid((np.array(x) / sd) @ b))
            trg = [r for r in G if r[2]["date"].year < Y]; teg = [r for r in G if r[2]["date"].year == Y]
            if trg and teg:
                bg, mu, sdg = self._train_g(trg)
                for x, _, f in teg:
                    f["gl"] = float(sigmoid(np.concatenate([[1.0], (np.array(x) - mu) / sdg]) @ bg))
        # method given winner
        M = []
        for f in self.fights:
            mc = mclass(f)
            if mc is None or f["date"].year < 2010:
                continue
            Wn, Ln = (f["_A"], f["_B"]) if f["winner"] == "a" else (f["_B"], f["_A"])
            M.append((_mvec(Wn, Ln, f["_mbase"], 0.0), mc, f))

        def train_m(rows):
            X = np.array([r[0] for r in rows]); y = np.array([r[1] for r in rows])
            mu, sd = X.mean(0), X.std(0) + 1e-9
            Z = np.hstack([np.ones((len(X), 1)), (X - mu) / sd])
            return fit_softmax(Z, y, l2=5.0), mu, sd

        def apply_m(f, par):
            Bm, mu, sd = par
            out = {}
            for side, (Wn, Ln) in (("a", (f["_A"], f["_B"])), ("b", (f["_B"], f["_A"]))):
                x = np.concatenate([[1.0], (np.array(_mvec(Wn, Ln, f["_mbase"], 0.0)) - mu) / sd])
                out[side] = [float(v) for v in softmax_p(x, Bm)]
            return out

        for Y in range(2015, last_year + 1):
            tr = [r for r in M if r[2]["date"].year < Y]
            te = [f for f in self.fights if f["date"].year == Y]
            if tr and te:
                par = train_m(tr)
                for f in te:
                    f["ms"] = apply_m(f, par)
        self.mpar = train_m(M)
        self.b, self.sd = self._train(W)
        self.bg, self.mug, self.sdg = self._train_g(G)
        self.coefs = {k: round(float(v), 3) for k, v in zip(FEATS, self.b)}

    # prediction for a fight that hasn't happened
    def predict(self, a, b, date, wc, sched=3, elo_a=None, elo_b=None):
        A = self.fighter_state(a, date, elo_a); B = self.fighter_state(b, date, elo_b)
        p = float(sigmoid((np.array(_vec(A, B)) / self.sd) @ self.b))
        base = self.wc_base(wc, date, sched)
        g = float(sigmoid(np.concatenate([[1.0], (np.array(_gvec(A, B, base, sched, wc)) - self.mug) / self.sdg]) @ self.bg))
        mb = self.m_base(wc, date)
        Bm, mu, sd = self.mpar
        ms = {}
        for side, (Wn, Ln) in (("a", (A, B)), ("b", (B, A))):
            x = np.concatenate([[1.0], (np.array(_mvec(Wn, Ln, mb, 0.0)) - mu) / sd])
            ms[side] = [float(v) for v in softmax_p(x, Bm)]
        self.last_ms = ms
        return p, g, A, B, base

    def rating(self, name, date=None):
        date = date or dt.date.today()
        h = self.hist.get(name) or []
        return round(summarize(h, date)["fig"], 1) if h else None


# ------------------------------------------------------------------ angles
def _price(f, side, when="close"):
    o = f.get("odds")
    if not o:
        return None
    m = o[when]["ma" if side == "a" else "mb"]
    if m is None:
        return None
    return 1 + m / 100 if m > 0 else 1 + 100 / (-m)


def _p(f, side, when="close"):
    o = f.get("odds")
    if not o:
        return None
    p = o[when]["p"]
    return p if side == "a" else 1 - p


def angle_sides(f, A, B, fl=None):
    """Return {angle_id: side} for every angle this fight qualifies for. Uses only pre-fight info."""
    out = {}
    o = f.get("odds")
    S = {"a": A, "b": B}
    opp = {"a": "b", "b": "a"}
    pc = o["close"]["p"] if o else None
    fav = None if pc is None else ("a" if pc >= 0.5 else "b")
    if fav:
        dog = opp[fav]
        pf = max(pc, 1 - pc)
        out["fav_all"] = fav; out["dog_all"] = dog
        band = "65" if pf < 0.60 else "70" if pf < 0.70 else "80" if pf < 0.80 else "99"
        out["fav_" + band] = fav; out["dog_" + band] = dog
        mv = (o["close"]["p"] - o["open"]["p"]) * 100
        if o["n"] >= 3 and o["open"]["t"][:10] != o["close"]["t"][:10]:
            if abs(mv) >= 3:
                out["steam3"] = "a" if mv > 0 else "b"
            if abs(mv) >= 6:
                out["steam6"] = "a" if mv > 0 else "b"
            if abs(mv) >= 3 and ("a" if mv > 0 else "b") == dog:
                out["steam_dog"] = dog
        ser = o.get("series") or []
        if len(ser) >= 4:
            import datetime as _dt
            tc = _dt.datetime.fromisoformat(ser[-1][0])
            early = [r for r in ser if (tc - _dt.datetime.fromisoformat(r[0])).total_seconds() >= 48 * 3600]
            if early and (tc - _dt.datetime.fromisoformat(ser[0][0])).days >= 5:
                late = (ser[-1][1] - early[-1][1]) * 100; erl = (early[-1][1] - ser[0][1]) * 100
                if abs(late) >= 2.5:
                    out["late_steam"] = "a" if late > 0 else "b"
                if abs(erl) >= 3:
                    out["early_steam"] = "a" if erl > 0 else "b"
                if abs(erl) >= 3 and abs(late) >= 1.5 and (erl > 0) != (late > 0):
                    out["buyback"] = "a" if late > 0 else "b"
        if (f.get("wc") or "").startswith("Women"):
            out["w_dog"] = dog
        if "Heavyweight" == (f.get("wc") or "").replace("Interim ", ""):
            out["hw_dog"] = dog
        if f.get("sched") == 5:
            out["five_fav"] = fav
    for s in "ab":
        me, op = S[s], S[opp[s]]
        if me.get("age") and op.get("age"):
            if op["age"] - me["age"] >= 5:
                out["younger5"] = s
            if op["age"] >= 36 and me["age"] < 32:
                out["vs_36"] = s
        if me.get("reach") and op.get("reach") and me["reach"] - op["reach"] >= 4:
            out["reach4"] = s
        if op["n"] > 0 and (op.get("lay") or 0) >= 450 and (me.get("lay") or 999) < 300 and me["n"] > 0:
            out["vs_layoff"] = s
        if op.get("offko") and not me.get("offko"):
            out["vs_offko"] = s
        if me["n"] >= 3 and op["n"] == 0:
            out["vet_vs_debut"] = s
        if me["n"] == 0 and op["n"] >= 3:
            out["debut_vs_vet"] = s
        if me["stance"] == "Southpaw" and op["stance"] == "Orthodox":
            out["southpaw"] = s
        if me["n"] > 0 and (me.get("lay") or 999) <= 50 and (op.get("lay") or 0) > 50:
            out["quick_turn"] = s
        if me["streak"] >= 4 and op["streak"] < 4:
            out["streak4"] = s
        if me["fig"] - op["fig"] >= 8 and fav and s != fav:
            out["fig_dog"] = s
        if me["fig"] - op["fig"] >= 8 and fav and s == fav:
            out["fig_fav"] = s
        if me.get("offloss") and op.get("offloss") == 0 and op["n"] > 0 and me["n"] > 0:
            out["off_loss_vs_win"] = s
        if me.get("last_fig") is not None and me["last_fig"] >= 90:
            out["off_big_fig"] = s
        if me.get("last_fig") is not None and me["last_fig"] <= 20:
            out["off_bad_fig"] = s
        lbs = wc_lbs(f.get("wc"))
        if lbs and me.get("last_lbs") and lbs > me["last_lbs"]:
            out["moving_up"] = s
        if lbs and me.get("last_lbs") and lbs < me["last_lbs"]:
            out["moving_down"] = s
        if me.get("age") and me["age"] >= 37:
            out["age37"] = s
        if me["n"] >= 3 and op["n"] >= 3:
            if me["td15"] >= 2.5 and op["tdd"] < 0.55:
                out["wrestler_weak_tdd"] = s
            if me["td15"] >= 2.5 and op["tdd"] >= 0.75:
                out["wrestler_strong_tdd"] = s
            if (me["slpm"] - me["sapm"]) >= 1.5 and (op["slpm"] - op["sapm"]) <= 0:
                out["striker_edge"] = s
            if me["kd15"] >= 0.6 and op["kol"] >= 2:
                out["power_vs_chin"] = s
            if me["ctrl"] >= 0.30 and op["ctrl"] < 0.10:
                out["grappler_vs_striker"] = s
            if me["ctrl"] < 0.10 and op["ctrl"] >= 0.30:
                out["striker_vs_grappler"] = s
    if fl is not None and pc is not None:
        d = fl - pc
        if abs(d) >= 0.05:
            out["fl5"] = "a" if d > 0 else "b"
        if abs(d) >= 0.10:
            out["fl10"] = "a" if d > 0 else "b"
        if abs(d) >= 0.10 and fav and ("a" if d > 0 else "b") != fav:
            out["fl10_dog"] = "a" if d > 0 else "b"
    return out


ANGLES = {
    "fav_all": "All favorites", "dog_all": "All underdogs",
    "fav_65": "Favorites, 50-60% implied", "fav_70": "Favorites, 60-70%", "fav_80": "Favorites, 70-80%", "fav_99": "Favorites, 80%+",
    "dog_65": "Underdogs vs 50-60% favorite", "dog_70": "Underdogs vs 60-70% favorite", "dog_80": "Underdogs vs 70-80% favorite", "dog_99": "Underdogs vs 80%+ favorite",
    "steam3": "Line moved 3+ pts toward fighter", "steam6": "Line moved 6+ pts toward fighter", "steam_dog": "Underdog steamed 3+ pts",
    "w_dog": "Women's underdogs", "hw_dog": "Heavyweight underdogs", "five_fav": "Five-round favorites",
    "younger5": "Younger by 5+ years", "vs_36": "Under 32 vs opponent 36+", "reach4": "Reach advantage 4\"+",
    "vs_layoff": "Active fighter vs 15+ month layoff", "vs_offko": "Facing a fighter off a KO loss",
    "vet_vs_debut": "3+ UFC fights vs UFC debut", "debut_vs_vet": "UFC debut vs 3+ UFC fights", "southpaw": "Southpaw vs orthodox",
    "quick_turn": "Turnaround of 50 days or less", "streak4": "On a 4+ fight win streak", "off_loss_vs_win": "Off a loss vs opponent off a win",
    "late_steam": "Late steam: 2.5+ pts in the final 48 hours", "early_steam": "Early steam: 3+ pts before the final 48 hours",
    "buyback": "Late move against the early steam (buyback side)",
    "off_big_fig": "Coming off a 90+ Form Figure", "off_bad_fig": "Coming off a Form Figure of 20 or lower",
    "moving_up": "Moving up a weight class", "moving_down": "Moving down a weight class", "age37": "Age 37 or older",
    "wrestler_weak_tdd": "2.5+ TD/15 vs takedown defense under 55%", "wrestler_strong_tdd": "2.5+ TD/15 vs takedown defense 75%+",
    "striker_edge": "Strike diff +1.5/min vs opponent at 0 or worse", "power_vs_chin": "0.6+ KD/15 vs opponent with 2+ KO losses",
    "grappler_vs_striker": "Control 30%+ vs opponent under 10%", "striker_vs_grappler": "Control under 10% vs opponent 30%+",
    "fig_dog": "Underdog with Form Figure rating 8+ higher", "fig_fav": "Favorite with Form Figure rating 8+ higher",
    "fl5": "Form Line 5+ pts above the close", "fl10": "Form Line 10+ pts above the close", "fl10_dog": "Underdog the Form Line likes by 10+ pts",
}


def research(model: FormModel):
    F = [f for f in model.fights if f.get("odds") and f["kind"] == "win"]
    out = {"n": len(F), "from": F[0]["date"].isoformat() if F else None, "to": F[-1]["date"].isoformat() if F else None}

    # ---- calibration of the close / open (favorite side)
    def calib(when):
        bins = [(0.5, 0.55), (0.55, 0.6), (0.6, 0.65), (0.65, 0.7), (0.7, 0.75), (0.75, 0.8), (0.8, 0.85), (0.85, 0.9), (0.9, 1.01)]
        rows = []
        for lo, hi in bins:
            xs = []
            for f in F:
                p = f["odds"][when]["p"]; fav = "a" if p >= 0.5 else "b"; pf = max(p, 1 - p)
                if lo <= pf < hi:
                    xs.append((pf, 1 if f["winner"] == fav else 0))
            if xs:
                rows.append({"band": f"{int(lo*100)}-{int(min(hi,1)*100)}%", "n": len(xs), "exp": round(sum(x[0] for x in xs) / len(xs), 4),
                             "act": round(sum(x[1] for x in xs) / len(xs), 4)})
        return rows

    out["calib_close"] = calib("close"); out["calib_open"] = calib("open")

    def ll(ps, ys):
        ps = np.clip(np.array(ps), 1e-6, 1 - 1e-6); ys = np.array(ys)
        return float(-(ys * np.log(ps) + (1 - ys) * np.log(1 - ps)).mean())

    def brier(ps, ys):
        return float(((np.array(ps) - np.array(ys)) ** 2).mean())

    ys = [1 if f["winner"] == "a" else 0 for f in F]
    G = [f for f in F if f.get("fl") is not None]
    yg = [1 if f["winner"] == "a" else 0 for f in G]
    acc = lambda ps, y: float(np.mean([(p > 0.5) == (v == 1) for p, v in zip(ps, y) if p != 0.5]))
    out["scores"] = [
        {"k": "Closing line (no-vig consensus)", "n": len(F), "ll": round(ll([f["odds"]["close"]["p"] for f in F], ys), 4), "brier": round(brier([f["odds"]["close"]["p"] for f in F], ys), 4), "acc": round(acc([f["odds"]["close"]["p"] for f in F], ys), 4)},
        {"k": "First-seen line", "n": len(F), "ll": round(ll([f["odds"]["open"]["p"] for f in F], ys), 4), "brier": round(brier([f["odds"]["open"]["p"] for f in F], ys), 4), "acc": round(acc([f["odds"]["open"]["p"] for f in F], ys), 4)},
        {"k": "Form Line (stats only, walk-forward)", "n": len(G), "ll": round(ll([f["fl"] for f in G], yg), 4), "brier": round(brier([f["fl"] for f in G], yg), 4), "acc": round(acc([f["fl"] for f in G], yg), 4)},
        {"k": "Elo only", "n": len(F), "ll": round(ll([1 / (1 + 10 ** ((f["elo_b"] - f["elo_a"]) / 400)) for f in F], ys), 4), "brier": round(brier([1 / (1 + 10 ** ((f["elo_b"] - f["elo_a"]) / 400)) for f in F], ys), 4), "acc": round(acc([1 / (1 + 10 ** ((f["elo_b"] - f["elo_a"]) / 400)) for f in F], ys), 4)},
        {"k": "Coin flip", "n": len(F), "ll": round(math.log(2), 4), "brier": 0.25, "acc": 0.5},
    ]
    # does the Form Line add anything to the close?  walk-forward blend
    blend_rows = []
    for Y in sorted({f["date"].year for f in G})[1:]:
        tr = [f for f in G if f["date"].year < Y]; te = [f for f in G if f["date"].year == Y]
        lg = lambda p: math.log(min(max(p, 1e-4), 1 - 1e-4) / (1 - min(max(p, 1e-4), 1 - 1e-4)))
        X = np.array([[lg(f["odds"]["close"]["p"]), lg(f["fl"])] for f in tr]); y = np.array([1 if f["winner"] == "a" else 0 for f in tr])
        b = fit_logit(np.vstack([X, -X]), np.concatenate([y, 1 - y]), l2=0.5)
        for f in te:
            blend_rows.append((float(sigmoid(np.array([lg(f["odds"]["close"]["p"]), lg(f["fl"])]) @ b)), f["odds"]["close"]["p"], 1 if f["winner"] == "a" else 0, b))
    if blend_rows:
        out["blend"] = {"n": len(blend_rows), "ll_blend": round(ll([r[0] for r in blend_rows], [r[2] for r in blend_rows]), 4),
                        "ll_close": round(ll([r[1] for r in blend_rows], [r[2] for r in blend_rows]), 4),
                        "w_close": round(float(blend_rows[-1][3][0]), 3), "w_form": round(float(blend_rows[-1][3][1]), 3)}


    # ---- favorite-longshot bias: slope of the no-vig close, and simple price-shopping sims
    lg = lambda p: math.log(min(max(p, 1e-4), 1 - 1e-4) / (1 - min(max(p, 1e-4), 1 - 1e-4)))
    dec = lambda ml_: (1 + ml_ / 100 if ml_ > 0 else 1 + 100 / (-ml_))

    def slope(rows):
        X = np.array([[lg(f["odds"]["close"]["p"])] for f in rows]); y = np.array([1 if f["winner"] == "a" else 0 for f in rows])
        return float(fit_logit(np.vstack([X, -X]), np.concatenate([y, 1 - y]), l2=0.5)[0])

    out["k"] = round(slope(F), 3)
    yrs = sorted({f["date"].year for f in F})
    out["k_by_year"] = {str(Y): round(slope([f for f in F if f["date"].year == Y]), 3) for Y in yrs}
    for Y in yrs[1:]:
        k = slope([f for f in F if f["date"].year < Y])
        for f in F:
            if f["date"].year == Y:
                f["_fair"] = float(sigmoid(k * lg(f["odds"]["close"]["p"])))

    def best(f, side):
        key = "ma" if side == "a" else "mb"
        v = [dec(b[key]) for b in (f["odds"].get("books") or {}).values() if b.get(key) is not None]
        return max(v) if v else None

    def book(name):
        def fn(f, side):
            b = (f["odds"].get("books") or {}).get(name)
            m_ = b and b.get("ma" if side == "a" else "mb")
            return dec(m_) if m_ is not None else None
        return fn

    cons = lambda f, s: dec(f["odds"]["close"]["ma" if s == "a" else "mb"]) if f["odds"]["close"]["ma" if s == "a" else "mb"] is not None else None
    favside = lambda f: "a" if f["odds"]["close"]["p"] >= 0.5 else "b"
    pfav = lambda f: max(f["odds"]["close"]["p"], 1 - f["odds"]["close"]["p"])

    def sim(name, pick, price, rows=None):
        n = w = 0; pnl = 0.0; by = {}
        for f in (rows if rows is not None else F):
            s_ = pick(f)
            if not s_:
                continue
            d = price(f, s_)
            if not d:
                continue
            won = f["winner"] == s_; r = (d - 1) if won else -1
            n += 1; w += won; pnl += r
            y_ = by.setdefault(str(f["date"].year), [0, 0.0]); y_[0] += 1; y_[1] += r
        return {"name": name, "n": n, "win": round(w / n, 4) if n else None, "roi": round(pnl / n, 4) if n else None, "pnl": round(pnl, 2),
                "years": {k_: [v[0], round(v[1] / v[0], 4)] for k_, v in sorted(by.items())}}

    def fair_edge(thr):
        def pick(f):
            if "_fair" not in f:
                return None
            for s_ in "ab":
                pr = f["_fair"] if s_ == "a" else 1 - f["_fair"]
                d = best(f, s_)
                if d and pr * d - 1 >= thr:
                    return s_
            return None
        return pick

    out["sims"] = [
        sim("Every favorite, consensus closing price", favside, cons),
        sim("Every favorite, best closing price across books", favside, best),
        sim("Every favorite, Pinnacle close", favside, book("pinnacle")),
        sim("Every favorite, DraftKings close", favside, book("draftkings")),
        sim("Every favorite, FanDuel close", favside, book("fanduel")),
        sim("Favorites 70%+, best closing price", lambda f: favside(f) if pfav(f) >= 0.7 else None, best),
        sim("Favorites 80%+, best closing price", lambda f: favside(f) if pfav(f) >= 0.8 else None, best),
        sim("Favorites under 60%, best closing price", lambda f: favside(f) if pfav(f) < 0.6 else None, best),
        sim("Every underdog, best closing price", lambda f: "b" if favside(f) == "a" else "a", best),
        sim("Bias-adjusted fair price shows 2%+ edge at best price (walk-forward)", fair_edge(0.02), best),
        sim("Bias-adjusted fair price shows 4%+ edge at best price (walk-forward)", fair_edge(0.04), best),
    ]

    # ---- which book's close is sharpest (fights where every listed book had a price)
    core = ["pinnacle", "draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "betonlineag"]
    common = [f for f in F if all((f["odds"].get("books") or {}).get(b, {}).get("p") is not None for b in core)]
    if common:
        yc = [1 if f["winner"] == "a" else 0 for f in common]
        rowsb = [{"book": b, "ll": round(ll([f["odds"]["books"][b]["p"] for f in common], yc), 4), "brier": round(brier([f["odds"]["books"][b]["p"] for f in common], yc), 4)} for b in core]
        rowsb.append({"book": "consensus", "ll": round(ll([f["odds"]["close"]["p"] for f in common], yc), 4), "brier": round(brier([f["odds"]["close"]["p"] for f in common], yc), 4)})
        rowsb.sort(key=lambda r: r["ll"])
        out["books"] = {"n": len(common), "rows": rowsb}
    # ---- drift: what happens to the opening favorite's price
    dr = [f for f in F if f["odds"]["n"] >= 4 and f["odds"]["open"]["t"][:10] < f["odds"]["close"]["t"][:10] and f["date"].year <= 2025]
    if dr:
        mv = []
        for f in dr:
            po, pc_ = f["odds"]["open"]["p"], f["odds"]["close"]["p"]
            mv.append((pc_ - po) if po >= 0.5 else (po - pc_))
        out["drift"] = {"n": len(dr), "mean": round(float(np.mean(mv)) * 100, 2), "shorter": round(float(np.mean([m_ > 0.005 for m_ in mv])), 4),
                        "longer": round(float(np.mean([m_ < -0.005 for m_ in mv])), 4)}

    # ---- angles
    agg = defaultdict(lambda: {"n": 0, "w": 0, "exp": 0.0, "pnl_c": 0.0, "pnl_o": 0.0, "n_o": 0, "by": defaultdict(lambda: [0, 0, 0.0])})
    for f in F:
        sides = angle_sides(f, f["_A"], f["_B"], f.get("fl"))
        f["_angles"] = sides
        for k, s in sides.items():
            a = agg[k]
            won = f["winner"] == s
            dc = _price(f, s, "close"); do = _price(f, s, "open")
            a["n"] += 1; a["w"] += won; a["exp"] += _p(f, s, "close")
            if dc:
                a["pnl_c"] += (dc - 1) if won else -1
            if do:
                a["pnl_o"] += (do - 1) if won else -1; a["n_o"] += 1
            y = a["by"][f["date"].year]; y[0] += 1; y[1] += won; y[2] += ((dc - 1) if won else -1) if dc else 0
    rows = []
    for k, a in agg.items():
        n = a["n"]; exp = a["exp"] / n; act = a["w"] / n
        se = math.sqrt(max(exp * (1 - exp), 1e-9) / n)
        rows.append({"id": k, "name": ANGLES.get(k, k), "n": n, "w": a["w"], "act": round(act, 4), "exp": round(exp, 4), "z": round((act - exp) / se, 2),
                     "roi_c": round(a["pnl_c"] / n, 4), "pnl_c": round(a["pnl_c"], 2), "roi_o": round(a["pnl_o"] / a["n_o"], 4) if a["n_o"] else None,
                     "years": {str(y): [v[0], v[1], round(v[2], 2)] for y, v in sorted(a["by"].items())}})
    order = list(ANGLES)
    rows.sort(key=lambda r: order.index(r["id"]) if r["id"] in order else 99)
    out["angles"] = rows

    # ---- totals / distance
    tot = []
    for f in model.fights:
        o = f.get("odds") or {}
        t = o.get("total")
        if not t or t.get("p_over") is None or not f["secs"] or f["kind"] == "nc":
            continue
        over = 1 if (is_dec(f) or f["secs"] > t["pt"] * 300) else 0
        d_o = (1 + t["over"] / 100 if t["over"] > 0 else 1 + 100 / -t["over"]) if t.get("over") else None
        d_u = (1 + t["under"] / 100 if t["under"] > 0 else 1 + 100 / -t["under"]) if t.get("under") else None
        tot.append((t["pt"], t["p_over"], over, ((d_o - 1) if over else -1) if d_o else 0, ((d_u - 1) if not over else -1) if d_u else 0))
    trows = []
    for pt in sorted({t[0] for t in tot}):
        xs = [t for t in tot if t[0] == pt]
        if len(xs) >= 25:
            trows.append({"pt": pt, "n": len(xs), "exp": round(sum(x[1] for x in xs) / len(xs), 4), "act": round(sum(x[2] for x in xs) / len(xs), 4),
                          "roi_over": round(sum(x[3] for x in xs) / len(xs), 4), "roi_under": round(sum(x[4] for x in xs) / len(xs), 4)})
    out["totals"] = trows

    since = dt.date(max(f["date"].year for f in model.fights) - 4, 1, 1)
    wc = defaultdict(lambda: {"n": 0, "dec": 0, "ko": 0, "sub": 0, "r1": 0, "secs": 0})
    for f in model.fights:
        if f["date"] < since or f["kind"] == "nc" or f["sched"] not in (3, 5):
            continue
        k = f["wc"].replace("Interim ", "")
        for key in (k, "All"):
            w = wc[(key, f["sched"])]
            w["n"] += 1; w["dec"] += is_dec(f); w["ko"] += "KO" in f["method"]; w["sub"] += "Sub" in f["method"]
            w["r1"] += (f["round"] == 1 and not is_dec(f)); w["secs"] += f["secs"] or 0
    out["wc"] = [{"wc": k, "sched": s, "n": w["n"], "dec": round(w["dec"] / w["n"], 4), "ko": round(w["ko"] / w["n"], 4), "sub": round(w["sub"] / w["n"], 4),
                  "r1": round(w["r1"] / w["n"], 4), "avg_min": round(w["secs"] / w["n"] / 60, 2)}
                 for (k, s), w in sorted(wc.items(), key=lambda kv: -kv[1]["n"]) if w["n"] >= 25]

    # distance model vs base rate
    GD = [f for f in model.fights if f.get("gl") is not None and f["date"].year >= 2022]
    if GD:
        yd = [1 if is_dec(f) else 0 for f in GD]
        out["gtd"] = {"n": len(GD), "ll_model": round(ll([f["gl"] for f in GD], yd), 4), "ll_base": round(ll([f["_base"] for f in GD], yd), 4),
                      "brier_model": round(brier([f["gl"] for f in GD], yd), 4), "brier_base": round(brier([f["_base"] for f in GD], yd), 4),
                      "rate": round(sum(yd) / len(yd), 4)}
        bins = [(0, .3), (.3, .4), (.4, .5), (.5, .6), (.6, .7), (.7, 1.01)]
        out["gtd_calib"] = [{"band": f"{int(lo*100)}-{int(min(hi,1)*100)}%", "n": len(xs), "exp": round(sum(x[0] for x in xs) / len(xs), 4), "act": round(sum(x[1] for x in xs) / len(xs), 4)}
                            for lo, hi in bins for xs in [[(f["gl"], 1 if is_dec(f) else 0) for f in GD if lo <= f["gl"] < hi]] if xs]

    # method-of-victory model, given the actual winner
    MM = [f for f in model.fights if f.get("ms") and mclass(f) is not None and f["date"].year >= 2022]
    if MM:
        def mll(get):
            return round(float(-np.mean([math.log(max(get(f)[mclass(f)], 1e-6)) for f in MM])), 4)
        out["method"] = {"n": len(MM), "ll_model": mll(lambda f: f["ms"][f["winner"]]), "ll_base": mll(lambda f: f["_mbase"]),
                         "share": [round(sum(1 for f in MM if mclass(f) == k_) / len(MM), 4) for k_ in range(3)]}
        cal = []
        for k_, nm_ in enumerate(["KO/TKO", "Submission", "Decision"]):
            for lo, hi in [(0, .15), (.15, .3), (.3, .45), (.45, .6), (.6, 1.01)]:
                xs = [(f["ms"][f["winner"]][k_], 1 if mclass(f) == k_ else 0) for f in MM if lo <= f["ms"][f["winner"]][k_] < hi]
                if len(xs) >= 30:
                    cal.append({"m": nm_, "band": f"{int(lo*100)}-{int(min(hi,1)*100)}%", "n": len(xs), "exp": round(sum(x[0] for x in xs) / len(xs), 4), "act": round(sum(x[1] for x in xs) / len(xs), 4)})
        out["method_calib"] = cal

    # form figure: does a higher rating win?
    fr = []
    for f in model.fights:
        if f["kind"] != "win" or f["date"].year < 2015 or f["_A"]["n"] == 0 or f["_B"]["n"] == 0:
            continue
        d = f["_A"]["fig"] - f["_B"]["fig"]
        fr.append((abs(d), 1 if (f["winner"] == "a") == (d > 0) else 0))
    fb = []
    for lo, hi in [(0, 3), (3, 6), (6, 10), (10, 15), (15, 99)]:
        xs = [x[1] for x in fr if lo <= x[0] < hi]
        if xs:
            fb.append({"band": f"{lo}-{hi if hi < 99 else '+'}", "n": len(xs), "act": round(sum(xs) / len(xs), 4)})
    out["fig_bands"] = fb
    out["coefs"] = model.coefs
    return out


if __name__ == "__main__":
    import sys, json
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    import build_form as bf
    cache = Path(__file__).resolve().parents[1] / ".form_cache"
    events, bio = bf.load_ufcstats(cache)
    bf.run_elo(events)
    by_id = bf.load_odds(cache); oidx = bf.index_odds(by_id)
    for e in events.values():
        if e["date"].year < 2022:
            continue
        for f in e["fights"]:
            eid, fl = bf.find_odds(oidx, by_id, f["a"], f["b"], e["date"])
            if eid:
                o = bf.summarize_odds(by_id[eid], fl, a_name=f["a"])
                if o:
                    f["odds"] = o
    m = FormModel(events, bio)
    r = research(m)
    for s in r["scores"]:
        print(s)
    print("blend", r.get("blend")); print("gtd", r.get("gtd")); print("fig", r["fig_bands"]); print("totals", r["totals"])
    for a in r["angles"]:
        print(f"{a['name'][:44]:44s} n={a['n']:5d} act={a['act']:.3f} exp={a['exp']:.3f} z={a['z']:+.2f} roi_close={a['roi_c']:+.3f} roi_open={a['roi_o'] if a['roi_o'] is None else round(a['roi_o'],3)}")
