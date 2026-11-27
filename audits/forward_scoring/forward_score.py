"""Forward scoring for registered tests T1 (power de-vig), T2 (Markov ML term) and T4 (women re-fit), plus the registered
forward shadow logs for T3 (drifting-dog veto, kept + shadow) and T6 (80%+ favorite rule, two sizings).
Bars: PREREG_model_review_2026-11-24.md and PREREG_T4_women_refit.md on audit-locks. This script only applies them; it never
moves a bar, never writes the sheet, never bets. Read-only on everything it is given.

Inputs per forward card (from 2026-12-05 on):
  * the T0 walkout lock CSV (audit-locks analysis/snap_locks/<date>.csv): Snapshots rows, then "#PropSnap" rows,
    written and hashed by snapshot_t0.gs BEFORE the first bout. Results are never taken from it.
  * the card's site event file (form/data/events/<date>-*.json): UFCStats result per bout (winner side), matched by names.

  verify  python3 -I forward_score.py verify --lock L.csv --event E.json [--commit-time ISO]
  score   python3 -I forward_score.py score --cards cards.json --close close.json --archive form/data/events [--out report.md]

cards.json: [{"date": "2026-12-05", "lock": "path/2026-12-05.csv", "event": "form/data/events/2026-12-05-....json",
              "lock_commit_utc": "2026-12-05T14:50:00Z", "first_bout_utc": "2026-12-05T15:00:00Z", "test": false}, ...]
A card counts only if its lock commit precedes its first bout and every bout row has a matched result (draw/NC excluded).
Run from a szerillo/ufc-projections checkout (imports scripts/fighter_names.py and scripts/sheet_v47.py).
"""
import argparse, csv, glob, hashlib, io, json, math, os, re, sys, datetime as dt
sys.path.insert(0, "scripts")
import fighter_names as FN
import sheet_v47 as SV

T1_CARDS, T2_CARDS = 10, 10          # "the next 10 graded cards from 2026-12-05 on"
T4_WOMEN, T4_CARDS = 30, 20          # T4: 30 graded women's bouts or 20 forward cards, whichever first
T3_DRIFT = 0.03                      # T3: drifting = close dog % at least 3 points below open dog %
FAV80, FAV80_FLOOR, T6_CAP = 0.80, -500, 2.0   # T6: 80%+ listed favorite; v4.9 floor (B46); risk cap sizing
FORWARD_FROM = "2026-12-05"
# Part (b) was scored once on 2026-11-24 (run_tests_out.txt, audit-locks): n=158, log loss diff -0.00147, MET. That verdict is
# frozen and reused as bar (2). Its rows are rebuilt here only for the pooled 70%+ favorite gap of part (c); results that landed
# after the registered run (UFC 334, Nov 21) are cut so the pool matches the scored set as closely as the archive allows.
B_FROZEN = {"n": 158, "diff": -0.00147, "met": True}
B_CUTOFF = "2026-11-14"
imp = SV.implied
lg = lambda p: math.log(p / (1 - p))
sg = lambda x: 1 / (1 + math.exp(-x))


def power(a, b):
    """Power de-vig of an American price pair; returns side-a probability (same code as run_tests.py)."""
    ia, ib = imp(a), imp(b); lo, hi = 1.0, 3.0
    for _ in range(60):
        k = (lo + hi) / 2; lo, hi = (k, hi) if ia ** k + ib ** k > 1 else (lo, k)
    return ia ** k


def mult(a, b):
    return imp(a) / (imp(a) + imp(b))


def ll(ps, ys):
    return -sum(y * math.log(min(max(p, 1e-6), 1 - 1e-6)) + (1 - y) * math.log(1 - min(max(p, 1e-6), 1 - 1e-6)) for p, y in zip(ps, ys)) / len(ps)


def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ps)


def num(x):
    try:
        return float(str(x).replace("%", "").replace(",", "")) if str(x).strip() not in ("", "-") else None
    except ValueError:
        return None


# ------------------------------------------------------------------ lock file
def read_lock(path):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8")
    snap = text.split("\n#PropSnap\n")[0]
    rows = list(csv.DictReader(io.StringIO(snap)))
    return hashlib.sha256(raw).hexdigest(), rows


def params(row):
    s = row.get("T0 params") or ""
    out = {k: num(v) for k, v in re.findall(r"(B4[1-6])[^=]*=\s*([-\d.]+)", s)}
    m = re.search(r"women=([-\d.]+)", s); out["women"] = num(m.group(1)) if m else None
    m = re.search(r"rules (v[\d.]+)", s); out["rules"] = m.group(1) if m else None
    return out


def bout_inputs(r, prm):
    d, i = num(r["dog price (D)"]), num(r["fav price (I)"])
    tag = str(r.get("tag") or "")
    return {"dog": r["dog"], "fav": r["fav"], "dog_odds": d, "fav_odds": i,
            "open_dog": num(r.get("dog open F")), "markov": num(r.get("Markov J")), "shift": prm.get("B42") or 0.0,
            "tap": num(r.get("Tap C")), "junk": num(r.get("Junk D")), "tip": num(r.get("Tip E")),
            "ctx": (r.get("K code") or "").strip() or None, "manual": 0.0, "women": tag.lower().startswith("w"),
            "G_stored": num(r.get("dog listed G (sheet)")), "Q_stored": num(r.get("model Q")),
            "close_dog": num(r.get("dog CLOSE (consensus)")), "flag_stored": (r.get("flag AA") or "").strip()}


# ------------------------------------------------------------------ results from the site event file (UFCStats)
def dog_won(event, dog, fav):
    f = find_bout(event, dog, fav)
    if f is None:
        return "unmatched"
    for f in [f]:
        a, b = f["a"]["name"], f["b"]["name"]
        r = f.get("result") or {}
        side = "a" if FN.name_match(a, dog) and FN.name_match(b, fav) else "b" if FN.name_match(b, dog) and FN.name_match(a, fav) else None
        if side is None:   # one-sided match from find_bout: orient on the side that matched
            side = "a" if FN.name_match(a, dog) or FN.name_match(b, fav) else "b"
        if r.get("kind") != "win" or r.get("winner") not in ("a", "b"):
            return "excluded (" + str(r.get("kind") or "no result") + ")"
        return 1.0 if r["winner"] == side else 0.0
    return "unmatched"


def find_bout(event, dog, fav):
    """Both names match, else the only bout where one of the two names matches (spelling variants such as
    Seok Hyun Ko / Seokhyeon Ko, Jose Henrique Souza / Jose Souza)."""
    F = event["fights"]
    both = [f for f in F if {FN.name_match(f["a"]["name"], dog) and FN.name_match(f["b"]["name"], fav),
                             FN.name_match(f["b"]["name"], dog) and FN.name_match(f["a"]["name"], fav)} & {True}]
    if both:
        return both[0]
    one = [f for f in F if any(FN.name_match(f[s]["name"], n) for s in "ab" for n in (dog, fav))]
    return one[0] if len(one) == 1 else None


def verify(a):
    sha, rows = read_lock(a.lock)
    ev = json.load(open(a.event))
    prm = params(rows[0]) if rows else {}
    starts = [f.get("start") for f in ev["fights"] if f.get("start")]
    first = min(starts) if starts else None
    kinds = sorted({r.get("T0 snap kind") for r in rows})
    print(f"lock {a.lock}: sha256 {sha}")
    print(f"rows {len(rows)}; snap kinds {kinds}; params {prm}")
    bad = [r["dog"] + " vs " + r["fav"] for r in rows if num(r.get("dog price (D)")) is None or num(r.get("fav price (I)")) is None]
    print("rows missing D/I prices:", bad or "none")
    names = [f["a"]["name"] + " vs " + f["b"]["name"] for f in ev["fights"]]
    unl = [n for n in names if not any(any(FN.name_match(s_, r["dog"]) or FN.name_match(s_, r["fav"]) for s_ in n.split(" vs ")) for r in rows)]
    print("event bouts with no lock row:", unl or "none")
    print("first bout (event file):", first or "unknown")
    if a.commit_time and first:
        ok = a.commit_time.replace("Z", "") < first.replace(" ", "T")
        print("lock committed before first bout:", "YES" if ok else "NO -> card does not count")
    mm = []
    for r in rows:
        x = bout_inputs(r, prm)
        if None in (x["dog_odds"], x["fav_odds"]):
            continue
        m = SV.row(x)
        if x["G_stored"] is not None and abs(m["listed"] - x["G_stored"]) > 0.0015:
            mm.append(f"{x['dog']}: G mirror {m['listed']:.4f} vs stored {x['G_stored']:.4f}")
        if x["Q_stored"] is not None and abs(m["Q"] - x["Q_stored"]) > 0.0015:
            mm.append(f"{x['dog']}: Q mirror {m['Q']:.4f} vs stored {x['Q_stored']:.4f}")
    print("mirror vs stored (tolerance 0.15 pt):", mm or "all match")


# ------------------------------------------------------------------ scoring
def load_cards(a):
    cards = []
    for c in json.load(open(a.cards)):
        sha, rows = read_lock(c["lock"])
        ev = json.load(open(c["event"]))
        prm = params(rows[0]) if rows else {}
        on_time = c.get("lock_commit_utc", "9") < c.get("first_bout_utc", "0")
        bouts, skipped = [], []
        for r in rows:
            x = bout_inputs(r, prm)
            y = dog_won(ev, x["dog"], x["fav"])
            if not isinstance(y, float) or None in (x["dog_odds"], x["fav_odds"]):
                skipped.append(f"{x['dog']} vs {x['fav']}: {y if not isinstance(y, float) else 'no D/I price'}")
                continue
            m_on = SV.row(x)
            m_off = SV.row({**x, "markov": None})           # H = G, so the 0.15*(H-G) term is exactly zero
            q_ok = x["Q_stored"] is None or abs(m_on["Q"] - x["Q_stored"]) <= 0.0015
            # mirror Q stands in for the sheet only where it reproduces the stored Q; otherwise remove the term from stored Q
            q_with = x["Q_stored"] if x["Q_stored"] is not None else m_on["Q"]
            q_without = m_off["Q"] if q_ok else SV.clamp(q_with - SV.BETA * (m_on["H"] - m_on["listed"]))
            bouts.append({**x, "y": y, "g_mult": mult(x["dog_odds"], x["fav_odds"]), "g_power": power(x["dog_odds"], x["fav_odds"]),
                          "q_with": q_with, "q_without": q_without, "q_mirror_ok": q_ok, "rec_with": m_on["rec"], "rec_without": m_off["rec"],
                          "flag": x["flag_stored"] or m_on["flag"]})
        cards.append({**c, "sha": sha, "params": prm, "on_time": on_time, "bouts": bouts, "skipped": skipped,
                      "counts": on_time and not c.get("test") and c["date"] >= FORWARD_FROM})
    cards.sort(key=lambda c: c["date"])
    return cards


def rec_units(rec, b):
    """Sean's unit rule at listed best prices: favorites bet to win 1u, even or plus money risk 1u. BET recs only."""
    if not rec.startswith("BET"):
        return 0.0, 0
    side = "fav" if rec.startswith("BET " + b["fav"]) else "dog"
    price = b["fav_odds"] if side == "fav" else b["dog_odds"]
    won = (b["y"] == 0.0) if side == "fav" else (b["y"] == 1.0)
    if price < 0:
        return (1.0 if won else price / 100), 1
    return (price / 100 if won else -1.0), 1


def t1(cards, close_path, archive_dir):
    B = [b for c in cards for b in c["bouts"]]
    out = [f"## T1 power de-vig (forward part a, plus part c pooled with part b)", f"forward cards counted: {len(cards)} of {T1_CARDS}; bouts {len(B)}"]
    if not B:
        return out + ["T1: PENDING (no counted forward card yet)"]
    y = [b["y"] for b in B]
    lm, lp = ll([b["g_mult"] for b in B], y), ll([b["g_power"] for b in B], y)
    out.append(f"(a) log loss G_mult {lm:.5f}  G_power {lp:.5f}  diff {lp - lm:+.5f}; Brier {brier([b['g_mult'] for b in B], y):.5f} / {brier([b['g_power'] for b in B], y):.5f}")
    # part (b) rows rebuilt exactly as run_tests.py does, for the pooled favorite gap in part (c)
    EV = {}
    for p in sorted(glob.glob(os.path.join(archive_dir, "202[2-6]-*.json"))):
        EV.setdefault(os.path.basename(p)[:10], []).append(json.load(open(p)))
    R = []
    for c in json.load(open(close_path)):
        if c.get("best_a") is None or c.get("best_b") is None or c["sched"][:10] >= B_CUTOFF:
            continue
        d0 = dt.date.fromisoformat(c["sched"][:10]); hit = None
        for dd in (d0, d0 - dt.timedelta(days=1)):
            for ev in EV.get(dd.isoformat(), []):
                for f in ev["fights"]:
                    r_ = f.get("result") or {}
                    if r_.get("kind") != "win":
                        continue
                    if FN.name_match(f["a"]["name"], c["a"]) and FN.name_match(f["b"]["name"], c["b"]): hit = 1.0 if r_["winner"] == "a" else 0.0
                    elif FN.name_match(f["b"]["name"], c["a"]) and FN.name_match(f["a"]["name"], c["b"]): hit = 1.0 if r_["winner"] == "b" else 0.0
        if hit is not None:
            R.append((mult(c["best_a"], c["best_b"]), power(c["best_a"], c["best_b"]), hit))
    if not R:
        return out + ["(b) close set gave no matched bouts on this checkout: cannot pool part (c); T1 not scored"]
    lmb, lpb = ll([r[0] for r in R], [r[2] for r in R]), ll([r[1] for r in R], [r[2] for r in R])
    out.append(f"(b) frozen registered result: n={B_FROZEN['n']}, diff {B_FROZEN['diff']:+.5f}, MET. Rebuilt for (c): n={len(R)}, diff {lpb - lmb:+.5f}"
               + ("" if len(R) == B_FROZEN["n"] else " (rebuilt n differs from the scored n; (c) uses the rebuilt rows, disclosed)"))
    # part (c): favorites priced 70%+ under power, pooled (a)+(b); gap = |mean priced fav p - fav win rate|
    pool = [(1 - b["g_mult"], 1 - b["g_power"], 1 - b["y"]) for b in B] + [(max(m, 1 - m), max(p, 1 - p), (y_ if p >= .5 else 1 - y_)) for m, p, y_ in R]
    F = [t for t in pool if t[1] >= 0.70]
    gm = abs(sum(t[0] for t in F) / len(F) - sum(t[2] for t in F) / len(F)) if F else None
    gp = abs(sum(t[1] for t in F) / len(F) - sum(t[2] for t in F) / len(F)) if F else None
    out.append(f"(c) favorites 70%+ pooled n={len(F)}: calibration gap mult {gm * 100:.2f} pts, power {gp * 100:.2f} pts" if F else "(c) no 70%+ favorites yet")
    parts = [lp <= lm, B_FROZEN["met"], (gp is not None and gp < gm)]
    status = "interim, not scored" if len(cards) < T1_CARDS else ("PASS" if all(parts) else "FAIL")
    out.append(f"bars: (1) {'met' if parts[0] else 'not met'}, (2) {'met' if parts[1] else 'not met'}, (3) {'met' if parts[2] else 'not met'} -> T1 {status}")
    return out


def t2(cards):
    out = [f"## T2 Markov ML term (Q with 0.15*(H-G) vs without)", f"forward cards counted: {len(cards)} of {T2_CARDS}"]
    if not cards:
        return out + ["T2: PENDING (no counted forward card yet)"]
    wins = 0; uw = uo = 0.0; nw = no = 0; YW, PW, PO = [], [], []
    for c in cards:
        B = c["bouts"]
        if not B:
            continue
        y = [b["y"] for b in B]; bw, bo = brier([b["q_with"] for b in B], y), brier([b["q_without"] for b in B], y)
        wins += bo < bw
        for b in B:
            u, k = rec_units(b["rec_with"], b); uw += u; nw += k
            u, k = rec_units(b["rec_without"], b); uo += u; no += k
        YW += y; PW += [b["q_with"] for b in B]; PO += [b["q_without"] for b in B]
        mis = sum(not b["q_mirror_ok"] for b in B)
        out.append(f"{c['date']}: n={len(B)} Brier with {bw:.5f} without {bo:.5f} -> {'without' if bo < bw else 'with'} better" + (f"; {mis} rows used stored-Q minus term (mirror off)" if mis else ""))
    bw, bo = brier(PW, YW), brier(PO, YW)
    out.append(f"pooled: Brier with {bw:.5f} without {bo:.5f} (diff {bo - bw:+.5f}); without better on {wins} cards")
    out.append(f"rec units (BET recs, 1u by the unit rule at listed best prices): with {uw:+.2f}u on {nw} bets, without {uo:+.2f}u on {no} bets")
    if len(cards) < T2_CARDS:
        v = "interim, not scored"
    elif bo <= bw and wins >= 6 and uo >= uw:
        v = "REMOVE the term (all three bars met; adoption still needs Sean's OK)"
    elif bw <= bo - 0.002:
        v = "KEEP (Q-with wins by 0.002+ Brier)"
    else:
        v = "INCONCLUSIVE: keep the term, extend 10 more cards"
    return out + [f"-> T2 {v}"]


def fit(M, y, it=60):
    """Newton logistic fit, no numpy (rows are small lists)."""
    k = len(M[0]); b = [0.0] * k
    for _ in range(it):
        g = [0.0] * k; H = [[1e-9 * (i == j) for j in range(k)] for i in range(k)]
        for x, t in zip(M, y):
            p = sg(sum(bi * xi for bi, xi in zip(b, x))); w = p * (1 - p)
            for i in range(k):
                g[i] += (t - p) * x[i]
                for j in range(k): H[i][j] += w * x[i] * x[j]
        b = [bi + di for bi, di in zip(b, solve(H, g))]
    return b


def solve(A, v):
    n = len(v); M = [row[:] + [v[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]; M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def archive_rows(archive_dir):
    X = []
    for p in sorted(glob.glob(os.path.join(archive_dir, "202[2-6]-*.json"))):
        if os.path.basename(p)[:10] >= FORWARD_FROM:
            continue
        for f in json.load(open(p))["fights"]:
            c = (f.get("odds") or {}).get("close"); r_ = f.get("result") or {}
            if not isinstance(c, dict) or c.get("p") is None or r_.get("kind") != "win" or not 0.01 < c["p"] < 0.99 or not (c.get("ma") and c.get("mb")):
                continue
            pw = power(c["ma"], c["mb"]); ya = 1.0 if r_["winner"] == "a" else 0.0
            X.append((lg(max(pw, 1 - pw)), ya if pw >= .5 else 1 - ya, 1.0 if (f.get("wc") or "").startswith("Women") else 0.0))
    return X


def t4(cards, archive_dir):
    out = ["## T4 women term re-fit (walk-forward on forward cards)"]
    base = archive_rows(archive_dir); nwom = 0; ncard = 0
    LA = []; LB = []; LC = []; YY = []; wins = 0; cards_w = 0; last_size = None
    for c in cards:
        ncard += 1
        W = [b for b in c["bouts"] if b["women"]]
        if W and sum(x[2] for x in base) < 30:
            out.append(f"{c['date']}: women bouts {len(W)}, training base too small to fit ({len(base)} bouts, {int(sum(x[2] for x in base))} women's): not scored")
            W = []
        if W:
            b0, b1, b2 = fit([[1.0, x[0], x[2]] for x in base], [x[1] for x in base])
            sizes = []
            for b in W:
                pf = 1 - power(b["dog_odds"], b["fav_odds"]); L = lg(max(pf, 1e-6))
                sizes.append((1 - sg(b0 + b1 * L)) - (1 - sg(b0 + b1 * L + b2)))   # dog p without minus with, as a fraction
            size = sum(sizes) / len(sizes); last_size = size
            qa = [b["q_with"] for b in W]
            qb = [SV.clamp(b["q_with"] + 0.04 - size) for b in W]
            qc = [SV.clamp(b["q_with"] + 0.04) for b in W]
            y = [b["y"] for b in W]
            cards_w += 1; wins += ll(qb, y) < ll(qa, y)
            LA += qa; LB += qb; LC += qc; YY += y; nwom += len(W)
            out.append(f"{c['date']}: women bouts {len(W)}, fitted size {size * 100:+.2f} pts; log loss A {ll(qa, y):.4f} B {ll(qb, y):.4f} C {ll(qc, y):.4f}")
        # the card's bouts join the training base before the next card is scored
        for b in c["bouts"]:
            pf = 1 - power(b["dog_odds"], b["fav_odds"])
            base.append((lg(max(pf, 1e-6)), 1 - b["y"] if pf >= .5 else b["y"], 1.0 if b["women"] else 0.0))
    out.append(f"graded women's bouts {nwom} of {T4_WOMEN}; forward cards {ncard} of {T4_CARDS}")
    if not YY:
        return out + ["T4: PENDING (no women's bout on a counted forward card yet)"]
    la, lb, lc = ll(LA, YY), ll(LB, YY), ll(LC, YY)
    out.append(f"pooled: log loss A {la:.5f} B {lb:.5f} C {lc:.5f}; Brier A {brier(LA, YY):.5f} B {brier(LB, YY):.5f} C {brier(LC, YY):.5f}; B beat A on {wins} of {cards_w} cards")
    if nwom < T4_WOMEN and ncard < T4_CARDS:
        return out + ["-> T4 interim, logged only (no interim adoption)"]
    pts = last_size * 100
    bars = [lb < la, wins > cards_w / 2, not (2 <= pts <= 6)]
    v = f"RE-FIT to {min(8.0, max(0.0, round(pts * 2) / 2)):.1f} pts (goes to Sean)" if all(bars) else "KEEP -4"
    if lc < min(la, lb):
        v += "; NOTE: C (no women term) beat A and B, which needs a new registration"
    return out + [f"bars: (1) {bars[0]}, (2) {bars[1]}, (3) last size {pts:.2f} outside 2-6: {bars[2]} -> T4 {v}"]


def dog_units(price, won):
    """T3 units: risk 1u on the dog at its price (plus money risks 1u; a dog at minus money also risks 1u, as registered)."""
    if price > 0:
        return (price / 100 if won else -1.0), 1.0
    return (100 / -price if won else -1.0), 1.0


def t3(cards):
    """T3 shadow (registered outcome: keep the veto + shadow log). No bar; logged every card."""
    out = ["## T3 shadow: drifting dogs on forward cards (veto kept; shadow only, no bar)"]
    if not cards:
        return out + ["T3 shadow: no counted forward card yet"]
    S = {"vetoed (sheet flag 'no dog bet (drifting)')": [], "drifting by T3 (3+ pts)": [], "other dogs": []}
    for c in cards:
        for b in c["bouts"]:
            if b["open_dog"] is None:
                continue
            close = b["close_dog"] if b["close_dog"] is not None else b["g_mult"]
            drift = b["open_dog"] - close
            u, r = dog_units(b["dog_odds"], b["y"] == 1.0)
            row = (c["date"], b["dog"], b["dog_odds"], round(drift * 100, 1), "W" if b["y"] == 1.0 else "L", round(u, 2))
            if b["flag"].startswith("no dog bet (drifting)"):
                S["vetoed (sheet flag 'no dog bet (drifting)')"].append(row)
            (S["drifting by T3 (3+ pts)"] if drift >= T3_DRIFT else S["other dogs"]).append(row)
    for k, R in S.items():
        if R:
            u = sum(r[5] for r in R); w = sum(r[4] == "W" for r in R)
            out.append(f"{k}: n={len(R)} won {w} units {u:+.2f} ROI {u / len(R) * 100:+.1f}% (risk 1u each at the walkout best dog price)")
        else:
            out.append(f"{k}: none")
    for r in S["vetoed (sheet flag 'no dog bet (drifting)')"]:
        out.append(f"  vetoed {r[0]} {r[1]} {r[2]:+.0f}: open-close {r[3]:+.1f} pts, {r[4]}, {r[5]:+.2f}u")
    return out


def t6(cards):
    """T6 shadow: the 80%+ favorite rule under to-win 1u and a 2u risk cap. No pass or fail (Sean's decision)."""
    out = ["## T6 shadow: 80%+ listed favorites, two sizings (no bar; Sean decides)"]
    R = []
    for c in cards:
        for b in c["bouts"]:
            if 1 - b["g_mult"] < FAV80 or b["fav_odds"] >= 0:
                continue
            won = b["y"] == 0.0; tw = -b["fav_odds"] / 100
            a = 1.0 if won else -tw                          # A: to win 1u (risk = price / 100)
            rb = min(tw, T6_CAP); bb = rb * 100 / -b["fav_odds"] if won else -rb   # B: risk capped at 2u
            R.append((c["date"], b["fav"], b["fav_odds"], "BET" if b["fav_odds"] >= FAV80_FLOOR else "PASS (v4.9 floor)", won, a, tw, bb, rb))
    if not R:
        return out + ["T6 shadow: no 80%+ favorite on a counted forward card yet"]
    for lab, ix, rx in (("A to-win 1u", 5, 6), ("B risk cap 2u", 7, 8)):
        for scope, S in (("all 80%+", R), ("v4.9 BET only (-500 or longer)", [r for r in R if r[3] == "BET"])):
            if S:
                out.append(f"{lab}, {scope}: bets {len(S)}, record {sum(r[4] for r in S)}-{sum(not r[4] for r in S)}, units {sum(r[ix] for r in S):+.2f}, "
                           f"risked {sum(r[rx] for r in S):.2f}, worst single loss " + (f"{min(r[ix] for r in S if not r[4]):+.2f}" if any(not r[4] for r in S) else "none"))
    for r in R:
        out.append(f"  {r[0]} {r[1]} {r[2]:+.0f} [{r[3]}]: {'W' if r[4] else 'L'}  A {r[5]:+.2f}u  B {r[7]:+.2f}u")
    return out


def score(a):
    allc = load_cards(a)
    C = [c for c in allc if c["counts"]]
    L = [f"# Forward scoring report (generated {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')})", ""]
    for c in allc:
        L.append(f"- {c['date']} lock sha256 {c['sha'][:16]}..., params {c['params'].get('rules')} B42={c['params'].get('B42')}, bouts scored {len(c['bouts'])}, "
                 f"{'COUNTS' if c['counts'] else 'does not count (' + ('test' if c.get('test') else 'late lock' if not c['on_time'] else 'before ' + FORWARD_FROM) + ')'}"
                 + (f"; skipped: {'; '.join(c['skipped'])}" if c["skipped"] else ""))
    T = [c for c in allc if c.get("test")]
    if T and not C:
        L += ["", "TEST RUN: the cards below are fixtures (pre-registration history), shown to prove the pipeline only; nothing here is a score.", ""]
        C = T
    for blk in (t1(C, a.close, a.archive), t2(C), t3(C), t4(C, a.archive), t6(C)):
        L += [""] + blk
    txt = "\n".join(L) + "\n"
    print(txt)
    if a.out:
        open(a.out, "w").write(txt)


ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
p1 = sp.add_parser("verify"); p1.add_argument("--lock", required=True); p1.add_argument("--event", required=True); p1.add_argument("--commit-time")
p2 = sp.add_parser("score"); p2.add_argument("--cards", required=True); p2.add_argument("--close", required=True); p2.add_argument("--archive", default="form/data/events"); p2.add_argument("--out")
a = ap.parse_args(); {"verify": verify, "score": score}[a.cmd](a)
