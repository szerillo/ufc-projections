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
       "pts": lambda x: f"{abs(x)*100:.1f}"}

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
    dr = next((s for s in mv if s["label"] == "Draw"), None)
    if dr and dr["books"]["consensus"]["cost"] < 1000: why.append(f'draw priced {mls(dr["books"]["consensus"]["cost"])}')
    if sum(1 for s in mv if s.get("opening_cost") == 100) >= 2: why.append("opening prices of exactly +100")
    fd = {s["label"] for s in bf["markets"].get("fight_distance", [])}
    d_ok = {"Yes", "No"} <= fd
    if not d_ok: why.append("distance market has only " + "/".join(sorted(fd)))
    return not any("draw" in w or "opening" in w or "method market" in w for w in why), d_ok, why

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
        return json.load(open(p_)) if p_ and p_.exists() else {"name": X["name"], "bio": {}, "fights": []}
    FA, FB = ffile(A_), ffile(B_)
    pa_ = [x for x in FA["fights"] if x["d"] < EVL["date"]]; pb_ = [x for x in FB["fights"] if x["d"] < EVL["date"]]
    ga, gb = agg(pa_), agg(pb_)
    o, fm = f.get("odds"), f.get("form")
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
    status = f'<div class="ff-odds-status"><span class="dot"></span>BettingPros snapshot {esc(bp_t)}</div>'
    def meta(F, g, side, key):
        fig = fm[key] if fm else None
        return (f'{esc(last(F["name"]))} <span class="num">{R(g["rec"], "str", "record", F["name"]+" UFC record", side=side)}</span> · Elo <span class="num">{R(f[side]["elo"], "int", "ev", F["name"]+" Elo", ev=EVF, pair=PAIR, path=f"{side}.elo")}</span>'
                f' · Fig <span class="num">{R(fig, "n1", "ev", F["name"]+" Form Figure", ev=EVF, pair=PAIR, path=f"form.{key}") if fig is not None else "—"}</span>')
    head = f'''<div class="ff-header"><div class="ff-brand" aria-label="Action Network"><span class="ff-brand-text">ACTION</span><span class="ff-brand-check">{CHECK_SVG}</span></div>
<div class="ff-title">{esc(EVL["name"])} · Fight Form</div><div class="ff-subtitle">{day} · {esc(EVL["location"])}</div>
<div class="ff-byline-header">By <a href="https://twitter.com/SeanZerillo" target="_blank" rel="noopener">@SeanZerillo</a></div>{status}</div>
<div class="panel"><div class="fp-title-row"><span class="fp-fight-num">FIGHT {n}</span><span class="fp-card-tag">{card_tag}</span>{'<span class="fp-title-belt">★ TITLE</span>' if f.get("title") else ""}<span class="fp-weight">{esc(f["wc"])} · {sched} RDS</span></div>
<div class="fp-headline">{esc(an)} <span class="vs">vs</span> {esc(bn)}</div>
<div class="fp-odds">{meta(FA, ga, "a", "ra")}<br>{meta(FB, gb, "b", "rb")}</div>'''

    # ---------- TOP: one table, Sean's projection vs market ----------
    def mov_nv(F, k):
        """no-vig share of 'F by k' inside BettingPros method_of_victory (6 fighter/method selections + draw)."""
        labs = [f"{bp_name(bf, x)} {MOVL[kk]}" for x in (an, bn) for kk in ("dec", "ko", "sub")] + ["Draw"]
        tot = sum(imp(bp_sel(bf, "method_of_victory", lb)["books"]["consensus"]["cost"]) for lb in labs)
        return imp(bp_sel(bf, "method_of_victory", f"{bp_name(bf, F)} {MOVL[k]}")["books"]["consensus"]["cost"]) / tot
    def sean(sd, k):
        F = nm_of[sd]
        if not pf and not EM: return '<td class="proj dim">—</td>'
        if not pf:
            ks = ("ko", "sub") if k == "itd" else (k,)
            if any(EM[sd].get(x) is None for x in ks): return '<td class="proj dim">—</td>'
            v = sum(EM[sd][x] for x in ks) / 100; rule = "evp_sum"; a_ = dict(ev=EVF, pair=PAIR, paths=[f"model.{sd}.{x}" for x in ks])
            return f'<td class="proj"><span class="odds">{R(v, "mlp", rule, f"Sean {k} ML {F} (build)", **a_)}</span><div class="pct">{R(v, "pct1", rule, f"Sean {k} % {F} (build)", **a_)}</div></td>'
        if k == "win":
            p = pwin(sd); return f'<td class="proj"><span class="odds">{R(p, "mlp", "pub_win", "Sean ML "+F, side=sd)}</span><div class="pct">{R(p, "pct1", "pub_win", "Sean win % "+F, side=sd)}</div></td>'
        m = pf["method"][role(sd)]; v = pwin(sd) * (m["ko"] + m["sub"] if k == "itd" else m[k])
        return f'<td class="proj"><span class="odds">{R(v, "mlp", "pub_meth", f"Sean {k} ML {F}", side=sd, k=k)}</span><div class="pct">{R(v, "pct1", "pub_meth", f"Sean {k} % {F}", side=sd, k=k)}</div></td>'
    def mkt(sd, k):
        F = nm_of[sd]
        if not bf: return '<td class="dim">—</td>'
        if k == "win":
            s = bp_sel(bf, "moneyline", bp_name(bf, F)); s2 = bp_sel(bf, "moneyline", bp_name(bf, nm_of[oth[sd]]))
            c = s["books"]["consensus"]["cost"]; nv = imp(c) / (imp(c) + imp(s2["books"]["consensus"]["cost"]))
            lab = bp_name(bf, F)
            return (f'<td><span class="odds">{R(c, "ml", "bp", "BP ML now "+F, market="moneyline", label=lab, field="cost")}</span><div class="pct">{R(nv, "pct1", "bp_nv", "BP ML no-vig "+F, market="moneyline", label=lab, other=bp_name(bf, nm_of[oth[sd]]))}</div>'
                    f'<div class="op">o {R(s["opening_cost"], "ml", "bp", "BP ML open "+F, market="moneyline", label=lab, field="opening_cost")}</div></td>')
        if not m_ok: return '<td class="dim">n/a</td>'
        if k == "itd":
            v = mov_nv(F, "ko") + mov_nv(F, "sub")
            return f'<td><span class="odds drv">{R(v, "mlp", "bp_mitd", f"BP ITD fair ML {F}", fighter=F)}</span><div class="pct">{R(v, "pct1", "bp_mitd", f"BP ITD no-vig {F}", fighter=F)}</div><div class="op">KO+SUB</div></td>'
        lab = f"{bp_name(bf, F)} {MOVL[k]}"; s = bp_sel(bf, "method_of_victory", lab)
        return (f'<td><span class="odds">{R(s["books"]["consensus"]["cost"], "ml", "bp", f"BP {k} now {F}", market="method_of_victory", label=lab, field="cost")}</span><div class="pct">{R(mov_nv(F, k), "pct1", "bp_mnv", f"BP {k} no-vig {F}", fighter=F, k=k)}</div>'
                f'<div class="op">o {R(s["opening_cost"], "ml", "bp", f"BP {k} open {F}", market="method_of_victory", label=lab, field="opening_cost")}</div></td>')
    LABS = [("win", "Win", "ML"), ("dec", "DEC", "decision"), ("ko", "KO", "KO/TKO"), ("sub", "SUB", "submission"), ("itd", "ITD", "KO + SUB")]
    rows = "".join(f'<tr data-row="{k}"><th class="rl">{lab}<small>{sub}</small></th>{sean("a", k)}{mkt("a", k)}{sean("b", k)}{mkt("b", k)}</tr>' for k, lab, sub in LABS)
    # GTD is fight-level: Sean's number spans both Sean columns, market spans both market columns
    if pf:
        g = pf["gtd"]; gs = f'<td class="proj" colspan="2"><span class="odds">{R(g, "mlp", "pub", "Sean GTD fair ML", key="gtd")}</span><div class="pct">{R(g, "pct1", "pub", "Sean GTD %", key="gtd")}</div></td>'
    elif EM and EM.get("gtd") is not None:
        g = EM["gtd"] / 100; a_ = dict(ev=EVF, pair=PAIR, paths=["model.gtd"])
        gs = f'<td class="proj" colspan="2"><span class="odds">{R(g, "mlp", "evp_sum", "Sean GTD fair ML (build)", **a_)}</span><div class="pct">{R(g, "pct1", "evp_sum", "Sean GTD % (build)", **a_)}</div></td>'
    else:
        gs = '<td class="proj dim" colspan="2">—</td>'
    if bf and d_ok:
        y, no = bp_sel(bf, "fight_distance", "Yes"), bp_sel(bf, "fight_distance", "No")
        nv = imp(y["books"]["consensus"]["cost"]) / (imp(y["books"]["consensus"]["cost"]) + imp(no["books"]["consensus"]["cost"]))
        gm = (f'<td colspan="2"><span class="odds">Y {R(y["books"]["consensus"]["cost"], "ml", "bp", "BP GTD yes now", market="fight_distance", label="Yes", field="cost")} / N {R(no["books"]["consensus"]["cost"], "ml", "bp", "BP GTD no now", market="fight_distance", label="No", field="cost")}</span>'
              f'<div class="pct">{R(nv, "pct1", "bp_nv", "BP GTD no-vig", market="fight_distance", label="Yes", other="No")}</div><div class="op">o Y {R(y["opening_cost"], "ml", "bp", "BP GTD yes open", market="fight_distance", label="Yes", field="opening_cost")}</div></td>')
    else:
        gm = '<td class="dim" colspan="2">n/a</td>'
    rows += f'<tr data-row="gtd" class="gtd"><th class="rl">GTD<small>goes distance</small></th>{gs}{gm}</tr>'
    fav_sd = "a" if (pwin("a") or .5) >= .5 else "b"
    tbl = f'''<div class="fp-proj-header"><span class="bullet"></span>Sean's projection vs market</div>
<table class="fp-proj-table pvm" data-proj-src="{proj_src or "none"}"><colgroup><col class="c0"><col><col><col><col></colgroup><thead>
<tr class="who"><th></th><th colspan="2" class="{"fav" if fav_sd == "a" else "dog"}">{esc(last(an))}</th><th colspan="2" class="{"fav" if fav_sd == "b" else "dog"}">{esc(last(bn))}</th></tr>
<tr class="src"><th></th><th class="proj">Sean</th><th>Market</th><th class="proj">Sean</th><th>Market</th></tr></thead><tbody>{rows}</tbody></table>
<div class="cap"><b>Sean</b> = fair price and % from Sean's projection sheet (win % × the sheet's DEC / KO / SUB split; ITD = KO + SUB){SRC_NOTE[proj_src]}. <b>Market</b> = BettingPros consensus price, de-vigged % below, o = open.{" Method % de-vigged across the full method market; ITD = no-vig KO + SUB." if bf and m_ok else ""}{(" Method / GTD market n/a where BettingPros prices for this bout are missing or look broken (" + esc("; ".join(bad_why)) + ").") if bf and bad_why else ""}</div>'''
    if bf and bad_why: gaps.append(f"Fight {n}: BettingPros method/distance markets suspect ({'; '.join(bad_why)}); market cells shown as n/a.")
    if not pf: gaps.append(f"Fight {n}: no row in the Publish to site export; Sean cells " + ("from the event file's model block (" + proj_src + ")." if EM else "empty."))
    asof = f'<div class="asof">{"Sheet: " + esc(PUB["source"]) + ", published " + esc(PUB["published_at"][:16].replace("T"," ")) + " UTC. " if pf else ("Sheet: site build pull (no Publish to site export). " if EM else "")}{"Market: BettingPros consensus, " + esc(bp_t) + "." if bf else ""}</div>'
    top = f'<section id="odds" class="top"><div class="fp-proj">{tbl}</div>{asof}</section>'

    def sec(id_, title, meta_, body, open_=False):
        return f'<details class="collapsible" id="{id_}"{" open" if open_ else ""}><summary><span class="bullet"></span>{title}<span class="meta">{meta_}</span></summary><div class="body">{body}</div></details>'
    secs = []

    # ---------- line movement (directly under the table) ----------
    body = ""
    if o:
        mv = o["close"]["p"] - o["open"]["p"]
        def best(sd):
            b = None
            for k, x in o["books"].items():
                if k not in US_BOOKS: continue   # Block 57: only US-regulated books are named (same list as form/app.js)
                m = x["ma" if sd == "a" else "mb"]
                if m is not None and (b is None or dec_odds(m) > dec_odds(b[0])): b = (m, k)
            return b
        ba, bb = best("a"), best("b")
        body += sparkline(o["series"]) + f'''<div class="kv"><span>Odds API open {o["open"]["t"][:10]}</span><span>{esc(last(an))} {R(o["open"]["ma"], "ml", "ev", "OA open ML a", ev=EVF, pair=PAIR, path="odds.open.ma")} · {esc(last(bn))} {R(o["open"]["mb"], "ml", "ev", "OA open ML b", ev=EVF, pair=PAIR, path="odds.open.mb")} · {R(o["open"]["p"], "pct1", "ev", "OA open p", ev=EVF, pair=PAIR, path="odds.open.p")}</span></div>
<div class="kv"><span>Odds API latest {o["close"]["t"][:10]}</span><span>{esc(last(an))} {R(o["close"]["ma"], "ml", "ev", "OA close ML a", ev=EVF, pair=PAIR, path="odds.close.ma")} · {esc(last(bn))} {R(o["close"]["mb"], "ml", "ev", "OA close ML b", ev=EVF, pair=PAIR, path="odds.close.mb")} · {R(o["close"]["p"], "pct1", "ev", "OA close p", ev=EVF, pair=PAIR, path="odds.close.p")}</span></div>
<div class="kv"><span>Drift</span><span>{R(mv, "pts", "oa_drift", "OA drift pts", ev=EVF, pair=PAIR)} pts toward {esc(an if mv >= 0 else bn)}</span></div>
<div class="kv"><span>Best price (Odds API latest)</span><span>{esc(last(an))} {R(ba[0], "ml", "oa_best", "OA best a", ev=EVF, pair=PAIR, side="a")} {esc(BOOKS.get(ba[1], ba[1]))} · {esc(last(bn))} {R(bb[0], "ml", "oa_best", "OA best b", ev=EVF, pair=PAIR, side="b")} {esc(BOOKS.get(bb[1], bb[1]))}</span></div>'''
    else:
        gaps.append(f"Fight {n}: no Odds API line history (no odds block in the event file).")
    if bf:
        la, lb = bp_name(bf, an), bp_name(bf, bn); sa, sb = bp_sel(bf, "moneyline", la), bp_sel(bf, "moneyline", lb)
        body += f'<div class="kv"><span>BettingPros open → now</span><span>{esc(last(an))} {R(sa["opening_cost"], "ml", "bp", "BP open a (move)", market="moneyline", label=la, field="opening_cost")} → {R(sa["books"]["consensus"]["cost"], "ml", "bp", "BP now a (move)", market="moneyline", label=la, field="cost")} · {esc(last(bn))} {R(sb["opening_cost"], "ml", "bp", "BP open b (move)", market="moneyline", label=lb, field="opening_cost")} → {R(sb["books"]["consensus"]["cost"], "ml", "bp", "BP now b (move)", market="moneyline", label=lb, field="cost")}</span></div>'
    if o:
        body += f'<div class="note">Chart: Odds API no-vig consensus for {esc(an)}, {R(len(o["series"]), "int", "oa_len", "Chart points", ev=EVF, pair=PAIR)} points from {R(o["n"], "int", "ev", "Snapshots", ev=EVF, pair=PAIR, path="odds.n")} snapshots, last {o["close"]["t"][:16].replace("T"," ")} UTC. BettingPros row is newer ({esc(bp_t)}).</div>'
    else:
        body += '<div class="note">No Odds API history for this bout, so no chart; BettingPros open → now only.</div>'
    secs.append(sec("move", "Line movement", "open → now", body, True))

    # ---------- props detail (BettingPros fight-level markets) ----------
    body = ""
    if bf:
        rows_ = []
        for mkt_, lab_ in [("fight_ending", "KO/TKO/DQ"), ("fight_ending", "Submission"), ("fight_ending", "Points"), ("fight_distance", "Yes"), ("fight_distance", "No"), ("total_rounds", "Over"), ("total_rounds", "Under")]:
            s = bp_sel(bf, mkt_, lab_)
            if not s: continue
            c = s["books"]["consensus"]
            lnh = (" " + R(c["line"], "str", "bp", f"BP line {mkt_} {lab_}", market=mkt_, label=lab_, field="line")) if mkt_ == "total_rounds" else ""
            nice = {"fight_ending": "Fight ends by ", "fight_distance": "Goes the distance: ", "total_rounds": "Rounds "}[mkt_] + lab_
            rows_.append(f'<tr><td class="l">{esc(nice)}{lnh}</td><td>{R(s["opening_cost"], "ml", "bp", f"BP open {mkt_} {lab_}", market=mkt_, label=lab_, field="opening_cost")}</td><td class="b">{R(c["cost"], "ml", "bp", f"BP now {mkt_} {lab_}", market=mkt_, label=lab_, field="cost")}</td><td class="dim">{R(imp(c["cost"]), "pct0", "bp_imp", f"BP implied {mkt_} {lab_}", market=mkt_, label=lab_)}</td></tr>')
        odd = [s["label"] for s in bf["markets"].get("method_of_victory", []) if s["selection"] == ""]
        body += f'<table class="t"><thead><tr><th class="l">BettingPros market</th><th>Open</th><th>Now</th><th>Implied</th></tr></thead><tbody>{"".join(rows_)}</tbody></table><div class="note">Consensus prices with vig; implied = raw 1/decimal.{" These prices look broken for this bout (" + esc("; ".join(bad_why)) + ")." if bad_why else ""}{" Not shown: method selections with a blank selection id (" + esc(", ".join(odd)) + ")." if odd else ""}</div>'
        if odd: gaps.append(f"Fight {n}: BettingPros method_of_victory has unlabeled selections {odd}; not displayed.")
    secs.append(sec("props", "Props detail", "fight-level markets", body or '<div class="note">No prop markets on file.</div>'))

    # ---------- fighter stats ----------
    agA = (dt.date.fromisoformat(EVL["date"]) - dt.date.fromisoformat(FA["bio"]["dob"])).days / 365.25 if FA["bio"].get("dob") else None
    agB = (dt.date.fromisoformat(EVL["date"]) - dt.date.fromisoformat(FB["bio"]["dob"])).days / 365.25 if FB["bio"].get("dob") else None
    def trow(lab, va, vb, fmt, rule, better=None, **args):
        ea = eb = ""
        if better and va is not None and vb is not None and va != vb and not isinstance(va, str):
            aw = va > vb if better == "hi" else va < vb; ea, eb = (" edge", "") if aw else ("", " edge")
        ca = R(va, fmt, rule, lab + " a", side="a", **args) if va not in (None, "") else "—"
        cb = R(vb, fmt, rule, lab + " b", side="b", **args) if vb not in (None, "") else "—"
        return f'<div class="row"><div class="a{ea}">{ca}</div><div class="k">{lab}</div><div class="b{eb}">{cb}</div></div>'
    ra_ = int(FA["bio"]["reach"]) if FA["bio"].get("reach") else None; rb_ = int(FB["bio"]["reach"]) if FB["bio"].get("reach") else None
    tape = "".join([
        trow("Age", agA, agB, "n1", "age", "lo"), trow("Reach", ra_, rb_, "in", "bio_reach", "hi"), trow("Height", FA["bio"].get("ht"), FB["bio"].get("ht"), "str", "bio", None, key="ht"),
        trow("Stance", FA["bio"].get("stance"), FB["bio"].get("stance"), "str", "bio", None, key="stance"), trow("UFC fights", ga["n"], gb["n"], "int", "nfights"),
        trow("SLpM", ga["slpm"], gb["slpm"], "n2", "stat", "hi", key="slpm"), trow("SApM", ga["sapm"], gb["sapm"], "n2", "stat", "lo", key="sapm"),
        trow("Strike diff /min", ga["diff"], gb["diff"], "s2", "stat", "hi", key="diff"), trow("Strike accuracy", ga["acc"], gb["acc"], "pct0", "stat", "hi", key="acc"),
        trow("Strike defence", ga["dfn"], gb["dfn"], "pct0", "stat", "hi", key="dfn"), trow("Takedowns /15", ga["td15"], gb["td15"], "n2", "stat", "hi", key="td15"),
        trow("TD defence", ga["tdd"], gb["tdd"], "pct0", "stat", "hi", key="tdd"), trow("Control time", ga["ctrlp"], gb["ctrlp"], "pct0", "stat", "hi", key="ctrlp")])
    small = [F["name"] for F, g_ in [(FA, ga), (FB, gb)] if g_["n"] <= 3]
    secs.append(sec("stats", "Fighter stats", "UFC only, before this fight", f'<div class="tape"><div class="row hdr"><div class="a">{esc(last(an))}</div><div class="k"></div><div class="b">{esc(last(bn))}</div></div>{tape}</div><div class="note">Green = better side. UFCStats rows before {EVL["date"]}.{(" THIN SAMPLE: " + esc(" and ".join(small)) + " (3 or fewer UFC fights).") if small else ""}</div>'))

    # ---------- recent form ----------
    def t5(F, Lf, sd):
        if not Lf: return f'<div class="col"><div class="cn">{esc(F["name"])}</div><div class="note">No prior UFC fights.</div></div>'
        chips = "".join(f'<i class="r {x["r"].lower()}">{x["r"] if x["r"] in "WLD" else "NC"}</i>' for x in Lf[:5])
        rw = []
        for i, x in enumerate(Lf[:5]):
            m_ = (x.get("m") or "").replace("Decision - ", "").replace("Unanimous", "UD").replace("Split", "SD").replace("Majority", "MD").replace("Submission", "SUB").replace("TKO - Doctor's Stoppage", "TKO (Dr)").replace("Could Not Continue", "CNC")
            fin = m_ if m_ in ("UD", "SD", "MD") else f'{m_} R{x["rd"]}'
            mc = (x.get("od") or {}).get("mc")
            rw.append(f'<tr><td class="l dim">{dt.date.fromisoformat(x["d"]).strftime("%b %y")}</td><td class="l"><b class="r-{x["r"].lower()}">{x["r"]}</b> {esc(x["o"])}</td><td class="l">{esc(fin)}</td><td>{R(x["fg"], "r0", "fight", "Fig "+F["name"]+" "+x["o"], side=sd, i=i, key="fg") if x.get("fg") is not None else "–"}</td><td class="dim">{R(mc, "ml", "fight", "Close "+F["name"]+" "+x["o"], side=sd, i=i, key="od.mc") if mc is not None else "—"}</td></tr>')
        return f'<div class="col"><div class="cn">{esc(F["name"])} <span class="chips">{chips}</span></div><table class="t ft"><thead><tr><th class="l">When</th><th class="l">Result</th><th class="l">How</th><th>Fig</th><th>Close</th></tr></thead><tbody>{"".join(rw)}</tbody></table></div>'
    secs.append(sec("form", "Recent form", "last 5 UFC", f'<div class="ftw">{t5(FA, pa_, "a")}{t5(FB, pb_, "b")}</div>'))

    # ---------- notes ----------
    ps = []
    if pf and bf:
        la, lb = bp_name(bf, an), bp_name(bf, bn)
        s, s2 = bp_sel(bf, "moneyline", la), bp_sel(bf, "moneyline", lb)
        nv = imp(s["books"]["consensus"]["cost"]) / (imp(s["books"]["consensus"]["cost"]) + imp(s2["books"]["consensus"]["cost"]))
        ps.append(f'Sean\'s sheet has {esc(an)} at {R(pwin("a"), "pct1", "pub_win", "Sheet % (note)", side="a")}, {R(pwin("a") - nv, "pts", "gap_pub_bp", "Sheet vs BP gap", side="a", market="moneyline", label=la, other=lb)} pts {"above" if pwin("a") > nv else "below"} the de-vigged market. Sheet flag: “{esc(pf["sheet"]["flag"])}”, rec “{esc(pf["sheet"]["rec"])}”.')
    cav = ["Timestamps differ by source: sheet export, BettingPros file and Odds API were pulled at different times (shown on each block).",
           "Markov sim, Form Line and other model numbers are not shown in embeds (THIN SAMPLE runs, e.g. this card's Markov favourites, are artifacts)."]
    if bf: cav.append("BettingPros <code>no_vig_pct</code> fields do not sum to 100%, so the card de-vigs consensus prices itself.")
    if small: cav.append("THIN SAMPLE: " + esc(", ".join(small)) + " (3 or fewer UFC fights before this card).")
    secs.append(sec("notes", "Notes &amp; data caveats", "read before using", "".join(f"<p>{x}</p>" for x in ps) + "<ul>" + "".join(f"<li>{x}</li>" for x in cav) + "</ul>"))

    nav = '<nav class="ffnav">' + "".join(f'<a href="#{i}">{t}</a>' for i, t in [("odds", "Odds"), ("move", "Movement"), ("props", "Props"), ("stats", "Stats"), ("form", "Form"), ("notes", "Notes")]) + "</nav>"
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
/* Action Network badge stays visible at every width (the site widget hides it under 440 px; the embed keeps it) */
@media (max-width:600px){{.ff-brand{{position:static;display:flex;justify-content:center;margin-bottom:6px}}.ff-header{{padding:12px 12px 10px}}.ff-title{{font-size:17px}}}}
@media (max-width:440px){{.ff-header{{padding:9px 8px 8px}}.ff-brand{{display:flex!important;margin-bottom:5px}}.ff-title{{font-size:14px}}.ff-subtitle{{font-size:10px}}
.panel,section.top,.secs{{padding-left:10px;padding-right:10px}}.ffnav{{padding:7px 10px}}.fp-headline{{font-size:17px}}.fp-odds{{font-size:10.5px}}
.fp-proj-table th,.fp-proj-table td{{padding:5px 3px;font-size:11px}}.fp-proj-table .odds{{font-size:11.5px}}.fp-proj-table .pct{{font-size:10px}}.pvm .op{{font-size:9px}}
.pvm col.c0{{width:16%}}.pvm th.rl{{padding-left:6px;font-size:11px}}.pvm th.rl small{{font-size:7.5px}}.fp-proj-header{{font-size:9px;padding:6px 9px}}.cap{{font-size:10px;padding:5px 8px}}
details.collapsible>summary{{padding:8px 10px;font-size:10px}}details.collapsible>summary .meta{{display:none}}details.collapsible>.body{{padding:10px}}
table.t{{font-size:11.5px}}table.t td,table.t th{{padding:5px 3px}}.kv{{font-size:11.5px;flex-wrap:wrap}}.tape .row{{font-size:12px}}.tape .k{{font-size:9.5px}}}}
</style></head><body><div class="ff">
{head}</div>{nav}{top}<div class="secs">{"".join(secs)}</div>
<div class="foot"><b>Fight Form</b> · Fight {n} of {NB}: fights are numbered by bout order on the card (1 = first early prelim, {NB} = main event), per the UFC.com order{CANC}. Sources: UFC Model sheet ({"Publish to site export" if proj_src == "publish" else "site build pull" if proj_src else "no projection"}), BettingPros, The Odds API, UFCStats. Not betting advice.</div></div>
<script>/* open a collapsed section when its nav chip is used */document.querySelectorAll('.ffnav a').forEach(function(a){{a.addEventListener('click',function(){{var d=document.querySelector(a.getAttribute('href'));if(d&&d.tagName==='DETAILS')d.open=true;}});}});</script>
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
