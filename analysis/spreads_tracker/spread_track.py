"""UFC point-spread tracker (registered Nov 24 2026). No auto-betting: it locks our prices, records book prices, grades.
Run from a szerillo/ufc-projections checkout with the UFCStats cache (.form_cache) and the audit-locks files beside it.

  lock   python3 -I spread_track.py lock  --slug S --event form/data/events/<card>.json --books books.json --out <date>.jsonl [--stage lock|close]
  table  python3 -I spread_track.py table --locks <date>.jsonl
  grade  python3 -I spread_track.py grade --locks <date>.jsonl [...] --results results.json

Prices: v0 (spreads_v0, price-only margin term) and v1 (registered fix: margin term on price + Fight Form round dominance q,
3-round bouts; 5-round bouts stay v0). P(fav covers -s) = P(fav finish) + P(fav decision win) x P(3-judge margin > s | fav
decision win); the finish/decision split is Sean's published export (never the staging copy).
books.json: [{"fighter": "Dan Hooker", "line": -3.5, "price": -120, "book": "DraftKings", "seen_at": "2026-11-20T18:00Z"}, ...]
  US-regulated books only (plus Kalshi / Novig / Polymarket if they ever list spreads; Kalshi has none today).
Lock rule: a "lock" row is refused once the card's first bout has started; a "close" row is refused for any bout that has
started. Rows are only appended; nothing is edited after a result."""
import argparse, json, math, sys, os, re, csv, collections, datetime as dt, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
FZ = json.load(open(os.path.join(HERE, "frozen_v1.json")))
lg = lambda p: math.log(p / (1 - p)); sg = lambda x: 1 / (1 + math.exp(-x))
def imp(o): return 100 / (o + 100) if o > 0 else -o / (-o + 100)
def ml(p): return f"-{round(100*p/(1-p))}" if p >= 0.5 else f"+{round(100*(1-p)/p)}"
def margin_p(model, sched, k, pf, q):
    if sched == 5 or model == "v0" or q is None:   # v1 = v0 on 5-round bouts and when a fighter has under 3 UFC rounds
        b = FZ["v0"].get(f"{sched}_{k}")
        return None if b is None else sg(b[0] + b[1] * lg(pf))
    b = FZ["v1"][f"3_{k}"]; return sg(b[0] + b[1] * lg(pf) + b[2] * lg(q))
def round_rates(cache, cut):
    sys.path.insert(0, "scripts"); import build_embed_metrics as B
    alias = {B.fold(k): v for k, v in json.load(open("form/data/name_aliases.json")).items() if not k.startswith("_")}
    canon = lambda s: B.fold(alias.get(B.fold(s), s))
    date = {r["EVENT"].strip(): dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").date().isoformat() for r in csv.DictReader(open(f"{cache}/ufc_event_details.csv", encoding="utf-8"))}
    res = {(r["EVENT"].strip(), r["BOUT"].strip()): r for r in csv.DictReader(open(f"{cache}/ufc_fight_results.csv", encoding="utf-8"))}
    rows = collections.defaultdict(dict)
    for r in csv.DictReader(open(f"{cache}/ufc_fight_stats.csv", encoding="utf-8")):
        m = re.match(r"Round (\d+)", r["ROUND"] or "")
        if m: rows[(r["EVENT"].strip(), r["BOUT"].strip())][(int(m.group(1)), r["FIGHTER"].strip())] = r
    cum = collections.defaultdict(lambda: [0.0, 0]); disp = {}
    for (e, b), r in res.items():
        d_ = date.get(e); byr = rows.get((e, b)); names = [x.strip() for x in b.split(" vs. ")]
        if not d_ or d_ >= cut or not byr or len(names) != 2: continue
        decided = r["OUTCOME"] in ("W/L", "L/W"); last_r = int(r["ROUND"]); winner = names[0] if r["OUTCOME"] == "W/L" else names[1] if decided else None
        for rd in range(1, min(last_r, 5) + 1):
            x, y = byr.get((rd, names[0])), byr.get((rd, names[1]))
            if not x or not y: continue
            if rd == last_r and decided and "Decision" not in r["METHOD"]: wa = 1.0 if winner == names[0] else 0.0
            else: sc = B.rscore(x) - B.rscore(y); wa = 1.0 if sc > 0 else 0.0 if sc < 0 else 0.5
            for n_, w_ in ((names[0], wa), (names[1], 1 - wa)): cum[canon(n_)][0] += w_; cum[canon(n_)][1] += 1; disp[canon(n_)] = n_
    K = FZ["K_pseudo_rounds"]; import fighter_names as FN
    def get(name):
        t = cum.get(canon(name))
        if t is None:   # sheet vs UFCStats spelling (Daniel / Dan Hooker): the pipeline's nickname-aware match, only if unique
            hits = [k for k, v in disp.items() if FN.name_match(v, name)]
            t = cum[hits[0]] if len(hits) == 1 else [0, 0]
        return None if t[1] < FZ["min_rounds"] else (t[0] + 0.5 * K) / (t[1] + K)
    return get
def lock(a):
    sys.path.insert(0, "scripts"); import fighter_names as FN
    now = dt.datetime.now(dt.timezone.utc)
    V = json.load(open(f"data/{a.slug}_projections.json"))
    if V.get("staging"): sys.exit("REFUSED: staging export; lock only on Sean's published numbers")
    ev = json.load(open(a.event)); O = json.load(open(f"data/{a.slug}_odds.json"))
    starts = {f["n"]: f.get("start") for f in ev["fights"]}
    first = min((dt.datetime.fromisoformat(s.replace(" ", "T") + "+00:00") for s in starts.values() if s), default=None)
    if first is None: first = dt.datetime.fromisoformat(ev["date"] + "T14:00:00+00:00")   # no start times: 9 am ET card day, conservative
    test = os.environ.get("SPREAD_TRACK_TEST") == "1"
    if test and not os.path.abspath(a.out).startswith("/tmp/"): sys.exit("REFUSED: test rows only outside the audit files")
    if a.stage == "lock" and now >= first and not test: sys.exit(f"REFUSED: card started at {first.isoformat()}; locks must precede results")
    books = json.load(open(a.books)) if a.books else []
    rate = round_rates(a.cache, ev["date"])
    def nv(name):
        for f in O["fights"]:
            for o in f["markets"]["moneyline"]:
                if FN.name_match(o["label"], name): return o["books"].get("consensus", {}).get("no_vig_pct")
    sha = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]
    out = open(a.out, "a"); n = 0
    for f in V["fights"]:
        evf = next((x for x in ev["fights"] if {FN.name_match(x["a"]["name"], f["fav"]) or FN.name_match(x["b"]["name"], f["fav"])} == {True} and (FN.name_match(x["a"]["name"], f["dog"]) or FN.name_match(x["b"]["name"], f["dog"]))), None)
        st = starts.get(evf["n"]) if evf else None
        if a.stage == "close" and st and not test and now >= dt.datetime.fromisoformat(st.replace(" ", "T") + "+00:00"): continue
        s = f["sheet"]; m = f["method"]; sched = 5 if f["tag"].endswith("-5") else 3
        pfav = s["true_fav"]; ff = pfav * (m["fav"]["ko"] + m["fav"]["sub"]); fdw = pfav * m["fav"]["dec"]
        nvp = nv(f["fav"]); pf = nvp / 100 if nvp else pfav
        rf, rd_ = rate(f["fav"]), rate(f["dog"]); q = None if rf is None or rd_ is None else rf * (1 - rd_) / (rf * (1 - rd_) + (1 - rf) * rd_)
        qres = None if q is None else (lg(q) - (FZ["q_on_price"][0] + FZ["q_on_price"][1] * lg(pf))) / FZ["q_resid_sd"]
        fair = {}
        for mdl in ("v0", "v1"):
            fair[mdl] = {}
            for line in (1.5, 2.5, 3.5, 4.5, 5.5, 6.5):
                mp = margin_p(mdl, sched, int(line + 0.5), pf, q)
                if mp is not None: fair[mdl][str(-line)] = round(ff + fdw * mp, 4)
        bk = []
        for b in books:
            side = "fav" if FN.name_match(b["fighter"], f["fav"]) else "dog" if FN.name_match(b["fighter"], f["dog"]) else None
            if not side: continue
            favline = b["line"] if side == "fav" else -b["line"]; key = str(favline)
            pc = {k: (fair[k].get(key) if side == "fav" else (1 - fair[k][key] if key in fair[k] else None)) for k in fair}
            bk.append({**b, "side": side, "implied": round(imp(b["price"]), 4), "p_model": pc,
                       "edge": {k: (round(v - imp(b["price"]), 4) if v is not None else None) for k, v in pc.items()}})
        row = {**({"test": True} if test else {}), "stage": a.stage, "at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "slug": a.slug, "fav": f["fav"], "dog": f["dog"], "rounds": sched,
               "export_published_at": V["published_at"], "odds_updated_at": O.get("updated_at"), "script_sha16": sha,
               "p_fav_sheet": round(pfav, 4), "p_fav_finish": round(ff, 4), "p_fav_dec_win": round(fdw, 4), "mkt_nv_fav": pf,
               "q_round": None if q is None else round(q, 4), "q_resid_sd": None if qres is None else round(qres, 2), "fair": fair, "books": bk}
        out.write(json.dumps(row) + "\n"); n += 1
    print(f"{a.stage}: {n} fights appended to {a.out} at {now.isoformat(timespec='seconds')}; book rows {sum(1 for _ in books)}")
def table(a):
    rows = [json.loads(l) for l in open(a.locks)]; last = {}
    for r in rows: last[(r["fav"], r["dog"], r["stage"])] = r
    print("| Fight | Fav fair -3.5 v0 / v1 | Round model vs price | Book lines (price, edge v1 / v0) |\n|---|---|---|---|")
    L = [r for (k, r) in last.items() if k[2] == "lock"]
    for r in sorted(L, key=lambda r: -(r["q_resid_sd"] or -9)):
        f0, f1 = r["fair"]["v0"].get("-3.5"), r["fair"]["v1"].get("-3.5")
        flag = "" if r["q_resid_sd"] is None else (f"{r['q_resid_sd']:+.2f} SD" + (" FLAG: round model well above price" if r["q_resid_sd"] >= 0.5 else " FLAG: round model well below price" if r["q_resid_sd"] <= -0.5 else ""))
        bks = "; ".join(f"{b['fighter']} {b['line']:+g} {b['price']:+d} {b['book']} ({(b['edge']['v1'] or 0)*100:+.1f} / {(b['edge']['v0'] or 0)*100:+.1f})" for b in r["books"]) or "no spread posted"
        print(f"| {r['fav']} vs {r['dog']} ({r['rounds']}R) | {f0*100:.1f}% ({ml(f0)}) / {f1*100:.1f}% ({ml(f1)}) | {flag} | {bks} |")
def grade(a):
    R = json.load(open(a.results))["fights"]
    def find(fav, dog):
        for x in R:
            if {x["winner"], x["loser"]} == {fav, dog}: return x
    B = collections.defaultdict(lambda: [0, 0, 0.0, 0.0]); allr = []
    for p in a.locks:
        rows = [json.loads(l) for l in open(p)]; L = {}; C = {}
        for r in rows: (L if r["stage"] == "lock" else C)[(r["fav"], r["dog"])] = r
        for k, r in L.items():
            x = find(*k)
            if not x: continue
            fav_m = None
            if x["method"].startswith("Decision"):
                sgn = 1 if x["winner"] == r["fav"] else -1; fav_m = sgn * sum(w - l for w, l in x["cards"])
            for b in r["books"]:
                fl = b["line"] if b["side"] == "fav" else -b["line"]
                fav_cov = (x["winner"] == r["fav"] and not x["method"].startswith("Decision")) or (fav_m is not None and fav_m > -fl)
                win = fav_cov if b["side"] == "fav" else not fav_cov
                if x["method"].startswith(("Draw", "No Contest")): continue
                stake_risk = (-b["price"] / 100) if b["price"] < 0 else 1.0; payout = 1.0 if b["price"] < 0 else b["price"] / 100
                u = payout if win else -stake_risk
                e = b["edge"]["v1"] if b["edge"]["v1"] is not None else b["edge"]["v0"]
                bucket = "<0" if e < 0 else "0-2" if e < .02 else "2-4" if e < .04 else "4+"
                cl = next((cb for cb in C.get(k, {}).get("books", []) if cb["fighter"] == b["fighter"] and cb["line"] == b["line"] and cb["book"] == b["book"]), None)
                clv = None if not cl else round(cl["implied"] - b["implied"], 4)
                B[bucket][0] += 1; B[bucket][1] += win; B[bucket][2] += u; B[bucket][3] += (clv or 0)
                allr.append((os.path.basename(p), r["fav"], r["dog"], b["fighter"], b["line"], b["price"], round(e * 100, 1), "W" if win else "L", round(u, 2), clv))
    print("card | fight | side | lock price | edge v1 % | result | units (1u to-win fav / 1u risk dog) | CLV (close implied minus lock)")
    for t in allr: print(" | ".join(map(str, t)))
    print("\nedge bucket | bets | won | units | avg CLV")
    for k in ("<0", "0-2", "2-4", "4+"):
        n, w, u, c = B[k]
        if n: print(f"{k} | {n} | {w} ({w/n*100:.0f}%) | {u:+.2f} | {c/n*100:+.2f} pts")
ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
p1 = sp.add_parser("lock"); p1.add_argument("--slug", required=True); p1.add_argument("--event", required=True); p1.add_argument("--books"); p1.add_argument("--out", required=True); p1.add_argument("--stage", default="lock", choices=["lock", "close"]); p1.add_argument("--cache", default=".form_cache")
p2 = sp.add_parser("table"); p2.add_argument("--locks", required=True)
p3 = sp.add_parser("grade"); p3.add_argument("--locks", nargs="+", required=True); p3.add_argument("--results", required=True)
a = ap.parse_args(); {"lock": lock, "table": table, "grade": grade}[a.cmd](a)
