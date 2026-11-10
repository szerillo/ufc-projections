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


def summarize_odds(snaps, flipped, max_points=140):
    """Build open/close/series from snapshots. Probabilities are for fighter A (flipped => A is 'away')."""
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
            da, db = (a, h) if flipped else (h, a)
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
    return out


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
                o = summarize_odds(by_id[eid], fl)
                if o:
                    f["odds"] = o
                    matched += 1
    print(f"  odds matched to {matched}/{total22} UFC fights since 2022")

    print("loading model widgets…")
    widgets = load_widgets()
    n_att = attach_models(events, widgets)
    print(f"  {len(widgets)} widgets, {n_att} fights with projections")

    # BettingPros: opening lines for 2026 cards + the upcoming card
    bp = load_bp()
    today = dt.date.today()
    upcoming = []
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
                "ti": 1 if f["title"] else 0, "u": f["url"]}
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
    for old in list((OUT / "fighters").glob("*.json")) + list((OUT / "events").glob("*.json")):
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
        out = {"name": name, "slug": slug_of[name], "bio": b, "dup_name": dup, "elo": elo_now.get(name), "ufc": rec, "fights": lines}
        json.dump(out, open(OUT / "fighters" / f"{slug_of[name]}.json", "w"), separators=(",", ":"))
        search.append([name, slug_of[name], lines[0]["d"], lines[0]["wc"], f"{rec['W']}-{rec['L']}-{rec['D']}", elo_now.get(name)])
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
        for k in ("odds", "model", "bp"):
            if f.get(k):
                o[k] = f[k]
        return o

    index_events = []
    for e in sorted(events.values(), key=lambda x: x["date"], reverse=True):
        fo = [fight_out(f) for f in sorted(e["fights"], key=lambda x: -x["n"])]
        doc = {"name": e["name"], "slug": e["slug"], "date": e["date"].isoformat(), "location": e["location"], "status": "final",
               "url": e["url"], "widget": e.get("widget"), "fights": fo}
        json.dump(doc, open(OUT / "events" / f"{e['slug']}.json", "w"), separators=(",", ":"))
        main_f = fo[0] if fo else None
        index_events.append({"name": e["name"], "slug": e["slug"], "date": e["date"].isoformat(), "loc": e["location"], "nf": len(fo),
                             "model": bool(e.get("widget")), "odds": sum(1 for f in fo if f.get("odds")),
                             "main": f"{main_f['a']['name']} vs {main_f['b']['name']}" if main_f else ""})

    # ------------------------------------------------ upcoming (from BettingPros card + Odds API live)
    up_index = []
    for slug, d, edate in sorted(upcoming, key=lambda x: x[2]):
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
                o = summarize_odds(by_id[eid], fl)
                if o:
                    fobj["odds"] = o
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
            fo.append(fobj)
        name = d.get("card") or slug
        eslug = f"{edate.isoformat()}-{slugify(name)}"[:90]
        doc = {"name": name, "slug": eslug, "date": edate.isoformat(), "location": d.get("venue") or "", "status": "upcoming",
               "url": None, "widget": {"file": w["file"], "title": (w["title"] or "").replace(" · Fight Form", "")} if w else None,
               "odds_updated": d.get("updated_at"), "fights": fo}
        json.dump(doc, open(OUT / "events" / f"{eslug}.json", "w"), separators=(",", ":"))
        up_index.append({"name": name, "slug": eslug, "date": edate.isoformat(), "loc": doc["location"], "nf": len(fo), "model": bool(w),
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
    json.dump(model, open(OUT / "model.json", "w"), separators=(",", ":"))

    json.dump({"built": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", "upcoming": up_index, "events": index_events,
               "books": BOOK_LABEL, "counts": {"events": len(events), "fights": sum(len(e["fights"]) for e in events.values()),
                                              "fighters": len(fighters), "odds_fights": matched}},
              open(OUT / "index.json", "w"), separators=(",", ":"))
    size = sum(p.stat().st_size for p in OUT.rglob("*.json")) / 1e6
    print(f"wrote {len(index_events)} events (+{len(up_index)} upcoming), {len(fighters)} fighters, {len(recs)} graded recs → {size:.1f} MB")


if __name__ == "__main__":
    main()
