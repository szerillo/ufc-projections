"""Score the registered B42 holdout (PREREG_b42_holdout_card10_2026-11-27.md). Runs the Nov 19 code unchanged
(common_nov19.py, bt_nov19.py) on the sheet's graded archive rows read from an xlsx export, and reports aggregates only.

  python3 -I score_holdout.py <model.xlsx> > score_holdout_out.txt

Step 0 (integrity): the walk-forward on cards 2-9 must reproduce the Nov 19 numbers (S0 Brier 0.2158, A 0.2162, 101 fights);
if it does not, the script stops before scoring card 10."""
import io, json, math, os, random, sys, tempfile, hashlib
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__)); XLSX = sys.argv[1]
print("input", os.path.basename(XLSX), "sha256", hashlib.sha256(open(XLSX, "rb").read()).hexdigest()[:16])
wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
raw = [r for r in wb["Snapshots"].iter_rows(values_only=True) if any(c not in (None, "") for c in r)]
def s(v):
    if v is None: return ""
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return str(v)
H = [s(h) for h in raw[0]]
snap = os.path.join(tempfile.mkdtemp(), "snap.json")
json.dump({"values": [H] + [[s(c) for c in r] + [""] * (len(H) - len(r)) for r in raw[1:]]}, open(snap, "w"))
ns = {}
exec(open(os.path.join(HERE, "common_nov19.py")).read().replace("/tmp/b42h/snap.json", snap), ns)
exec(open(os.path.join(HERE, "bt_nov19.py")).read().replace("sys.path.insert(0,'/tmp/b42h')", "").replace("from common import *", ""), ns)
CARDS, card_rows, methods_for, y_of, rec, pl, f = (ns[k] for k in ("CARDS", "card_rows", "methods_for", "y_of", "rec", "pl", "f"))
print("cards in order:", len(CARDS), [ns["card_rows"](p)[0]["date"] for p in CARDS])
HOLD = CARDS.index(next(p for p in CARDS if "Prochazka" in card_rows(p)[0]["event"]))
assert HOLD == len(CARDS) - 1 == 9, ("card 10 must be the 10th and last card", HOLD, len(CARDS))

def score(cis):
    out = {}; per = {}
    for ci in cis:
        M, info = methods_for(ci)
        for name, qs in M.items():
            for r in card_rows(CARDS[ci]):
                y = y_of(r)
                if y is None: continue
                q = qs[id(r)]
                out.setdefault(name, []).append(((q - y) ** 2, -(y * math.log(q) + (1 - y) * math.log(1 - q)), ci, r, q))
    return out

# Step 0: reproduce Nov 19 (cards 2-9 = indexes 1..8)
S = score(range(1, 9))
b = {k: sum(x[0] for x in v) / len(v) for k, v in S.items()}
n0 = len(S["S0 live per-card B42"])
print(f"\nStep 0, cards 2-9: n={n0}; Brier S0 {b['S0 live per-card B42']:.4f}, A {b['A fixed offset (prior cards)']:.4f} (Nov 19: 101, 0.2158, 0.2162)")
if not (n0 == 101 and round(b["S0 live per-card B42"], 4) == 0.2158 and round(b["A fixed offset (prior cards)"], 4) == 0.2162):
    sys.exit("STOP: the export does not reproduce the Nov 19 backtest; card 10 not scored")
print("Step 0 reproduced: OK")

# Card 10 (holdout)
S10 = score([HOLD]); M10, info10 = methods_for(HOLD)
print(f"\n## Card 10 holdout: {len(S10['S0 live per-card B42'])} graded fights; S0 shift (card average) {info10['live']:.4f}; A fixed offset (cards 1-9) {info10['fixed']:.4f}")
print("option | Brier | log loss")
for k, v in S10.items():
    print(f"{k} | {sum(x[0] for x in v) / len(v):.4f} | {sum(x[1] for x in v) / len(v):.4f}")
a = [x[0] for x in S10["A fixed offset (prior cards)"]]; s0 = [x[0] for x in S10["S0 live per-card B42"]]
d = [x - y for x, y in zip(a, s0)]; diff = sum(d) / len(d)
random.seed(7); bs = sorted(sum(random.choice(d) for _ in d) / len(d) for _ in range(10000)); lo, hi = bs[249], bs[9749]
print(f"\nPRIMARY: Brier A minus S0 on card 10 = {diff:+.5f} (95% CI {lo:+.5f} to {hi:+.5f}, bootstrap over fights, seed 7)")
v = "A holds" if diff <= 0.002 else ("A worse" if lo > 0 else "inconclusive")
print(f"Registered reading: {v}")

# Pooled walk-forward cards 2-10
P = score(range(1, 10))
print("\n## Pooled walk-forward, cards 2-10 (reported, no bar)")
for k, vv in P.items():
    print(f"{k} | n={len(vv)} | Brier {sum(x[0] for x in vv) / len(vv):.4f} | log loss {sum(x[1] for x in vv) / len(vv):.4f}")

# Recs on card 10 (Nov 19 rule function, v4.7 rules, 1u per rec; reported only)
print("\n## Card 10 recs (Nov 19 rule function, v4.7 rules, 1u per rec at snapshot prices; reported only)")
for k, qs in M10.items():
    W = L = 0; u = 0.0; recs = []
    for r in card_rows(CARDS[HOLD]):
        t, side = rec(r, qs[id(r)])
        if t != "BET": continue
        sd = "fav" if side in ("fav", "fav80") else "dog"; p = pl(r, sd)
        if p is None: continue
        W += p > 0; L += p < 0; u += p; recs.append(f"{r['fav'] if sd == 'fav' else r['dog']} ({'W' if p > 0 else 'L'})")
    print(f"{k}: BET {W}-{L}, {u:+.2f} units; " + ", ".join(recs))

# Sensitivity, NOT registered: A with the offset the live sheet actually used on card 10 (B42 = 0.1086, graded rows only),
# instead of the Nov 19 code's all-rows walk-forward offset.
rr = [r for r in card_rows(CARDS[HOLD]) if y_of(r) is not None]
q86 = [ns["q_of"](r, 0.1086) for r in rr]; ys = [y_of(r) for r in rr]
b86 = sum((q - y) ** 2 for q, y in zip(q86, ys)) / len(ys)
print(f"\nSensitivity (not registered): A at the live B42 0.1086 on card 10: Brier {b86:.4f}; minus S0 {b86 - sum(s0) / len(s0):+.5f}")
