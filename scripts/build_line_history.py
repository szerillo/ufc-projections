#!/usr/bin/env python3
"""Embed line history + Listed-price check (Block 59, Kirk round 6; rules pre-registered in Round6_PREREG.md, sha 5e450467).

    python3 -I scripts/build_line_history.py --slug ufc_334 --event form/data/events/<slug>.json [--cache .form_cache]

Writes data/embeds/line_history_<slug>.json. Per bout:
  open    : first pre-start snapshot pricing the bout at 3+ BOOK_ORDER books (any books; shown only as "opener")
  current : newest pre-start snapshot with 1+ regulated book, no-vig median over regulated books only, and no more than
            6 h older than the bout's newest snapshot; otherwise null ("current line not available")
  series  : regulated-only points after the opener
  listed  : the sheet export's Listed ML per side, checked against regulated books in the 24 h before the export
No book names reach the page; the "books" lists here are for the audit only.
"""
import argparse, datetime as dt, importlib.util, json, statistics, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
spec = importlib.util.spec_from_file_location("build_form", REPO / "scripts/build_form.py")
BF = importlib.util.module_from_spec(spec); spec.loader.exec_module(BF)

REG = ("draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "circasports")
OFF = ("pinnacle", "betonlineag", "lowvig", "bovada")
MIN_OPEN_BOOKS, CUR_MAX_AGE_H, LISTED_WINDOW_H, TOL = 3, 6, 24, 2


def ts(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def am(d): return BF.dec_to_american(d)


def side_prices(s, a_name, fl):
    """{book: (dec_a, dec_b)} for one snapshot, oriented to fighter a (home/away can swap between snapshots)."""
    out = {}
    mh, mw = BF.name_match(a_name, s["home"]), BF.name_match(a_name, s["away"])
    f_ = (mw > mh) if mh != mw else fl
    for b, m in s["books"].items():
        h2h = m.get("h2h")
        if not h2h or b not in BF.BOOK_ORDER: continue
        h, a = h2h; out[b] = (a, h) if f_ else (h, a)
    return out


def point(s, pr, books):
    ps = [(BF.novig(*pr[b]), pr[b]) for b in books]; ps = [x for x in ps if x[0] is not None]
    if not ps: return None
    return {"t": s["t"], "p": round(statistics.median(x[0] for x in ps), 3), "ma": am(statistics.median(x[1][0] for x in ps)),
            "mb": am(statistics.median(x[1][1] for x in ps)), "nb": len(ps), "books": sorted(books)}


def history(snaps, fl, a_name):
    start = snaps[-1]["start"]; pre = [s for s in snaps if s["t"] <= start] or snaps
    rows = [(s, side_prices(s, a_name, fl)) for s in pre]; rows = [(s, pr) for s, pr in rows if pr]
    if not rows: return None
    op = next(((s, pr) for s, pr in rows if len(pr) >= MIN_OPEN_BOOKS), None)
    newest = rows[-1][0]["t"]
    regs = [(s, pr) for s, pr in rows if set(pr) & set(REG) and (op is None or s["t"] >= op[0]["t"])]
    cur = None
    if regs and (ts(newest) - ts(regs[-1][0]["t"])).total_seconds() <= CUR_MAX_AGE_H * 3600:
        s, pr = regs[-1]; cur = point(s, pr, [b for b in pr if b in REG])
    o = point(op[0], op[1], list(op[1])) if op else None
    if o: o["offshore_only"] = not (set(o["books"]) & set(REG)); o["has_offshore"] = bool(set(o["books"]) & set(OFF))
    ser = [p for p in (point(s, pr, [b for b in pr if b in REG]) for s, pr in regs) if p]
    if len(ser) > 140: ser = ser[:: len(ser) // 140 + 1] + [ser[-1]]
    # the same "current" with offshore books included, for the audit table only (never shown)
    s, pr = rows[-1]; withoff = point(s, pr, list(pr))
    return {"open": o, "current": cur, "series": [{"t": p["t"], "p": p["p"]} for p in ser], "newest": newest, "start": start,
            "audit_all_books_newest": withoff}


def better_or_near(book_am, listed_am):
    """True if a book price is the Listed price or better for the bettor, or within TOL American cents of it."""
    if (book_am > 0) == (listed_am > 0) and abs(book_am - listed_am) <= TOL: return True
    dec = lambda x: 1 + (x / 100 if x > 0 else 100 / -x)
    return dec(book_am) >= dec(listed_am)


def listed_check(snaps, fl, a_name, listed_a, listed_b, until):
    lo = (ts(until) - dt.timedelta(hours=LISTED_WINDOW_H)).isoformat()[:19]; hi = ts(until).isoformat()[:19]
    seen = {"a": None, "b": None}; best = {"a": None, "b": None}
    for s in snaps:
        if not (lo <= s["t"][:19] <= hi): continue
        pr = side_prices(s, a_name, fl)
        for b, (da, db) in pr.items():
            if b not in REG: continue
            for sd, d_, L in (("a", da, listed_a), ("b", db, listed_b)):
                x = am(d_)
                if best[sd] is None or (1 + (x / 100 if x > 0 else 100 / -x)) > (1 + (best[sd][0] / 100 if best[sd][0] > 0 else 100 / -best[sd][0])): best[sd] = (x, b, s["t"][:16])
                if L is not None and better_or_near(x, L): seen[sd] = (x, b, s["t"][:16])
    return {sd: {"listed": L, "ok": seen[sd] is not None, "hit": seen[sd], "best_regulated": best[sd]} for sd, L in (("a", listed_a), ("b", listed_b))}, [lo, hi]


def kalshi_fallback(K, an, bn):
    """Dormant (Kalshi_Fallback_PREREG): both '<fighter> wins' markets, last trade <= 3 h before the read, spread <= 3 cents."""
    pick = lambda nm: max(K["markets"], key=lambda m: BF.name_match(nm, m["name"]), default=None)
    ma, mb = pick(an), pick(bn)
    if not ma or not mb or BF.name_match(an, ma["name"]) < 1 or BF.name_match(bn, mb["name"]) < 1 or ma["event"] != mb["event"]: return None
    for m in (ma, mb):
        if not m["last_trade"] or (ts(K["read_at"]) - ts(m["last_trade"])).total_seconds() > 3 * 3600 or m["ask"] - m["bid"] > 0.03 + 1e-9: return None
    xa, xb = (ma["bid"] + ma["ask"]) / 2, (mb["bid"] + mb["ask"]) / 2
    p = xa / (xa + xb)
    return {"t": K["read_at"], "p": round(p, 3), "ma": am(1 / p), "mb": am(1 / (1 - p)), "nb": 1, "books": ["kalshi"]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", required=True); ap.add_argument("--event", required=True)
    ap.add_argument("--cache", default=str(REPO / ".form_cache")); ap.add_argument("--export", default=None); ap.add_argument("--out", default=None)
    ap.add_argument("--kalshi", default=None, help="data/embeds/kalshi_<slug>.json; used only by the dormant fallback (Kalshi_Fallback_PREREG sha 4b6d292e)")
    a = ap.parse_args()
    ev = json.loads(Path(a.event).read_text()); d = dt.date.fromisoformat(ev["date"])
    exp = json.loads(Path(a.export or REPO / "data/pending" / f"{a.slug}_projections.json").read_text())
    by_id = BF.load_odds(Path(a.cache)); idx = BF.index_odds(by_id)
    out = {"slug": a.slug, "rules": "Round6_PREREG.md sha 5e450467", "archive_newest": max(s["t"] for v in by_id.values() for s in v),
           "export_published_at": exp.get("published_at"), "fights": {}}
    for f in ev["fights"]:
        an, bn = f["a"]["name"], f["b"]["name"]; key = f"{an}|{bn}"
        eid, fl = BF.find_odds(idx, by_id, an, bn, d)
        rec = {"n": f["n"], "event_id": eid}
        if eid: rec.update(history(by_id[eid], fl, an) or {})
        if not rec.get("current") and a.kalshi: rec["current"] = kalshi_fallback(json.loads(Path(a.kalshi).read_text()), an, bn); rec["current_source"] = "kalshi_fallback" if rec["current"] else None
        pf = next((x for x in exp["fights"] if {BF.norm(x["fav"]), BF.norm(x["dog"])} == {BF.norm(an), BF.norm(bn)}
                   or (BF.name_match(x["fav"], an) and BF.name_match(x["dog"], bn)) or (BF.name_match(x["fav"], bn) and BF.name_match(x["dog"], an))), None)
        if pf and eid:
            a_is_fav = BF.name_match(pf["fav"], an) >= BF.name_match(pf["fav"], bn)
            la, lb = (pf["inputs"]["fav_odds"], pf["inputs"]["dog_odds"]) if a_is_fav else (pf["inputs"]["dog_odds"], pf["inputs"]["fav_odds"])
            rec["listed"], rec["listed_window"] = listed_check(by_id[eid], fl, an, la, lb, exp["published_at"])
        out["fights"][key] = rec
        o, c = rec.get("open"), rec.get("current")
        lc = rec.get("listed") or {}
        print(f"{f['n']:>2} {an} vs {bn}: open {o and (o['t'][5:16], o['nb'], o['p'])} current {c and (c['t'][5:16], c['nb'], c['p'])} "
              f"listed {[ (sd, v['listed'], v['ok']) for sd, v in lc.items()]}")
    # Kirk round 16 call 2: this file is public once merged, so no non-US book is named in it; "books" lists keep the count
    def mask(x):
        if isinstance(x, dict): return {k: (["offshore" if b in OFF else b for b in v] if k == "books" and isinstance(v, list) else mask(v)) for k, v in x.items()}
        if isinstance(x, list): return [mask(v) for v in x]
        return x
    p = Path(a.out or REPO / "data/embeds" / f"line_history_{a.slug}.json"); p.write_text(json.dumps(mask(out), indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
