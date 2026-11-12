#!/usr/bin/env python3
"""UFC Fight Form single-fight embeds, v4: one self-contained HTML file per bout on an upcoming card.

    python3 scripts/build_fight_embeds.py --slug ufc_334            # writes embeds/ufc_334/fight_NN.html (+ .registry.json, card.json)
    python3 scripts/verify_fight_embeds.py --slug ufc_334           # independent re-check of every number in every embed

Sources (all in this repo):
  form/data/events/<event>.json          site build (fight list, Elo, Form Figure, Odds API line history); found via data/<slug>_odds.json
  data/<slug>_projections.json, else data/pending/<slug>_projections.json
                                         Sean's projection: the sheet's "Publish to site" export (scripts/publish_source.py).
                                         No export for the card: the event file's model block (the build's sheet pull) is used and
                                         the embed + registry say so (proj_src "sheet"/"widget").
  data/<slug>_odds.json                  BettingPros (consensus prices, openers, method and distance markets)
  data/card_overrides.json               bout order / cancellations / segments (fight number = bout order, 1 = opener)
  form/data/fighters/*.json, form/data/index.json (k, books)
  ufc_333_fight_form.html                header / panel / collapsible CSS is copied verbatim from this file
One merged "Sean's projection vs market" table, line movement right under it, no model comparison, no Markov numbers.

Every displayed number goes through R(), which formats a raw value and logs a registry row with a rule id + args.
verify_fight_embeds.py recomputes each rule from the source files with its own code and diffs the text."""
import argparse, json, math, html, re, sys, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_source  # noqa: E402
import card_overrides  # noqa: E402  (one fighter-name rule: Charlie Radke ~ Charles Radtke, Alateng Heili ~ Alatengheili)

REPO = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--slug", default="ufc_334")
ap.add_argument("--event", help="event file (default: the upcoming event whose bp_file is data/<slug>_odds.json)")
ap.add_argument("--out", help="output dir (default embeds/<slug>)")
ap.add_argument("--line-history", help="line history file (default data/embeds/line_history_<slug>.json); round 12 C, scratch tests")
ap.add_argument("--no-vs-bar", action="store_true", help="Kirk round 6 4d comparison only: drop the VS name bar on Stats (kept: it is the only name label over the stat columns)")
ARGS = ap.parse_args()
SLUG = ARGS.slug
FD = REPO / "form" / "data"
def find_event(slug):
    idx = json.load(open(FD / "index.json"))
    for u in idx.get("upcoming", []):
        p = FD / "events" / f'{u["slug"]}.json'
        if p.exists() and json.load(open(p)).get("bp_file") == f"data/{slug}_odds.json":
            return p
    raise SystemExit(f"no upcoming event file with bp_file data/{slug}_odds.json")
EV_PATH = Path(ARGS.event) if ARGS.event else find_event(SLUG)
EVL = json.load(open(EV_PATH))
EVF = str(EV_PATH.resolve().relative_to(REPO)) if EV_PATH.resolve().is_relative_to(REPO) else str(EV_PATH.resolve())
PUB, PUB_P = publish_source.load_export(SLUG, REPO)
PUBF = str(PUB_P.relative_to(REPO)) if PUB_P else None
BPO = json.load(open(REPO / "data" / f"{SLUG}_odds.json"))
OVR = json.load(open(REPO / "data" / "card_overrides.json"))[SLUG]
IDX = json.load(open(FD / "index.json"))
K = IDX["k"]; BOOKS = IDX["books"]
W333 = open(REPO / "ufc_333_fight_form.html").read()
OUT = Path(ARGS.out) if ARGS.out else REPO / "embeds" / SLUG
OUT.mkdir(parents=True, exist_ok=True)
L = FD

esc = lambda s: html.escape(str(s), quote=True)
last = lambda n: n.split(" ")[-1]
nrm = lambda s: re.sub(r"[^a-z]", "", s.lower())
same = lambda x, y: card_overrides.same(x, y) or nrm(x) == nrm(y)   # "Alateng Heili" (BettingPros) = "Alatengheili"
pair = lambda x1, y1, x2, y2: (same(x1, x2) and same(y1, y2)) or (same(x1, y2) and same(y1, x2))

# ---------------------------------------------------------------- formatting + registry
def ml_of(p):
    if p is None or p <= 0 or p >= 1: return None
    return -round(100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)
US_BOOKS = {"draftkings", "fanduel", "betmgm", "williamhill_us", "caesars", "betrivers", "fanatics", "espnbet", "hardrockbet", "circasports"}
def imp(m): return 100 / (m + 100) if m > 0 else -m / (-m + 100)
def dec_odds(m): return 1 + m / 100 if m > 0 else 1 + 100 / -m
def fair(p): p = min(max(p, .001), .999); return 1 / (1 + math.exp(-K * math.log(p / (1 - p))))
def mls(v): return "—" if v is None else (f"+{v}" if v > 0 else str(v))
FMT = {"pct1": lambda x: f"{x*100:.1f}%", "pct0": lambda x: f"{x*100:.0f}%", "ml": lambda x: mls(x), "mlp": lambda x: mls(ml_of(x)),
       "n1": lambda x: f"{x:.1f}", "n2": lambda x: f"{x:.2f}", "s2": lambda x: f"{x:+.2f}", "int": lambda x: str(x), "intc": lambda x: f"{x:,}",
       "d3": lambda x: f"{x:.3f}", "d4": lambda x: f"{x:.4f}", "str": lambda x: str(x), "in": lambda x: f'{x}"', "r0": lambda x: str(int(round(x))),
       "pts": lambda x: f"{abs(x)*100:.1f}", "sp": lambda x: f"{x*100:+.1f}", "spp": lambda x: f"{x*100:+.1f}%", "s1": lambda x: f"{x:+.1f}", "sint": lambda x: f"{int(x):+d}", "mmss": lambda x: f"{int(x) // 60}:{int(round(x)) % 60:02d}"}

class Reg:
    def __init__(s): s.rows = []
    def __call__(s, raw, fmt, rule, desc, **args):
        i = f"v{len(s.rows)+1}"; txt = FMT[fmt](raw)
        s.rows.append(dict(id=i, text=txt, fmt=fmt, rule=rule, args=args, desc=desc, raw=raw))
        return f'<span data-id="{i}">{esc(txt)}</span>'

# ---------------------------------------------------------------- source lookups
def pub_fight(an, bn):
    for pf in (PUB or {}).get("fights", []):
        if pf.get("publish") is not False and pair(pf["dog"], pf["fav"], an, bn): return pf
def bp_fight(an, bn):
    for bf in BPO["fights"]:
        if pair(bf["fighter_a"]["name"], bf["fighter_b"]["name"], an, bn): return bf
def bp_name(bf, F):  # BettingPros spelling of fighter F
    return next(x["name"] for x in (bf["fighter_a"], bf["fighter_b"]) if same(x["name"], F))
def bp_sel(bf, market, label):
    return next((s for s in bf["markets"].get(market, []) if s["label"] == label), None)

def agg(lines):
    a = dict(n=0, w=0, l=0, d=0, nc=0, secs=0, s=[0] * 13)
    for x in lines:
        a["n"] += 1; r = x["r"]
        a["w" if r == "W" else "l" if r == "L" else "d" if r == "D" else "nc"] += 1
        if x.get("s") and x.get("secs"):
            a["secs"] += x["secs"]; a["s"] = [u + v for u, v in zip(a["s"], x["s"])]
    s, mn = a["s"], a["secs"] / 60
    a.update(slpm=s[0] / mn if mn else None, sapm=s[2] / mn if mn else None, diff=(s[0] - s[2]) / mn if mn else None,
             acc=s[0] / s[1] if s[1] else None, dfn=1 - s[2] / s[3] if s[3] else None, td15=s[6] / mn * 15 if mn else None,
             tdd=1 - s[8] / s[9] if s[9] else None, ctrlp=s[10] / a["secs"] if a["secs"] else None)
    a["rec"] = f'{a["w"]}-{a["l"]}-{a["d"]}' + (f' ({a["nc"]} NC)' if a["nc"] else "")
    return a

def sparkline(series):
    W, H, Lm, Rm, T, B = 560, 120, 34, 46, 10, 20
    pts = [(dt.datetime.fromisoformat(r[0]), r[1]) for r in series if r[1] is not None]
    t0, t1 = pts[0][0], pts[-1][0]; lo = min(p for _, p in pts); hi = max(p for _, p in pts)
    pad = max(.02, (hi - lo) * .15); lo, hi = max(.01, lo - pad), min(.99, hi + pad)
    X = lambda t: Lm + (W - Lm - Rm) * ((t - t0).total_seconds() / max(1, (t1 - t0).total_seconds()))
    Y = lambda p: T + (H - T - B) * (1 - (p - lo) / (hi - lo))
    d = "".join(("M" if i == 0 else "L") + f"{X(t):.1f} {Y(p):.1f}" for i, (t, p) in enumerate(pts))
    g = "".join(f'<line x1="{Lm}" x2="{W-Rm}" y1="{Y(lo+(hi-lo)*k/2):.1f}" y2="{Y(lo+(hi-lo)*k/2):.1f}" stroke="#e5e1d8"/><text x="{Lm-5}" y="{Y(lo+(hi-lo)*k/2)+3.5:.1f}" text-anchor="end" font-size="10" fill="#6b6b6b">{(lo+(hi-lo)*k/2)*100:.0f}%</text>' for k in range(3))
    ticks = "".join(f'<text x="{Lm+(W-Lm-Rm)*fr:.1f}" y="{H-5}" text-anchor="{an}" font-size="10" fill="#6b6b6b">{(t0+(t1-t0)*fr).strftime("%b %-d")}</text>' for fr, an in [(0, "start"), (.5, "middle"), (1, "end")])
    (ta, pa), (tb, pb) = pts[0], pts[-1]
    return (f'<svg class="spark" viewBox="0 0 {W} {H}" role="img" aria-label="No-vig consensus win % history">{g}{ticks}<path d="{d}" fill="none" stroke="#1a1a1a" stroke-width="2"/>'
            f'<circle cx="{X(ta):.1f}" cy="{Y(pa):.1f}" r="3.5" fill="#fff" stroke="#1a1a1a" stroke-width="1.5"/><circle cx="{X(tb):.1f}" cy="{Y(pb):.1f}" r="4" fill="#0a8842"/>'
            f'<text x="{X(tb)+7:.1f}" y="{Y(pb)+4:.1f}" font-size="11" font-weight="700" fill="#0a8842">{pb*100:.1f}%</text></svg>')

SITE = "https://szerillo.github.io/ufc-projections/"
GPART = {"st": "striking", "gr": "grappling", "pw": "power", "ca": "cardio", "en": "endings"}
PARTS = {"Moneyline": "ml", "Fight": "length", "Method": "method"}   # Block 59h: ?part=<key> shows one section alone


SPOTS = {}
TREND_PTS = {}
LHF = ARGS.line_history or f"data/embeds/line_history_{SLUG}.json"; LH = json.loads((REPO / LHF).read_text())
LABS_ACC = json.loads((REPO / "form/data/labs.json").read_text())["scoring"]["acc"]   # decision-model accuracy, quoted in the key


def explain(items):
    """Block 59g: plain-English key for a section, closed by default."""
    return ('<details class="xpl"><summary>What these numbers mean</summary><dl>'
            + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items) + "</dl></details>")


XPL = {
    "proj": [("Model", "Our projection: the fair price and win chance for each side."),
             ("Listed", "The price on our sheet when the projection was published."),
             ("Market", "The current consensus price. The % is the straight conversion of that price, so it still includes the book's margin."),
             ("Edge", "Model % minus the listed % (moneyline, goes the distance) or minus the market % (inside the distance, method). Positive means the model likes that side more than the price does. Coloured only at 2.0 points or more either way."),
             ("Price unavailable", "The odds feed has a price, but it fails our sanity rule (rule v3: a one-sided distance market; this bout's method prices adding up to over 140% or, when complete, under 100%; a draw shorter than +1000; or two of them opening at exactly +100), so we do not show it. Not offered = no price in the feed."),
             ("Line move", "How far the win chance has moved from the opener to the current line, with the opener of the side it moved toward. The current line uses US-regulated books only."),
             ("Spot to watch", "Shows only when a tested angle applies to this fight: the striking-edge rule (career strike differential gap 1.9+ per minute, both fighters with 4+ UFC fights), the round-3 rule (R3 differential gap about 2.9+ per minute), or the comeback spot (one fighter much better in round 3 than round 1 relative to the other). Each line gives the test it comes from. None has been tested on live prices."),
             ("Price unverified", "The listed price was not seen at a US-regulated book in the 24 hours before our projection was published, so we do not colour its edge until the sheet is checked.")],
    "st": [("Where they land", "Share of each fighter's landed significant strikes that hit the head, body and legs."),
           ("Diff /min", "Strikes landed minus strikes absorbed to that target, per minute of fight time."),
           ("Head defence", "Share of opponents' head strikes that missed.")],
    "gr": [("Takedowns /15", "Takedowns landed per 15 minutes."),
           ("TD accuracy / defence", "Share of their takedown attempts that land; share of opponents' attempts they stop."),
           ("Time in control / controlled", "Share of fight time spent controlling the opponent, or being controlled."),
           ("Net control, opp-adjusted", "Control time minus time controlled, as a share of fight time, corrected for how strong the opponents were. Controlling good opponents counts for more. In testing it predicted who wins the grappling better than the raw number in each of the last five years."),
           ("Won the grappling", "Fights with real grappling (a minute of control or a takedown): who had more control time, or more takedowns when control was level."),
           ("Sub attempts /15", "Submission attempts per 15 minutes.")],
    "pw": [("Power", "Share of UFC fights where they knocked the opponent down or stopped them on the feet. Ground-and-pound finishes without a knockdown do not count."),
           ("Durability", "Share of UFC fights where they were knocked down or stopped by strikes (doctor and injury stoppages left out). Lower is better, so the scale runs backwards: right is better on both."),
           ("Recent fights count more", "The latest fight counts fully and a fight three back counts half. Last 5 and all-time counts are shown next to the %."),
           ("Black tick", "The division average in UFC fights since 2020.")],
    "ca": [("Rounds won", "Share of rounds they won. A round that ends in a finish goes to the fighter who finished it. Other rounds are scored by our judging model (strikes by target, knockdowns, takedowns, control time, submission attempts), which picks the winner of UFC decisions " + f"{LABS_ACC*100:.0f}% of the time."),
           ("Small numbers", "Strike differential per minute in that round, and how many UFC fights reached it."),
           ("Five-round rows", "Output and differential in rounds 4-5 compared with rounds 1-3, for fighters who have been there."),
           ("Output kept R3", "Round-3 significant strike attempts as a share of round-1 attempts, in fights that got through round 3 (Labs; needs 3 such fights). Over 100% means they throw more late.")],
    "en": [("Bar", "UFC results by method: wins by KO, submission and decision, then losses."),
           ("Avg fight, Finished in R1", "Average fight length in minutes, and share of their fights that ended in round 1.")],
}
GEN = "All stats use UFC fights before this card only. Green = the better side; darker green = a bigger gap. A small fight count beside a number means it is below the sample Labs requires (5 UFC fights for head defence, 3 for pace)."   # the public Fight Form site the embeds link into


def minispark(series, who):
    """Block 59f: small line under the moneyline stack (market win % of the first-named fighter)."""
    W, H, Lm, Rm, T, B = 300, 46, 4, 44, 6, 6
    pts = [(dt.datetime.fromisoformat(r[0]), r[1]) for r in series if r[1] is not None]
    t0, t1 = pts[0][0], pts[-1][0]; lo = min(p for _, p in pts); hi = max(p for _, p in pts)
    pad = max(.01, (hi - lo) * .15); lo, hi = lo - pad, hi + pad
    X = lambda t: Lm + (W - Lm - Rm) * ((t - t0).total_seconds() / max(1, (t1 - t0).total_seconds()))
    Y = lambda p: T + (H - T - B) * (1 - (p - lo) / (hi - lo))
    d = "".join(("M" if i == 0 else "L") + f"{X(t):.1f} {Y(p):.1f}" for i, (t, p) in enumerate(pts))
    (ta, pa), (tb, pb) = pts[0], pts[-1]
    return (f'<svg class="mspark" viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="{esc(who)} market win % from {pa*100:.0f}% to {pb*100:.0f}%">'
            f'<path d="{d}" fill="none" stroke="#1a1a1a" stroke-width="1.6" vector-effect="non-scaling-stroke"/>'
            f'<circle cx="{X(ta):.1f}" cy="{Y(pa):.1f}" r="2.5" fill="#fff" stroke="#1a1a1a"/><circle cx="{X(tb):.1f}" cy="{Y(pb):.1f}" r="3" fill="#0a8842"/></svg>')

# ---------------------------------------------------------------- CSS: copied verbatim from the site's fight-form widget
def css_rules(src, selectors):
    out = []
    for sel in selectors:
        m = re.search(r"^" + re.escape(sel) + r"\s*\{.*?^\}", src, re.M | re.S)
        if not m: raise SystemExit(f"selector not found in ufc_333_fight_form.html: {sel}")
        out.append(m.group(0))
    return "\n".join(out)
SITE_CSS = css_rules(W333, [":root", ".ff-header", ".ff-title", ".ff-subtitle", ".ff-byline-header", ".ff-byline-header a", ".ff-odds-status", ".ff-odds-status .dot",
    ".ff-brand", ".ff-brand-text", ".ff-brand-check", ".ff-brand-check svg", ".fp-title-belt", ".fp-title-row", ".fp-fight-num", ".fp-card-tag", ".fp-weight", ".fp-headline",
    ".fp-headline .vs", ".fp-odds", ".fp-odds .num", ".fp-proj", ".fp-proj-header", ".fp-proj-header .bullet", ".fp-proj-table", ".fp-proj-table th", ".fp-proj-table th.tleft",
    ".fp-proj-table td", ".fp-proj-table td.tleft", ".fp-proj-table tr:last-child td", ".fp-proj-table .odds", ".fp-proj-table .pct", ".fp-proj-table tr.fav td:first-child",
    ".fp-proj-table tr.dog td:first-child", ".fp-proj-table td.itd-col", "details.collapsible", "details.collapsible > summary", "details.collapsible > summary::-webkit-details-marker",
    "details.collapsible > summary::before", "details.collapsible[open] > summary::before", "details.collapsible > summary .bullet", "details.collapsible > summary .meta", "details.collapsible > .body"])
CHECK_SVG = re.search(r'<span class="ff-brand-check">(<svg.*?</svg>)</span>', W333, re.S).group(1)

# ---------------------------------------------------------------- bout order (v4)
ORDER = OVR["order"]                       # main event first, as on UFC.com; cancelled bout already removed
NB = len(ORDER)
def bout_no(an, bn):
    """Fight number = position on the card counted from the opener: 1 = first early prelim, NB = main event."""
    i = next(i for i, s in enumerate(ORDER) if pair(*s.split("|"), an, bn))
    return NB - i, i
SRC_NOTE = {"publish": ", from the sheet's Publish to site export",
            "sheet": "; no Publish to site export for this card, so these are the site build's sheet pull",
            "widget": "; no Publish to site export for this card, so these are the card widget's projections",
            "event_publish": "; export file not found, so these are the export numbers already in the site's event file", None: ""}
CANC = "".join(f"; cancelled {esc(x)}–{esc(y)} is not counted" for x, y in OVR.get("cancel", []))
MOVL = {"dec": "Points", "ko": "KO/TKO/DQ", "sub": "Submission"}
def mov_ok(bf, an, bn):
    """BettingPros method / distance markets look broken on some low-profile bouts (draw priced near even,
    opening prices of exactly 100, one-sided distance market). Returns (method_ok, distance_ok, reasons)."""
    why = []; mv = bf["markets"].get("method_of_victory", [])
    have = {s["label"] for s in mv}
    miss = [F for F in (an, bn) if not all(f"{bp_name(bf, F)} {MOVL[k]}" in have for k in ("dec", "ko", "sub"))]
    if miss: why.append("method market has no DEC/KO/SUB prices for " + " or ".join(miss))
    # Broken-price rule v3 (claude/Price_Rule_v3_PREREG_2026-11-12.md, sha 93ee47e7; passed its one run): judged only on
    # the rows this embed reads, "<fighter> KO/TKO/DQ | Submission | Points" for the bout's two feed names, plus "Draw"
    use = [s for s in mv if s["label"] == "Draw" or s["label"] in {f"{bp_name(bf, F)} {MOVL[k]}" for F in (an, bn) for k in ("dec", "ko", "sub")}]
    ip = lambda c: 100 / (c + 100) if c > 0 else -c / (-c + 100)
    tot = sum(ip(s["books"]["consensus"]["cost"]) for s in use)
    if tot > 1.40: why.append(f"method outcomes sum to {tot * 100:.0f}% (margin over 40%)")                     # B
    if len(use) >= 7 and tot < 1.0: why.append(f"complete method set sums to {tot * 100:.0f}% (under 100%)")    # C
    dr = next((s for s in use if s["label"] == "Draw"), None)
    if dr and dr["books"]["consensus"]["cost"] < 1000: why.append(f'draw priced {mls(dr["books"]["consensus"]["cost"])}')  # D
    if sum(1 for s in use if s.get("opening_cost") == 100) >= 2: why.append("opening prices of exactly +100")   # O
    fd = {s["label"] for s in bf["markets"].get("fight_distance", [])}
    d_ok = {"Yes", "No"} <= fd
    if not d_ok: why.append("distance market has only " + "/".join(sorted(fd)))
    return not any("draw" in w or "opening" in w or "method market" in w or "margin" in w or "under 100" in w for w in why), d_ok, why

# ---------------------------------------------------------------- build one fight
def build(names, outname):
    R = Reg(); gaps = []
    f = next(x for x in EVL["fights"] if pair(x["a"]["name"], x["b"]["name"], *names))
    SN = f["n"]        # the event file's n (= bout order once card_overrides has run); shown, never used to find a row
    PAIR = [f["a"]["name"], f["b"]["name"]]   # Block 58: registry rows locate their source bout by both fighters' names
    A_, B_ = f["a"], f["b"]; an, bn = A_["name"], B_["name"]
    n, pos = bout_no(an, bn)
    def ffile(X):   # UFC debutants have no fighter file (no UFC fights yet)
        p_ = L / "fighters" / f'{X["slug"]}.json' if X.get("slug") else None
        if p_ and p_.exists(): return json.load(open(p_))
        em_ = json.load(open(L / "embed_metrics" / f"{SLUG}.json"))["fighters"].get(X["name"]) or {}   # Block 59i: debut bio from UFCStats list
        return {"name": X["name"], "bio": em_.get("bio") or {}, "fights": []}
    FA, FB = ffile(A_), ffile(B_)
    pa_ = [x for x in FA["fights"] if x["d"] < EVL["date"]]; pb_ = [x for x in FB["fights"] if x["d"] < EVL["date"]]
    ga, gb = agg(pa_), agg(pb_)
    fm = f.get("form")
    # Block 59n (Kirk round 6): line history from data/embeds/line_history_<slug>.json (scripts/build_line_history.py):
    # opener from 3+ books of any kind, current line from US-regulated books only; no book is ever named on the page
    lh = LH["fights"].get(f"{an}|{bn}") or {}
    o_open, o_cur = lh.get("open"), lh.get("current")
    o = {"open": o_open, "close": o_cur, "series": [[x_["t"], x_["p"]] for x_ in lh.get("series", [])]} if (o_open and o_cur) else None
    def listed_ok(sd):
        c_ = (lh.get("listed") or {}).get(sd)
        return True if c_ is None else c_["ok"]
    pf, bf = pub_fight(an, bn), bp_fight(an, bn)
    a_is_dog = pf is not None and same(pf["dog"], an)
    role = lambda sd: None if pf is None else (("dog" if a_is_dog else "fav") if sd == "a" else ("fav" if a_is_dog else "dog"))
    # Sean's projection: the Publish to site export; else the event file's model block (older sheet pull / widget)
    EM = f.get("model") if pf is None else None
    if EM and (EM.get("a") or {}).get("win") is None: EM = None
    proj_src = "publish" if pf else ({"sheet": "sheet", "publish": "event_publish"}.get(EM.get("src"), "widget") if EM else None)
    def pwin(sd):
        if pf is not None: return pf["sheet"]["true_dog" if role(sd) == "dog" else "true_fav"]
        return EM[sd]["win"] / 100 if EM else None
    nm_of = {"a": an, "b": bn}; oth = {"a": "b", "b": "a"}
    day = dt.date.fromisoformat(EVL["date"]).strftime("%A, %B %-d, %Y")
    seg = OVR["segments"]
    card_tag = "MAIN EVENT" if pos == 0 else "MAIN CARD" if pos < seg["main"] else "PRELIMS" if pos < seg["main"] + seg["prelims"] else "EARLY PRELIMS"
    sched = f.get("sched") or 3
    m_ok, d_ok, bad_why = mov_ok(bf, an, bn) if bf else (False, False, [])

    # ---------- header (site .ff-header + .fp-title-row, as in ufc_333_fight_form.html); text only ----------
    bp_t = BPO["updated_at"].replace("T", " ")[:16] + " UTC"
    # Block 59j (Kirk): source timestamps on every embed, so a stale price is visible to the reader
    pub_t = (PUB.get("published_at") or "").replace("T", " ")[:16] + " UTC" if pf else "not published"
    # Block 59n (Kirk round 6, 4a): one small muted "Data as of" line; no source, book or method names
    sh_ = lambda t_: t_[5:16].replace("-", "/").replace("T", " ") + " UTC"
    lm_t = sh_(o["close"]["t"]) if o else (sh_(o_open["t"]) + " (opener only)" if o_open else "n/a")
    stamps = f'Data as of: sheet {esc(sh_(PUB["published_at"]) if pf else "n/a")} · odds {esc(sh_(BPO["updated_at"]))} · line move {esc(lm_t)}'
    status = f'<div class="ff-odds-status"><span class="dot"></span>Odds updated {esc(bp_t)}</div>'
    def meta(F, g, side, key):
        fig = fm[key] if fm else None
        return (f'{esc(last(F["name"]))} <span class="num">{R(g["rec"], "str", "record", F["name"]+" UFC record", side=side)}</span> · Elo <span class="num">{R(f[side]["elo"], "int", "ev", F["name"]+" Elo", ev=EVF, pair=PAIR, path=f"{side}.elo")}</span>'
                f' · Fig <span class="num">{R(fig, "n1", "ev", F["name"]+" Form Figure", ev=EVF, pair=PAIR, path=f"form.{key}") if fig is not None else "—"}</span>')
    # ---------- tale of the tape (Block 59c): compact, open, under the names; arrows point at the side with the edge ----------
    agA = (dt.date.fromisoformat(EVL["date"]) - dt.date.fromisoformat(FA["bio"]["dob"])).days / 365.25 if FA["bio"].get("dob") else None
    agB = (dt.date.fromisoformat(EVL["date"]) - dt.date.fromisoformat(FB["bio"]["dob"])).days / 365.25 if FB["bio"].get("dob") else None
    def inch(h):
        m_ = re.match(r"(\d+)'\s*(\d+)", str(h or "")); return int(m_.group(1)) * 12 + int(m_.group(2)) if m_ else None
    # rules: height 2+ in = 1 arrow, 4+ = 2; reach 2+ in = 1, 5+ = 2; age 3+ years younger = 1, 6+ = 2
    RULES = {"Height": (2, 4), "Reach": (2, 5), "Age": (3, 6)}
    def arrows(lab, va, vb, better):
        if va is None or vb is None: return ""
        d_ = (va - vb) if better == "hi" else (vb - va)
        t1, t2 = RULES[lab]; k_ = 2 if abs(d_) >= t2 else 1 if abs(d_) >= t1 else 0
        if not k_: return ""
        return f'<span class="arw" aria-label="{k_} arrow{"s" if k_ > 1 else ""} toward {esc(last(an if d_ > 0 else bn))}">{("◀" if d_ > 0 else "▶") * k_}</span>'
    def mrow(lab, ca, cb, arw="", win=None):
        ea, eb = (" adv", "") if win == "a" else ("", " adv") if win == "b" else ("", "")
        return f'<div class="mt-r"><div class="mt-a{ea}">{ca}</div><div class="mt-k">{lab}{arw}</div><div class="mt-b{eb}">{cb}</div></div>'
    hA, hB = inch(FA["bio"].get("ht")), inch(FB["bio"].get("ht"))
    ra_ = int(FA["bio"]["reach"]) if FA["bio"].get("reach") else None; rb_ = int(FB["bio"]["reach"]) if FB["bio"].get("reach") else None
    def wside(va, vb, better, lab):
        if va is None or vb is None or not arrows(lab, va, vb, better): return None
        return "a" if ((va > vb) if better == "hi" else (va < vb)) else "b"
    def v_(x, fmt, rule, desc, side, **k): return R(x, fmt, rule, desc, side=side, **k) if x not in (None, "") else '<span class="dim">n/a</span>'
    mini_tape = ('<div class="mt" data-part="tape" role="table" aria-label="Tale of the tape">'
        + mrow("UFC record", v_(ga["rec"], "str", "record", an + " UFC record", "a"), v_(gb["rec"], "str", "record", bn + " UFC record", "b"))
        + mrow("Age", v_(agA, "n1", "age", "Age a", "a"), v_(agB, "n1", "age", "Age b", "b"), arrows("Age", agA, agB, "lo"), wside(agA, agB, "lo", "Age"))
        + mrow("Height", v_(FA["bio"].get("ht"), "str", "bio", "Height a", "a", key="ht"), v_(FB["bio"].get("ht"), "str", "bio", "Height b", "b", key="ht"), arrows("Height", hA, hB, "hi"), wside(hA, hB, "hi", "Height"))
        + mrow("Reach", v_(ra_, "in", "bio_reach", "Reach a", "a"), v_(rb_, "in", "bio_reach", "Reach b", "b"), arrows("Reach", ra_, rb_, "hi"), wside(ra_, rb_, "hi", "Reach"))
        + mrow("Stance", v_(FA["bio"].get("stance"), "str", "bio", "Stance a", "a", key="stance"), v_(FB["bio"].get("stance"), "str", "bio", "Stance b", "b", key="stance"))
        + '</div>')
    head = f'''<div class="ff-header"><div class="ff-brand" aria-label="Action Network"><span class="ff-brand-text">ACTION</span><span class="ff-brand-check">{CHECK_SVG}</span></div>
<div class="ff-title">{esc(EVL["name"])} · Fight Form</div><div class="ff-subtitle">{day} · {esc(EVL["location"])}</div>
<div class="ff-byline-header">By <a href="https://twitter.com/SeanZerillo" target="_blank" rel="noopener">@SeanZerillo</a></div>{status}</div>
<div class="panel"><div class="fp-title-row"><span class="fp-fight-num">FIGHT {n}</span><span class="fp-card-tag">{card_tag}</span>{'<span class="fp-title-belt">★ TITLE</span>' if f.get("title") else ""}{'<span class="fp-thin" title="3 or fewer UFC fights before this card">THIN SAMPLE</span>' if min(ga["n"], gb["n"]) <= 3 else ""}<span class="fp-weight">{esc(f["wc"])} · {sched} RDS</span></div>
<div class="fp-headline">{esc(an)} <span class="vs">vs</span> {esc(bn)}</div>
{mini_tape}'''

    # ---------- PROJECTION (Block 59b): the old embed's horizontal stacks, Model vs Listed vs Market, edge chips ----------
    # Market % is the straight conversion of the price (vig included), as Sean asked; nothing on this tab is de-vigged.
    def chip(sid, mid, lab, unver=False):
        sv = next(r_["raw"] for r_ in R.rows if r_["id"] == sid); mv_ = next(r_["raw"] for r_ in R.rows if r_["id"] == mid)
        # Block 59n (Kirk round 6): coloured only at 2.0 points or more on the shown (0.1-rounded) edge; a Listed price that
        # failed the Listed-price check stays neutral with "price unverified"
        e = sv - mv_; e1 = round(e * 100, 1); cls = "flat" if unver else "pos" if e1 >= 2.0 else "neg" if e1 <= -2.0 else "flat"
        return f'<span class="ech {cls}">{R(e, "spp", "edge", lab, of=[sid, mid])}</span>' + ('<span class="unv">price unverified</span>' if unver else "")
    def lid(): return R.rows[-1]["id"]
    def cell(price_html, pct_html, cls=""):
        return f'<td class="{cls}"><span class="odds">{price_html}</span><div class="pct">{pct_html}</div></td>'
    def stack(title, heads, body):
        return (f'<div class="stk" data-part="{PARTS.get(title.split(" ")[0], "")}"><div class="stk-h"><span class="bullet"></span>{title}</div><table class="stk-t"><thead><tr>'
                + "".join(f'<th{" class=l" if k == 0 else ""}>{h}</th>' for k, h in enumerate(heads)) + f'</tr></thead><tbody>{body}</tbody></table></div>')
    side_cls = {"a": "fav" if (pwin("a") or .5) >= .5 else "dog"}; side_cls["b"] = "dog" if side_cls["a"] == "fav" else "fav"
    proj = ""
    if pf:
        # moneyline: Model | Listed | Market | Edge (edge = model minus listed implied, as the old embed did)
        body = ""
        for sd in ("a", "b"):
            F = nm_of[sd]; p_ = pwin(sd)
            mdl = cell(R(p_, "mlp", "pub_win", "Model ML " + F, side=sd), R(p_, "pct1", "pub_win", "Model win % " + F, side=sd), "model"); m_id = lid()
            lst_ml = pf["inputs"]["dog_odds" if role(sd) == "dog" else "fav_odds"]
            lst = cell(R(lst_ml, "ml", "pub_ml", "Listed ML " + F, side=sd), R(imp(lst_ml), "pct1", "pub_ml_imp", "Listed implied " + F, side=sd)); l_id = lid()
            if bf:
                lab_ = bp_name(bf, F); c_ = bp_sel(bf, "moneyline", lab_)["books"]["consensus"]["cost"]
                mk = cell(R(c_, "ml", "bp", "Market ML " + F, market="moneyline", label=lab_, field="cost"), R(imp(c_), "pct1", "bp_imp", "Market implied " + F, market="moneyline", label=lab_))
            else:
                mk = '<td class="dim">n/a</td>'
            nmcell = f'<td class="l nm"><i class="dot {side_cls[sd]}"></i>{esc(F)}<div class="nb"><i class="{side_cls[sd]}" style="width:{p_*100:.1f}%"></i></div></td>'
            body += f'<tr>{nmcell}{mdl}{lst}{mk}<td>{chip(m_id, l_id, "Edge ML " + F, unver=not listed_ok(sd))}</td></tr>'
        proj += stack("Moneyline · model vs market", ["Fighter", "Model", "Listed", "Market", "Edge"], body).replace("</table></div>", "</table>@@MOVE@@@@ANGLES@@</div>", 1)
        # fight length: GTD (listed from the sheet) and ITD; edge vs listed for GTD, vs market for ITD
        body = ""
        g = pf["gtd"]
        mdl = cell(R(g, "mlp", "pub", "Model GTD", key="gtd"), R(g, "pct1", "pub", "Model GTD %", key="gtd"), "model"); m_id = lid()
        gl = pf.get("gtd_listed")
        if gl is not None:
            lst = cell(R(gl, "mlp", "pub", "Listed GTD price", key="gtd_listed"), R(gl, "pct1", "pub", "Listed GTD %", key="gtd_listed")); l_id = lid()
        else:
            lst, l_id = '<td class="dim">n/a</td>', None
        if bf and d_ok:
            y = bp_sel(bf, "fight_distance", "Yes")["books"]["consensus"]["cost"]
            mk = cell(R(y, "ml", "bp", "Market GTD yes", market="fight_distance", label="Yes", field="cost"), R(imp(y), "pct1", "bp_imp", "Market GTD implied", market="fight_distance", label="Yes")); y_id = lid()
        else:
            mk, y_id = ('<td class="dim pu">price unavailable</td>' if bf and not d_ok else '<td class="dim">n/a</td>'), None
        ed = chip(m_id, l_id, "Edge GTD vs listed") if l_id else (chip(m_id, y_id, "Edge GTD vs market") if y_id else '<span class="dim">n/a</span>')
        body += f'<tr><td class="l nm">Goes the distance</td>{mdl}{lst}{mk}<td>{ed}</td></tr>'
        mdl = cell(R(1 - g, "mlp", "pub", "Model ITD", key="gtd", inv=True), R(1 - g, "pct1", "pub", "Model ITD %", key="gtd", inv=True), "model"); m_id = lid()
        if bf and d_ok:
            no = bp_sel(bf, "fight_distance", "No")["books"]["consensus"]["cost"]
            mk = cell(R(no, "ml", "bp", "Market ITD no", market="fight_distance", label="No", field="cost"), R(imp(no), "pct1", "bp_imp", "Market ITD implied", market="fight_distance", label="No")); n_id = lid()
            ed = chip(m_id, n_id, "Edge ITD vs market")
        else:
            mk, ed = ('<td class="dim pu">price unavailable</td>' if bf and not d_ok else '<td class="dim">n/a</td>'), '<span class="dim">n/a</span>'
        body += f'<tr><td class="l nm">Inside the distance</td>{mdl}<td class="dim">n/a</td>{mk}<td>{ed}</td></tr>'
        proj += stack("Fight length · GTD and ITD", ["Outcome", "Model", "Listed", "Market", "Edge"], body)
        mx = max(pwin(sd) * (pf["method"][role(sd)]["ko"] + pf["method"][role(sd)]["sub"]) for sd in "ab")
        mx = max([mx] + [pwin(sd) * pf["method"][role(sd)][k] for sd in "ab" for k in ("dec", "ko", "sub")]) or 1
        body = ""
        for sd in ("a", "b"):
            F = nm_of[sd]; tds = ""; tdm = ""
            for k in ("dec", "ko", "sub", "itd"):
                m = pf["method"][role(sd)]; v = pwin(sd) * (m["ko"] + m["sub"] if k == "itd" else m[k])
                mp = R(v, "mlp", "pub_meth", f"Model {k} ML {F}", side=sd, k=k); mpc = R(v, "pct1", "pub_meth", f"Model {k} % {F}", side=sd, k=k); m_id = lid()
                broken = bool(bf) and any(("draw" in w_ or "opening" in w_ or "margin" in w_ or "under 100" in w_) for w_ in bad_why)
                own_ok = bf and not broken and all(bp_sel(bf, "method_of_victory", f"{bp_name(bf, F)} {MOVL[x]}") for x in ("dec", "ko", "sub"))
                if own_ok:
                    if k == "itd":
                        labs_ = [f"{bp_name(bf, F)} {MOVL[x]}" for x in ("ko", "sub")]
                        iv = sum(imp(bp_sel(bf, "method_of_victory", lb)["books"]["consensus"]["cost"]) for lb in labs_)
                        live = f'<div class="live">&nbsp;</div><div class="live">{R(iv, "pct1", "bp_imp_sum", f"Market ITD implied {F}", market="method_of_victory", labels=labs_)}</div>'
                    else:
                        lb = f"{bp_name(bf, F)} {MOVL[k]}"; c_ = bp_sel(bf, "method_of_victory", lb)["books"]["consensus"]["cost"]
                        live = f'<div class="live">{R(c_, "ml", "bp", f"Market {k} {F}", market="method_of_victory", label=lb, field="cost")}</div><div class="live">{R(imp(c_), "pct1", "bp_imp", f"Market {k} implied {F}", market="method_of_victory", label=lb)}</div>'
                    x_id = lid(); ed = chip(m_id, x_id, f"Edge {k} {F}")
                else:
                    live, ed = ('<div class="live dim pu">price unavailable</div>' if broken else '<div class="live dim">not offered</div>'), ""
                tds += f'<td data-k="{k}"><span class="odds">{mp}</span><div class="pct">{mpc}</div><div class="cb"><i class="{side_cls[sd]}" style="width:{v / mx * 100:.1f}%"></i></div></td>'
                tdm += f'<td data-k="{k}" class="mkc">{live}{ed}</td>'
            # Block 59n (Kirk round 6, 4c): no "mkt" tag; a labelled Market row under each fighter's Model row
            body += (f'<tr class="{side_cls[sd]}"><td class="l nm"><i class="dot {side_cls[sd]}"></i>{esc(F)}<div class="rl">Model</div></td>{tds}</tr>'
                     f'<tr class="{side_cls[sd]} mkr"><td class="l rl">Market</td>{tdm}</tr>')
        proj += stack("Method · model vs market", ["Fighter", "DEC", "KO", "SUB", "ITD"], body)
        proj += "@@LIVE@@" + '<div class="legend">Market % is the straight conversion of the price, vig included.</div>' + explain(XPL["proj"])
    else:
        proj += '<div class="note">No model projection published for this bout yet.</div>'
        gaps.append(f"Fight {n}: no row in the Publish to site export; no model numbers shown.")
    top = proj

    PANELS = {}
    def sec(id_, title, meta_, body, open_=False):
        PANELS[id_] = (title, body)
        return f'<details class="collapsible" id="{id_}"{" open" if open_ else ""}><summary><span class="bullet"></span>{title}<span class="meta">{meta_}</span></summary><div class="body">{body}</div></details>'
    secs = []

    # ---------- line movement: folded into the moneyline stack (Block 59f: no books, no open -> now) ----------
    body = ""
    if o:
        mv = o["close"]["p"] - o["open"]["p"]
        tow = an if mv >= 0 else bn
        tsd = "a" if mv >= 0 else "b"
        po, pc = (o["open"]["p"], o["close"]["p"]) if tsd == "a" else (1 - o["open"]["p"], 1 - o["close"]["p"])
        if abs(mv) < 0.01:   # Kirk round 11 D: under 1 pt the bar shows nothing; one line instead (the site marks moves from 1 pt)
            body = (f'<div class="mvrow mvq" data-part="move"><div class="mvt"><span class="mvl">Line</span> Steady · {esc(last(tow))} opened <b class="mvo">{R(o["open"]["m" + tsd], "ml", "lh_open_ml", "LH open ML " + tow, lh=LHF, pair=PAIR, side=tsd)}</b> {o["open"]["t"][5:10].replace("-", "/")} · '
                    f'<b>{R(abs(mv), "pts", "lh_drift_abs", "LH drift pts", lh=LHF, pair=PAIR)}&nbsp;pts</b>'
                    f'<span class="mvasof">line data as of {esc(o["close"]["t"][5:16].replace("-", "/").replace("T", " "))} UTC</span></div>'
                    + (f'<details class="mvx"><summary>Price path</summary>{minispark(o["series"], an)}<div class="mvc">{esc(last(an))} win %, US-regulated books</div></details>' if len(o.get("series") or []) >= 2 else "") + '</div>')
        else:
                body = (f'<div class="mvrow" data-part="move"><div class="mvt"><span class="mvl">Line move</span> {esc(last(tow))} opener <b class="mvo">{R(o["open"]["m" + tsd], "ml", "lh_open_ml", "LH open ML " + tow, lh=LHF, pair=PAIR, side=tsd)}</b> on {o["open"]["t"][5:10].replace("-", "/")}, '
                    f'moved <b>{R(abs(mv), "pts", "lh_drift_abs", "LH drift pts", lh=LHF, pair=PAIR)}&nbsp;pts</b>'
                    f'<span class="mvasof">line data as of {esc(o["close"]["t"][5:16].replace("-", "/").replace("T", " "))} UTC</span></div>'
                    f'<div class="mvtr" role="img" aria-label="{esc(last(tow))} win chance from {po*100:.1f}% at the opener to {pc*100:.1f}% now"><span class="mvp">{R(po, "pct1", "lh_p", "LH open p " + tow, lh=LHF, pair=PAIR, side=tsd, at="open")}</span>'
                    f'<div class="mvbar"><i class="mvfrom" style="left:{po*100:.1f}%"></i><i class="mvspan" style="left:{min(po,pc)*100:.1f}%;width:{abs(pc-po)*100:.1f}%"></i><i class="mvto" style="left:{pc*100:.1f}%"></i></div>'
                    f'<span class="mvp mve">{R(pc, "pct1", "lh_p", "LH current p " + tow, lh=LHF, pair=PAIR, side=tsd, at="current")}</span></div>'
                    f'<div class="mvc">{esc(last(tow))} win chance, opener to now</div>'
                    + (f'<details class="mvx"><summary>Price path</summary>{minispark(o["series"], an)}<div class="mvc">{esc(last(an))} win %, US-regulated books</div></details>' if len(o.get("series") or []) >= 2 else "") + '</div>')
    elif o_open:   # Kirk round 6: opener only; no regulated current line
        fav_sd = "a" if o_open["p"] >= 0.5 else "b"; F_ = an if fav_sd == "a" else bn
        body = (f'<div class="mvrow" data-part="move"><div class="mvt"><span class="mvl">Line move</span> {esc(last(F_))} opener <b class="mvo">{R(o_open["m" + fav_sd], "ml", "lh_open_ml", "LH open ML " + F_, lh=LHF, pair=PAIR, side=fav_sd)}</b> on {o_open["t"][5:10].replace("-", "/")}; '
                f'<span class="dim">current line not available</span></div></div>')
        gaps.append(f"Fight {n}: opener only; no US-regulated current line.")
    else:
        gaps.append(f"Fight {n}: no line history.")
    proj = proj.replace("@@MOVE@@", body)   # @@ANGLES@@ is filled once the stats are built
    top = proj


    # ---------- props detail: dropped (Block 59c, Sean: our projections and stats are the star) ----------

    # ---------- our stats (Block 59c): labs.json (site-built metrics, cardio, pace) + UFCStats grappling rates ----------
    LABS = json.load(open(L / "labs.json"))
    def labv(section, slug, key):
        if not slug: return None
        if section == "metrics":
            r_ = next((x for x in LABS["metrics"] if x.get("s") == slug), None); return None if r_ is None else r_.get(key)
        sec_, sub_ = section.split(".")
        for u in LABS[sec_][sub_]:
            for sd_ in ("a", "b"):
                if isinstance(u.get(sd_), dict) and u[sd_].get("s") == slug and u[sd_].get(key) is not None: return u[sd_][key]
        return None
    BIG = {"sd": 1.0, "hd": 0.8, "bd": 0.3, "ld": 0.3, "hdef": 0.08, "kd15": 0.3, "chin": 1.0, "sw": 6.0, "out": 0.3, "d3": 3.0, "min": 3.0, "r1": 0.2, "dec": 0.2,
           "wko": 0.25, "wsub": 0.2, "lko": 0.2, "lsub": 0.15, "td15": 1.5, "tdd": 0.15, "ctd": 30}
    def srow(lab, bkey, va, vb, fmt, rule, better, tip="", **args):
        if va is None and vb is None: return ""
        ca = R(va, fmt, rule, lab + " a", side="a", **dict(args, slug=A_.get("slug"))) if va is not None else '<span class="dim">n/a</span>'
        cb = R(vb, fmt, rule, lab + " b", side="b", **dict(args, slug=B_.get("slug"))) if vb is not None else '<span class="dim">n/a</span>'
        ea = eb = ""
        if better and va is not None and vb is not None and va != vb:
            aw = va > vb if better == "hi" else va < vb; big = abs(va - vb) >= BIG.get(bkey, 1e9)
            cls_ = " adv big" if big else " adv"; ea, eb = (cls_, "") if aw else ("", cls_)
        return f'<div class="row"><div class="a{ea}">{ca}</div><div class="k" title="{esc(tip)}">{lab}</div><div class="b{eb}">{cb}</div></div>'
    def L3(section, key, lab, fmt, better, tip=""):
        return srow(lab, key, labv(section, A_.get("slug"), key), labv(section, B_.get("slug"), key), fmt, "labs", better, tip, section=section, key=key)
    def grp(title, rows_):
        if not rows_: return ""
        inner = rows_ if rows_.lstrip().startswith("<div class=\"t") or rows_.lstrip().startswith("<div class=\"sc") or rows_.lstrip().startswith("<div class=\"ds") or rows_.lstrip().startswith("<table") else f'<div class="tape">{rows_}</div>'
        return f'<div class="sg"><div class="sg-h">{title}</div><div class="sg-b">{inner}</div></div>'
    # ---------- Block 59d: our database (UFCStats rows, every UFC fight, no minimum) + career KO record ----------
    EMX = json.load(open(L / "embed_metrics" / f"{SLUG}.json"))
    ema, emb = EMX["fighters"].get(an, {}), EMX["fighters"].get(bn, {})
    def emv(rec, path):
        x = rec
        for k_ in path.split("."):
            x = x[int(k_)] if isinstance(x, list) else (x or {}).get(k_)
            if x is None: return None
        return x
    def E(path, lab, fmt, better, tip="", floor=None):
        va, vb = emv(ema, path), emv(emb, path)
        if va is None and vb is None: return ""
        ca = R(va, fmt, "em", lab + " a", fighter=an, path=path) if va is not None else '<span class="dim">n/a</span>'
        cb = R(vb, fmt, "em", lab + " b", fighter=bn, path=path) if vb is not None else '<span class="dim">n/a</span>'
        if floor:   # Block 59k (Kirk): below the Labs sample floor the number stays, with its sample size beside it
            fp_, fmin, fword = floor
            for sd_, F_, rec_ in (("a", an, ema), ("b", bn, emb)):
                nn = emv(rec_, fp_)
                if (va if sd_ == "a" else vb) is not None and nn is not None and nn < fmin:
                    note = f' <small class="ssm">{R(nn, "int", "em", f"{lab} sample {F_}", fighter=F_, path=fp_)} {"fight" if nn == 1 else fword}</small>'
                    if sd_ == "a": ca += note
                    else: cb += note
        ea = eb = ""
        if better and va is not None and vb is not None and va != vb:
            aw = va > vb if better == "hi" else va < vb; big = abs(va - vb) >= BIG.get(path.split(".")[-1], 1e9)
            cls_ = " adv big" if big else " adv"; ea, eb = (cls_, "") if aw else ("", cls_)
        return f'<div class="row"><div class="a{ea}">{ca}</div><div class="k" title="{esc(tip)}">{lab}</div><div class="b{eb}">{cb}</div></div>'
    BIG.update({"head": 0.8, "body": 0.3, "leg": 0.3, "diff_pm": 1.0, "landed_pm": 1.5, "diff_pm_45": 1.5})
    # Block 59h: dot strips, one dot per UFC fight (newest on the left), filled when they won that part of the fight
    def strip(title, key, test, tip):
        rows_ = ""
        for F, sd_, rec in ((an, "a", ema), (bn, "b", emb)):
            fl = [e_ for e_ in (rec.get("fights") or []) if test(e_) is not None]
            kn = rec.get(key) or {}
            if not kn.get("n"): rows_ += f'<div class="ds-r"><span class="tb-n">{esc(last(F))}</span><span class="dim">no fights to count</span></div>'; continue
            dots = "".join(f'<i class="{"on" if test(e_) else "off"}" title="{esc(e_["d"][:7])} vs {esc(e_["o"])}"></i>' for e_ in fl)
            rows_ += (f'<div class="ds-r"><span class="tb-n">{esc(last(F))}</span><span class="ds-d">{dots}</span>'
                      f'<b class="ds-k">{R(kn["k"], "int", "em", f"{title} k {F}", fighter=F, path=key + ".k")} of {R(kn["n"], "int", "em", f"{title} n {F}", fighter=F, path=key + ".n")}</b></div>')
        return f'<div class="ds"><div class="ds-h" title="{esc(tip)}">{title}</div>{rows_}</div>'
    def _ol(e_): return (e_["sl"] > e_["sa"]) if e_["secs"] else None
    def _gw(e_):
        if not (e_["cf"] + e_["ca"] >= 60 or e_["tdl"] + e_["tdo"] > 0): return None
        return (e_["cf"] - e_["ca"] > 0) or (e_["cf"] == e_["ca"] and e_["tdl"] > e_["tdo"])
    # where they land: one stacked bar per fighter (share of significant strikes landed to head / body / legs)
    def tbar(rec, F, sd):
        t_ = rec.get("target") or {}
        if t_.get("head") is None: return f'<div class="tb-row"><span class="tb-n">{esc(last(F))}</span><span class="dim">n/a</span></div>'
        seg = "".join(f'<i class="tb-{k_}" style="width:{t_[k_]*100:.1f}%"><b>{R(t_[k_], "pct0", "em", f"Target {k_} {F}", fighter=F, path=f"target.{k_}")}</b></i>' for k_ in ("head", "body", "leg"))
        return f'<div class="tb-row"><span class="tb-n">{esc(last(F))}</span><div class="tb-bar" role="img" aria-label="{esc(F)} lands {t_["head"]*100:.0f}% head, {t_["body"]*100:.0f}% body, {t_["leg"]*100:.0f}% legs">{seg}</div></div>'
    target_html = (f'<div class="tb"><div class="tb-key"><span><i class="tb-head"></i>Head</span><span><i class="tb-body"></i>Body</span><span><i class="tb-leg"></i>Legs</span><span class="dim">where they land</span></div>'
                   f'{tbar(ema, an, "a")}{tbar(emb, bn, "b")}</div>')
    # power and durability on the feet, against the division: share of UFC fights with a knockdown or a standing KO/TKO,
    # for (power) and against (durability). Ground-and-pound finishes with no knockdown are left out.
    wc_ = re.sub(r"^(UFC )?(Interim )?", "", f.get("wc") or "")
    def scale(title, key, flip, ends):
        davg = EMX["division_power_share" if key == "power" else "division_dropped_share"].get(wc_)
        vals = {}
        for F, sd, rec in ((an, "a", ema), (bn, "b", emb)):
            if rec.get("ufc_fights"): vals[sd] = (rec[key + "_w"], rec[key + "_fights"], rec["ufc_fights"], rec["last5"][key], rec["last5"]["fights"])
        if not vals: return ""
        top = max([0.5] + [v[0] for v in vals.values()] + ([davg] if davg else []))
        px = lambda v: (1 - v / top) * 100 if flip else v / top * 100     # durability runs backwards: right = rarely dropped
        pos = {sd: px(v[0]) for sd, v in vals.items()}
        close = len(pos) == 2 and abs(pos["a"] - pos["b"]) < 4
        marks = ""
        for sd in vals:
            F = an if sd == "a" else bn
            dy = (";top:-2px" if sd == "a" else ";top:10px") if close else ""
            marks += f'<i class="sc-dot {side_cls[sd]}" style="left:{min(max(pos[sd], 1.5), 98.5):.1f}%{dy}" title="{esc(F)}"></i>'
        avg = f'<i class="sc-avg" style="left:{px(davg):.1f}%"></i>' if davg else ""
        def lab(sd, v, k_, n_, k5, n5):
            F = an if sd == "a" else bn
            tag = ""
            if davg and n_ >= 5 and abs(v - davg) >= 0.05:
                good = (v < davg) if flip else (v > davg)
                tag = f' <span class="sc-t {"up" if good else "dn"}">{"better" if good else "worse"} than avg</span>'
            elif davg and n_ < 5: tag = ' <span class="sc-t">small sample</span>'
            # Block 59j declutter: fight counts are printed once, under the section title; here only the events
            return (f'<div class="sc-l"><i class="dot {side_cls[sd]}"></i>{esc(last(F))} <b>{R(v, "pct0", "em", f"{title} {sd}", fighter=F, path=key + "_w")}</b>'
                    f' <span class="dim">· {R(k5, "int", "em", f"{title} last5 {sd}", fighter=F, path="last5." + key)} in last {n5} · {R(k_, "int", "em", f"{title} count {sd}", fighter=F, path=key + "_fights")} all-time</span>{tag}</div>')
        labs_ = "".join(lab(sd, *vals[sd]) for sd in vals)
        avgl = f'<div class="sc-l dim">Division average {R(davg, "pct0", "em_div", "Division share " + title, wc=wc_, key=key)}</div>' if davg else ""
        return (f'<div class="sc"><div class="sc-h">{title}</div><div class="sc-track" role="img" aria-label="{esc(title)}">{avg}{marks}</div>'
                f'<div class="sc-e"><span>{ends[0]}</span><span>{ends[1]}</span></div>{labs_}{avgl}</div>')
    nfa, nfb = ema.get("ufc_fights", 0), emb.get("ufc_fights", 0)
    pw_n = (f'<div class="sc-n">UFC fights: {esc(last(an))} {R(nfa, "int", "em", "Power section fights a", fighter=an, path="ufc_fights")}, '
            f'{esc(last(bn))} {R(nfb, "int", "em", "Power section fights b", fighter=bn, path="ufc_fights")}</div>') if (nfa or nfb) else ""
    power_html = pw_n + (scale("Power: drops or stops them on the feet", "power", False, ("rarely", "often"))
                  + scale("Durability: gets dropped or stopped", "dropped", True, ("often", "rarely")))
    # how their fights end: one bar per fighter, UFC wins (KO, SUB, DEC) then losses (DEC, SUB, KO), counts in the segments
    OC = (("w", "ko", "W KO"), ("w", "sub", "W SUB"), ("w", "dec", "W DEC"), ("l", "dec", "L DEC"), ("l", "sub", "L SUB"), ("l", "ko", "L KO"))
    def obar(rec, F):
        oc = rec.get("outcomes")
        tot = sum(oc[w][m] for w, m, _ in OC) if oc else 0
        if not tot: return f'<div class="tb-row"><span class="tb-n">{esc(last(F))}</span><span class="dim">no UFC results</span></div>'
        seg = "".join(f'<i class="oc-{w}{m}" style="width:{oc[w][m] / tot * 100:.1f}%" title="{lab_} {oc[w][m]}"><b>{R(oc[w][m], "int", "em", f"Outcome {w}{m} {F}", fighter=F, path=f"outcomes.{w}.{m}") if oc[w][m] / tot >= 0.09 else ""}</b></i>'
                      for w, m, lab_ in OC if oc[w][m])
        wl = f'{sum(oc["w"].values())}-{sum(oc["l"].values())}'
        return f'<div class="tb-row"><span class="tb-n">{esc(last(F))}</span><div class="tb-bar oc" role="img" aria-label="{esc(F)} UFC {wl}: ' + ", ".join(f"{lab_} {oc[w][m]}" for w, m, lab_ in OC) + f'">{seg}</div></div>'
    outcome_html = ('<div class="tb"><div class="tb-key">' + "".join(f'<span><i class="oc-{w}{m}"></i>{lab_}</span>' for w, m, lab_ in OC) + '</div>'
                    + obar(ema, an) + obar(emb, bn) + '</div>')
    # cardio by round (UFC rounds, every fight): strike differential per minute, rounds 1-3, plus 4-5 when the fight is scheduled for 5
    nrd = 5 if (f.get("sched") or 3) == 5 else 3
    def rcells(rec, F, sd):
        out_ = ""
        for rd in range(nrd):
            w_ = emv(rec, f"rounds.{rd}.won"); v = emv(rec, f"rounds.{rd}.diff_pm"); nfr = emv(rec, f"rounds.{rd}.fights")
            if w_ is None or not nfr: out_ += '<td class="dim">n/a</td>'; continue
            cl = "pos" if w_ >= 0.6 else "neg" if w_ <= 0.4 else ""
            out_ += (f'<td class="{cl}"><button type="button" class="ddb" data-dd="{sd}{rd + 1}" aria-expanded="false" aria-label="{esc(last(F))} round {rd + 1} fights">'
                     f'<span class="rw">{R(w_, "pct0", "em", f"R{rd+1} won {F}", fighter=F, path=f"rounds.{rd}.won")}</span>'
                     f'<small>{R(v, "s1", "em", f"R{rd+1} diff {F}", fighter=F, path=f"rounds.{rd}.diff_pm")} · {R(nfr, "int", "em", f"R{rd+1} fights {F}", fighter=F, path=f"rounds.{rd}.fights")}</small></button></td>')
        return f'<tr><td class="l nm"><i class="dot {side_cls[sd]}"></i>{esc(last(F))}</td>{out_}</tr>'
    def ddpanels(rec, F, sd):   # Block 59h: tap a round cell to see the fights behind it
        out_ = ""
        for rd in range(1, nrd + 1):
            rows_ = ""
            for i_, e_ in enumerate(rec.get("fights") or []):
                for j_, (r_n, r_w, r_d) in enumerate(e_["rw"]):
                    if r_n != rd: continue
                    opp = esc(e_["o"])
                    if e_.get("es") and e_.get("n") is not None:
                        opp = f'<a class="fl" href="{SITE}#/fight/{e_["es"]}/{e_["n"]}" target="_blank" rel="noopener">{opp}</a>'
                    res = "Won" if r_w == 1 else "Lost" if r_w == 0 else "Even"
                    rows_ += (f'<tr><td class="l dim">{dt.date.fromisoformat(e_["d"]).strftime("%b %y")}</td><td class="l">{opp}</td>'
                              f'<td class="l"><b class="r-{"w" if r_w == 1 else "l" if r_w == 0 else "d"}">{res}</b></td><td>{R(r_d, "sint", "em", f"R{rd} fight diff {F} {i_}", fighter=F, path=f"fights.{i_}.rw.{j_}.2")}</td></tr>')
            if rows_:
                out_ += (f'<div class="dd" data-dd="{sd}{rd}" hidden><div class="dd-h">{esc(last(F))} · round {rd} <button type="button" class="ddx" aria-label="Close">×</button></div>'
                         f'<table class="t ft"><thead><tr><th class="l">When</th><th class="l">Opponent</th><th class="l">Round</th><th>Strikes +/-</th></tr></thead><tbody>{rows_}</tbody></table></div>')
        return out_
    rounds_html = ('<table class="rt"><thead><tr><th class="l">Rounds won</th>' + "".join(f"<th>R{r_+1}</th>" for r_ in range(nrd)) + '</tr></thead><tbody>'
                   + rcells(ema, an, "a") + rcells(emb, bn, "b") + '</tbody></table><div class="rt-n">big = rounds won · small = strike diff per min · fights reaching the round · tap a cell for the fights</div>'
                   + ddpanels(ema, an, "a") + ddpanels(emb, bn, "b"))
    # Block 59o (Kirk round 7): round trend. Strike differential per minute in R1, R2, R3 for both fighters (the same
    # rounds.N.diff_pm numbers as the table), drawn as two lines on one axis with a zero line; a round needs 1+ fight.
    def trend_svg():
        S_ = []
        for rec_, F_, sd_ in ((ema, an, "a"), (emb, bn, "b")):
            pts_ = [(i_, emv(rec_, f"rounds.{i_}.diff_pm")) for i_ in range(3) if (emv(rec_, f"rounds.{i_}.fights") or 0) >= 1 and emv(rec_, f"rounds.{i_}.diff_pm") is not None]
            S_.append((F_, sd_, rec_, pts_))
        # Kirk round 8 A (Round_Trend_Floor_PREREG, sha 55e79839): 15-minute floor per round; line only through rounds at or
        # above it, others hollow grey; chart only if both fighters have 2+ rounds at or above it
        TF = 15.0
        okr = lambda rec_, i_: (emv(rec_, f"rounds.{i_}.mins") or 0) >= TF
        if any(sum(okr(rec_, i_) for i_, _ in pts_) < 2 for _, _, rec_, pts_ in S_): return ""
        vals_ = [v_ for *_, pts_ in S_ for _, v_ in pts_]; lo_, hi_ = min(vals_ + [0]), max(vals_ + [0]); pad_ = max(0.5, (hi_ - lo_) * 0.12); lo_ -= pad_; hi_ += pad_
        W_, H_, L_, Rm_, T_, B_ = 340, 150, 34, 92, 12, 24
        X_ = lambda i_: L_ + i_ * (W_ - L_ - Rm_) / 2; Y_ = lambda v_: T_ + (hi_ - v_) / (hi_ - lo_) * (H_ - T_ - B_)
        col_ = {"fav": "#2a78d6", "dog": "#eb6834"}
        g_ = [f'<line x1="{L_}" x2="{W_ - Rm_}" y1="{Y_(0):.1f}" y2="{Y_(0):.1f}" stroke="#b9b4aa" stroke-width="1" stroke-dasharray="3 3"/>',
              f'<text x="{L_ - 6}" y="{Y_(0) + 3:.1f}" text-anchor="end" font-size="10" fill="#6b665e">0</text>']
        g_ += [f'<text x="{X_(i_):.1f}" y="{H_ - 6}" text-anchor="middle" font-size="10.5" fill="#6b665e">R{i_ + 1}</text>' for i_ in range(3)]
        ends_ = []
        for F_, sd_, rec_, pts_ in S_:
            c_ = col_[side_cls[sd_]]
            full_ = [(i_, v_) for i_, v_ in pts_ if okr(rec_, i_)]
            g_.append(f'<polyline fill="none" stroke="{c_}" stroke-width="2" points="{" ".join(f"{X_(i_):.1f},{Y_(v_):.1f}" for i_, v_ in full_)}"/>')
            g_ += [(f'<circle cx="{X_(i_):.1f}" cy="{Y_(v_):.1f}" r="4" fill="{c_}" stroke="#fff" stroke-width="2"/>' if okr(rec_, i_)
                    else f'<circle class="thin" cx="{X_(i_):.1f}" cy="{Y_(v_):.1f}" r="4" fill="#fff" stroke="#8a857c" stroke-width="2"/>') for i_, v_ in pts_]
            ends_.append([Y_(full_[-1][1]), F_, c_, full_[-1]])
            TREND_PTS.setdefault(n, []).append((F_, [(i_, round(v_, 4)) for i_, v_ in pts_]))
        ends_.sort()
        if len(ends_) == 2 and ends_[1][0] - ends_[0][0] < 14: ends_[0][0] -= (14 - (ends_[1][0] - ends_[0][0])) / 2; ends_[1][0] = ends_[0][0] + 14
        for y_, F_, c_, (i_, v_) in ends_:
            g_.append(f'<text x="{X_(i_) + 9:.1f}" y="{y_ + 4:.1f}" font-size="11" font-weight="700" fill="#1d1b18">{esc(last(F_))}</text>')
        legend_ = " · ".join(f'<b style="color:{col_[side_cls[sd_]]}">{esc(last(F_))}</b> ' + " → ".join(R(v_, "s1", "em", f"Trend R{i_ + 1} {F_}", fighter=F_, path=f"rounds.{i_}.diff_pm")
                             + ("" if okr(rec_, i_) else f' <span class="dim">({R(emv(rec_, f"rounds.{i_}.mins"), "r0", "em", f"Trend R{i_ + 1} mins {F_}", fighter=F_, path=f"rounds.{i_}.mins")} min)</span>') for i_, v_ in pts_) for F_, sd_, rec_, pts_ in S_)
        # Kirk round 9 call 1: a joined round within 1 minute of the floor gets a plain thin-sample note
        near_ = [f'{esc(last(F_))}: R{i_ + 1} sits right at the 15-minute floor; thin sample.' for F_, sd_, rec_, pts_ in S_ for i_, _ in pts_ if TF <= (emv(rec_, f"rounds.{i_}.mins") or 0) < TF + 1]
        note_ = f'<div class="trn">{" ".join(near_)}</div>' if near_ else ""
        return (f'<div class="trend" data-part="trend"><div class="mvl">Strike diff per minute, by round</div>'
                f'<svg viewBox="0 0 {W_} {H_}" role="img" aria-label="Strike differential per minute in rounds 1 to 3 for both fighters">{"".join(g_)}</svg>'
                f'<div class="rt-n">{legend_}<br>Above the dashed line = out-landing opponents in that round. Lines join rounds with 15+ UFC minutes; hollow grey dots have less (minutes shown). Fight counts are in the table below.</div>{note_}</div>')
    rounds_html = trend_svg() + rounds_html
    champ = ""
    if nrd == 5:
        champ = (E("r45.fights", "Fights to R4+", "int", None) + E("r45.landed_pm_13", "Output R1-3 /min", "n1", "hi") + E("r45.landed_pm_45", "Output R4-5 /min", "n1", "hi")
                 + E("r45.diff_pm_45", "Diff R4-5 /min", "s1", "hi"))
        if not champ: champ = '<div class="note">Neither fighter has been past round 3 in the UFC.</div>'
    BIG.update({"td15": 1.0, "td_acc": 0.15, "tdd": 0.15, "ctrl": 0.10, "ctrl_ag": 0.10, "sub15": 0.5, "adj_net_ctrl": 0.15})
    grap_html = (E("grap.td15", "Takedowns /15", "n2", "hi", "Takedowns landed per 15 minutes") + E("grap.td_acc", "TD accuracy", "pct0", "hi")
                 + E("grap.tdd", "TD defence", "pct0", "hi", "Share of opponents' takedown attempts stopped")
                 + E("grap.ctrl", "Time in control", "pct0", "hi", "Share of fight time spent controlling the opponent")
                 + E("grap.adj_net_ctrl", "Net control, opp-adjusted", "spp", "hi", "Control time minus time controlled, as a share of fight time, corrected for the strength of the opponents")
                 + E("grap.ctrl_ag", "Time controlled", "pct0", "lo", "Share of fight time spent being controlled")
                 + E("grap.sub15", "Sub attempts /15", "n2", "hi"))
    # Block 59f: Stats sub-toggles, in Sean's order. Without JS every group shows.
    def tot(rec):
        t_ = rec.get("target_diff") or {}
        return None if t_.get("head") is None else t_["head"] + t_["body"] + t_["leg"]
    ta_, tb_ = tot(ema), tot(emb)
    def totcell(v, F):
        return R(v, "s2", "em_sum", "Total diff " + F, fighter=F, paths=["target_diff.head", "target_diff.body", "target_diff.leg"]) if v is not None else '<span class="dim">n/a</span>'
    tot_row = ""
    if ta_ is not None or tb_ is not None:
        ea = eb = ""
        if ta_ is not None and tb_ is not None and ta_ != tb_:
            c_ = " adv big" if abs(ta_ - tb_) >= 2.0 else " adv"; ea, eb = (c_, "") if ta_ > tb_ else ("", c_)
        tot_row = f'<div class="row"><div class="a{ea}">{totcell(ta_, an)}</div><div class="k">Strike diff /min</div><div class="b{eb}">{totcell(tb_, bn)}</div></div>'
    tot_row += E("sos.adj_sd", "Opp-adjusted diff", "s2", "hi", "Strike differential corrected for the quality of opponents faced")
    groups = [("st", "Striking", "Striking", target_html + strip("Out-landed the opponent", "out_landed", _ol, "UFC fights where they landed more significant strikes") + '<div class="tape">' + tot_row + E("target_diff.head", "Head diff /min", "s2", "hi") + E("target_diff.body", "Body diff /min", "s2", "hi")
               + E("target_diff.leg", "Leg diff /min", "s2", "hi") + E("hdef", "Head defence", "pct0", "hi", "Share of opponents' head strike attempts that missed", floor=("ufc_fights", 5, "fights")) + '</div>'),
              ("gr", "Grappling", "Grappling", strip("Won the grappling", "grap_won", _gw, "Fights with real grappling (a minute of control or a takedown): more control time, or more takedowns when control is level") + '<div class="tape">' + grap_html + '</div>'),
              ("pw", "Power", "Power and durability", power_html),
              ("ca", "Cardio", "Cardio" + (" · 5 rounds" if nrd == 5 else ""), rounds_html + ('<div class="tape">' + champ + '</div>' if nrd == 5 else "")
               + '<div class="tape">' + L3("cardio.upcoming", "out", "Output kept R3", "pct0", "hi", "Round 3 significant strike attempts as a share of round 1, in fights that got through round 3") + '</div>'),
              ("en", "Endings", "How their fights end", outcome_html + '<div class="tape">' + E("pace.min", "Avg fight, min", "n1", None, floor=("pace.n", 3, "fights")) + E("pace.r1", "Finished in R1", "pct0", None, floor=("pace.n", 3, "fights")) + '</div>')]
    groups = [(k, t, h, grp(h, b)) for k, t, h, b in groups if b]
    stats_html = ('<div class="sgt" role="group" aria-label="Stat groups">' + "".join(f'<button type="button" data-g="{k}" aria-pressed="{"true" if i_ == 0 else "false"}">{t}</button>' for i_, (k, t, _, _) in enumerate(groups)) + '</div>'
                  + (f'<div class="tape"><div class="row hdr"><div class="a">{esc(last(an))}</div><div class="k vs">VS</div><div class="b">{esc(last(bn))}</div></div></div>' if not ARGS.no_vs_bar else "")
                  + "".join(f'<div class="sgw" data-g="{k}" data-part="{GPART[k]}">{h}{explain(XPL[k] + [("Note", GEN)])}</div>' for k, _, _, h in groups))
    # Block 59n (Kirk round 6): "Spot to watch" replaces the live guide, the flip flag and the striking-angle box. It shows
    # only when a tested angle fires (Round6_PREREG.md A). Backtest numbers come from data/embeds/spot_tests.json (copied from
    # the backtest's out/results.json, sha recorded there); the comeback numbers from labs.json cardio.wf.
    ST = json.loads((REPO / "data/embeds/spot_tests.json").read_text())
    def btn(test, key, fmt): return R(ST[test][key], fmt, "bt", f"Backtest {test} {key}", test=test, key=key)
    def btci(test): return R(ST[test]["ci"][0], "spp", "bt", f"Backtest {test} ci lo", test=test, key="ci", i=0) + " to " + R(ST[test]["ci"][1], "spp", "bt", f"Backtest {test} ci hi", test=test, key="ci", i=1)
    spots = []
    ok4 = ema.get("ufc_fights", 0) >= 4 and emb.get("ufc_fights", 0) >= 4
    if ta_ is not None and tb_ is not None and ok4 and abs(ta_ - tb_) >= ST["T1"]["cut"]:
        w_ = an if ta_ > tb_ else bn; o_ = bn if w_ == an else an
        spots.append(("T1", w_, f'<li data-spot="T1"><b>{esc(last(w_))}</b> has the striking edge: career strike diff {totcell(ta_ if w_ == an else tb_, w_)} vs {totcell(tb_ if w_ == an else ta_, o_)} per min. '
                     f'<span class="dim">Fighters with a gap this size won {btn("T1", "win", "pct1")} vs {btn("T1", "imp", "pct1")} priced in, {btn("T1", "roi", "spp")} ROI (95% CI {btci("T1")}). '
                     f'</span><span class="unconf">Never confirmed on new cards: all {btn("T1", "n", "int")} bets are from the 2022-26 data the angle was found on. This card is its first out-of-sample test. Never tested live.</span></li>'))
    r3a, r3b = emv(ema, "rounds.2.diff_pm"), emv(emb, "rounds.2.diff_pm")
    if (r3a is not None and r3b is not None and (emv(ema, "rounds.2.fights") or 0) >= 3 and (emv(emb, "rounds.2.fights") or 0) >= 3
            and ok4 and abs(r3a - r3b) >= ST["T17"]["cut"]):
        w_ = an if r3a > r3b else bn; o_ = bn if w_ == an else an
        spots.append(("T17", w_, f'<li data-spot="T17"><b>{esc(last(w_))}</b> wins round 3: R3 strike diff {R(r3a if w_ == an else r3b, "s1", "em", "Spot R3 " + w_, fighter=w_, path="rounds.2.diff_pm")} vs {R(r3b if w_ == an else r3a, "s1", "em", "Spot R3 " + o_, fighter=o_, path="rounds.2.diff_pm")} per min. '
                     f'<span class="dim">Past spots won {btn("T17", "win", "pct1")} vs {btn("T17", "imp", "pct1")} priced in, {btn("T17", "roi", "spp")} ROI on {btn("T17", "n", "int")} bets; 95% CI {btci("T17")} includes zero. Thin evidence, never tested live.</span></li>'))
    CW = LABS["cardio"]; up_ = {x_.get("s"): x_ for u_ in CW.get("upcoming", []) for x_ in (u_["a"], u_["b"])}
    ca_, cb_ = up_.get(f["a"].get("slug")), up_.get(f["b"].get("slug"))
    if ca_ and cb_ and ca_.get("sw") is not None and cb_.get("sw") is not None and ca_["n"] >= 3 and cb_["n"] >= 3 and abs(ca_["sw"] - cb_["sw"]) >= 3:
        late = ca_ if ca_["sw"] > cb_["sw"] else cb_; w_ = an if late is ca_ else bn
        spots.append(("CB", w_, f'<li data-spot="CB">If <b>{esc(last(w_))}</b> loses R1 on strikes, don\'t write off R3: fighters with the better late-round record who dropped R1 '
                     f'won R3 on strikes {R(CW["wf"]["lost1_won3"], "pct0", "labs_wf", "Spot comeback won3", key="lost1_won3")} of the time vs {R(CW["base_lost1_won3"], "pct0", "labs_wf", "Spot comeback base", key="base_lost1_won3")} for all R1 losers. '
                     f'<span class="dim">Based on {R(CW["wf"]["lost1_n"], "int", "labs_wf", "Spot comeback n", key="lost1_n")} fights. Tested on round results, not live prices.</span></li>'))
    spot_html = (f'<div class="stk spot" data-part="spot"><div class="stk-h"><span class="bullet"></span>Spot to watch</div><ul class="lvl">{"".join(x[2] for x in spots)}</ul>'
                 + ('<div class="see">See round trend: Stats › Cardio</div>' if 'data-part="trend"' in rounds_html else "") + '</div>') if spots else ""
    SPOTS[n] = [(k_, w_) for k_, w_, _ in spots]
    top = top.replace("@@ANGLES@@", "").replace("@@LIVE@@", spot_html)
    small = [F["name"] for F, g_ in [(FA, ga), (FB, gb)] if g_["n"] <= 3]
    secs.append(sec("ourstats", "Stats", "", stats_html))

    # ---------- recent form ----------
    def t5(F, Lf, sd):
        if not Lf: return f'<div class="col"><div class="cn">{esc(F["name"])}</div><div class="note">No prior UFC fights.</div></div>'
        def row(i, x):
            m_ = (x.get("m") or "").replace("Decision - ", "").replace("Unanimous", "UD").replace("Split", "SD").replace("Majority", "MD").replace("Submission", "SUB").replace("TKO - Doctor's Stoppage", "TKO (Dr)").replace("Could Not Continue", "CNC")
            fin = m_ if m_ in ("UD", "SD", "MD") else f'{m_} R{x["rd"]}'
            mc = (x.get("od") or {}).get("mc")
            opp = esc(x["o"])
            if x.get("es") and x.get("n") is not None:   # Block 59g: each past fight opens its full breakdown on the site
                opp = f'<a class="fl" href="{SITE}#/fight/{x["es"]}/{x["n"]}" target="_blank" rel="noopener">{opp}</a>'
            return f'<tr><td class="l dim">{dt.date.fromisoformat(x["d"]).strftime("%b %y")}</td><td class="l"><b class="r-{x["r"].lower()}">{x["r"]}</b> {opp}</td><td class="l">{esc(fin)}</td><td class="dim">{R(mc, "ml", "fight", "Close "+F["name"]+" "+x["o"], side=sd, i=i, key="od.mc") if mc is not None else "—"}</td></tr>'
        head = '<thead><tr><th class="l">When</th><th class="l">Result</th><th class="l">How</th><th>Close</th></tr></thead>'
        rows5 = "".join(row(i, x) for i, x in enumerate(Lf[:5]))
        more = ""
        if len(Lf) > 5:   # Block 59f: full UFC history behind a toggle
            more = (f'<details class="fmore"><summary>All {len(Lf)} UFC fights</summary><table class="t ft">{head}<tbody>'
                    + "".join(row(i, x) for i, x in enumerate(Lf) if i >= 5) + '</tbody></table></details>')
        return f'<div class="col"><div class="cn"><a class="fl" href="{SITE}#/fighter/{F["slug"]}" target="_blank" rel="noopener">{esc(F["name"])}</a><span class="cn-s">fighter page ↗</span></div><table class="t ft">{head}<tbody>{rows5}</tbody></table>{more}</div>'
    secs.append(sec("form", "Recent form", "last 5 UFC", f'<div class="ftw" data-part="form">{t5(FA, pa_, "a")}{t5(FB, pb_, "b")}</div>'))

    # ---------- notes: dropped (Block 59) ----------
    pass   # Block 59: notes and caveats section dropped

    nav = '<nav class="ffnav">' + "".join(f'<a href="#{i}">{t}</a>' for i, t in [("odds", "Odds"), ("move", "Movement"), ("props", "Props"), ("stats", "Stats"), ("form", "Form"), ("notes", "Notes")]) + "</nav>"
    # ---------- tabs (Block 59b): Projection first; tale of the tape collapsed at its top ----------
    # Block 59e: Movement folded into Projection (Sean: consolidate), as a compact block under the method stack
    tabdefs = [("proj", "Projection", top)] + [(k, t, PANELS[k][1]) for k, t in (("ourstats", "Stats"), ("form", "Form")) if k in PANELS]
    tabs_html = ('<div class="tabs" role="tablist" aria-label="Fight sections">' + "".join(
        f'<button type="button" role="tab" id="tb-{k}" aria-controls="tp-{k}" aria-selected="{"true" if i_ == 0 else "false"}" tabindex="{0 if i_ == 0 else -1}">{t}</button>' for i_, (k, t, _) in enumerate(tabdefs)) + '</div>'
        + "".join(f'<section class="tp" id="tp-{k}" role="tabpanel" aria-labelledby="tb-{k}" tabindex="0"><h2 class="tp-h">{t}</h2>{b}</section>' for k, t, b in tabdefs))
    page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light only">
<title>{esc(an)} vs {esc(bn)} · {esc(EVL["name"])} · Fight Form</title>
<style>
/* copied verbatim from ufc_333_fight_form.html (szerillo/ufc-projections) */
{SITE_CSS}
/* v4 embed layout */
*{{box-sizing:border-box}}html,body{{margin:0;background:#fff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;color:var(--text);font-size:13px;line-height:1.4}}
html{{scroll-behavior:smooth;scroll-padding-top:44px}}
.ff{{max-width:720px;margin:0 auto;background:var(--bg);border:1px solid var(--border);border-radius:8px;overflow:clip}}
.panel{{padding:12px 16px 2px}}.fp-odds{{margin-bottom:6px;line-height:1.6}}
.ffnav{{position:sticky;top:0;z-index:5;display:flex;gap:6px;overflow-x:auto;padding:8px 16px;background:rgba(255,255,255,.96);border-bottom:1px solid var(--border);-webkit-overflow-scrolling:touch;scrollbar-width:none}}
.ffnav::-webkit-scrollbar{{display:none}}
.ffnav a{{flex:0 0 auto;font:800 10.5px/1 inherit;font-family:inherit;text-transform:uppercase;letter-spacing:.6px;color:var(--text);text-decoration:none;background:var(--bg-muted);border:1px solid var(--border);border-radius:12px;padding:6px 10px}}
.ffnav a:first-child{{background:var(--header-bg);color:#fff;border-color:var(--header-bg)}}
section.top{{padding:12px 16px 2px}}.secs{{padding:2px 16px 12px}}
.fp-proj{{margin-bottom:4px}}
.pvm{{table-layout:fixed}}.pvm col.c0{{width:17%}}
.pvm thead tr.who th{{font-size:12px;letter-spacing:.3px;text-transform:none;color:var(--text);border-bottom:1px solid var(--border)}}
.pvm thead tr.who th.fav{{box-shadow:inset 0 -3px 0 var(--action-green)}}
.pvm thead tr.src th{{font-size:9.5px}}.pvm th.proj,.pvm td.proj{{background:var(--fav-b-soft)}}
.pvm th.rl{{text-align:left;font-size:12px;font-weight:800;color:var(--text);background:var(--bg-muted);padding-left:10px;text-transform:none;letter-spacing:0}}
.pvm th.rl small{{display:block;font-size:9px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.3px}}
.pvm td{{vertical-align:top}}.pvm .op{{font-size:10px;color:var(--text-muted);font-family:"SF Mono",Menlo,monospace;margin-top:1px}}.pvm .drv{{font-style:italic}}
.pvm tr[data-row="win"] td,.pvm tr[data-row="win"] th{{border-bottom:2px solid var(--border)}}.pvm tr.gtd td,.pvm tr.gtd th{{border-top:2px solid var(--border)}}
.fp-proj-table .dim,.dim{{color:var(--text-muted)}}
.cap{{font-size:11px;color:var(--text-muted);padding:6px 12px;border-top:1px solid var(--border);background:var(--bg-card)}}
.asof{{font-size:10.5px;color:var(--text-muted);margin:2px 0 6px}}
table.t{{border-collapse:collapse;width:100%;font-size:12.5px;font-variant-numeric:tabular-nums}}
table.t th{{background:var(--bg-muted);font-size:9.5px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:var(--text-muted);padding:6px;text-align:right;border-bottom:2px solid var(--border)}}
table.t td{{padding:6px;text-align:right;border-bottom:1px solid var(--border);vertical-align:top}}
.l{{text-align:left!important}}.b{{font-weight:800}}
.spark{{width:100%;height:auto;display:block}}
.kv{{display:flex;justify-content:space-between;gap:10px;font-size:12.5px;padding:5px 0;border-bottom:1px dotted var(--border)}}.kv span:first-child{{color:var(--text-muted)}}.kv span:last-child{{text-align:right}}
.note{{font-size:11.5px;color:var(--text-muted);font-style:italic;margin:6px 0}}
.tape .row{{display:grid;grid-template-columns:1fr 1.2fr 1fr;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums}}.tape .row>div{{padding:5px 6px}}
.tape .a{{text-align:right}}.tape .k{{text-align:center;color:var(--text-muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;align-self:center}}
.tape .hdr{{font-weight:800}}.tape .edge{{color:var(--pos-strong);font-weight:800}}
.ftw{{display:grid;gap:12px}}.cn{{font-weight:800;display:flex;justify-content:space-between;margin-bottom:3px}}
.chips i{{display:inline-block;width:20px;height:18px;line-height:18px;text-align:center;font:800 10px/18px inherit;font-family:inherit;color:#fff;margin-left:2px;font-style:normal;border-radius:3px}}
.chips .w{{background:var(--action-green-dark)}}.chips .l{{background:var(--neg)}}.chips .d,.chips .nc{{background:var(--neutral)}}
.r-w{{color:var(--action-green-dark)}}.r-l{{color:var(--neg)}}
.ft td,.ft th{{font-size:11.5px;padding:4px 5px}}
#notes p{{font-size:12.5px;margin:4px 0 8px}}#notes li{{font-size:12px;margin:3px 0;color:var(--text-muted)}}
.foot{{padding:10px 16px;background:var(--bg-muted);font-size:10.5px;color:var(--text-muted);border-top:1px solid var(--border)}}
/* Block 59: middle-ground layout (dark header kept; old embed's tape and dark section bars; edge chips; win bar) */
.legend{{font-size:10.5px;color:var(--text-muted);margin:6px 2px 10px}}
.pvm .edge{{display:inline-block;margin-top:3px;font:800 10.5px/1 "SF Mono",Menlo,monospace;padding:3px 5px;border-radius:4px}}
.pvm .edge.pos{{background:var(--pos-soft);color:var(--pos-strong)}}.pvm .edge.neg{{background:var(--neg-soft);color:var(--neg-strong)}}.pvm .edge.flat{{color:var(--text-muted)}}
.wb{{margin:2px 0 12px}}.wb-head{{display:flex;justify-content:space-between;font-weight:800;font-size:12px;margin-bottom:4px}}.wb-t{{font-size:9.5px;letter-spacing:.8px;text-transform:uppercase;color:var(--text-muted);align-self:center}}
.wb-row{{display:grid;grid-template-columns:54px 1fr;align-items:center;gap:8px;margin:4px 0}}.wb-l{{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;color:var(--text-muted)}}
.wb-bar{{display:flex;height:22px;border-radius:4px;overflow:hidden;gap:2px}}.wb-bar i{{display:flex;align-items:center;font-style:normal;min-width:44px}}
.wb-bar b{{font:800 11px/1 "SF Mono",Menlo,monospace;color:#fff;padding:0 7px}}.wb-bar .wbb{{justify-content:flex-end}}
.wb-bar.s .wa{{background:#0e1116}}.wb-bar.s .wbb{{background:#6b6b6b}}.wb-bar.m .wa{{background:var(--action-green-dark)}}.wb-bar.m .wbb{{background:#9bd8b4}}.wb-bar.m .wbb b{{color:#0a3d20}}
.tape .row.hdr{{background:var(--header-bg);color:#fff;font-size:13px}}.tape .row.hdr .vs{{background:var(--action-green);color:#fff;font-weight:900;letter-spacing:1px}}
.tape .edge{{background:var(--pos-soft)}}
.fp-thin{{font-size:10px;font-weight:800;line-height:1;letter-spacing:.6px;padding:4px 6px;border-radius:3px;background:#fff3cd;color:#7a5a00;margin-left:6px}}
/* Block 59b: tabs, old-style stacks, method bars, drift */
.tabs{{display:flex;gap:6px;padding:10px 16px 0;border-bottom:1px solid var(--border);overflow-x:auto;scrollbar-width:none}}.tabs::-webkit-scrollbar{{display:none}}
.tabs [role=tab]{{flex:0 0 auto;font:inherit;font-size:12px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;color:var(--text-muted);background:none;border:0;border-bottom:3px solid transparent;padding:8px 10px 9px;cursor:pointer}}
.tabs [role=tab][aria-selected=true]{{color:var(--text);border-bottom-color:var(--action-green)}}.tabs [role=tab]:focus-visible{{outline:2px solid var(--action-green-dark);outline-offset:2px}}
.tp{{padding:12px 16px 4px}}.tp:focus-visible{{outline:2px solid var(--action-green-dark)}}
.tp-h{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
details.taped{{margin:0 0 12px;border:1px solid var(--border);border-radius:6px;background:var(--bg-card)}}details.taped>summary{{display:flex;align-items:center;gap:8px;padding:10px 12px;font-weight:800;font-size:12px;letter-spacing:.6px;text-transform:uppercase;cursor:pointer;list-style:none}}
details.taped>summary::-webkit-details-marker{{display:none}}details.taped>summary .meta{{margin-left:auto;font-size:10px;font-weight:600;letter-spacing:.3px;text-transform:none;color:var(--text-muted)}}
details.taped .chev{{width:0;height:0;border-left:6px solid var(--action-green-dark);border-top:5px solid transparent;border-bottom:5px solid transparent;transition:transform .15s}}details.taped[open] .chev{{transform:rotate(90deg)}}
details.taped[open]>summary .meta{{visibility:hidden}}details.taped>.body{{padding:0 10px 10px}}
.stk{{margin:0 0 12px;border:1px solid var(--border);border-radius:6px;overflow:hidden}}.stk-h{{background:var(--header-bg);color:#fff;font-size:10.5px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;padding:8px 12px;display:flex;align-items:center;gap:8px}}
.stk-t{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}.stk-t th{{background:var(--bg-muted);font-size:9.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--text-muted);padding:7px 6px;text-align:center;border-bottom:1px solid var(--border)}}
.stk-t th.l,.stk-t td.l{{text-align:left}}.stk-t td{{padding:9px 6px;text-align:center;border-bottom:1px solid var(--border);vertical-align:middle}}.stk-t tr:last-child td{{border-bottom:0}}
.stk-t td.nm{{font-weight:800;font-size:12.5px;line-height:1.25}}.stk-t .odds{{font:700 12.5px/1.2 "SF Mono",Menlo,monospace}}.stk-t .pct{{font-size:11px;color:var(--text-muted)}}.stk-t td.model{{background:var(--fav-b-soft)}}
.stk-t .live{{font:600 10.5px/1.3 "SF Mono",Menlo,monospace;color:var(--text-muted)}}.stk-t .live:first-of-type{{margin-top:3px}}.stk-t .rl{{font:700 9px/1.2 inherit;font-family:inherit;letter-spacing:.4px;text-transform:uppercase;color:var(--text-muted);margin-top:2px}}.stk-t tr.mkr td{{padding-top:0;border-top:0}}.stk-t td.l.rl{{vertical-align:top;padding-top:4px;font-size:9px}}.unv{{display:block;font-size:9.5px;color:var(--text-muted);margin-top:2px}}
.stk-t td[data-k]{{border-left:1px solid var(--border)}}
.dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:1px}}.dot.fav{{background:#2a78d6}}.dot.dog{{background:#eb6834}}
.ech{{display:inline-block;margin-top:3px;font:800 11px/1 "SF Mono",Menlo,monospace;padding:3px 5px;border-radius:4px;color:var(--text-muted)}}.ech.pos{{background:var(--pos-soft);color:var(--pos-strong)}}.ech.neg{{background:var(--neg-soft);color:var(--neg-strong)}}
.wb-bar{{display:flex;height:24px;border-radius:4px;overflow:hidden;gap:2px}}.wb-bar i{{display:flex;align-items:center;font-style:normal;min-width:46px}}.wb-bar i.r{{justify-content:flex-end}}.wb-bar i.fav{{background:#2a78d6}}.wb-bar i.dog{{background:#eb6834}}
.mb{{padding:10px 12px}}.mb-row{{display:grid;grid-template-columns:96px 1fr 48px;align-items:center;gap:8px;margin:5px 0}}.mb-l{{font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.mb-track{{height:14px;background:var(--bg-muted);border-radius:3px;overflow:hidden}}.mb-track i{{display:block;height:100%;border-radius:3px}}.mb-track i.fav{{background:#2a78d6}}.mb-track i.dog{{background:#eb6834}}.mb-v{{font:700 12px/1 "SF Mono",Menlo,monospace;text-align:right}}
.drift{{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin:2px 0 6px}}.drift .dl{{font-size:10px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;color:var(--text-muted)}}.drift .dv{{font:800 20px/1 "SF Mono",Menlo,monospace}}.drift .dt{{font-size:12px;color:var(--text-muted)}}
@media (max-width:440px){{.tabs{{padding:8px 10px 0}}.tabs [role=tab]{{font-size:11px;padding:8px 7px 9px}}.tp{{padding:10px 10px 4px}}.stk-t td,.stk-t th{{padding:7px 3px}}.stk-t td.nm{{font-size:11.5px}}.stk-t .odds{{font-size:11.5px}}.stk-t .pct{{font-size:10px}}.stk-t .live{{font-size:9.5px}}.ech{{font-size:10px;padding:2px 4px}}.mb-row{{grid-template-columns:84px 1fr 44px}}}}
/* Block 59c: tape under the names, bars inside the stacks, stats groups */
.mt{{margin:8px 0 2px;border:1px solid var(--border);border-radius:6px;overflow:hidden;font-variant-numeric:tabular-nums}}
.mt-r{{display:grid;grid-template-columns:1fr 104px 1fr;border-bottom:1px solid var(--border)}}.mt-r:last-child{{border-bottom:0}}
.mt-r>div{{padding:5px 8px;font-size:12.5px;display:flex;align-items:center}}.mt-a{{justify-content:flex-end}}.mt-a{{text-align:right;font-weight:700}}.mt-b{{font-weight:700}}
.mt-k{{text-align:center;font-size:9.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--text-muted);background:var(--bg-muted);flex-direction:column;justify-content:center;gap:1px}}
.mt .adv{{background:var(--pos-soft);color:var(--pos-strong)}}.arw{{color:var(--action-green-dark);font-size:10px;letter-spacing:1px}}
.nb{{height:5px;background:var(--bg-muted);border-radius:3px;margin-top:5px;max-width:120px;overflow:hidden}}.nb i,.cb i{{display:block;height:100%;border-radius:3px}}
.nb i.fav,.cb i.fav{{background:#2a78d6}}.nb i.dog,.cb i.dog{{background:#eb6834}}
.cb{{height:5px;background:var(--bg-muted);border-radius:3px;margin:4px auto 2px;width:80%;overflow:hidden}}
.sg{{margin:0 0 12px}}.sg-h{{background:var(--header-bg);color:#fff;font-size:10.5px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;padding:7px 10px;border-radius:6px 6px 0 0}}
.sg .tape{{border:1px solid var(--border);border-top:0;border-radius:0 0 6px 6px}}
.tape .adv{{background:var(--pos-soft);color:var(--pos-strong);font-weight:800}}.tape .adv.big{{background:#9fe3bb;color:#063d1e}}
@media (max-width:440px){{.mt-r{{grid-template-columns:1fr 86px 1fr}}.mt-r>div{{padding:4px 6px;font-size:12px}}.mt-k{{font-size:8.5px}}}}
/* Block 59d: target bars, power and chin scales, rounds table */
.sg-b{{border:1px solid var(--border);border-top:0;border-radius:0 0 6px 6px;overflow:hidden}}.sg .sg-b .tape{{border:0;border-radius:0}}
.tb{{padding:8px 10px 6px;border-bottom:1px solid var(--border)}}.tb-key{{display:flex;gap:12px;font-size:10.5px;margin-bottom:6px;flex-wrap:wrap}}.tb-key i{{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:-1px}}
.tb-row{{display:grid;grid-template-columns:70px 1fr;align-items:center;gap:8px;margin:5px 0}}.tb-n{{font-weight:800;font-size:12px}}
.tb-bar{{display:flex;height:20px;border-radius:4px;overflow:hidden;gap:2px}}.tb-bar i{{display:flex;align-items:center;justify-content:center;font-style:normal;min-width:30px}}.tb-bar b{{font:800 10.5px/1 "SF Mono",Menlo,monospace;color:#fff}}
.tb-head{{background:#0e1116}}.tb-body{{background:#2a78d6}}.tb-leg{{background:#7fb3ea}}.tb-bar .tb-leg b{{color:#0e1116}}
.sc{{padding:9px 12px;border-bottom:1px solid var(--border)}}.sc:last-child{{border-bottom:0}}.sc-h{{font-size:10.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--text-muted);margin-bottom:8px}}
.sc-track{{position:relative;height:8px;background:linear-gradient(90deg,var(--bg-muted),#d9d4c8);border-radius:4px;margin:4px 6px 8px}}
.sc-dot{{position:absolute;top:50%;width:14px;height:14px;border-radius:50%;transform:translate(-50%,-50%);border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.2)}}.sc-dot.fav{{background:#2a78d6}}.sc-dot.dog{{background:#eb6834}}
.sc-avg{{position:absolute;top:-5px;width:2px;height:18px;background:#0e1116;transform:translateX(-1px)}}.sc-l{{font-size:12px;margin:2px 0}}.oc i b{{color:#fff}}.oc-wko{{background:#0a7a3a}}.oc-wsub{{background:#22a85a}}.oc-wdec{{background:#8fd6aa}}.oc-ldec{{background:#f2b8b0}}.oc-lsub{{background:#e0675a}}.oc-lko{{background:#b3261e}}.oc .oc-wdec b,.oc .oc-ldec b{{color:#0e1116}}.tb-bar.oc i{{min-width:0}}
.mvrow{{padding:8px 12px;border-top:1px solid var(--border);background:var(--bg-muted)}}.mvt{{font-size:12.5px}}.mvt b{{font-family:"SF Mono",Menlo,monospace}}.mvl{{font-size:10.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--text-muted)}}.mvt small{{display:block;font-size:10.5px;color:var(--text-muted);margin-top:2px}}.mspark{{width:100%;height:34px;display:block}}.mvs{{display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center;margin-top:4px;font:700 11px/1 "SF Mono",Menlo,monospace;color:var(--text-muted)}}.mvs .mve{{color:#0a8842}}.mvc{{font-size:10px;color:var(--text-muted);text-align:center}}
.sgt{{display:flex;gap:6px;overflow-x:auto;padding:2px 0 10px;scrollbar-width:none}}.sgt button{{flex:1 1 0;min-width:0;border:1px solid var(--border);background:#fff;border-radius:999px;padding:7px 2px;font:700 11px/1 inherit;letter-spacing:-.1px;white-space:nowrap;font-family:inherit;color:var(--text-muted);cursor:pointer}}.sgt button[aria-pressed=true]{{background:#0e1116;border-color:#0e1116;color:#fff}}.js .sgw{{display:none}}.js .sgw.on{{display:block}}
.fmore{{margin:4px 0 12px}}.fmore>summary{{cursor:pointer;font-size:12px;font-weight:700;color:var(--action-green-dark);padding:6px 2px;list-style:none}}.fmore>summary::-webkit-details-marker{{display:none}}.fmore>summary::before{{content:"▸ "}}.fmore[open]>summary::before{{content:"▾ "}}.fmore[open]>summary{{font-size:0}}.fmore[open]>summary::before{{font-size:12px}}.fmore[open]>summary::after{{content:"Hide older fights";font-size:12px}}
.fl{{color:inherit;text-decoration:none;border-bottom:1px dotted #9a9a9a}}a.fl{{display:inline-block;padding:5px 0 4px;line-height:15px}}.stamps a{{display:inline-block;padding:6px 4px;margin:-6px 0;color:inherit}}.fl:hover{{color:var(--action-green-dark);border-bottom-color:currentColor}}.cn-s{{font-size:10.5px;font-weight:600;color:var(--text-muted);margin-left:8px}}
.xpl{{margin:8px 0 4px;border:1px solid var(--border);border-radius:8px;background:#fff}}.xpl>summary{{cursor:pointer;padding:8px 12px;font-size:12px;font-weight:700;color:var(--text-muted);list-style:none}}.xpl>summary::-webkit-details-marker{{display:none}}.xpl>summary::before{{content:"ⓘ  "}}.xpl dl{{margin:0;padding:0 12px 10px}}.xpl dt{{font-size:11.5px;font-weight:800;margin-top:6px}}.xpl dd{{margin:1px 0 0;font-size:11.5px;line-height:1.4;color:var(--text-muted)}}
.ang{{padding:8px 12px;border-top:1px solid var(--border);background:#fffbea}}.ang ul{{margin:3px 0 0;padding-left:16px;font-size:12.5px}}.ang li{{margin:2px 0}}.ang b{{font-weight:800}}
.mvtr{{display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center;margin-top:6px;font:700 11px/1 "SF Mono",Menlo,monospace;color:var(--text-muted)}}.mvtr .mve{{color:#0a8842}}.mvbar{{position:relative;height:8px;border-radius:4px;background:linear-gradient(90deg,#e9e5dc,#d9d4c8)}}.mvbar i{{position:absolute;top:50%;transform:translate(-50%,-50%)}}.mvfrom{{width:10px;height:10px;border-radius:50%;background:#fff;border:2px solid #1a1a1a}}.mvto{{width:12px;height:12px;border-radius:50%;background:#0a8842;border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.2)}}.mvspan{{height:4px;background:#0a8842;opacity:.5;transform:translateY(-50%)!important}}.mvx>summary{{cursor:pointer;font-size:10.5px;color:var(--text-muted);margin-top:6px;list-style:none}}.mvx>summary::-webkit-details-marker{{display:none}}.mvx>summary::before{{content:"▸ "}}.mvx[open]>summary::before{{content:"▾ "}}
.ds{{padding:8px 10px;border-bottom:1px solid var(--border)}}.ds-h{{font-size:10.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--text-muted);margin-bottom:4px}}.ds-r{{display:grid;grid-template-columns:70px 1fr auto;gap:8px;align-items:center;margin:4px 0}}.ds-d{{display:flex;flex-wrap:wrap;gap:3px}}.ds-d i{{width:9px;height:9px;border-radius:50%;display:inline-block}}.ds-d i.on{{background:#0a8842}}.ds-d i.off{{background:#fff;border:1.5px solid #c9c3b6;box-sizing:border-box}}.ds-k{{font:800 12px/1 "SF Mono",Menlo,monospace;white-space:nowrap}}
.ddb{{all:unset;cursor:pointer;display:block;width:100%}}.ddb:focus-visible{{outline:2px solid #2a78d6;outline-offset:2px}}.dd{{margin:6px 8px 10px;border:1px solid var(--border);border-radius:8px;overflow:hidden}}.dd-h{{display:flex;justify-content:space-between;align-items:center;background:#0e1116;color:#fff;font-size:11px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;padding:6px 10px}}.ddx{{all:unset;cursor:pointer;font-size:16px;line-height:1;padding:0 4px}}.r-d{{color:var(--text-muted)}}
.spot .lvl{{margin:0;padding:8px 12px 10px 28px;font-size:12.5px}}.spot .lvl li{{margin:4px 0}}.spot b{{font-weight:800}}.spot .dim{{display:block;font-size:11px}}.trend{{padding:8px 4px 6px}}.trend .trn{{margin:4px 4px 0;font-size:11px;font-weight:700;color:#8a5a00}}.trend svg{{width:100%;height:auto;display:block}}.trend .mvl{{display:block;margin:0 0 2px 4px}}.spot .see{{padding:0 12px 10px 28px;font-size:11.5px;font-weight:700;color:var(--text-muted)}}.spot .unconf{{display:block;font-size:11px;font-weight:700;color:#8a5a00}}.flip{{padding:8px 12px;background:#eef5ff;border-bottom:1px solid var(--border);font-size:12.5px}}
.part .ff-subtitle,.part .ff-odds-status,.part .tabs,.part .tp{{display:none}}.part .partw{{margin-top:8px}}.part .xpl{{display:none}}
.sc-n{{padding:6px 12px 0;font-size:11px;color:var(--text-muted)}}
.stamps{{margin-top:4px;font-size:10px;color:var(--text-muted)}}
.ssm{{font-size:9.5px;font-weight:600;color:var(--text-muted);font-family:inherit}}
.mvasof{{display:block;font-size:10.5px;color:var(--text-muted);margin-top:2px}}
.pu{{font-size:10.5px;font-style:italic}}
.mvo{{background:#fff3c4;padding:0 3px;border-radius:3px}}
.rt .rw{{display:block;font:800 14px/1.2 "SF Mono",Menlo,monospace}}
.mvb{{margin:10px 0 0;border:1px solid var(--border);border-radius:8px;overflow:hidden}}.mvb-h{{background:#0e1116;color:#fff;font-size:11px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;padding:7px 12px}}
.sc-e{{display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin:-4px 6px 6px;text-transform:uppercase;letter-spacing:.4px}}.sc-t{{font-size:10px;font-weight:700;padding:1px 5px;border-radius:3px;background:var(--bg-muted);color:var(--text-muted)}}.sc-t.up{{background:#d9f5e4;color:#0a7a3a}}.sc-t.dn{{background:#fde3e0;color:#b3261e}}.sc-l b{{font-family:"SF Mono",Menlo,monospace}}
.rt{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}.rt th{{background:var(--bg-muted);font-size:9.5px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;color:var(--text-muted);padding:6px 4px;text-align:center}}
.rt td{{padding:7px 4px;text-align:center;border-top:1px solid var(--border);font:700 12px/1.2 "SF Mono",Menlo,monospace}}.rt td small{{display:block;white-space:nowrap;letter-spacing:-.3px;font:600 8.5px/1 inherit;font-family:inherit;color:var(--text-muted);margin-top:2px}}
.rt td.pos{{background:var(--pos-soft);color:var(--pos-strong)}}.rt td.neg{{background:var(--neg-soft);color:var(--neg-strong)}}.rt td.nm{{font-family:inherit;font-size:12px;text-align:left}}
.rt-n{{font-size:10px;color:var(--text-muted);padding:4px 10px 6px}}
/* Action Network badge stays visible at every width (the site widget hides it under 440 px; the embed keeps it) */
@media (max-width:600px){{.ff-brand{{position:static;display:flex;justify-content:center;margin-bottom:6px}}.ff-header{{padding:12px 12px 10px}}.ff-title{{font-size:17px}}}}
@media (max-width:440px){{.ff-header{{padding:9px 8px 8px}}.ff-brand{{display:flex!important;margin-bottom:5px}}.ff-title{{font-size:14px}}.ff-subtitle{{font-size:10px}}
.panel,section.top,.secs{{padding-left:10px;padding-right:10px}}.ffnav{{padding:7px 10px}}.fp-headline{{font-size:17px}}.fp-odds{{font-size:10.5px}}
.fp-proj-table th,.fp-proj-table td{{padding:5px 3px;font-size:11px}}.fp-proj-table .odds{{font-size:11.5px}}.fp-proj-table .pct{{font-size:10px}}.pvm .op{{font-size:9px}}
.pvm col.c0{{width:16%}}.pvm th.rl{{padding-left:6px;font-size:11px}}.pvm th.rl small{{font-size:7.5px}}.fp-proj-header{{font-size:9px;padding:6px 9px}}.cap{{font-size:10px;padding:5px 8px}}
details.collapsible>summary{{padding:8px 10px;font-size:10px}}details.collapsible>summary .meta{{display:none}}details.collapsible>.body{{padding:10px}}
table.t{{font-size:11.5px}}table.t td,table.t th{{padding:5px 3px}}.kv{{font-size:11.5px;flex-wrap:wrap}}.tape .row{{font-size:12px}}.tape .k{{font-size:9.5px}}}}
</style></head><body><div class="ff">
{head}</div>{tabs_html}
<div class="foot ff-foot"><div class="stamps">{stamps} · <a href="https://szerillo.github.io/ufc-projections/form/corrections.html" target="_blank" rel="noopener">Corrections</a></div></div></div>
<script>(function(){{var tabs=[].slice.call(document.querySelectorAll('[role=tab]')),ps=[].slice.call(document.querySelectorAll('[role=tabpanel]'));
function show(i,f){{tabs.forEach(function(t,j){{var on=j===i;t.setAttribute('aria-selected',on);t.tabIndex=on?0:-1;ps[j].hidden=!on;}});if(f)tabs[i].focus();}}
tabs.forEach(function(t,i){{t.addEventListener('click',function(){{show(i);}});t.addEventListener('keydown',function(e){{var k=e.key,n=tabs.length;
if(k==='ArrowRight'){{show((i+1)%n,1);e.preventDefault();}}if(k==='ArrowLeft'){{show((i+n-1)%n,1);e.preventDefault();}}if(k==='Home'){{show(0,1);e.preventDefault();}}if(k==='End'){{show(n-1,1);e.preventDefault();}}}});}});
document.documentElement.classList.add('js');show(0);
function sg(root,k){{[].forEach.call(root.querySelectorAll('.sgt button'),function(b){{b.setAttribute('aria-pressed',b.dataset.g===k);}});[].forEach.call(root.querySelectorAll('.sgw'),function(w){{w.classList.toggle('on',w.dataset.g===k);}});}}
document.addEventListener('click',function(e){{var b=e.target.closest('.sgt button');if(b){{sg(b.closest('.tp')||document,b.dataset.g);return;}}
var d=e.target.closest('.ddb');if(d){{var k=d.dataset.dd,root=d.closest('.sgw')||document,on=d.getAttribute('aria-expanded')!=='true';
[].forEach.call(root.querySelectorAll('.ddb'),function(x){{x.setAttribute('aria-expanded','false');}});[].forEach.call(root.querySelectorAll('.dd'),function(x){{x.hidden=true;}});
if(on){{d.setAttribute('aria-expanded','true');var p=root.querySelector('.dd[data-dd="'+k+'"]');if(p)p.hidden=false;}}return;}}
var x=e.target.closest('.ddx');if(x){{var pn=x.closest('.dd');pn.hidden=true;var r2=pn.closest('.sgw')||document,bt=r2.querySelector('.ddb[data-dd="'+pn.dataset.dd+'"]');if(bt)bt.setAttribute('aria-expanded','false');}}}});
var g0=document.querySelector('.sgt button');if(g0)sg(document,g0.dataset.g);
/* Block 59h: ?part=ml|move|live|length|method|tape|striking|grappling|power|cardio|endings|form shows one section alone, for screenshots and small embeds */
var part=(location.search.match(/[?&]part=([a-z]+)/)||[])[1];
if(part){{var t=document.querySelector('[data-part="'+part+'"]');if(t){{var pn=document.querySelector('.panel'),keep=[pn.querySelector('.fp-title-row'),pn.querySelector('.fp-headline')];
var c=t.cloneNode(true);if(c.classList.contains('sgw'))c.classList.add('on');if(part==='move'||part==='ml'){{}}
pn.innerHTML='';keep.forEach(function(k){{if(k)pn.appendChild(k);}});var w=document.createElement('div');w.className='partw';w.appendChild(c);pn.appendChild(w);
document.documentElement.classList.add('part');}}}}
}})();</script>
</body></html>'''
    (OUT / outname).write_text(page)
    reg = dict(fight=n, of=NB, site_pair=PAIR, pair=[an, bn], file=outname, event=EVF, proj_src=proj_src, proj_file=PUBF if pf else (EVF if EM else None),
               published_at=PUB.get("published_at") if pf else None, rows=R.rows, gaps=gaps)
    (OUT / outname.replace(".html", ".registry.json")).write_text(json.dumps(reg, indent=1, default=str))
    print(outname, len(page), "bytes,", len(R.rows), "numbers,", len(gaps), "gaps")

def card():
    """Full numbered card (bout order) cross-checked against BettingPros scheduled order and the site ids."""
    bp_by = sorted(BPO["fights"], key=lambda x: x["scheduled_utc"])
    out = []
    for i, s in enumerate(ORDER):
        a, b = s.split("|"); n = NB - i
        # one matching fighter is enough here: BettingPros spells "Charlie Radke", "Christopher Duncan"
        hit = lambda x, y: any(same(p, q) for p in (x, y) for q in (a, b))
        bpi = next(j + 1 for j, x in enumerate(bp_by) if hit(x["fighter_a"]["name"], x["fighter_b"]["name"]))
        sn = next((x["n"] for x in EVL["fights"] if hit(x["a"]["name"], x["b"]["name"])), None)
        seg = OVR["segments"]; tag = "Main event" if i == 0 else "Main card" if i < seg["main"] else "Prelims" if i < seg["main"] + seg["prelims"] else "Early prelims"
        out.append(dict(fight=n, bout=f"{a} vs {b}", segment=tag, bp_sched_rank=bpi, site_n=sn))
        assert sn == n, f"{EVF}: n={sn} for {a} vs {b}, bout order says {n}; run scripts/card_overrides.py on the event file"
        assert bpi == n, (s, bpi, n)
    json.dump(dict(slug=SLUG, event=EVF, rule="fight number = bout order on the card; 1 = opener, %d = main event" % NB, cancelled=OVR.get("cancel", []),
                   proj_file=PUBF, published_at=(PUB or {}).get("published_at"), card=out), open(OUT / "card.json", "w"), indent=1)
    return out
    for r in out: print(f'  {r["fight"]:>2}  {r["segment"]:<13} {r["bout"]:<36} BP#{r["bp_sched_rank"]:<3} site n={r["site_n"]}')

def write_roster(rows):
    """embed.html: replace this card's FIGHTS_BY_CARD block (between the v4-roster markers) with the numbered card."""
    p = REPO / "embed.html"; s = p.read_text()
    beg = f"// <v4-roster {SLUG}>"; end = "// </v4-roster>"
    i, j = s.index(beg), s.index(end, s.index(beg))
    head = s[i:s.index("\n", i) + 1]
    ent = []
    for r in rows:
        f = next(x for x in EVL["fights"] if pair(x["a"]["name"], x["b"]["name"], *r["bout"].split(" vs ")))
        meta = f'{r["segment"].title()} · {f["wc"]} · {f.get("sched") or 3}R'
        ent.append(f'    {{ n: {r["fight"]}, matchup: {json.dumps(last(f["a"]["name"]) + " vs " + last(f["b"]["name"]), ensure_ascii=False)}, meta: {json.dumps(meta, ensure_ascii=False)}' + (', belt: "Title"' if f.get("title") else "") + " },")
    body = f"  {SLUG}: [\n" + "\n".join(ent) + "\n  ],\n  "
    p.write_text(s[:i] + head + body + s[j:])

def fname(n, a, b):
    return f"fight_{n:02d}.html"

if __name__ == "__main__":
    rows = card()
    write_roster(rows)
    for i, sp in enumerate(ORDER):
        a, b = sp.split("|")
        build((a, b), fname(NB - i, a, b))
    print(f"{len(rows)} embeds in {OUT}; Sean's numbers from {PUBF or 'the event file (no Publish to site export)'}")
