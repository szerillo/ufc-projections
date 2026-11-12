#!/usr/bin/env python3
"""
MMA Fight Form — static data build.

Joins three sources into the JSON the site reads from form/data/:

  1. Fight results + per-round stats (UFCStats, via the public GPL-3.0 dataset
     github.com/Greco1899/scrape_ufc_stats — refreshed after every event)
  2. Odds history (The Odds API snapshots archived in szerillo/sharp-tracker:
     data/oddsapi/compact/mma.jsonl.gz 2022-2025, data/oddsapi/mma/*.json.gz 2026,
     data/mma/oddsapi_live.jsonl for the live window)
  3. Model projections (FIGHTS + USER_PROJECTIONS_BY_FIGHT inside each
     ufc_*_fight_form.html widget in this repo) and BettingPros snapshots in data/

Usage:  python3 scripts/build_form.py [--cache DIR] [--no-download]
Writes: form/data/index.json, events/*.json, fighters/*.json, search.json, model.json
"""
from __future__ import annotations
import form_model
import card_overrides
import publish_source
import math
import argparse, csv, datetime as dt, glob, gzip, io, json, os, re, statistics, subprocess, sys, unicodedata, urllib.request
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "form" / "data"
UFCSTATS_BASE = "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/"
UFCSTATS_FILES = ["ufc_event_details.csv", "ufc_fight_results.csv", "ufc_fight_stats.csv", "ufc_fighter_tott.csv"]
ST_RAW = "https://raw.githubusercontent.com/szerillo/sharp-tracker/main/data/"
ST_API_TREE = "https://api.github.com/repos/szerillo/sharp-tracker/git/trees/main:data/oddsapi/mma"
BOOK_ORDER = ["pinnacle", "draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "betonlineag", "lowvig", "bovada", "circasports"]
BOOK_LABEL = {"pinnacle": "Pinnacle", "draftkings": "DraftKings", "fanduel": "FanDuel", "betmgm": "BetMGM",
              "williamhill_us": "Caesars", "betrivers": "BetRivers", "betonlineag": "BetOnline", "lowvig": "LowVig",
              "bovada": "Bovada", "circasports": "Circa"}


# ----------------------------------------------------------------- helpers
def fetch(url: str, dest: Path, timeout=120):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "mma-fight-form-build/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        dest.write_bytes(r.read())


def norm(name: str) -> str:
    s = unicodedata.normalize("NFD", name or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s.replace("-", " ").replace("'", ""))
    return re.sub(r"\s+", " ", s).strip()


SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def toks(name: str) -> set:
    return {t for t in norm(name).split() if len(t) >= 3 and t not in SUFFIX}


def slugify(name: str) -> str:
    return norm(name).replace(" ", "-")


def name_match(a: str, b: str) -> int:
    """0 no match, 1 token overlap incl. a last-name-ish token, 2 same token set, 3 exact."""
    na, nb = norm(a), norm(b)
    if na == nb:
        return 3
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return 0
    if ta == tb:
        return 2
    # Block 59m: same name once spaces are removed, in either token order ("Heili Alateng" = "Alatengheili")
    import itertools
    ja, jb = na.replace(" ", ""), nb.replace(" ", "")
    if ja == jb or any("".join(p) == jb for p in itertools.permutations(na.split())) or any("".join(p) == ja for p in itertools.permutations(nb.split())):
        return 2
    la, lb = na.split()[-1], nb.split()[-1]
    if la in tb or lb in ta:
        return 1
    if len(ta & tb) >= 2:
        return 1
    return 0


def pair_match(a, b, h, w):
    """Score matching fighters (a,b) to an odds event (home h, away w). Returns (score, flipped)."""
    s1 = min(name_match(a, h), name_match(b, w))
    s2 = min(name_match(a, w), name_match(b, h))
    if s1 == 0 and s2 == 0:
        return 0, False
    return (s1, False) if s1 >= s2 else (s2, True)


def of(s):
    m = re.match(r"\s*(\d+)\s+of\s+(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def mmss(s):
    m = re.match(r"\s*(\d+):(\d+)", s or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0


def dec_to_american(d):
    if not d or d <= 1:
        return None
    return int(round((d - 1) * 100)) if d >= 2 else int(round(-100 / (d - 1)))


def american_to_dec(a):
    if a is None:
        return None
    return 1 + a / 100 if a > 0 else 1 + 100 / (-a)


def novig(h, a):
    if not h or not a or h <= 1 or a <= 1:
        return None
    ph, pa = 1 / h, 1 / a
    return ph / (ph + pa)


def r3(x):
    return None if x is None else round(x, 4)


# ----------------------------------------------------------------- 1. UFCStats
def load_ufcstats(cache: Path):
    ev = list(csv.DictReader(open(cache / "ufc_event_details.csv", encoding="utf-8")))
    res = list(csv.DictReader(open(cache / "ufc_fight_results.csv", encoding="utf-8")))
    st = list(csv.DictReader(open(cache / "ufc_fight_stats.csv", encoding="utf-8")))
    tott = list(csv.DictReader(open(cache / "ufc_fighter_tott.csv", encoding="utf-8")))

    events = {}
    for e in ev:
        name = e["EVENT"].strip()
        d = dt.datetime.strptime(e["DATE"].strip(), "%B %d, %Y").date()
        events[name] = {"name": name, "date": d, "location": e["LOCATION"].strip(), "url": e["URL"].strip(), "fights": []}

    # per-fight per-fighter totals
    tot = defaultdict(lambda: defaultdict(lambda: {"kd": 0, "sl": 0, "sa": 0, "tl": 0, "ta": 0, "sub": 0, "ctrl": 0,
                                                    "head": 0, "body": 0, "leg": 0, "dist": 0, "clinch": 0, "ground": 0, "rounds": 0}))
    for r in st:
        key = (r["EVENT"].strip(), r["BOUT"].strip())
        f = (r["FIGHTER"] or "").strip()
        if not f:
            continue
        t = tot[key][f]
        try:
            t["kd"] += int(float(r["KD"] or 0))
        except ValueError:
            pass
        l, a = of(r["SIG.STR."]); t["sl"] += l; t["sa"] += a
        l, a = of(r["TD"]); t["tl"] += l; t["ta"] += a
        try:
            t["sub"] += int(float(r["SUB.ATT"] or 0))
        except ValueError:
            pass
        t["ctrl"] += mmss(r["CTRL"])
        for k, col in (("head", "HEAD"), ("body", "BODY"), ("leg", "LEG"), ("dist", "DISTANCE"), ("clinch", "CLINCH"), ("ground", "GROUND")):
            t[k] += of(r[col])[0]
        t["rounds"] += 1
        rn = re.search(r"(\d+)", r["ROUND"] or "")
        rn = int(rn.group(1)) if rn else 0
        if rn == 1:
            t["r1"] = t.get("r1", 0) + of(r["SIG.STR."])[0]
        elif rn >= 3:
            t["late"] = t.get("late", 0) + of(r["SIG.STR."])[0]

    seen = set()
    for r in res:
        en, bout = r["EVENT"].strip(), r["BOUT"].strip()
        if en not in events or bout.count(" vs. ") != 1 or (en, bout) in seen:
            continue
        seen.add((en, bout))
        a, b = [x.strip() for x in bout.split(" vs. ")]
        oc = r["OUTCOME"].strip()
        winner = "a" if oc == "W/L" else "b" if oc == "L/W" else None
        kind = "draw" if oc == "D/D" else "nc" if oc == "NC/NC" else "win"
        fmt = r["TIME FORMAT"].strip()
        m = re.match(r"(\d+) Rnd", fmt)
        sched = int(m.group(1)) if m else None
        try:
            rnd = int(r["ROUND"])
        except ValueError:
            rnd = None
        tsec = mmss(r["TIME"])
        secs = ((rnd - 1) * 300 + tsec) if (rnd and "5-5" in fmt) else None
        wc = re.sub(r"\s+Bout$", "", r["WEIGHTCLASS"].strip())
        title = "Title" in wc
        t = tot.get((en, bout), {})
        fight = {
            "event": en, "a": a, "b": b, "winner": winner, "kind": kind,
            "method": r["METHOD"].strip(), "round": rnd, "time": r["TIME"].strip(), "sched": sched, "secs": secs,
            "wc": wc.replace("UFC ", "").replace(" Title", ""), "title": title, "ref": r["REFEREE"].strip(),
            "details": r["DETAILS"].strip(), "url": r["URL"].strip(),
            "sa": dict(t.get(a, {})) or None, "sb": dict(t.get(b, {})) or None,
        }
        events[en]["fights"].append(fight)
    for e in events.values():
        n = len(e["fights"])
        for i, f in enumerate(e["fights"]):
            f["n"] = n - i  # main event = highest n
            f["date"] = e["date"]

    bio = {}
    for t in tott:
        nm = norm(t["FIGHTER"])
        if nm in bio and bio[nm].get("_dup"):
            continue
        entry = {"ht": t["HEIGHT"].strip().replace(" ", ""), "wt": t["WEIGHT"].strip(), "reach": t["REACH"].strip().replace('"', ""),
                 "stance": t["STANCE"].strip(), "dob": t["DOB"].strip(), "url": t["URL"].strip()}
        for k in ("ht", "reach", "dob", "wt"):
            if entry[k] in ("--", ""):
                entry[k] = None
        if entry["dob"]:
            try:
                entry["dob"] = dt.datetime.strptime(entry["dob"], "%b %d, %Y").date().isoformat()
            except ValueError:
                entry["dob"] = None
        if nm in bio:
            bio[nm]["_dup"] = True  # two UFCStats fighters share this name
        else:
            bio[nm] = entry
    return events, bio


# ----------------------------------------------------------------- 2. Elo
def run_elo(events):
    elo = defaultdict(lambda: 1500.0)
    nf = defaultdict(int)
    for e in sorted(events.values(), key=lambda x: x["date"]):
        for f in sorted(e["fights"], key=lambda x: x["n"]):
            a, b = f["a"], f["b"]
            ra, rb = elo[a], elo[b]
            f["elo_a"], f["elo_b"] = round(ra), round(rb)
            f["nf_a"], f["nf_b"] = nf[a], nf[b]
            if f["kind"] == "nc":
                continue
            ea = 1 / (1 + 10 ** ((rb - ra) / 400))
            sa = 0.5 if f["kind"] == "draw" else (1.0 if f["winner"] == "a" else 0.0)
            ka = 48 if nf[a] < 4 else 32
            kb = 48 if nf[b] < 4 else 32
            elo[a] = ra + ka * (sa - ea)
            elo[b] = rb + kb * ((1 - sa) - (1 - ea))
            nf[a] += 1; nf[b] += 1
    return {k: round(v) for k, v in elo.items()}


# ----------------------------------------------------------------- 3. Odds history
def load_odds(cache: Path):
    """Return {event_id: [snapshots sorted by t]}; snapshot = {t,start,home,away,books:{book:{h2h:[h,a],tot:[pt,o,u]}}}"""
    by_id = defaultdict(list)
    p = cache / "oddsapi" / "compact" / "mma.jsonl.gz"
    if p.exists():
        with gzip.open(p, "rt") as f:
            for line in f:
                r = json.loads(line)
                by_id[r["id"]].append({"t": r["t"], "start": r["start"], "home": r["home"], "away": r["away"], "books": r["books"]})
    for fp in sorted(glob.glob(str(cache / "oddsapi" / "mma" / "*.json.gz"))):
        try:
            d = json.load(gzip.open(fp))
        except Exception:
            continue
        t = d.get("timestamp")
        for ev in d.get("data", []):
            books = {}
            for bm in ev.get("bookmakers", []):
                e = {}
                for m in bm.get("markets", []):
                    oc = m.get("outcomes", [])
                    if m["key"] == "h2h" and len(oc) == 2:
                        px = {o["name"]: o["price"] for o in oc}
                        if ev["home_team"] in px and ev["away_team"] in px:
                            e["h2h"] = [px[ev["home_team"]], px[ev["away_team"]]]
                    elif m["key"] == "totals" and len(oc) == 2:
                        px = {o["name"]: o for o in oc}
                        if "Over" in px and "Under" in px:
                            e["tot"] = [px["Over"].get("point"), px["Over"]["price"], px["Under"]["price"]]
                if e:
                    books[bm["key"]] = e
            if books:
                by_id[ev["id"]].append({"t": t, "start": ev["commence_time"], "home": ev["home_team"], "away": ev["away_team"], "books": books})
    p = cache / "mma" / "oddsapi_live.jsonl"
    if p.exists():
        for line in open(p):
            try:
                r = json.loads(line)
            except Exception:
                continue
            books = {b: {"h2h": v} for b, v in (r.get("books") or {}).items() if isinstance(v, list) and len(v) == 2}
            if books:
                by_id[r["id"]].append({"t": r["t"], "start": r["start"], "home": r["home"], "away": r["away"], "books": books})
    for k in by_id:
        by_id[k].sort(key=lambda s: s["t"])
    return by_id


_CLOSE_FIXES = None


def close_fix(a, b, date):
    """Kirk round 14: hand-fixed bouts in data/odds_close_fixes.json -> 'before' time (str) or None. Two bouts only."""
    global _CLOSE_FIXES
    if _CLOSE_FIXES is None:
        p_ = REPO / "data" / "odds_close_fixes.json"
        _CLOSE_FIXES = json.load(open(p_)).get("fixes", []) if p_.exists() else []
    for x in _CLOSE_FIXES:
        if str(date) == x["date"] and pair_match(a, b, x["a"], x["b"])[0] >= 2:
            x["_used"] = x.get("_used", 0) + 1
            return x["before"]
    return None


def close_fixes_unused():
    """Kirk round 15 B: every hand fix must match exactly one bout in the build, or the build stops (a renamed fighter or a
    wrong date would otherwise drop the fix silently)."""
    return [f'{x["a"]} vs {x["b"]} {x["date"]} (matched {x.get("_used", 0)})' for x in (_CLOSE_FIXES or []) if x.get("_used", 0) != 1]


def summarize_odds(snaps, flipped, max_points=140, a_name=None, close_before=None):
    """Build open/close/series from snapshots. Probabilities are for fighter A (flipped => A is 'away').
    close_before: hand fix only (data/odds_close_fixes.json); the published close and chart use snapshots strictly before it."""
    start = snaps[-1]["start"]
    pre = [s for s in snaps if s["t"] <= start] or snaps
    pts = []
    for s in pre:
        ps, decs_a, decs_b, per = [], [], [], {}
        for b, m in s["books"].items():
            h2h = m.get("h2h")
            if not h2h or b not in BOOK_ORDER:
                continue
            h, a = h2h
            fl = flipped
            if a_name:  # home/away can swap between snapshots of the same event id
                mh, mw = name_match(a_name, s["home"]), name_match(a_name, s["away"])
                if mh != mw:
                    fl = mw > mh
            da, db = (a, h) if fl else (h, a)
            p = novig(da, db)
            if p is None:
                continue
            ps.append(p); decs_a.append(da); decs_b.append(db); per[b] = (p, da, db)
        if not ps:
            continue
        pts.append({"t": s["t"], "p": statistics.median(ps), "da": statistics.median(decs_a), "db": statistics.median(decs_b),
                    "per": per, "nb": len(ps), "tot": {b: m["tot"] for b, m in s["books"].items() if m.get("tot")}})
    if not pts:
        return None
    # drop a lone-book opener that disagrees wildly with everything after it (bad feed rows)
    while len(pts) > 2 and pts[0]["nb"] <= 1 and abs(pts[0]["p"] - pts[1]["p"]) > 0.12:
        pts.pop(0)

    def pack(pt):
        return {"t": pt["t"], "p": r3(pt["p"]), "ma": dec_to_american(pt["da"]), "mb": dec_to_american(pt["db"]), "nb": pt["nb"]}

    o, c = pts[0], pts[-1]
    out = {"open": pack(o), "close": pack(c), "n": len(pts), "start": start}
    out["books"] = {b: {"p": r3(v[0]), "ma": dec_to_american(v[1]), "mb": dec_to_american(v[2])}
                    for b, v in sorted(c["per"].items(), key=lambda kv: BOOK_ORDER.index(kv[0]) if kv[0] in BOOK_ORDER else 99)}
    # totals at close: prefer Pinnacle, else most common line
    tot = c["tot"]
    if tot:
        b = "pinnacle" if "pinnacle" in tot else sorted(tot)[0]
        pt, ov, un = tot[b]
        pov = novig(ov, un)
        out["total"] = {"book": b, "pt": pt, "p_over": r3(pov), "over": dec_to_american(ov), "under": dec_to_american(un)}
    # series (downsample evenly, always keep first/last)
    idx = list(range(len(pts)))
    if len(idx) > max_points:
        step = (len(idx) - 1) / (max_points - 1)
        idx = sorted({round(i * step) for i in range(max_points)})
    out["series"] = [[pts[i]["t"][:16], r3(pts[i]["p"]),
                      r3(pts[i]["per"]["pinnacle"][0]) if "pinnacle" in pts[i]["per"] else None,
                      r3(pts[i]["per"]["draftkings"][0]) if "draftkings" in pts[i]["per"] else None,
                      r3(pts[i]["per"]["fanduel"][0]) if "fanduel" in pts[i]["per"] else None] for i in idx]
    # Kirk round 12 (Consensus_US_PREREG sha cbb10eb9): the PUBLISHED current line and chart use US-regulated books only;
    # the opener keeps every listed book. Research keeps the all-books close above. public_odds() builds the published block.
    rp = []
    for pt in pts:
        rg = [v for b, v in pt["per"].items() if b in US_REGULATED]
        if rg:
            rp.append({"t": pt["t"], "p": statistics.median(v[0] for v in rg), "da": statistics.median(v[1] for v in rg),
                       "db": statistics.median(v[2] for v in rg), "nb": len(rg), "per": {b: v for b, v in pt["per"].items() if b in US_REGULATED}})
    rp = [x for x in rp if x["t"] >= o["t"]]
    if close_before:
        rp = [x for x in rp if x["t"][:19] < close_before[:19]]
    ridx = list(range(len(rp)))
    if len(ridx) > max_points:
        st_ = (len(ridx) - 1) / (max_points - 1); ridx = sorted({round(i * st_) for i in range(max_points)})
    out["_reg"] = {"close": pack(rp[-1]) if rp else None,
                   "books": {b: {"p": r3(v[0]), "ma": dec_to_american(v[1]), "mb": dec_to_american(v[2])} for b, v in rp[-1]["per"].items()} if rp else {},
                   "series": [[o["t"][:16], r3(o["p"]), None, None, None]] + [[rp[i]["t"][:16], r3(rp[i]["p"]),
                              None, r3(rp[i]["per"]["draftkings"][0]) if "draftkings" in rp[i]["per"] else None,
                              r3(rp[i]["per"]["fanduel"][0]) if "fanduel" in rp[i]["per"] else None] for i in ridx]}
    return out


US_REGULATED = ("draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "circasports")


def public_odds(o):
    """The odds block as published: opener (all books), current/close and chart from US-regulated books only (no close if none)."""
    if not o or "_reg" not in o:
        return o
    r = o["_reg"]; pub = {"open": o["open"], "n": o.get("n"), "start": o.get("start"), "books": r["books"], "series": r["series"], "close_src": "us_regulated"}
    if r["close"]:
        pub["close"] = r["close"]
    return pub


def index_odds(by_id):
    """date -> list of (id, home, away, start) using each event's final snapshot."""
    idx = defaultdict(list)
    for eid, snaps in by_id.items():
        last = snaps[-1]
        try:
            d = dt.datetime.fromisoformat(last["start"].replace("Z", "+00:00")).date()
        except Exception:
            continue
        idx[d].append((eid, last["home"], last["away"]))
    return idx


def find_odds(idx, by_id, a, b, date):
    best = (0, None, False, 99)
    for off in (0, 1, -1, 2):
        for eid, h, w in idx.get(date + dt.timedelta(days=off), []):
            sc, fl = pair_match(a, b, h, w)
            if sc > best[0] or (sc == best[0] and sc > 0 and abs(off) < best[3]):
                best = (sc, eid, fl, abs(off))
    if best[0] >= 1:
        return best[1], best[2]
    return None, False


# ----------------------------------------------------------------- 4. Model widgets
NODE_EXTRACT = r"""
const fs=require('fs');const s=fs.readFileSync(process.argv[2],'utf8');
function grab(re){const m=s.match(re);return m?m[1]:null;}
const F=grab(/const FIGHTS = (\[[\s\S]*?\n\]);/);const P=grab(/const USER_PROJECTIONS_BY_FIGHT = (\{[\s\S]*?\n\});/);
const t=grab(/<div class="ff-title">([^<]*)/);const sub=grab(/<div class="ff-subtitle">([^<]*)/);
let fights=[],proj={};try{fights=(new Function('return '+F))();}catch(e){}try{proj=(new Function('return '+P))();}catch(e){}
console.log(JSON.stringify({title:t,subtitle:sub,fights,proj}));
"""


def load_widgets():
    out = []
    js = REPO / ".form_extract.js"
    js.write_text(NODE_EXTRACT)
    try:
        for fp in sorted(REPO.glob("ufc_*_fight_form.html")):
            try:
                raw = subprocess.run(["node", str(js), str(fp)], capture_output=True, text=True, timeout=30).stdout
                d = json.loads(raw)
            except Exception as ex:
                print("  widget parse failed", fp.name, ex, file=sys.stderr)
                continue
            m = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", d.get("subtitle") or "")
            if not m or not d["fights"]:
                continue
            d["date"] = dt.datetime.strptime(m.group(1), "%B %d, %Y").date()
            d["file"] = fp.name
            d["slug"] = fp.name.replace("ufc_", "").replace("_fight_form.html", "")
            out.append(d)
    finally:
        js.unlink(missing_ok=True)
    return out


def attach_models(events, widgets):
    by_date = defaultdict(list)
    for e in events.values():
        by_date[e["date"]].append(e)
    n_att = 0
    for w in widgets:
        cands = [e for off in (0, 1, -1) for e in by_date.get(w["date"] + dt.timedelta(days=off), [])]
        best, bs = None, 0
        for e in cands:
            sc = sum(1 for wf in w["fights"] for f in e["fights"] if pair_match(wf["a"]["name"], wf["b"]["name"], f["a"], f["b"])[0] >= 1)
            if sc > bs:
                best, bs = e, sc
        w["event"] = best["name"] if best else None
        if not best:
            continue
        best["widget"] = {"file": w["file"], "title": (w["title"] or "").replace(" · Fight Form", "")}
        for wf in w["fights"]:
            for f in best["fights"]:
                sc, fl = pair_match(wf["a"]["name"], wf["b"]["name"], f["a"], f["b"])
                if sc < 1:
                    continue
                p = (w["proj"] or {}).get(str(wf["n"])) or (w["proj"] or {}).get(wf["n"]) or {}
                wa, wb = wf["a"], wf["b"]
                pa, pb = p.get("a") or {}, p.get("b") or {}
                ma = {"win": pa.get("win", wa.get("win")), "ko": pa.get("ko"), "sub": pa.get("sub"), "dec": pa.get("dec"), "ml": wa.get("ml")}
                mb = {"win": pb.get("win", wb.get("win")), "ko": pb.get("ko"), "sub": pb.get("sub"), "dec": pb.get("dec"), "ml": wb.get("ml")}
                if fl:
                    ma, mb = mb, ma
                rec = p.get("bet_rec")
                rec_side = None
                if rec:
                    rec_side = "a" if name_match(rec, f["a"]) >= name_match(rec, f["b"]) else "b"
                    if max(name_match(rec, f["a"]), name_match(rec, f["b"])) == 0:
                        rec_side = None
                gtd = p.get("gtd_pct")
                if gtd is None and (wf.get("sim") or {}).get("itd") is not None:
                    gtd = round(100 - wf["sim"]["itd"], 1)
                f["model"] = {"a": ma, "b": mb, "gtd": gtd, "rec": rec_side, "widget_n": wf["n"]}
                n_att += 1
                break
    return n_att


# ----------------------------------------------------------------- 5. BettingPros snapshots (this repo)
def load_bp():
    out = []
    for fp in sorted((REPO / "data").glob("*_odds.json")):
        try:
            d = json.load(open(fp))
        except Exception:
            continue
        out.append((fp.stem.replace("_odds", ""), d))
    return out


def bp_ml(fight):
    """-> {fighter_name: {open, cons, dk, fd}} from a BP fight record."""
    res = {}
    for sel in (fight.get("markets") or {}).get("moneyline", []):
        b = sel.get("books") or {}
        op = sel.get("opening_cost")
        if op is not None and abs(op) > 2500:
            op = None  # BettingPros placeholder openers
        res[sel.get("label")] = {"open": op, "cons": (b.get("consensus") or {}).get("cost"),
                                 "dk": (b.get("draftkings") or {}).get("cost"), "fd": (b.get("fanduel") or {}).get("cost")}
    return res


# ----------------------------------------------------------------- 6. Model sheet (Google Sheet) + Markov outputs
# The sheet ID is deliberately NOT in this repo (the sheet may be editable by anyone holding its link).
# Supply it at build time: env UFC_SHEET_ID, or a one-line file .form_cache/sheet_id.txt (gitignored).
SHEET_ID = os.environ.get("UFC_SHEET_ID") or ((REPO / ".form_cache" / "sheet_id.txt").read_text().strip() if (REPO / ".form_cache" / "sheet_id.txt").exists() else "")
SHEET_TABS = {"Snapshots": 2055839074, "Calculator": 1491130651, "Main Card": 0, "Prelims": 69135179, "PropSnap": 564385760}


def _pf(v):
    """'34.5%' or '0.345' -> 0.345 ; '' -> None"""
    v = (v or "").strip()
    if not v or v in ("-", "—"):
        return None
    try:
        if v.endswith("%"):
            return float(v[:-1].replace(",", "")) / 100
        x = float(v.replace(",", ""))
        return x / 100 if x > 1.0001 else x
    except ValueError:
        return None


def _raw(v):
    try:
        return float((v or "").strip())
    except ValueError:
        return None


def _pml(v):
    v = (v or "").strip().replace("+", "")
    try:
        return int(float(v))
    except ValueError:
        return None


def load_sheet(cache: Path, download=True):
    out = {}
    for tab, gid in SHEET_TABS.items():
        dest = cache / f"sheet_{tab.replace(' ', '_')}.csv"
        if download and SHEET_ID:
            try:
                fetch(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}", dest, timeout=40)
            except Exception as ex:
                print("  sheet tab skipped", tab, ex, file=sys.stderr)
        if dest.exists():
            out[tab] = list(csv.reader(open(dest, encoding="utf-8")))
    return out


def sheet_current(sheet):
    """Upcoming card rows from Main Card / Prelims joined to Calculator -> list of dicts keyed by dog/fav names."""
    calc = {}
    for r in (sheet.get("Calculator") or [])[1:40]:
        if len(r) > 30 and r[0] and r[1] and r[0] != "Underdog":
            calc[(norm(r[0]), norm(r[1]))] = r
    cal = sheet.get("Calculator") or []
    cell = lambda i: _raw(cal[i][1]) if len(cal) > i and len(cal[i]) > 1 else None
    par = [0.15, cell(41) or 0.0, cell(42) if cell(42) is not None else 0.15, cell(43) if cell(43) is not None else 0.075]
    rows = []
    for tab in ("Main Card", "Prelims"):
        for r in (sheet.get(tab) or [])[1:14]:
            if len(r) < 28 or not r[1] or not r[2] or r[1] in ("Underdog", "Fighter") or _pf(r[5]) is None:
                continue
            c = calc.get((norm(r[1]), norm(r[2]))) or [""] * 40
            rows.append({
                "dog": r[1], "fav": r[2], "tab": tab, "tag": (r[0] or "").strip(), "par": par, "dog_ml": _pml(r[3]), "fav_ml": _pml(r[8]), "dog_p": _pf(r[5]), "fav_p": _pf(r[10]),
                "dog_edge": _pf(r[7]), "fav_edge": _pf(r[12]), "rec": (r[13] or "").strip(), "hold": _pf(r[14]), "play": (r[15] or "").strip(),
                "gtd": _pf(r[16]), "gtd_listed": _pf(r[18]), "dog_m": [_pf(r[21]), _pf(r[22]), _pf(r[23])], "fav_m": [_pf(r[25]), _pf(r[26]), _pf(r[27])],
                "tap": _pf(c[2]), "junk": _pf(c[3]), "tip": _pf(c[4]), "open": _pf(c[5]), "listed": _pf(c[6]), "markov": _pf(c[9]),
                "ctx": (c[10] or "").strip(), "women": 1 if (c[8] or "").strip() == "1" else 0, "o25_listed": _pf(c[13]), "o25_model": _pf(c[14]), "ou_play": (c[21] or "").strip(),
                "flag": (c[26] or "").strip(), "momentum": (c[27] or "").strip(), "dog_best": (c[28] or "").strip(), "fav_best": (c[29] or "").strip()})
    return rows


def sheet_snapshots(sheet):
    rows = sheet.get("Snapshots") or []
    if not rows:
        return []
    hdr = rows[0]
    out = []
    for r in rows[1:]:
        d = dict(zip(hdr, r))
        if not d.get("dog") or not d.get("fav"):
            continue
        try:
            d["_date"] = dt.datetime.strptime(d["date"], "%m/%d/%Y").date()
        except Exception:
            continue
        out.append(d)
    return out


def sheet_obj(a_name, row, snap=False):
    """Orient a sheet row (dog/fav) onto the fight's a/b sides."""
    if snap:
        d = row
        dog, fav = d["dog"], d["fav"]
        a_is_dog = name_match(a_name, dog) >= name_match(a_name, fav)
        g = lambda k: _pf(d.get(k))
        side = lambda x: x if a_is_dog else (None if x is None else 1 - x)
        dm = [g("model dog DEC (V)"), g("model dog KO (W)"), g("model dog SUB (X)")]; fm_ = [g("model fav DEC (Z)"), g("model fav KO (AA)"), g("model fav SUB (AB)")]
        pm = {"dog": [g("P mkt dogDEC"), g("P mkt dogKO"), g("P mkt dogSUB")], "fav": [g("P mkt favDEC"), g("P mkt favKO"), g("P mkt favSUB")]}
        o = {"dog": "a" if a_is_dog else "b", "tap": side(g("Tap C")), "junk": side(g("Junk D")), "tip": side(g("Tip E")), "open": side(g("dog open F")),
             "listed": side(g("dog listed G (sheet)")), "close": side(g("dog CLOSE (consensus)")), "markov": side(g("Markov J")), "model": side(g("model Q")),
             "exch": side(g("exch fair dog (AG)")), "flag": d.get("flag AA") or "", "momentum": d.get("momentum AB") or "", "rec": d.get("bet rec") or "",
             "play": d.get("GTD/ITD play") or "", "ou_play": d.get("O/U play") or "", "gtd": g("Fight GTD model"), "gtd_listed": g("GTD listed"),
             "gtd_close": g("GTD close"), "markov_dec": g("Markov P(dec)"), "o25_listed": g("O2.5 listed"), "o25_model": g("O2.5 model"),
             "ml": {"a": _pml(d.get("dog price (D)")) if a_is_dog else _pml(d.get("fav price (I)")), "b": _pml(d.get("fav price (I)")) if a_is_dog else _pml(d.get("dog price (D)"))},
             "meth": {"a": dm if a_is_dog else fm_, "b": fm_ if a_is_dog else dm},
             "meth_mkt": {"a": pm["dog"] if a_is_dog else pm["fav"], "b": pm["fav"] if a_is_dog else pm["dog"]},
             "k": (d.get("K code") or "").strip(), "w": 1 if (d.get("tag") or "").startswith("w") else 0,
             "par": [0.15, 0.0, 0.10, 0.05], "pl": None}
        try:
            o["pl"] = float(d["rec ML P/L (u)"]) if d.get("rec ML P/L (u)") not in (None, "") else None
        except ValueError:
            o["pl"] = None
        return o
    r = row
    a_is_dog = name_match(a_name, r["dog"]) >= name_match(a_name, r["fav"])
    side = lambda x: x if a_is_dog else (None if x is None else 1 - x)
    return {"dog": "a" if a_is_dog else "b", "tap": side(r["tap"]), "junk": side(r["junk"]), "tip": side(r["tip"]), "open": side(r["open"]),
            "listed": side(r["listed"]), "markov": side(r["markov"]), "model": r["dog_p"] if a_is_dog else r["fav_p"],
            "flag": r["flag"], "momentum": r["momentum"], "rec": r["rec"], "play": r["play"], "ou_play": r["ou_play"], "gtd": r["gtd"], "gtd_listed": r["gtd_listed"],
            "o25_listed": r["o25_listed"], "o25_model": r["o25_model"], "hold": r["hold"], "ctx": r["ctx"], "tag": r.get("tag", ""),
            "k": r["ctx"], "w": r.get("women", 0), "par": r.get("par"),
            "ml": {"a": r["dog_ml"] if a_is_dog else r["fav_ml"], "b": r["fav_ml"] if a_is_dog else r["dog_ml"]},
            "edge": {"a": r["dog_edge"] if a_is_dog else r["fav_edge"], "b": r["fav_edge"] if a_is_dog else r["dog_edge"]},
            "meth": {"a": r["dog_m"] if a_is_dog else r["fav_m"], "b": r["fav_m"] if a_is_dog else r["dog_m"]},
            "best": {"a": r["dog_best"] if a_is_dog else r["fav_best"], "b": r["fav_best"] if a_is_dog else r["dog_best"]}}


def load_markov():
    """ARCHIVE blocks from markov/*.md -> list of {a,b,shrunk,raw,pdec,exp,r[5]} (probabilities for the first-named fighter)."""
    out = []
    for fp in sorted((REPO / "markov").glob("*.md")):
        txt = fp.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"## ARCHIVE.*?```\n(.*?)```", txt, re.S)
        if not m:
            continue
        for line in m.group(1).strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 10 or " vs " not in parts[0]:
                continue
            a, b = [x.strip() for x in parts[0].split(" vs ", 1)]
            try:
                nums = [float(x) for x in parts[1:10]]
            except ValueError:
                continue
            out.append({"a": a, "b": b, "shrunk": nums[0], "raw": nums[1], "pdec": nums[2], "exp": nums[3], "r": nums[4:9], "file": fp.name})
        # Flags column of the SHEET INPUT TABLE (row k = ARCHIVE line k), e.g. "artifact (thin pace)", "Hasan §1d, THIN", "SYN"
        rows = [x for x in out if x["file"] == fp.name]
        for line in txt.splitlines():
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) >= 7 and c[0].isdigit() and 1 <= int(c[0]) <= len(rows):
                m_ = rows[int(c[0]) - 1]
                if any(t and t in norm(c[1]) for t in toks(m_["a"]) | toks(m_["b"])):
                    m_["flags"] = c[-1]
    return out


def pair_match_sq(a, b, h, w):
    """pair_match, plus a space-insensitive fallback ("Alateng Heili" = "Alatengheili"). Used only by the Markov attach / model log."""
    sc, fl = pair_match(a, b, h, w)
    if sc >= 2:
        return sc, fl
    q = lambda x: norm(x).replace(" ", "")
    ok = lambda x, y: q(x) == q(y) or name_match(x, y) >= 2
    if ok(a, h) and ok(b, w):
        return 2, False
    if ok(a, w) and ok(b, h):
        return 2, True
    return sc, fl


def markov_thin(m_, nf_a, nf_b):
    """THIN SAMPLE per the site glossary: 3 or fewer UFC fights on either side, or the run itself marked the sample thin."""
    why = []
    if min(nf_a or 0, nf_b or 0) <= 3:
        why.append("3 or fewer UFC fights")
    fl = m_.get("flags") or ""
    if re.search(r"thin|artifact|\bSYN\b", fl, re.I):
        why.append("run flag: " + fl)
    return bool(why), "; ".join(why)


def _nv(x, y):
    if x is None or y is None:
        return None
    i = lambda m: 100 / (m + 100) if m > 0 else -m / (-m + 100)
    return round(i(x) / (i(x) + i(y)), 4)


def write_model_compare(doc, pending=None, bp_fights=None):
    """form/data/model_compare/<event>.json + .csv: one row per fight with every model next to the market.
    Data log only; no page reads it. Win % columns are for fighter A; bout = position on the card, 1 = opener."""
    d_ = OUT / "model_compare"
    d_.mkdir(parents=True, exist_ok=True)
    fights = doc["fights"]
    rows = []
    for i, f in enumerate(fights):
        an, bn = f["a"]["name"], f["b"]["name"]
        sh, mk_, fm, od, bpm = f.get("sheet") or {}, f.get("markov"), f.get("form") or {}, f.get("odds"), f.get("bp") or {}
        r = {"bout": len(fights) - i, "site_n": f["n"], "a": an, "b": bn, "status": doc.get("status")}
        pf = None
        for x in (pending or {}).get("fights", []):
            if pair_match_sq(x["dog"], x["fav"], an, bn)[0] >= 1:
                pf = x
                break
        if pf:
            a_dog = not pair_match_sq(pf["dog"], pf["fav"], an, bn)[1]
            ra, rb = ("dog", "fav") if a_dog else ("fav", "dog")
            r.update({"sheet_pub_p": round(pf["sheet"]["true_" + ra], 4), "sheet_pub_gtd": None if pf.get("gtd") is None else round(pf["gtd"], 4),
                      "sheet_pub_markov_in": None if pf["inputs"].get("markov") is None else round(pf["inputs"]["markov"] if a_dog else 1 - pf["inputs"]["markov"], 4),
                      "sheet_pub_meth_a": pf["method"][ra], "sheet_pub_meth_b": pf["method"][rb], "sheet_pub_flag": pf["sheet"].get("flag"),
                      "sheet_pub_at": pending.get("published_at")})
            # Calculator inputs exactly as the sheet holds them (dog %, not oriented to A): C Tap, D Junk, E Tip, J Markov
            pin = pf.get("inputs") or {}
            r.update({"sheet_dog": pf["dog"], "pub_tap_dog": pin.get("tap"), "pub_junk_dog": pin.get("junk"), "pub_tip_dog": pin.get("tip"),
                      "pub_markov_j_dog": pin.get("markov")})
        wm = f.get("model") or {}
        if wm and wm.get("src") != "sheet" and (wm.get("a") or {}).get("win") is not None:
            r["widget_p"] = round(wm["a"]["win"] / 100, 4)
        r.update({"sheet_build_p": sh.get("model"), "sheet_build_gtd": sh.get("gtd"), "sheet_build_markov": sh.get("markov")})
        if sh:
            # same C/D/E/J from the build's own sheet pull, converted back to dog %
            dog_a = sh.get("dog") == "a"
            undo = lambda x: x if (x is None or dog_a) else round(1 - x, 4)
            r.setdefault("sheet_dog", an if dog_a else bn)
            r.update({"build_tap_dog": undo(sh.get("tap")), "build_junk_dog": undo(sh.get("junk")), "build_tip_dog": undo(sh.get("tip")),
                      "build_markov_j_dog": undo(sh.get("markov"))})
        a_, b_ = bpm.get("a") or {}, bpm.get("b") or {}
        r.update({"bp_open_ml": [a_.get("open"), b_.get("open")], "bp_open_p": _nv(a_.get("open"), b_.get("open")),
                  "bp_now_ml": [a_.get("cons"), b_.get("cons")], "bp_now_p": _nv(a_.get("cons"), b_.get("cons"))})
        if od:
            r.update({"oa_open_p": od["open"]["p"], "oa_open_t": od["open"]["t"], "oa_close_p": (od.get("close") or {}).get("p"), "oa_close_t": (od.get("close") or {}).get("t"),
                      "oa_close_is_final": doc.get("status") == "final"})
        for bf in bp_fights or []:
            if pair_match_sq(bf["fighter_a"]["name"], bf["fighter_b"]["name"], an, bn)[0] >= 1:
                cost = lambda lab: next((s["books"]["consensus"]["cost"] for s in (bf.get("markets") or {}).get("fight_distance", [])
                                         if s.get("label") == lab and (s.get("books") or {}).get("consensus")), None)
                r["bp_gtd_p"] = _nv(cost("Yes"), cost("No"))
                break
        if mk_:
            thin, why = mk_.get("thin"), mk_.get("thin_why")
            if thin is None:
                thin, why = markov_thin(mk_, f["a"].get("nf"), f["b"].get("nf"))
            r.update({"markov_p": mk_["p"], "markov_raw": mk_["raw"], "markov_dec": mk_["dec"], "markov_exp": mk_["exp"],
                      "markov_thin": thin, "markov_thin_why": why, "markov_flags": mk_.get("flags")})
        r.update({"form_p": fm.get("p"), "form_gtd": fm.get("g"), "form_div_base": fm.get("base")})
        rows.append(r)
    json.dump({"event": doc["name"], "slug": doc["slug"], "date": doc["date"], "status": doc.get("status"),
               "_doc": write_model_compare.__doc__.strip(), "fights": rows}, open(d_ / f"{doc['slug']}.json", "w"), indent=1)
    cols = ["bout", "site_n", "a", "b", "sheet_pub_p", "sheet_build_p", "widget_p", "bp_open_p", "bp_now_p", "oa_open_p", "oa_close_p", "markov_p", "markov_raw",
            "markov_thin", "form_p", "sheet_pub_gtd", "sheet_build_gtd", "bp_gtd_p", "markov_dec", "form_gtd", "form_div_base", "markov_thin_why",
            "sheet_dog", "pub_tap_dog", "pub_junk_dog", "pub_tip_dog", "pub_markov_j_dog", "build_tap_dog", "build_junk_dog", "build_tip_dog", "build_markov_j_dog"]
    with open(d_ / f"{doc['slug']}.csv", "w", newline="") as fh:
        w_ = csv.writer(fh)
        w_.writerow(cols)
        for r in rows:
            w_.writerow([r.get(c) for c in cols])
    return len(rows)


# ----------------------------------------------------------------- build
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(REPO / ".form_cache"))
    ap.add_argument("--no-download", action="store_true")
    args = ap.parse_args()
    cache = Path(args.cache)

    if not args.no_download:
        for f in UFCSTATS_FILES:
            fetch(UFCSTATS_BASE + f, cache / f)
        for rel in ["oddsapi/compact/mma.jsonl.gz", "mma/oddsapi_live.jsonl"]:
            try:
                fetch(ST_RAW + rel, cache / rel, timeout=300)
            except Exception as ex:
                print("  skip", rel, ex, file=sys.stderr)
        try:
            req = urllib.request.Request(ST_API_TREE, headers={"User-Agent": "mma-fight-form-build/1.0"})
            tree = json.load(urllib.request.urlopen(req, timeout=60))
            for t in tree.get("tree", []):
                dest = cache / "oddsapi" / "mma" / t["path"]
                if not dest.exists():
                    fetch(ST_RAW + "oddsapi/mma/" + t["path"], dest)
        except Exception as ex:
            print("  skip 2026 snapshots", ex, file=sys.stderr)

    print("loading UFCStats…")
    events, bio = load_ufcstats(cache)
    elo_now = run_elo(events)
    print(f"  {len(events)} events, {sum(len(e['fights']) for e in events.values())} fights")

    print("loading odds history…")
    by_id = load_odds(cache)
    oidx = index_odds(by_id)
    print(f"  {len(by_id)} odds events, {sum(len(v) for v in by_id.values())} snapshots")

    matched = total22 = 0
    for e in events.values():
        if e["date"].year < 2022:
            continue
        for f in e["fights"]:
            total22 += 1
            eid, fl = find_odds(oidx, by_id, f["a"], f["b"], e["date"])
            if eid:
                o = summarize_odds(by_id[eid], fl, a_name=f["a"], close_before=close_fix(f["a"], f["b"], e["date"]))
                if o:
                    f["odds"] = o
                    matched += 1
    print(f"  odds matched to {matched}/{total22} UFC fights since 2022")
    close_fix("", "", None)   # loads data/odds_close_fixes.json even when no 2022+ bout reached it
    if close_fixes_unused():
        sys.exit("odds_close_fixes.json: fix not applied to exactly one bout: " + "; ".join(close_fixes_unused()))

    print("loading model widgets…")
    widgets = load_widgets()
    n_att = attach_models(events, widgets)
    print(f"  {len(widgets)} widgets, {n_att} fights with projections")

    print("loading model sheet + Markov outputs…")
    sheet = load_sheet(cache, download=not args.no_download)
    snaps = sheet_snapshots(sheet)
    cur_rows = sheet_current(sheet)
    mk = load_markov()
    by_date_ev = defaultdict(list)
    for e in events.values():
        by_date_ev[e["date"]].append(e)
    n_sn = 0
    for d in snaps:
        for off in (0, 1, -1):
            hit = False
            for e in by_date_ev.get(d["_date"] + dt.timedelta(days=off), []):
                for f in e["fights"]:
                    if pair_match(d["dog"], d["fav"], f["a"], f["b"])[0] >= 1:
                        f["sheet"] = sheet_obj(f["a"], d, snap=True); n_sn += 1; hit = True
                        break
                if hit:
                    break
            if hit:
                break
    ps_rows = sheet.get("PropSnap") or []
    n_ps = 0
    if ps_rows:
        hdr = ps_rows[0]
        grp = defaultdict(list)
        for r in ps_rows[1:]:
            d = dict(zip(hdr, r))
            if d.get("dog") and d.get("fav") and d.get("market"):
                grp[(d["date"], d["dog"], d["fav"])].append(d)
        for (dd, dog, fav), lst in grp.items():
            try:
                pdate = dt.datetime.strptime(dd, "%m/%d/%Y").date()
            except Exception:
                continue
            for off in (0, 1, -1):
                done = False
                for e in by_date_ev.get(pdate + dt.timedelta(days=off), []):
                    for f in e["fights"]:
                        if pair_match(dog.replace("\u2019", "'"), fav.replace("\u2019", "'"), f["a"], f["b"])[0] >= 1:
                            a_is_dog = name_match(f["a"], dog) >= name_match(f["a"], fav)
                            pr = {}
                            for d in lst:
                                mk_ = d["market"]
                                for who in ("dog", "fav"):
                                    if mk_.startswith(who + " ") or mk_ == "ML " + who:
                                        mk_ = mk_.replace(who, "a" if (who == "dog") == a_is_dog else "b")
                                        break
                                pv = _pf(d.get("prob")); od_ = _pml(d.get("odds"))
                                pr.setdefault(mk_, {})[d["source"]] = [pv, od_, (d.get("weight/vol") or "")[:14]]
                            f["props"] = pr; n_ps += 1; done = True
                            break
                    if done:
                        break
                if done:
                    break
    n_mk = 0
    for e in events.values():
        if e["date"].year < 2026:
            continue
        for f in e["fights"]:
            for m_ in mk:
                sc, fl = pair_match(f["a"], f["b"], m_["a"], m_["b"])
                if sc >= 2:
                    f["markov"] = {"p": round((100 - m_["shrunk"]) / 100 if fl else m_["shrunk"] / 100, 4), "raw": round((100 - m_["raw"]) / 100 if fl else m_["raw"] / 100, 4),
                                   "dec": round(m_["pdec"] / 100, 4), "exp": m_["exp"], "r": m_["r"]}
                    n_mk += 1
                    break
    print(f"  sheet: {n_sn} graded snapshot fights, {len(cur_rows)} current rows, {n_ps} fights with prop prices; Markov: {n_mk} fights")

    # BettingPros: opening lines for 2026 cards + the upcoming card
    bp = load_bp()
    today = dt.date.today()
    upcoming = []
    bp_by_date = {}
    for slug, d in bp:
        fights = d.get("fights") or []
        if not fights:
            continue
        sched = [f.get("scheduled_utc") for f in fights if f.get("scheduled_utc")]
        try:
            edate = dt.datetime.fromisoformat(min(sched).replace(" ", "T")).date()
        except Exception:
            continue
        # completed card -> enrich matching UFCStats fights with BP open/close
        target = None
        for e in events.values():
            if abs((e["date"] - edate).days) <= 1:
                target = e
                break
        if target:
            for bf in fights:
                an, bn = bf["fighter_a"]["name"], bf["fighter_b"]["name"]
                for f in target["fights"]:
                    sc, fl = pair_match(f["a"], f["b"], an, bn)
                    if sc < 1:
                        continue
                    ml = bp_ml(bf)
                    ra = next((v for k, v in ml.items() if name_match(k or "", f["a"]) >= 1), None)
                    rb = next((v for k, v in ml.items() if name_match(k or "", f["b"]) >= 1), None)
                    if ra and rb:
                        f["bp"] = {"a": ra, "b": rb}
                    break
        elif edate >= today - dt.timedelta(days=1):
            upcoming.append((slug, d, edate))
        bp_by_date[edate] = fights

    # ------------------------------------------------ figures, Form Line, backtests
    print("fitting figures / Form Line / backtests…")
    FM = form_model.FormModel(events, bio)
    R = form_model.research(FM)
    for f in FM.fights:
        if "_angles" not in f and f.get("odds"):
            f["_angles"] = form_model.angle_sides(f, f["_A"], f["_B"], f.get("fl"))
    print(f"  Form Line log loss {R['scores'][2]['ll']} vs close {R['scores'][0]['ll']} on {R['scores'][0]['n']} fights; bias slope k={R['k']}")

    # ------------------------------------------------ fighters
    fighters = defaultdict(list)
    for e in events.values():
        for f in e["fights"]:
            fighters[f["a"]].append((f, "a"))
            fighters[f["b"]].append((f, "b"))

    slug_of, used = {}, {}
    for name in sorted(fighters, key=lambda n: -len(fighters[n])):
        s = slugify(name) or "fighter"
        base, i = s, 2
        while s in used:
            s = f"{base}-{i}"; i += 1
        used[s] = name
        slug_of[name] = s

    def ev_slug(e):
        return f"{e['date'].isoformat()}-{slugify(e['name'])}"[:90]

    for e in events.values():
        e["slug"] = ev_slug(e)

    def pp_line(f, side):
        o = "b" if side == "a" else "a"
        me, opp = f[side], f[o]
        s_me, s_op = f["s" + side], f["s" + o]
        res = "NC" if f["kind"] == "nc" else "D" if f["kind"] == "draw" else ("W" if f["winner"] == side else "L")
        line = {"d": f["date"].isoformat(), "e": f["event"], "es": events[f["event"]]["slug"], "n": f["n"],
                "o": opp, "os": slug_of.get(opp), "oe": f["elo_" + o], "el": f["elo_" + side], "r": res,
                "m": f["method"], "rd": f["round"], "t": f["time"], "sc": f["sched"], "secs": f["secs"], "wc": f["wc"],
                "ti": 1 if f["title"] else 0, "u": f["url"], "fg": f.get("fig_" + side)}
        det = f.get("details") or ""
        sc_ = re.findall(r"(\d{2})\s*-\s*(\d{2})", det)
        if "Decision" in f["method"] and sc_:
            cards = [(int(x), int(y)) for x, y in sc_[:3]]
            # orient each card as me-opponent: the winner must have the majority of cards
            mine = sum(1 for x, y in cards if x > y); theirs = sum(1 for x, y in cards if y > x)
            if (res == "W" and theirs > mine) or (res == "L" and mine > theirs):
                cards = [(y, x) for x, y in cards]
            line["dt"] = " ".join(f"{x}-{y}" for x, y in cards)
        elif det and "Decision" not in f["method"]:
            line["dt"] = re.sub(r"\s+", " ", det)[:34]
        if s_me and s_op and f["secs"] and f["round"]:
            r1s = 300 if f["round"] > 1 else f["secs"]
            lates = max(0, f["secs"] - 600)
            line["rs"] = [s_me.get("r1", 0), s_op.get("r1", 0), r1s, s_me.get("late", 0), s_op.get("late", 0), lates]
        if s_me and s_op:
            line["s"] = [s_me["sl"], s_me["sa"], s_op["sl"], s_op["sa"], s_me["kd"], s_op["kd"], s_me["tl"], s_me["ta"],
                         s_op["tl"], s_op["ta"], s_me["ctrl"], s_op["ctrl"], s_me["sub"], s_op["sub"]]
        od = f.get("odds")
        if od:
            pa_o, pa_c = od["open"]["p"], od["close"]["p"]
            line["od"] = {"po": r3(pa_o if side == "a" else 1 - pa_o), "pc": r3(pa_c if side == "a" else 1 - pa_c),
                          "mo": od["open"]["ma" if side == "a" else "mb"], "mc": od["close"]["ma" if side == "a" else "mb"]}
        elif f.get("bp"):
            me_bp = f["bp"][side]
            if me_bp.get("cons") is not None:
                line["od"] = {"mo": me_bp.get("open"), "mc": me_bp.get("cons"), "src": "bp"}
        return line

    (OUT / "fighters").mkdir(parents=True, exist_ok=True)
    (OUT / "events").mkdir(parents=True, exist_ok=True)
    for old in list((OUT / "fighters").glob("*.json")) + list((OUT / "events").glob("*.json")) + list((OUT / "model_compare").glob("*.*")):
        old.unlink()

    search = []
    for name, lst in fighters.items():
        lst.sort(key=lambda x: (x[0]["date"], x[0]["n"]), reverse=True)
        lines = [pp_line(f, side) for f, side in lst]
        rec = {"W": 0, "L": 0, "D": 0, "NC": 0}
        for ln in lines:
            rec[ln["r"]] += 1
        b = dict(bio.get(norm(name)) or {})
        dup = b.pop("_dup", False)
        out = {"name": name, "slug": slug_of[name], "bio": b, "dup_name": dup, "elo": elo_now.get(name), "fig": FM.rating(name), "ufc": rec, "fights": lines}
        json.dump(out, open(OUT / "fighters" / f"{slug_of[name]}.json", "w"), separators=(",", ":"))
        search.append([name, slug_of[name], lines[0]["d"], lines[0]["wc"], f"{rec['W']}-{rec['L']}-{rec['D']}", elo_now.get(name), FM.rating(name), len(lines)])
    search.sort(key=lambda x: x[2], reverse=True)
    json.dump(search, open(OUT / "search.json", "w"), separators=(",", ":"))

    # ------------------------------------------------ events
    def fight_out(f):
        o = {"n": f["n"], "a": {"name": f["a"], "slug": slug_of[f["a"]], "elo": f["elo_a"], "nf": f["nf_a"]},
             "b": {"name": f["b"], "slug": slug_of[f["b"]], "elo": f["elo_b"], "nf": f["nf_b"]},
             "wc": f["wc"], "title": f["title"], "sched": f["sched"],
             "result": {"winner": f["winner"], "kind": f["kind"], "method": f["method"], "round": f["round"], "time": f["time"],
                        "ref": f["ref"], "details": f["details"]},
             "stats": {"a": f["sa"], "b": f["sb"]}, "url": f["url"]}
        for k in ("odds", "model", "bp", "sheet", "markov", "props"):
            if f.get(k):
                o[k] = public_odds(f[k]) if k == "odds" else f[k]
        o["form"] = {"p": r3(f.get("fl")), "g": r3(f.get("gl")), "base": r3(f.get("_base")),
                     "ra": round(f["_A"]["fig"], 1), "rb": round(f["_B"]["fig"], 1), "ang": f.get("_angles") or {}}
        if f.get("ms"):
            o["form"]["ms"] = {k_: [round(v, 3) for v in f["ms"][k_]] for k_ in "ab"}
        return o

    index_events = []
    for e in sorted(events.values(), key=lambda x: x["date"], reverse=True):
        fo = [fight_out(f) for f in sorted(e["fights"], key=lambda x: -x["n"])]
        doc = {"name": e["name"], "slug": e["slug"], "date": e["date"].isoformat(), "location": e["location"], "status": "final",
               "url": e["url"], "widget": e.get("widget"), "fights": fo}
        json.dump(doc, open(OUT / "events" / f"{e['slug']}.json", "w"), separators=(",", ":"))
        if e["date"].year >= 2026 and any(f.get("markov") or f.get("sheet") or f.get("model") for f in fo):
            write_model_compare(doc, bp_fights=next((v for k, v in bp_by_date.items() if abs((k - e["date"]).days) <= 1), None))
        main_f = fo[0] if fo else None
        index_events.append({"name": e["name"], "slug": e["slug"], "date": e["date"].isoformat(), "loc": e["location"], "nf": len(fo),
                             "model": bool(e.get("widget")), "odds": sum(1 for f in fo if f.get("odds")),
                             "main": f"{main_f['a']['name']} vs {main_f['b']['name']}" if main_f else ""})

    # ------------------------------------------------ upcoming (from BettingPros card + Odds API live)
    up_index = []
    for slug, d, edate in sorted(upcoming, key=lambda x: x[2]):
        # real-card corrections (cancelled bouts, replacements, title flags, order) live in
        # data/card_overrides.json so a rebuild never brings stale feed bouts back
        d = dict(d, fights=card_overrides.apply_feed(slug, d["fights"]))
        w = next((w for w in widgets if abs((w["date"] - edate).days) <= 1), None)
        fo = []
        for bf in sorted(d["fights"], key=lambda x: -x["n"]):
            an, bn = bf["fighter_a"]["name"], bf["fighter_b"]["name"]

            def resolve(nm):
                best, bs = None, 0
                for cand in fighters:
                    sc = name_match(nm, cand)
                    if sc > bs:
                        best, bs = cand, sc
                if bs >= 2:
                    return best
                # nickname / spelling variants (Chris~Christopher, Radke~Radtke): same-ish surname + same first initial,
                # and only fighters active in the last 3 years
                import difflib
                n0 = norm(nm).split()
                cands = []
                for cand, lst in fighters.items():
                    c0 = norm(cand).split()
                    if not c0 or not n0 or c0[0][0] != n0[0][0]:
                        continue
                    if (edate - max(x[0]["date"] for x in lst)).days > 1100:
                        continue
                    if difflib.SequenceMatcher(None, c0[-1], n0[-1]).ratio() >= 0.83 and \
                       (c0[0].startswith(n0[0][:4]) or n0[0].startswith(c0[0][:4]) or difflib.SequenceMatcher(None, c0[0], n0[0]).ratio() >= 0.6):
                        cands.append(cand)
                if not cands:
                    return None
                full = norm(nm)
                cands.sort(key=lambda c: difflib.SequenceMatcher(None, norm(c), full).ratio(), reverse=True)
                return cands[0]

            ra, rb = resolve(an), resolve(bn)
            fa = {"name": ra or an, "slug": slug_of.get(ra), "elo": elo_now.get(ra) if ra else None, "nf": len(fighters[ra]) if ra else 0}
            fb = {"name": rb or bn, "slug": slug_of.get(rb), "elo": elo_now.get(rb) if rb else None, "nf": len(fighters[rb]) if rb else 0}
            wcl = (bf.get("weight_class") or "").split("(")[0].strip().title()
            if ra and fighters[ra] and max(fighters[ra], key=lambda x: x[0]["date"])[0]["wc"].startswith("Women") and not wcl.startswith("Women"):
                wcl = "Women's " + wcl
            fobj = {"n": bf["n"], "a": fa, "b": fb, "wc": wcl, "title": False,
                    "sched": None, "result": None, "stats": None, "url": None, "start": bf.get("scheduled_utc")}
            ml = bp_ml(bf)
            ba = next((v for k, v in ml.items() if name_match(k or "", an) >= 1), None)
            bb = next((v for k, v in ml.items() if name_match(k or "", bn) >= 1), None)
            if ba and bb:
                fobj["bp"] = {"a": ba, "b": bb}
            eid, fl = find_odds(oidx, by_id, fa["name"], fb["name"], edate)
            if not eid:
                eid, fl = find_odds(oidx, by_id, an, bn, edate)
            if eid:
                o = summarize_odds(by_id[eid], fl, a_name=fa["name"])
                if o:
                    fobj["odds"] = o
            # Kirk round 12 (Form_Fix_PREREG sha d78b86a2): five rounds if the bout is a title fight (card_overrides title list,
            # from UFC.com) or the main event; it used to be the main event only, so a title co-main was built as 3 rounds
            ovr_t = (card_overrides.load(slug) or {}).get("title", [])
            is_title = any(card_overrides.bout_is(an, bn, x_, y_) for x_, y_ in ovr_t)
            # Kirk round 13 (call 2): UFCStats shows "Time format" only for completed bouts (past Form already reads it from
            # ufc_fight_results.csv); upcoming fight-details pages have none, so a non-title five-round bout needs the card flag
            # "five_rounds": [["A", "B"], ...] in data/card_overrides.json, sourced from UFC.com. Empty for UFC 334.
            is_5r = any(card_overrides.bout_is(an, bn, x_, y_) for x_, y_ in (card_overrides.load(slug) or {}).get("five_rounds", []))
            sched_u = 5 if (is_title or is_5r or bf["n"] == max(x["n"] for x in d["fights"])) else 3
            fobj["sched"] = sched_u
            try:
                pw, pg, SA, SB, base = FM.predict(fa["name"], fb["name"], edate, wcl, sched_u, fa["elo"], fb["elo"])
                tmp = {"odds": fobj.get("odds"), "wc": wcl, "sched": sched_u}
                fobj["form"] = {"p": r3(pw), "g": r3(pg), "base": r3(base), "ra": round(SA["fig"], 1), "rb": round(SB["fig"], 1),
                                "ang": form_model.angle_sides(tmp, SA, SB, pw) if (SA["n"] or SB["n"]) else {},
                                "ms": {k_: [round(v, 3) for v in FM.last_ms[k_]] for k_ in "ab"}}
            except Exception as ex:
                print("  predict failed", an, bn, ex, file=sys.stderr)
            if w:
                for wf in w["fights"]:
                    sc, fl2 = pair_match(wf["a"]["name"], wf["b"]["name"], an, bn)
                    if sc >= 1:
                        p = (w["proj"] or {}).get(str(wf["n"])) or {}
                        pa, pb = p.get("a") or {}, p.get("b") or {}
                        ma = {"win": pa.get("win", wf["a"].get("win")), "ko": pa.get("ko"), "sub": pa.get("sub"), "dec": pa.get("dec"), "ml": wf["a"].get("ml")}
                        mb = {"win": pb.get("win", wf["b"].get("win")), "ko": pb.get("ko"), "sub": pb.get("sub"), "dec": pb.get("dec"), "ml": wf["b"].get("ml")}
                        if fl2:
                            ma, mb = mb, ma
                        rec = p.get("bet_rec")
                        fobj["model"] = {"a": ma, "b": mb, "gtd": p.get("gtd_pct"),
                                         "rec": None if not rec else ("a" if name_match(rec, an) >= name_match(rec, bn) else "b"), "widget_n": wf["n"]}
                        break
            for r_ in cur_rows:
                if pair_match(r_["dog"], r_["fav"], fa["name"], fb["name"])[0] >= 1 or pair_match(r_["dog"], r_["fav"], an, bn)[0] >= 1:
                    so = sheet_obj(fa["name"], r_)
                    fobj["sheet"] = so
                    fobj["sched"] = 5 if so.get("tag", "").endswith("-5") else 3
                    if "model" not in fobj and so.get("model") is not None:
                        pa_ = so["model"]
                        mm = lambda p_, sh: {"win": round(p_ * 100, 1), "dec": None if sh[0] is None else round(p_ * sh[0] * 100, 1),
                                             "ko": None if sh[1] is None else round(p_ * sh[1] * 100, 1), "sub": None if sh[2] is None else round(p_ * sh[2] * 100, 1)}
                        ma_ = mm(pa_, so["meth"]["a"]); mb_ = mm(1 - pa_, so["meth"]["b"])
                        ma_["ml"], mb_["ml"] = so["ml"]["a"], so["ml"]["b"]
                        rec_side = None
                        if so["rec"] and so["rec"].upper().startswith("BET"):
                            ra_, rb_ = name_match(so["rec"], fa["name"]), 0
                            for tok in toks(fa["name"]):
                                if tok in norm(so["rec"]):
                                    ra_ = 3
                            for tok in toks(fb["name"]):
                                if tok in norm(so["rec"]):
                                    rb_ = 3
                            rec_side = "a" if ra_ > rb_ else "b" if rb_ > ra_ else None
                        fobj["model"] = {"a": ma_, "b": mb_, "gtd": None if so["gtd"] is None else round(so["gtd"] * 100, 1), "rec": rec_side,
                                         "rec_text": so["rec"], "src": "sheet"}
                    break
            # Markov ARCHIVE row for the upcoming card (same attach as the completed-event loop; until now only graded cards got it)
            for m_ in mk:
                sc, fl = pair_match_sq(fa["name"], fb["name"], m_["a"], m_["b"])
                if sc >= 2:
                    thin, why = markov_thin(m_, fa["nf"], fb["nf"])
                    fobj["markov"] = {"p": round((100 - m_["shrunk"]) / 100 if fl else m_["shrunk"] / 100, 4), "raw": round((100 - m_["raw"]) / 100 if fl else m_["raw"] / 100, 4),
                                      "dec": round(m_["pdec"] / 100, 4), "exp": m_["exp"], "r": m_["r"], "thin": thin, "thin_why": why, "flags": m_.get("flags")}
                    break
            if fobj.get("odds"): fobj["odds"] = public_odds(fobj["odds"])   # Consensus_US_PREREG
            fo.append(fobj)
        name = d.get("card") or slug
        eslug = f"{edate.isoformat()}-{slugify(name)}"[:90]
        doc = {"name": name, "slug": eslug, "date": edate.isoformat(), "location": d.get("venue") or "", "status": "upcoming",
               "url": None, "widget": {"file": w["file"], "title": (w["title"] or "").replace(" · Fight Form", "")} if w else None,
               "odds_updated": d.get("updated_at"), "bp_file": f"data/{slug}_odds.json", "fights": fo}
        doc = card_overrides.apply_doc(slug, doc, OUT / "fighters")
        fo = doc["fights"]
        for err in card_overrides.check(slug, doc):
            print("  card override check", slug, err, file=sys.stderr)
        # model_compare logs the build's own sheet pull next to the export, so it runs before the export replaces it
        pend, pend_p = publish_source.load_export(slug, REPO)
        n_mc = write_model_compare(doc, pend, d["fights"])
        # Sean's projection (win %, DEC/KO/SUB split, GTD) on the site = the "Publish to site" export when one exists
        doc = publish_source.apply(doc, slug, REPO, pend, str(pend_p.relative_to(REPO)) if pend_p else None)
        fo = doc["fights"]
        json.dump(doc, open(OUT / "events" / f"{eslug}.json", "w"), separators=(",", ":"))
        print(f"  {eslug}: Markov on {sum(1 for x in fo if x.get('markov'))}/{len(fo)} fights; model_compare {n_mc} rows; projections {doc['proj_source']['fights']} from {doc['proj_source']['file'] or 'build'}")
        up_index.append({"name": name, "slug": eslug, "date": edate.isoformat(), "loc": doc["location"], "nf": len(fo), "model": bool(w) or any(x.get("model") for x in fo),
                         "main": f"{fo[0]['a']['name']} vs {fo[0]['b']['name']}" if fo else ""})

    # ------------------------------------------------ model report card
    recs, cal = [], []
    for e in events.values():
        for f in e["fights"]:
            m = f.get("model")
            if not m or f["kind"] != "win":
                continue
            wa = (m["a"] or {}).get("win")
            if wa is not None:
                cal.append({"p": wa / 100, "won": 1 if f["winner"] == "a" else 0,
                            "pc": (f.get("odds") or {}).get("close", {}).get("p")})
            if m.get("rec"):
                side = m["rec"]
                ml = (m[side] or {}).get("ml")
                won = f["winner"] == side
                dec = american_to_dec(ml) if ml else None
                # risk 1u on plus money, to-win 1u on minus money
                if dec:
                    pnl = ((dec - 1) if ml > 0 else 1.0) if won else (-1.0 if ml > 0 else -1 / (dec - 1))
                    risk = 1.0 if ml > 0 else 1 / (dec - 1)
                else:
                    pnl = risk = None
                pc = (f.get("odds") or {}).get("close", {}).get("p")
                if pc is not None and side == "b":
                    pc = 1 - pc
                recs.append({"d": e["date"].isoformat(), "e": e["name"], "es": e["slug"], "n": f["n"], "pick": f[side], "opp": f["b" if side == "a" else "a"],
                             "ml": ml, "win": (m[side] or {}).get("win"), "won": won, "pnl": r3(pnl), "risk": r3(risk),
                             "close_p": r3(pc), "close_ml": (f.get("odds") or {}).get("close", {}).get("ma" if side == "a" else "mb")})
    recs.sort(key=lambda x: (x["d"], x["n"]), reverse=True)

    def brier(key):
        xs = [(c[key] - c["won"]) ** 2 for c in cal if c.get(key) is not None]
        return r3(sum(xs) / len(xs)) if xs else None

    both = [c for c in cal if c.get("pc") is not None]
    model = {"recs": recs, "n_fights": len(cal),
             "brier_model": r3(sum((c["p"] - c["won"]) ** 2 for c in both) / len(both)) if both else None,
             "brier_close": r3(sum((c["pc"] - c["won"]) ** 2 for c in both) / len(both)) if both else None, "n_both": len(both)}
    try:
        import numpy as _np
        lg_ = lambda p_: math.log(min(max(p_, 1e-3), 1 - 1e-3) / (1 - min(max(p_, 1e-3), 1 - 1e-3)))
        Xb = _np.array([[lg_(c["pc"]), lg_(c["p"])] for c in both]); yb = _np.array([c["won"] for c in both])
        wb_ = form_model.fit_logit(_np.vstack([Xb, -Xb]), _np.concatenate([yb, 1 - yb]), l2=0.5)
        model["blend"] = {"w_close": round(float(wb_[0]), 3), "w_model": round(float(wb_[1]), 3), "n": len(both)}
        ll_ = lambda ps: round(float(-_np.mean([math.log(max(p_, 1e-6)) if y_ else math.log(max(1 - p_, 1e-6)) for p_, y_ in zip(ps, yb)])), 4)
        model["ll_model"] = ll_([c["p"] for c in both]); model["ll_close"] = ll_([c["pc"] for c in both])
        # agreement: when the model's side matches the bias-adjusted favourite
        agree = [c for c in both if (c["p"] - c["pc"]) * (c["pc"] - 0.5) > 0]
        model["edge_fav"] = {"n": len(agree), "w": sum(1 for c in agree if (c["won"] == 1) == (c["pc"] > 0.5))}
        dis = [c for c in both if (c["p"] - c["pc"]) * (c["pc"] - 0.5) < 0]
        model["edge_dog"] = {"n": len(dis), "w": sum(1 for c in dis if (c["won"] == 1) == (c["pc"] < 0.5))}
    except Exception as ex:
        print("  model blend failed", ex, file=sys.stderr)

    try:
        six_u, six_f, n6 = 0.0, 0.0, 0
        lgk = lambda p_: 1 / (1 + math.exp(-R["k"] * math.log(min(max(p_, 1e-3), 1 - 1e-3) / (1 - min(max(p_, 1e-3), 1 - 1e-3)))))
        for e in events.values():
            for f in e["fights"]:
                m_ = f.get("model"); mc = form_model.mclass(f)
                if not m_ or mc is None or not f.get("ms") or not f.get("odds"):
                    continue
                side = f["winner"]
                um = m_[side]
                key = ["ko", "sub", "dec"][mc]
                if um.get(key) is None or (m_["a"].get("ko") is None):
                    continue
                tot_u = sum((m_[s_].get(k_) or 0) for s_ in "ab" for k_ in ("ko", "sub", "dec"))
                if tot_u <= 0:
                    continue
                pu = max(um[key] / tot_u, 1e-4)
                pfair = lgk(f["odds"]["close"]["p"]); pw_ = pfair if side == "a" else 1 - pfair
                pf = max(pw_ * f["ms"][side][mc], 1e-4)
                six_u -= math.log(pu); six_f -= math.log(pf); n6 += 1
        if n6:
            model["method6"] = {"n": n6, "ll_model": round(six_u / n6, 4), "ll_form": round(six_f / n6, 4)}
    except Exception as ex:
        print("  method6 failed", ex, file=sys.stderr)

    try:
        fl_ = lambda v: float(v) if v not in (None, "") else None
        G_ = [d for d in snaps if d.get("graded")]
        def mean(key, rows):
            xs = [fl_(d.get(key)) for d in rows]; xs = [x for x in xs if x is not None]
            return (round(sum(xs) / len(xs), 4), len(xs)) if xs else (None, 0)
        allb = [d for d in G_ if all(d.get(k) not in (None, "") for k in ("Brier close", "Brier model Q", "Brier Markov J"))]
        sb = {"n": len(G_), "cards": len({d["event"] for d in G_}),
              "ml": [{"k": "Closing line", "v": mean("Brier close", allb)}, {"k": "Sheet model", "v": mean("Brier model Q", allb)},
                     {"k": "Markov", "v": mean("Brier Markov J", allb)}, {"k": "Exchange fair price", "v": mean("Brier exch fair", G_)}],
              "gtd": [{"k": "Closing GTD price", "v": mean("Brier GTD close", G_)}, {"k": "Sheet GTD", "v": mean("Brier GTD model", G_)}, {"k": "Markov P(dec)", "v": mean("Brier GTD Markov", G_)}],
              "method": [{"k": "Sheet method split", "v": mean("Brier method model", G_)}, {"k": "Market method prices", "v": mean("Brier method mkt", G_)}]}
        flags = defaultdict(lambda: [0, 0, 0.0])
        for d in G_:
            dw, cp = fl_(d.get("dog won")), fl_(d.get("dog CLOSE (consensus)"))
            if dw is None or cp is None:
                continue
            key = re.sub(r"\s*\(.*", "", d.get("flag AA") or "ok").strip() or "ok"
            v = flags[key]; v[0] += 1; v[1] += dw; v[2] += cp
        sb["flags"] = [{"flag": k_, "n": v[0], "dog_w": int(v[1]), "dog_exp": round(v[2] / v[0], 4)} for k_, v in sorted(flags.items(), key=lambda kv: -kv[1][0])]
        pub = [0, 0, 0.0]
        for d in G_:
            t_, j_, dw, cp = fl_(d.get("Tap C")), fl_(d.get("Junk D")), fl_(d.get("dog won")), fl_(d.get("dog CLOSE (consensus)"))
            if None in (t_, j_, dw, cp):
                continue
            if max(t_, j_) - cp >= 0.10:
                pub[0] += 1; pub[1] += dw; pub[2] += cp
        sb["public_dog"] = {"n": pub[0], "dog_w": int(pub[1]), "dog_exp": round(pub[2] / pub[0], 4) if pub[0] else None}
        rp = [fl_(d.get("rec ML P/L (u)")) for d in G_]; rp = [x for x in rp if x is not None]
        gp = [fl_(d.get("GTD/ITD play P/L (u)")) for d in G_]; gp = [x for x in gp if x is not None]
        sb["rec"] = {"n": len(rp), "w": sum(1 for x in rp if x > 0), "pnl": round(sum(rp), 2)}
        sb["plays"] = {"n": len(gp), "w": sum(1 for x in gp if x > 0), "pnl": round(sum(gp), 2)}
        model["sheet"] = sb
    except Exception as ex:
        print("  sheet scoreboard failed", ex, file=sys.stderr)

    def split(rs):
        w_ = sum(1 for x in rs if x["won"]); pn = sum(x["pnl"] or 0 for x in rs); rk = sum(x["risk"] or 0 for x in rs)
        return {"n": len(rs), "w": w_, "pnl": round(pn, 2), "risk": round(rk, 2)}
    model["splits"] = {"Favorites": split([x for x in recs if (x["ml"] or 0) < 0]), "Underdogs": split([x for x in recs if (x["ml"] or 0) > 0])}
    json.dump(model, open(OUT / "model.json", "w"), separators=(",", ":"))
    json.dump(R, open(OUT / "research.json", "w"), separators=(",", ":"))

    json.dump({"built": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", "upcoming": up_index, "events": index_events,
               "books": BOOK_LABEL, "k": R["k"],
               "angles": {a["id"]: [a["name"], a["n"], a["act"], a["exp"], a["roi_c"], a["z"]] for a in R["angles"]}, "counts": {"events": len(events), "fights": sum(len(e["fights"]) for e in events.values()),
                                              "fighters": len(fighters), "odds_fights": matched}},
              open(OUT / "index.json", "w"), separators=(",", ":"))
    size = sum(p.stat().st_size for p in OUT.rglob("*.json")) / 1e6
    print(f"wrote {len(index_events)} events (+{len(up_index)} upcoming), {len(fighters)} fighters, {len(recs)} graded recs → {size:.1f} MB")


if __name__ == "__main__":
    main()
