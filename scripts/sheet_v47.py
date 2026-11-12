#!/usr/bin/env python3
"""Mirror of the UFC Model sheet's moneyline block (rules v4.7), for checking and publishing.

The sheet stays the source of truth. This reproduces Calculator G (listed), H, Q, True %,
edges, drift, flag (AA) and the tab N recommendation from the same inputs, so a pipeline
can (1) verify the sheet after inputs are entered and (2) show the same numbers on the site.

Inputs per fight (dict): dog, fav, dog_odds, fav_odds (best bettable prices, American),
open_dog (de-vigged open prob, Calc F), markov (dog %, 0-1, Calc J, optional), shift (B42),
tap, junk, tip (0-1, optional), ctx (Calc K: "D", "G", "GF", "R" or a number), manual (Calc M),
women (bool).

Checked against the live sheet on 2026-11-11: Hokit/Gane +170/-200 -> listed 35.7%,
edges -1.3% / -2.4%, drift -6.3%, flag "no dog bet (drifting)"; Radtke/Thompson
+140/-150 -> 41.0%, -0.7% / -1.0%.
"""

B43, B44, BETA, WOMEN = 0.15, 0.075, 0.15, 0.04


def implied(ml):
    ml = float(ml)
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def clamp(x, lo=0.02, hi=0.98):
    return max(lo, min(hi, x))


def ctx_adj(code):
    if code in (None, "", "D"):
        return 0.0
    if code in ("G", "R"):
        return -0.04
    if code == "GF":
        return 0.04
    try:
        return float(code)
    except (TypeError, ValueError):
        return 0.0


def row(f):
    E, J = implied(f["dog_odds"]), implied(f["fav_odds"])
    listed = E / (E + J)
    H = listed if f.get("markov") is None else clamp(f["markov"] - (f.get("shift") or 0.0))
    tap, junk = f.get("tap"), f.get("junk")
    pub = [x for x in (tap, junk) if x is not None]
    hi = max(pub) if pub else None
    lo = min(pub) if pub else None
    Q = listed + BETA * (H - listed) - WOMEN * bool(f.get("women")) + ctx_adj(f.get("ctx"))
    if hi is not None:
        Q -= B43 * max(0.0, hi - listed)
        Q -= B44 * max(0.0, lo - listed)
    Q = clamp(Q)
    true_dog = Q + (f.get("manual") or 0.0)
    true_fav = 1 - true_dog
    dog_edge, fav_edge = true_dog - E, true_fav - J
    drift = listed - f["open_dog"] if f.get("open_dog") is not None else 0.0
    # flag AA, first match
    if f.get("ctx") == "D":
        flag = "DEBUTANT DOG - no dog bet"
    elif (f.get("tip") or 0) >= 0.5:
        flag = "SHARPS ON DOG - no dog bet"
    elif drift <= -0.04:
        flag = "no dog bet (drifting)"
    elif tap is not None and junk is not None and tap > listed and junk > listed:
        flag = "public on dog - no dog bet"
    elif hi is not None and hi > listed:
        flag = "public lean (dog)"
    else:
        flag = "ok"
    fav_nv = 1 - listed
    if fav_nv >= 0.80:
        rec = f"BET {f['fav']} (80%+ rule, shop)"
    elif dog_edge >= 0.08 and flag == "ok":
        rec = f"BET {f['dog']}"
    elif fav_edge >= 0.02 and flag.startswith("SHARPS"):
        # Main Card!N2 keys the fade off the FLAG text (LEFT(AA,6)="SHARPS"), so a D-code dog
        # with sharps on it gets no fade. Fixed 2026-11-11 (audit block 31).
        rec = f"BET {f['fav']} (fade sharp dog)"
    elif fav_edge >= 0.03:
        rec = f"BET {f['fav']}"
    elif dog_edge >= 0.05 and flag == "ok":
        rec = f"lean {f['dog']}"
    elif fav_edge >= 0.02:
        rec = f"lean {f['fav']}"
    else:
        rec = "-"
    if drift <= -0.03 and rec.startswith("BET") and f["fav"] in rec:
        # Main Card!N2: the late tag only goes on favorite BET strings (80%+, fade, plain BET fav)
        # Whole percent, half rounded up as Sheets does (Python's :.0f rounds half to even). Matches all 5 late
        # tags in Snapshots history; none sat on a .5 tie, so tie handling is assumed, not observed.
        pct = int(abs(drift) * 100 + 0.5 + 1e-9)
        rec += f" [late: fav moved {pct}% from open]"
    return {"listed": listed, "H": H, "Q": Q, "true_dog": true_dog, "true_fav": true_fav, "hold": E + J - 1,
            "dog_edge": dog_edge, "fav_edge": fav_edge, "drift": drift, "flag": flag, "rec": rec}


def markov_shift(rows):
    """B42: card mean of (Markov - listed) over fights with a Markov %."""
    d = [r["markov"] - implied(r["dog_odds"]) / (implied(r["dog_odds"]) + implied(r["fav_odds"])) for r in rows if r.get("markov") is not None]
    return sum(d) / len(d) if d else 0.0


if __name__ == "__main__":
    for f, want in (({"dog": "Josh Hokit", "fav": "Ciryl Gane", "dog_odds": 170, "fav_odds": -200, "open_dog": 0.420},
                     (0.357, -0.013, -0.024, "no dog bet (drifting)")),
                    ({"dog": "Charles Radtke", "fav": "Stephen Thompson", "dog_odds": 140, "fav_odds": -150, "open_dog": None},
                     (0.410, -0.007, -0.010, None))):
        r = row(f)
        got = (round(r["true_dog"], 3), round(r["dog_edge"], 3), round(r["fav_edge"], 3))
        ok = got == want[:3] and (want[3] is None or r["flag"] == want[3])
        print(f["dog"], got, r["flag"], r["rec"], "MATCHES SHEET" if ok else f"MISMATCH want {want}")


# ---------------------------------------------------------------- method split and fight GTD (Main Card / Prelims V:AB, Q)
# Mirror of the tab formulas (v4.3+ "method shares flow from the trusted GTD"), Block 44. Inputs per fight (method_inputs in
# the published file): L = Calculator L (true dog), ap/aq = Markov decision shares (AP/AQ), ad/ae and ah/ai = projected
# DEC/KO for dog and fav (AD/AE, AH/AI; SUB = 1 - DEC - KO as in AF/AJ), al/am/an = weight-class baseline DEC/KO/SUB (AL:AN),
# s = listed GTD (S), cx/cy = Calculator X/Y (finish given dog / fav win), ko_dog/sub_dog and ko_fav/sub_fav = the market
# KO / SUB prices on the tab's lower table (P:Q, rows 14+2k and 15+2k), b41 = method market anchor, b45 = Markov weight.

def _n(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else 0.0


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _avg(*xs):
    v = [float(x) for x in xs if _num(x)]
    return sum(v) / len(v) if v else 0.0


def _dec_share(L, own_dec, other_dec, proj_dec, other_proj_dec, mi, fin_self, fallback):
    ap, aq = own_dec, other_dec
    mk = L * ap + (1 - L) * aq if _num(ap) and _num(aq) else -1
    tp = L * proj_dec + (1 - L) * other_proj_dec if _num(proj_dec) and _num(other_proj_dec) else -1
    X, Y = _n(mi.get("cx")), _n(mi.get("cy"))
    rc = 1 - (L * X + (1 - L) * Y) if mi.get("cx") is not None or mi.get("cy") is not None else 0.0   # Calculator Z
    bs, S = _n(mi.get("al")), mi.get("s")
    wm = 0 if mk < 0 else _n(mi.get("b45"))
    wt = 0 if tp < 0 else 0.1
    wr = 0.3 if rc > 0 else 0
    wb = 0.15 if bs > 0 else 0
    tot = wm + wt + wr + wb
    m = _n(S) if tot == 0 else (wm * max(mk, 0) + wt * max(tp, 0) + wr * rc + wb * bs) / tot
    T = _n(S) + 0.4 * (m - _n(S)) if _n(S) > 0 else m
    fin = L * X + (1 - L) * Y
    k = (1 - T) / fin if fin > 0 else 1
    return 1 - min(0.97, max(0.03, fin_self * k)) if fin_self > 0 else fallback


def _ko_share(dec, fp, bp, ko, su, b41):
    p = 1 - dec
    w = max(0.6, min(0.9, 0.7 + 0.3 * (p - 0.5)))
    own = w * fp + (1 - w) * bp
    a = _n(b41) if ko != 0 and su != 0 else 0
    ik = -ko / (100 - ko) if ko < 0 else 100 / (100 + ko)
    is_ = -su / (100 - su) if su < 0 else 100 / (100 + su)
    mk = ik / (ik + is_) if a > 0 else own
    return p * (a * mk + (1 - a) * own)


def method_gtd(L, mi):
    """Returns dict with dog/fav dec, ko, sub and gtd, as the tab computes them."""
    ap, aq, ad, ae, ah, ai = (mi.get(k) for k in ("ap", "aq", "ad", "ae", "ah", "ai"))
    al, am, an, S = mi.get("al"), _n(mi.get("am")), _n(mi.get("an")), mi.get("s")
    X, Y = _n(mi.get("cx")), _n(mi.get("cy"))
    V = _dec_share(L, ap, aq, ad, ah, mi, X, _avg(ad, ap, al, S))
    Z = _dec_share(L, ap, aq, ad, ah, mi, Y, _avg(ah, aq, al, S))
    af = 1 - _n(ae) - _n(ad)                      # AF = SUM(1-AE-AD)
    aj = 1 - _n(ai) - _n(ah)
    bpw = 0.5 if am + an == 0 else am / (am + an)
    fpw = bpw if _n(ae) + af == 0 else _n(ae) / (_n(ae) + af)
    W = _ko_share(V, fpw, bpw, _n(mi.get("ko_dog")), _n(mi.get("sub_dog")), mi.get("b41"))
    fpa = _n(ai) / (_n(ai) + aj) if (_n(ai) + aj) != 0 else 0.0   # IFERROR(..., 0)
    bpa = am / (am + an) if (am + an) != 0 else 0.0
    AA = _ko_share(Z, fpa, bpa, _n(mi.get("ko_fav")), _n(mi.get("sub_fav")), mi.get("b41"))
    return {"dog": {"dec": V, "ko": W, "sub": 1 - V - W}, "fav": {"dec": Z, "ko": AA, "sub": 1 - Z - AA}, "gtd": L * V + (1 - L) * Z}
