"""DRAFT Dec 5 odds + D-code check. 4-book median (FanDuel, Caesars, BetRivers, Unibet; pipeline Step 1a), median of the
books present when fewer than 4 post; no-vig by multiplicative de-vig of the two medians (display only; the sheet does its own).
D-code (pipeline §4): DOG + 3 or fewer UFC/DWCS bouts + last pre-UFC promotion minor = auto-veto of the dog. Veto only.
Usage: python3 -I build_odds_dcode.py bfo_raw.txt sherdog.txt kdstats.txt out_prefix"""
import json, re, statistics, sys
raw, sher, kd, out = sys.argv[1:5]
COL = ["Polymarket", "Kalshi", "FanDuel", "Caesars", "BetRivers", "BetWay", "Unibet", "BetMGM", "DraftKings"]
MED4 = ["FanDuel", "Caesars", "BetRivers", "Unibet"]
def imp(o): return 100 / (o + 100) if o > 0 else -o / (-o + 100)
def med(xs):
    xs = sorted(xs); n = len(xs)
    return None if not n else xs[n // 2] if n % 2 else round((xs[n // 2 - 1] + xs[n // 2]) / 2)
rows = []
for l in open(raw):
    if l.startswith("#") or "|" not in l: continue
    n, v = l.rstrip("\n").split("|"); p = dict(zip(COL, [int(x) if x else None for x in v.split(",")])); rows.append((n, p))
feed = {}; ufcn = {}
for l in open(sher):
    m = re.match(r'"([^"]+)":\s*(\{.*?\})', l)
    if m: feed[m.group(1).lower()] = json.loads(m.group(2))["d_code_feeder"],
for l in open(kd):
    m = re.match(r'"([^"]+)":\s*(\{.*?\})', l)
    if m: ufcn[m.group(1).lower()] = json.loads(m.group(2))["ufc_fights"]
ufcn.setdefault("ivan gnizditskiy", 0)
def key(n):
    n = n.lower().replace("junyong", "junyong")
    for k in set(feed) | set(ufcn):
        if k.split()[-1] == n.split()[-1] and k.split()[0][:3] == n.split()[0][:3]: return k
    return n
L = ["fight|fighter|4-book median|books used|no-vig %|dog|UFC bouts|feeder|D-code"]; D = []
for i in range(0, len(rows), 2):
    pair = rows[i:i + 2]; ms = []
    for n, p in pair:
        used = [b for b in MED4 if p[b] is not None]; ms.append((n, med([p[b] for b in used]), used))
    ia, ib = imp(ms[0][1]), imp(ms[1][1]); nv = [ia / (ia + ib), ib / (ia + ib)]
    dog = 0 if nv[0] < nv[1] else 1
    for j, (n, m, used) in enumerate(ms):
        k = key(n); u = ufcn.get(k); f = feed.get(k, ("n/a (4+ UFC bouts)",))[0]
        is_dog = j == dog; dc = "VETO (D-code)" if is_dog and u is not None and u <= 3 and f == "minor" else ("exempt (major feeder)" if is_dog and u is not None and u <= 3 else "-")
        if dc.startswith("VETO"): D.append(n)
        L.append(f"{i // 2 + 1}|{n}|{m:+d}|{len(used)}|{nv[j] * 100:.1f}|{'DOG' if is_dog else 'fav'}|{u if u is not None else '4+'}|{f}|{dc}")
open(out + ".txt", "w").write("# DRAFT card (UFC.com not yet confirmed). BFO pull 2026-11-27 ~09:35 UTC. Fight numbers follow BFO page order, not UFC.com order.\n" + "\n".join(L) + "\n")
print("\n".join(L)); print("D-code vetoes:", D)
