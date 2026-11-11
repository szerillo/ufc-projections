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
    elif fav_edge >= 0.02 and (f.get("tip") or 0) >= 0.5:
        rec = f"BET {f['fav']} (fade sharp dog)"
    elif fav_edge >= 0.03:
        rec = f"BET {f['fav']}"
    elif dog_edge >= 0.05 and flag == "ok":
        rec = f"lean {f['dog']}"
    elif fav_edge >= 0.02:
        rec = f"lean {f['fav']}"
    else:
        rec = "-"
    if drift <= -0.03 and rec != "-":
        rec += f" [late: ->FAV {abs(drift)*100:.0f}%]"
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
