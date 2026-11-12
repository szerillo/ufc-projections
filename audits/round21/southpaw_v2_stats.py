"""Southpaw box v2 numbers (prereg Southpaw_Box_v2_PREREG_2026-11-12.md). Corrected set = main's published southpaw bets
(fresh-code members of bouts priced in main's event files) with the right namesake row (namesake_effect.json).
Prices, no-vig p and winners from main's event files. Writes southpaw_v2.json with per-bet list."""
import json, math, random, subprocess, pathlib, collections
H = pathlib.Path(__file__).parent; repo = "/tmp/e5"
git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True).stdout
MO = {}
for p_ in git("ls-tree", "--name-only", "origin/main", "form/data/events/").split():
    e = json.loads(git("show", f"origin/main:{p_}"))
    for f in e["fights"]:
        if f.get("odds"): MO[(e["date"], frozenset((f["a"]["name"], f["b"]["name"])))] = (f["a"]["name"], f["odds"], (f.get("result") or {}).get("winner"))
dec = lambda m: 1 + (m / 100 if m > 0 else 100 / -m)
NS = json.load(open(H / "namesake_effect.json"))
rem = {(d, frozenset((a, b)), a if s == "a" else b) for d, a, b, k, s, x in NS if k == "southpaw" and x == "REMOVE"}
rows = [l.strip().split("|") for l in open("/tmp/s21_members_multi.txt") if l.startswith("southpaw|")]
mem = [(r[1], r[2], r[3], r[4]) for r in rows if (r[1], frozenset((r[2], r[3]))) in MO and (r[1], frozenset((r[2], r[3])), r[2] if r[4] == "a" else r[3]) not in rem]
added = [(d, a, b, s) for d, a, b, k, s, x in NS if k == "southpaw" and x == "ADD" and (d, frozenset((a, b))) in MO]
bets = []
for d, a, b, s in mem + added:
    an, o, w = MO[(d, frozenset((a, b)))]
    me = a if s == "a" else b
    side = "a" if me == an else "b"
    p = o["close"]["p"] if side == "a" else 1 - o["close"]["p"]; pr = dec(o["close"]["ma" if side == "a" else "mb"])
    bets.append({"d": d, "fighter": me, "opp": b if s == "a" else a, "p": round(p, 4), "price": round(pr, 4), "won": w == side})
n = len(bets); w = sum(b["won"] for b in bets); act = w / n; exp = sum(b["p"] for b in bets) / n
r = [(b["price"] - 1) if b["won"] else -1.0 for b in bets]; roi = sum(r) / n
margin = sum(b["p"] * b["price"] - 1 for b in bets) / n
cards = collections.defaultdict(list)
for b, x in zip(bets, r): cards[b["d"]].append(x)
C = list(cards.values()); random.seed(20261112); Bc = []
for _ in range(10000):
    pk = [random.choice(C) for _ in range(len(C))]; Bc.append(sum(sum(c) for c in pk) / sum(len(c) for c in pk))
Bc.sort()
split = {}
for lab, sel in (("favorite", lambda b: b["p"] >= 0.5), ("underdog", lambda b: b["p"] < 0.5)):
    xs = [(b, x) for b, x in zip(bets, r) if sel(b)]
    split[lab] = {"n": len(xs), "won": round(sum(b["won"] for b, _ in xs) / len(xs), 4), "implied": round(sum(b["p"] for b, _ in xs) / len(xs), 4),
                  "roi": round(sum(x for _, x in xs) / len(xs), 4)}
out = {"angle": "southpaw", "n": n, "w": w, "act": round(act, 4), "exp": round(exp, 4), "roi": round(roi, 4), "pnl": round(sum(r), 2),
       "win_ci": [round(act - 1.96 * math.sqrt(act * (1 - act) / n), 4), round(act + 1.96 * math.sqrt(act * (1 - act) / n), 4)],
       "cards": len(C), "roi_ci_boot_cards": [round(Bc[249], 4), round(Bc[9749], 4)], "margin": round(margin, 4),
       "boot_cards_share_above_margin": round(sum(x > margin for x in Bc) / len(Bc), 3), "split": split,
       "published_n": n - len(added), "added": [list(x) for x in added], "labs_angles": 46, "bets": bets}
json.dump(out, open(H / "southpaw_v2.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "bets"}, indent=1))
