"""Rebuild the exact published research.json set for Labs angles, per bet, and their uncertainty.
Fresh build angle members (instrumented form_model, /tmp/angle_members.txt) minus the bouts the round-7 matcher fix added
(odds on embeds-v5, not on main) = the published set. Per bet: all-books close p and price (as the research close).
Stats: win CI (normal), ROI CI (normal), ROI CI by bootstrap over BETS and CLUSTERED BY CARD (10,000 draws each),
margin = expected ROI if the no-vig close were the true chance."""
import sys, json, subprocess, random, math, statistics, datetime as dt, importlib.util, pathlib
repo = pathlib.Path("/tmp/e5"); sys.path.insert(0, str(repo / "scripts"))
sp = importlib.util.spec_from_file_location("bf", repo / "scripts/build_form.py"); BF = importlib.util.module_from_spec(sp); sp.loader.exec_module(BF)
by = BF.load_odds(repo / ".form_cache"); idx = BF.index_odds(by)
git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout
def odds_bouts(ref):
    out = set()
    for p in git("ls-tree", "--name-only", ref, "form/data/events/").split():
        e = json.loads(git("show", f"{ref}:{p}"))
        for f in e["fights"]:
            if f.get("odds"): out.add((e["date"], frozenset((f["a"]["name"], f["b"]["name"]))))
    return out
NEW = odds_bouts("HEAD") - odds_bouts("origin/main")
R = {x["id"]: x for x in json.load(open(repo / "form/data/research.json"))["angles"]}
dec = lambda m: 1 + (m / 100 if m > 0 else 100 / -m)
mem = [l.strip().split("|") for l in open("/tmp/angle_members.txt") if l.strip()]
out = {}
for ang in sys.argv[1:]:
    rows = [m[1:] for m in mem if m[0] == ang]
    pub = [r for r in rows if (r[0], frozenset((r[1], r[2]))) not in NEW]
    bets = []
    for d, a, b, s in pub:
        dd = dt.date.fromisoformat(d); eid, fl = BF.find_odds(idx, by, a, b, dd); o = BF.summarize_odds(by[eid], fl, a_name=a)
        p = o["close"]["p"] if s == "a" else 1 - o["close"]["p"]; price = dec(o["close"]["ma"] if s == "a" else o["close"]["mb"])
        bets.append((d, p, price))
    # winners from UFCStats via the site's event files (result.winner)
    W = {}
    for pth in (repo / "form/data/events").glob("*.json"):
        e = json.load(open(pth))
        for f in e["fights"]: W[(e["date"], f["a"]["name"], f["b"]["name"])] = (f.get("result") or {}).get("winner")
    won = []
    for (d, a, b, s) in pub:
        w = W.get((d, a, b)); w = w if w is not None else ({"a": "b", "b": "a"}[W[(d, b, a)]] if W.get((d, b, a)) else None)
        won.append(w == s)
    n = len(bets); r = [(pr - 1) if wn else -1.0 for (d, p, pr), wn in zip(bets, won)]
    act = sum(won) / n; exp = sum(p for _, p, _ in bets) / n; roi = sum(r) / n; sd = statistics.pstdev(r); se = sd / math.sqrt(n)
    margin = sum(p * pr - 1 for _, p, pr in bets) / n
    random.seed(20261112); Bb = sorted(sum(random.choice(r) for _ in range(n)) / n for _ in range(10000))
    cards = {}
    for (d, p, pr), x in zip(bets, r): cards.setdefault(d, []).append(x)
    C = list(cards.values()); random.seed(20261112); Bc = []
    for _ in range(10000):
        pick = [random.choice(C) for _ in range(len(C))]; Bc.append(sum(sum(c) for c in pick) / sum(len(c) for c in pick))
    Bc.sort()
    pubv = R[ang]
    out[ang] = {"n": n, "w": sum(won), "act": round(act, 4), "exp": round(exp, 4), "roi": round(roi, 4), "pnl": round(sum(r), 2),
                "matches_research_json": (n == pubv["n"] and sum(won) == pubv["w"] and abs(round(exp, 4) - pubv["exp"]) < 1e-4 and abs(round(sum(r), 2) - pubv["pnl_c"]) < 0.01),
                "win_ci": [round(act - 1.96 * math.sqrt(act * (1 - act) / n), 4), round(act + 1.96 * math.sqrt(act * (1 - act) / n), 4)],
                "roi_sd": round(sd, 3), "roi_se": round(se, 4), "roi_ci": [round(roi - 1.96 * se, 4), round(roi + 1.96 * se, 4)],
                "roi_ci_boot_bets": [round(Bb[249], 4), round(Bb[9749], 4)], "cards": len(C), "roi_ci_boot_cards": [round(Bc[249], 4), round(Bc[9749], 4)],
                "margin_roi": round(margin, 4), "boot_cards_share_above_margin": round(sum(x > margin for x in Bc) / len(Bc), 3),
                "fresh_n": len(rows), "dropped_matcher_fix": len(rows) - n}
    print(ang, json.dumps(out[ang]))
json.dump(out, open(pathlib.Path(__file__).with_name("angle_stats.json"), "w"), indent=1)
