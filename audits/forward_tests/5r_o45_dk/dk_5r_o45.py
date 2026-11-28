"""Logger and scorer for the registered DraftKings five-round over 4.5 forward test.
Registration: PREREG_5R_O45_DK_forward_2026-11-27.md + AMEND1_entry_source_2026-11-28.md (this folder). This script applies the
bars as written; it never changes them, never bets, never writes the sheet.

  extract  python3 -I dk_5r_o45.py extract --slug <bp-slug> --event form/data/events/<card>.json --log log.jsonl [--ref origin/main]
           Entry fields for every five-round bout on the card, from the odds-bot feed as committed to main (source 1 of AMEND 1).
           Run any time after the card's first bout (it only reads commits made before each cutoff). Appends; refuses a bout
           already in the log.
  grade    python3 -I dk_5r_o45.py grade --event form/data/events/<card>.json --log log.jsonl
           Writes result fields (UFCStats result in the site event file) into lines that have none. Never rewrites a graded line.
  score    python3 -I dk_5r_o45.py score --log log.jsonl [--today YYYY-MM-DD]
           Interim lines until the 40th qualifying bet or 2027-12-31; then the registered reading.
  manual   python3 -I dk_5r_o45.py manual --log log.jsonl --card-date D --bout "A vs B" --over -130 --under +105 --seen-at ISO
           --source "DK page"|"BFO DK column" [--stage entry|close]   (sources 2 and 3 of AMEND 1, when the feed has no 4.5 line)
Run from a szerillo/ufc-projections checkout."""
import argparse, datetime as dt, json, os, random, subprocess, sys

END_DATE, N_SCORE = "2027-12-31", 40
FROM_DATE = "2026-12-05"


def imp(o): return 100 / (o + 100) if o > 0 else -o / (-o + 100)


def novig_over(over, under):
    a, b = imp(over), imp(under); return a / (a + b)


def ts(s):
    s = str(s).strip().replace(" ", "T")
    if s.endswith("Z"): s = s[:-1] + "+00:00"
    d = dt.datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def snapshot_before(path, cutoff, ref):
    """(commit, commit_time, parsed json) of the last commit on ref touching path with commit time < cutoff."""
    for line in git("log", "--format=%H %cI", ref, "--", path).splitlines():
        h, t = line.split(" ", 1)
        if ts(t) < cutoff:
            return h, t, json.loads(git("show", f"{h}:{path}"))
    return None


def dk_pair(feed, a, b):
    """DraftKings Over/Under for the bout a vs b in a feed snapshot: (line, over_cost, under_cost, updated) or None."""
    sys.path.insert(0, "scripts")
    from card_overrides import bout_is
    for f in feed.get("fights") or []:
        if not bout_is(f["fighter_a"]["name"], f["fighter_b"]["name"], a, b):
            continue
        tr = (f.get("markets") or {}).get("total_rounds") or []
        side = {s.get("label"): (s.get("books") or {}).get("draftkings") or {} for s in tr if isinstance(s, dict)}
        o, u = side.get("Over") or {}, side.get("Under") or {}
        if o.get("cost") is None or u.get("cost") is None:
            return None
        return o.get("line"), int(o["cost"]), int(u["cost"]), o.get("updated")
    return None


def five_round_bouts(ev):
    return [f for f in ev["fights"] if f.get("sched") == 5]


def read_log(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def entry_line(card_date, bout, pr, seen_at, source, close=None, close_seen=None):
    line, over, under = (pr[0], pr[1], pr[2]) if pr else (None, None, None)
    q = bool(pr and line == 4.5 and novig_over(over, under) >= 0.5)
    note = "" if pr else "no DraftKings two-sided total in the feed at entry"
    if pr and line != 4.5:
        note = f"line not 4.5 ({line})"
    return {"card_date": card_date, "bout": bout, "dk_line": line, "dk_over_entry": over, "dk_under_entry": under, "entry_seen_at": seen_at,
            "entry_source": source, "dk_over_close": close[1] if close else None, "dk_under_close": close[2] if close else None,
            "close_seen_at": close_seen, "qualifies": q, "result_rounds": None, "went_over": None, "units": None, "risked": None, "note": note}


def extract(a):
    ev = json.load(open(a.event)); path = f"data/{a.slug}_odds.json"
    starts = [ts(f["start"]) for f in ev["fights"] if f.get("start")]
    if not starts: sys.exit("REFUSED: the event file has no start times")
    first = min(starts); have = {(l["card_date"], l["bout"]) for l in read_log(a.log)}
    out = []
    for f in five_round_bouts(ev):
        bout = f"{f['a']['name']} vs {f['b']['name']}"
        if (ev["date"], bout) in have:
            print("skip (already logged):", bout); continue
        s = snapshot_before(path, first, a.ref)
        pr = dk_pair(s[2], f["a"]["name"], f["b"]["name"]) if s else None
        bs = ts(f["start"]) if f.get("start") else first
        c = snapshot_before(path, bs, a.ref)
        cp = dk_pair(c[2], f["a"]["name"], f["b"]["name"]) if c else None
        L = entry_line(ev["date"], bout, pr, s[1] if s else None, f"odds-bot feed {s[0][:8]}" if s else "none",
                       cp if (cp and cp[0] == 4.5) else None, c[1] if c else None)
        out.append(L); print(json.dumps(L))
    with open(a.log, "a") as fh:
        for L in out: fh.write(json.dumps(L) + "\n")


def manual(a):
    have = read_log(a.log)
    pr = (4.5, int(a.over), int(a.under), a.seen_at)
    if a.stage == "close":
        hit = [l for l in have if l["card_date"] == a.card_date and l["bout"] == a.bout]
        if not hit or hit[0].get("went_over") is not None: sys.exit("REFUSED: no ungraded entry line for that bout")
        hit[0].update(dk_over_close=pr[1], dk_under_close=pr[2], close_seen_at=a.seen_at)
        open(a.log, "w").write("".join(json.dumps(l) + "\n" for l in have)); return
    if any(l["card_date"] == a.card_date and l["bout"] == a.bout for l in have): sys.exit("REFUSED: bout already logged")
    with open(a.log, "a") as fh: fh.write(json.dumps(entry_line(a.card_date, a.bout, pr, a.seen_at, a.source)) + "\n")


def went_over(res):
    """AMEND 1 settlement: over if a decision (or a draw to the distance) or a finish in round 5 after 2:30. NC = void (None)."""
    if not res or str(res.get("kind") or "").lower().replace("_", " ") in ("nc", "no contest") or not (res.get("method") or res.get("kind") == "draw"):
        return None
    m = str(res.get("method") or "")
    if "Decision" in m or "DEC" in m.upper() or res.get("kind") == "draw":
        return True
    r = int(res.get("round") or 0); mm, ss = (str(res.get("time") or "0:00").split(":") + ["0"])[:2]
    return r == 5 and int(mm) * 60 + int(ss) > 150


def units(price, won):
    """Sean's unit rule: minus money to win 1u, even or plus money risk 1u. Returns (units, risked)."""
    if price < 0:
        risk = -price / 100; return (1.0 if won else -risk), risk
    return (price / 100 if won else -1.0), 1.0


def grade(a):
    ev = json.load(open(a.event)); L = read_log(a.log); n = 0
    sys.path.insert(0, "scripts"); from card_overrides import bout_is
    for l in L:
        if l["card_date"] != ev["date"] or l.get("went_over") is not None or l.get("note", "").startswith("void"):
            continue
        x, y = l["bout"].split(" vs ")
        f = next((f for f in ev["fights"] if bout_is(f["a"]["name"], f["b"]["name"], x, y)), None)
        if not f or not f.get("result"): continue
        wo = went_over(f["result"])
        l["result_rounds"] = f"R{f['result'].get('round')} {f['result'].get('time')} {f['result'].get('method')}"
        if wo is None:
            l["note"] = "void (no contest)"; n += 1; continue
        l["went_over"] = wo
        if l["qualifies"]:
            l["units"], l["risked"] = units(l["dk_over_entry"], wo)
        n += 1
    open(a.log, "w").write("".join(json.dumps(l) + "\n" for l in L)); print(f"graded {n} line(s)")


def clv(l):
    if l.get("dk_over_close") is None: return None
    return (novig_over(l["dk_over_close"], l["dk_under_close"]) - novig_over(l["dk_over_entry"], l["dk_under_entry"])) * 100


def reading(B, today):
    if not B:
        return "no qualifying graded bet yet", None
    u = sum(b["units"] for b in B); r = sum(b["risked"] for b in B); roi = u / r
    random.seed(7); bs = []
    for _ in range(10000):
        s = [random.choice(B) for _ in B]; bs.append(sum(x["units"] for x in s) / sum(x["risked"] for x in s))
    bs.sort(); lo, hi = bs[499], bs[9499]
    cl = [c for c in (clv(b) for b in B) if c is not None]; mclv = sum(cl) / len(cl) if cl else None
    final = len(B) >= N_SCORE or today >= END_DATE
    if not final:
        v = f"interim, not scored ({len(B)} of {N_SCORE} bets)"
    elif roi > 0 and lo > 0 and mclv is not None and mclv >= 0:
        v = "SUPPORTED"
    elif roi < 0:
        v = "NOT SUPPORTED"
    else:
        v = "NOT SHOWN"
    hit = sum(b["went_over"] for b in B) / len(B); pri = sum(novig_over(b["dk_over_entry"], b["dk_under_entry"]) for b in B) / len(B)
    return (f"bets {len(B)}, record {sum(b['went_over'] for b in B)}-{sum(not b['went_over'] for b in B)}, units {u:+.2f} on {r:.2f} risked, "
            f"ROI {roi * 100:+.1f}% (90% bootstrap {lo * 100:+.1f}% to {hi * 100:+.1f}%), hit {hit * 100:.1f}% vs priced {pri * 100:.1f}%, "
            f"mean CLV {('%+.2f pts' % mclv) if mclv is not None else 'n/a'} -> {v}"), v


def score(a):
    L = [l for l in read_log(a.log) if l["card_date"] >= FROM_DATE]
    today = a.today or dt.date.today().isoformat()
    B = [l for l in L if l["qualifies"] and l.get("went_over") is not None]
    U = [l for l in L if not l["qualifies"] and l.get("went_over") is not None and l.get("dk_line") == 4.5]
    txt, _ = reading(B, today)
    print("DK 5R O4.5 forward test:", txt)
    print(f"descriptive, DK no-vig over under 50%: n={len(U)}, went over {sum(l['went_over'] for l in U)}")
    for l in L:
        if l.get("note"): print("  note:", l["card_date"], l["bout"], l["note"])


ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
p = sp.add_parser("extract"); p.add_argument("--slug", required=True); p.add_argument("--event", required=True); p.add_argument("--log", required=True); p.add_argument("--ref", default="origin/main")
p = sp.add_parser("grade"); p.add_argument("--event", required=True); p.add_argument("--log", required=True)
p = sp.add_parser("score"); p.add_argument("--log", required=True); p.add_argument("--today")
p = sp.add_parser("manual"); p.add_argument("--log", required=True); p.add_argument("--card-date", required=True); p.add_argument("--bout", required=True)
p.add_argument("--over", required=True); p.add_argument("--under", required=True); p.add_argument("--seen-at", required=True)
p.add_argument("--source", choices=["DK page", "BFO DK column"], default="DK page"); p.add_argument("--stage", choices=["entry", "close"], default="entry")
if __name__ == "__main__":
    a = ap.parse_args(); {"extract": extract, "grade": grade, "score": score, "manual": manual}[a.cmd](a)
