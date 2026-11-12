#!/usr/bin/env python3
"""Independent check for the v4 fight embeds (embeds/<slug>/fight_NN.html). Does not import build_fight_embeds.py.
For each <span data-id> in each embed, takes the registry's rule + args (which source, which field), recomputes the value
from the repo's source files with code written here, formats it and diffs the text. Then structural assertions per embed
and for the whole card.

    python3 scripts/verify_fight_embeds.py --slug ufc_334            # exit 1 on any mismatch
    python3 scripts/verify_fight_embeds.py --slug ufc_334 --negative # plant errors in a temp copy; every one must be caught
"""
import argparse, difflib, json, math, re, shutil, subprocess, sys, tempfile, html as H
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FD = REPO / "form" / "data"
US = {"draftkings", "fanduel", "betmgm", "williamhill_us", "caesars", "betrivers", "fanatics", "espnbet", "hardrockbet", "circasports"}   # written here, not imported
sq = lambda s: re.sub(r"[^a-z]", "", (s or "").lower())
sur = lambda s: sq(s.split()[-1])
# Block 58: a registry row finds its bout by both fighters' names (feed spellings through form/data/name_aliases.json,
# exact keys), and must find exactly one. A row still keyed by number is an error, not a fallback.
ALIAS = {sq(k): v for k, v in json.loads((REPO / "form" / "data" / "name_aliases.json").read_text()).items() if not k.startswith("_")}
def by_name(ev, a):
    if "pair" not in a:
        raise KeyError(f"registry row keyed by number (n={a.get('n')}), not by name")
    c = lambda s: sq(ALIAS.get(sq(s), s))
    want = {c(a["pair"][0]), c(a["pair"][1])}
    hits = [x for x in ev["fights"] if {c(x["a"]["name"]), c(x["b"]["name"])} == want]
    if len(hits) != 1:
        raise KeyError(f"{a['pair']} matches {len(hits)} bouts")
    return hits[0]

def is_(x, y):
    """same fighter: squashed names equal (Alateng Heili = Alatengheili), or close surname with a matching first initial (Charlie Radke = Charles Radtke)"""
    if sq(x) == sq(y): return True
    tx, ty = x.split(), y.split()
    if len(tx) < 2 or len(ty) < 2: return False
    return difflib.SequenceMatcher(None, sur(x), sur(y)).ratio() >= 0.8 and sq(tx[0])[:1] == sq(ty[0])[:1]
def bout(x, y, p, q): return (is_(x, p) and is_(y, q)) or (is_(x, q) and is_(y, p))

def implied(m): return 100 / (m + 100) if m > 0 else -m / (-m + 100)
def fairp(p): p = min(max(p, .001), .999); return 1 / (1 + math.exp(-KK * math.log(p / (1 - p))))
def p2ml(p): return -round(100 * p / (1 - p)) if p >= .5 else round(100 * (1 - p) / p)
def sml(m): return f"+{m}" if m > 0 else str(m)
def fmt(x, k):
    return {"pct1": lambda: f"{x*100:.1f}%", "pct0": lambda: f"{x*100:.0f}%", "ml": lambda: sml(x), "mlp": lambda: sml(p2ml(x)), "n1": lambda: f"{x:.1f}",
            "n2": lambda: f"{x:.2f}", "s2": lambda: f"{x:+.2f}", "int": lambda: str(x), "intc": lambda: f"{x:,}", "d3": lambda: f"{x:.3f}", "d4": lambda: f"{x:.4f}",
            "str": lambda: str(x), "in": lambda: f'{x}"', "r0": lambda: str(int(round(x))), "pts": lambda: f"{abs(x)*100:.1f}", "sp": lambda: f"{x*100:+.1f}", "spp": lambda: f"{x*100:+.1f}%", "s1": lambda: f"{x:+.1f}", "sint": lambda: f"{int(x):+d}", "mmss": lambda: f"{int(x) // 60}:{int(round(x)) % 60:02d}"}[k]()

def dig(o, path):
    for p in str(path).split("."):
        o = o[int(p)] if isinstance(o, list) else o[p]
    return o

def load_sources(slug):
    G = {}
    G["SLUG"] = slug
    G["ODDS"] = json.load(open(REPO / "data" / f"{slug}_odds.json"))
    G["OV"] = json.load(open(REPO / "data" / "card_overrides.json"))[slug]
    G["KK"] = json.load(open(FD / "index.json"))["k"]
    exp = [p for p in (REPO / "data" / f"{slug}_projections.json", REPO / "data" / "pending" / f"{slug}_projections.json") if p.exists()]
    G["PUBF"] = str(exp[0].relative_to(REPO)) if exp else None
    G["PUB"] = json.load(open(exp[0])) if exp else {"fights": []}
    return G

def check(D, htmlfile, G):
    page = open(D / htmlfile).read(); reg = json.load(open(D / htmlfile.replace(".html", ".registry.json")))
    EV = {reg["event"]: json.load(open(REPO / reg["event"]))}
    DATE = EV[reg["event"]]["date"]; OV = G["OV"]; PUB = G["PUB"]; BPO = G["ODDS"]; KK = G["KK"]
    def fairp(p): p = min(max(p, .001), .999); return 1 / (1 + math.exp(-KK * math.log(p / (1 - p))))
    shown = {m.group(1): H.unescape(m.group(2)) for m in re.finditer(r'<span data-id="(v\d+)">([^<]*)</span>', page)}
    fight = next(x for x in EV[reg["event"]]["fights"] if bout(x["a"]["name"], x["b"]["name"], *reg["pair"]))
    A, B = fight["a"]["name"], fight["b"]["name"]; NM = {"a": A, "b": B}
    EMB = json.loads((FD / "embed_metrics" / f"{G['SLUG']}.json").read_text())["fighters"] if (FD / "embed_metrics" / f"{G['SLUG']}.json").exists() else {}
    FT = {s: (json.load(open(FD / "fighters" / f'{fight[s]["slug"]}.json')) if fight[s].get("slug") and (FD / "fighters" / f'{fight[s]["slug"]}.json').exists()
              else {"bio": (EMB.get(fight[s]["name"]) or {}).get("bio") or {}, "fights": []}) for s in "ab"}   # debut bio checked by verify_embed_metrics
    prior = {s: [x for x in FT[s]["fights"] if x["d"] < DATE] for s in "ab"}
    pub = next((p for p in PUB["fights"] if p.get("publish") is not False and bout(p["dog"], p["fav"], A, B)), None)
    bpf = next((x for x in BPO["fights"] if bout(x["fighter_a"]["name"], x["fighter_b"]["name"], A, B)), None)

    def pwin(sd):
        role = "dog" if is_(pub["dog"], NM[sd]) else "fav"
        return pub["sheet"]["true_" + role], role
    def bp_cost(market, label, field="cost"):
        s = next(s for s in bpf["markets"][market] if s["label"] == label)
        return s["opening_cost"] if field == "opening_cost" else s["books"]["consensus"]["line" if field == "line" else "cost"]
    def nv(market, label, other):
        x, y = implied(bp_cost(market, label)), implied(bp_cost(market, other)); return x / (x + y)
    SEL = {"dec": "points", "ko": "ko-tko-dq", "sub": "submission"}
    def mnv(fighter, k):   # own formulation: share of one selection among every method selection that has a selection id
        mv = [x for x in bpf["markets"]["method_of_victory"] if x["selection"]]
        tot_ = sum(implied(x["books"]["consensus"]["cost"]) for x in mv)
        me = [x for x in mv if x["selection"] == SEL[k] and is_(fighter, x["label"].rsplit(" ", 1)[0].replace(" KO/TKO/DQ", ""))]
        assert len(me) == 1, me
        return implied(me[0]["books"]["consensus"]["cost"]) / tot_
    def tot(sd):
        rows = [x for x in prior[sd] if x.get("s") and x.get("secs")]
        col = lambda i: sum(x["s"][i] for x in rows); secs = sum(x["secs"] for x in rows); return col, secs
    def stat(sd, key):
        col, secs = tot(sd); mins = secs / 60
        return {"slpm": lambda: col(0) / mins, "sapm": lambda: col(2) / mins, "diff": lambda: (col(0) - col(2)) / mins, "acc": lambda: col(0) / col(1),
                "dfn": lambda: 1 - col(2) / col(3), "td15": lambda: col(6) / mins * 15, "tdd": lambda: 1 - col(8) / col(9), "ctrlp": lambda: col(10) / secs}[key]()
    def form_win(a, sd):
        ff = EV[a["ev"]]["fights"]; f_ = by_name(EV[a["ev"]], a)
        p = fairp(f_["odds"]["close"]["p"]) if a["base"] == "fair(odds.close.p)" else f_["form"]["p"]
        return (p if sd == "a" else 1 - p), f_

    ok, bad = 0, []
    vals = {}   # Block 59: values this script recomputed, by row id, for the edge rule
    for r in reg["rows"]:
        a, rule, txt = r["args"], r["rule"], shown.get(r["id"])
        if txt is None: bad.append((r["id"], r["desc"], "missing from HTML")); continue
        try:
            inv = a.get("inv")
            if rule == "edge":
                # Sean % minus market no-vig %, both recomputed here from their own sources (rows listed in "of")
                x_, y_ = a["of"]
                if x_ not in vals or y_ not in vals: raise KeyError(f"edge needs {x_}, {y_} verified first")
                v = vals[x_] - vals[y_]
            elif rule == "record":
                L_ = prior[a["side"]]; c = lambda t: sum(1 for x in L_ if x["r"] == t); nc = len(L_) - c("W") - c("L") - c("D")
                v = f'{c("W")}-{c("L")}-{c("D")}' + (f" ({nc} NC)" if nc else "")
            elif rule in ("ev", "ev_p"):
                f_ = by_name(EV[a["ev"]], a); v = dig(f_, a["path"]); v = 1 - v if inv else v
            elif rule == "fair":
                f_ = by_name(EV[a["ev"]], a); v = fairp(dig(f_, a["path"])); v = 1 - v if inv else v
            elif rule == "evp_sum":
                f_ = by_name(EV[a["ev"]], a); v = sum(dig(f_, p_) for p_ in a["paths"]) / 100
            elif rule == "pub_win":
                v = pwin(a["side"])[0]; v = 1 - v if inv else v
            elif rule == "pub_meth":
                p, role = pwin(a["side"]); m = pub["method"][role]; v = p * (m["ko"] + m["sub"] if a["k"] == "itd" else m[a["k"]])
            elif rule == "pub": v = dig(pub, a["key"]); v = 1 - v if inv else v
            elif rule in ("pub_ml", "pub_ml_imp"):   # the sheet's listed price for this side (export inputs), and its straight implied %
                role = pwin(a["side"])[1]; v = pub["inputs"][role + "_odds"]; v = implied(v) if rule == "pub_ml_imp" else v
            elif rule == "em_sum":   # Block 59g: total strike diff = head + body + leg diff
                EM_ = G.setdefault("EMX", json.loads((FD / "embed_metrics" / f"{G['SLUG']}.json").read_text()))
                v = 0.0
                for pth in a["paths"]:
                    x_ = EM_["fighters"][a["fighter"]]
                    for k_ in pth.split("."): x_ = x_[k_]
                    v += x_
            elif rule in ("em", "em_share", "em_div"):
                # Block 59d/e: form/data/embed_metrics/<card>.json (our UFCStats rows, every UFC fight)
                EM_ = G.setdefault("EMX", json.loads((FD / "embed_metrics" / f"{G['SLUG']}.json").read_text()))
                if rule == "em":
                    v = EM_["fighters"][a["fighter"]]
                    for k_ in a["path"].split("."): v = v[int(k_)] if isinstance(v, list) else v[k_]
                elif rule == "em_share": r_ = EM_["fighters"][a["fighter"]]; v = r_[a["key"]] / r_["ufc_fights"]
                else: v = EM_["division_power_share" if a.get("key", "power") == "power" else "division_dropped_share"][a["wc"]]
            elif rule == "labs":
                # the site's own metrics in form/data/labs.json, looked up here by the fighter's slug
                LJ = G.setdefault("LABS", json.loads((FD / "labs.json").read_text()))
                if a["section"] == "metrics":
                    v = next(x for x in LJ["metrics"] if x.get("s") == a["slug"])[a["key"]]
                else:
                    s1_, s2_ = a["section"].split(".")
                    v = next(u[sd][a["key"]] for u in LJ[s1_][s2_] for sd in ("a", "b") if isinstance(u.get(sd), dict) and u[sd].get("s") == a["slug"] and u[sd].get(a["key"]) is not None)
            elif rule == "bp_imp_sum": v = sum(implied(bp_cost(a["market"], lb)) for lb in a["labels"])
            elif rule == "pubp": v = PUB["params"][a["key"]]
            elif rule == "bp": v = bp_cost(a["market"], a["label"], a["field"])
            elif rule == "bp_nv": v = nv(a["market"], a["label"], a["other"]); v = 1 - v if inv else v
            elif rule == "bp_imp": v = implied(bp_cost(a["market"], a["label"]))
            elif rule == "bp_mnv": v = mnv(a["fighter"], a["k"])
            elif rule == "bp_mitd": v = mnv(a["fighter"], "ko") + mnv(a["fighter"], "sub")
            elif rule == "gap_pub_bp": v = pwin(a["side"])[0] - nv(a["market"], a["label"], a["other"])
            elif rule == "form_meth":
                p, f_ = form_win(a, a["side"]); ms = f_["form"]["ms"][a["side"]]
                v = p * {"ko": ms[0], "sub": ms[1], "dec": ms[2], "itd": ms[0] + ms[1]}[a["k"]]
            elif rule == "form_gtd":
                p, f_ = form_win(a, "a"); v = p * f_["form"]["ms"]["a"][2] + (1 - p) * f_["form"]["ms"]["b"][2]
            elif rule in ("oa_drift", "oa_drift_abs"):
                f_ = by_name(EV[a["ev"]], a); v = f_["odds"]["close"]["p"] - f_["odds"]["open"]["p"]
                if rule == "oa_drift_abs": v = abs(v)
            elif rule == "labs_live":
                LV_ = G.setdefault("LIVE", {r_["label"]: r_ for r_ in json.loads((FD / "labs.json").read_text())["live"]["rows"]})
                v = LV_[a["label"]][a["field"]]
            elif rule == "oa_p":   # win chance at open/close for the named side (event file a = first name of the pair)
                f_ = by_name(EV[a["ev"]], a); v = f_["odds"][a["at"]]["p"]
                c_ = lambda s_: sq(ALIAS.get(sq(s_), s_)); first = c_(f_["a"]["name"]) == c_(a["pair"][0])
                if (a["side"] == "b") == first: v = 1 - v
            elif rule == "oa_open_ml":
                f_ = by_name(EV[a["ev"]], a); v = f_["odds"]["open"]["m" + a["side"]]
                c_ = lambda s_: sq(ALIAS.get(sq(s_), s_))   # side a must be the first name of the pair in the event file too
                if c_(f_["a"]["name"]) != c_(a["pair"][0]): v = f_["odds"]["open"]["m" + ("b" if a["side"] == "a" else "a")]
            elif rule in ("oa_open", "oa_close"):
                f_ = by_name(EV[a["ev"]], a); v = f_["odds"]["open" if rule == "oa_open" else "close"]["p"]
            elif rule == "oa_len":
                f_ = by_name(EV[a["ev"]], a); v = len(f_["odds"]["series"])
            elif rule == "oa_best":
                f_ = by_name(EV[a["ev"]], a); k = "ma" if a["side"] == "a" else "mb"
                v = max((b[k] for bk, b in f_["odds"]["books"].items() if bk in US and b.get(k) is not None), key=lambda m: m / 100 if m > 0 else 100 / -m)   # US books only (Block 57)
            elif rule == "age": v = (date.fromisoformat(DATE) - date.fromisoformat(FT[a["side"]]["bio"]["dob"])).days / 365.25
            elif rule == "bio_reach": v = int(FT[a["side"]]["bio"]["reach"])
            elif rule == "bio": v = FT[a["side"]]["bio"][a["key"]]
            elif rule == "nfights": v = len(prior[a["side"]])
            elif rule == "stat": v = stat(a["side"], a["key"])
            elif rule == "fight": v = dig(prior[a["side"]][a["i"]], a["key"])
            else: bad.append((r["id"], r["desc"], f"no verifier rule {rule}")); continue
            exp = fmt(v, r["fmt"]); vals[r["id"]] = v
        except Exception as e:
            bad.append((r["id"], r["desc"], f"error {e!r}")); continue
        if exp == txt: ok += 1
        else: bad.append((r["id"], r["desc"], f"shown {txt!r} expected {exp!r}"))
    extra = set(shown) - {r["id"] for r in reg["rows"]}
    # numbers outside spans: strip spans, scripts, styles, svg, tags; flag leftover digits that are not dates/labels
    body = re.sub(r"<style.*?</style>|<script.*?</script>|<svg.*?</svg>|<span data-id=\"v\d+\">[^<]*</span>", " ", page, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", H.unescape(body))
    V6 = 'role="tablist"' in page
    if V6:
        # (a6) method stack: every number in a data-k cell belongs to that method (model rows by k, market rows by label)
        for k_, chunk in re.findall(r'<td data-k="([a-z]+)">(.*?)</td>', page, re.S):
            for sid in re.findall(r'data-id="(v\d+)"', chunk):
                rr = next(r for r in reg["rows"] if r["id"] == sid); ar = rr["args"]
                kk = ar.get("k") or ({"Points": "dec", "KO/TKO/DQ": "ko", "Submission": "sub"}.get(str(ar.get("label", "")).rsplit(" ", 1)[-1]))
                if rr["rule"] == "bp_imp_sum": kk = "itd"
                if rr["rule"] == "edge": continue
                if kk != k_: bad.append((sid, rr["desc"], f"method {kk} shown in column {k_}"))
        # (e6) model cells: only export rules, and all 24 present (ML, GTD, ITD price+% and DEC/KO/SUB/ITD x 2 fighters price+%)
        mids = [sid for td in re.findall(r'<td class="model">(.*?)</td>', page, re.S) for sid in re.findall(r'data-id="(v\d+)"', td)]
        mids += [sid for td in re.findall(r'<td data-k="[a-z]+"><span class="odds">(.*?)</div>', page, re.S) for sid in re.findall(r'data-id="(v\d+)"', td)]
        mrules = {next(r["rule"] for r in reg["rows"] if r["id"] == sid) for sid in mids}
        if pub is not None:
            if len(mids) != 24: bad.append(("proj", "model cells", f"{len(mids)} model numbers, want 24"))
            if not mrules <= {"pub_win", "pub_meth", "pub"}: bad.append(("proj", "model rules", f"non-export rules in model cells: {mrules}"))
        # Block 59f: an opponent named Sean in the fight history (Dober vs Sean Spencer) is not the model label
        if re.search(r"\bSean\b(?! [A-Z][a-z])", re.sub(r"@SeanZerillo|twitter.com/SeanZerillo", "", page)) or re.search(r">Sean<|Sean (fair|vs|ML|%)", page): bad.append(("page", "label", "'Sean' used as the model name"))
        if re.search(r'class="op"', page): bad.append(("page", "open price", "o-prefixed open price in the projection"))
        if re.search(r"BettingPros", text): bad.append(("page", "source name", "BettingPros named on the page"))
        if re.search(r"\bElo\b|\bFig\b|Form Figure", text): bad.append(("page", "rating", "Elo or Form Figure shown"))
        # Block 59g: every link into the site must land on a real fight or fighter
        for es_, n_ in re.findall(r'#/fight/([^/"]+)/(\d+)"', page):
            ef = FD / "events" / f"{es_}.json"
            if not ef.exists() or not any(str(x["n"]) == n_ for x in json.loads(ef.read_text())["fights"]): bad.append(("link", "fight", f"{es_}/{n_} not on the site"))
        for sl_ in re.findall(r'#/fighter/([^/"]+)"', page):
            if not (FD / "fighters" / f"{sl_}.json").exists(): bad.append(("link", "fighter", f"{sl_} not on the site"))
        # Block 59g: striking angles recomputed from the metrics file; the page must show exactly these
        EMv = json.loads((FD / "embed_metrics" / f"{G['SLUG']}.json").read_text())["fighters"]
        pa_, pb_ = (EMv.get(x_, {}) for x_ in reg["pair"]); want = []
        def td_(r): t = r.get("target_diff") or {}; return None if t.get("head") is None else t["head"] + t["body"] + t["leg"]
        ok4 = pa_.get("ufc_fights", 0) >= 4 and pb_.get("ufc_fights", 0) >= 4
        if ok4 and td_(pa_) is not None and td_(pb_) is not None and abs(td_(pa_) - td_(pb_)) >= 2.0: want.append(reg["pair"][0] if td_(pa_) > td_(pb_) else reg["pair"][1])
        ra_, rb_ = pa_.get("rounds", [{}] * 3)[2], pb_.get("rounds", [{}] * 3)[2]
        if ok4 and ra_.get("diff_pm") is not None and rb_.get("diff_pm") is not None and ra_.get("fights", 0) >= 3 and rb_.get("fights", 0) >= 3 and abs(ra_["diff_pm"] - rb_["diff_pm"]) >= 2.9231:
            want.append(reg["pair"][0] if ra_["diff_pm"] > rb_["diff_pm"] else reg["pair"][1])
        m_ = re.search(r'<div class="ang">(.*?)</div>', page)
        got = re.findall(r"<li><b>([^<]+)</b>", m_.group(1)) if m_ else []
        if [g.split()[-1] for g in got] != [w.split()[-1] for w in want]: bad.append(("angle", "striking", f"page {got} vs recomputed {want}"))
        # Block 59h: flip flag recomputed (R1 diff 1.0+ one way, R3 diff 1.0+ the other, both 3+ fights reaching R3)
        rr = lambda r, i: (r.get("rounds") or [{}] * 3)[i]
        a1, b1, a3, b3 = rr(pa_, 0).get("diff_pm"), rr(pb_, 0).get("diff_pm"), rr(pa_, 2).get("diff_pm"), rr(pb_, 2).get("diff_pm")
        wantf = (None not in (a1, b1, a3, b3) and rr(pa_, 2).get("fights", 0) >= 3 and rr(pb_, 2).get("fights", 0) >= 3
                 and min(rr(pa_, 0).get("mins", 0), rr(pb_, 0).get("mins", 0), rr(pa_, 2).get("mins", 0), rr(pb_, 2).get("mins", 0)) >= 15
                 and ((a1 - b1 >= 1 and b3 - a3 >= 1) or (b1 - a1 >= 1 and a3 - b3 >= 1)))
        if wantf != ('class="flip"' in page): bad.append(("flag", "flip", f"page {'class=\"flip\"' in page} vs recomputed {wantf}"))
        # the decision-model accuracy quoted in the Cardio key must match labs.json
        acc_ = re.search(r"decisions (\d+)% of the time", page)
        if acc_ and int(acc_.group(1)) != round(json.loads((FD / "labs.json").read_text())["scoring"]["acc"] * 100): bad.append(("text", "key", "judging-model accuracy in the key"))
    # ---- v4 structural assertions ----
    # (a) method order DEC / KO / SUB in the merged table, and every method cell sits in the row of its own method
    rows_ = re.findall(r'<tr data-row="([a-z]+)"', page)
    if not V6 and rows_ != ["win", "dec", "ko", "sub", "itd", "gtd"]: bad.append(("table", "row order", f"{rows_}"))
    for rk, chunk in re.findall(r'<tr data-row="([a-z]+)"(.*?)</tr>', page, re.S):
        for sid in re.findall(r'data-id="(v\d+)"', chunk):
            rr = next(r for r in reg["rows"] if r["id"] == sid)
            k_ = rr["args"].get("k") or {"Points": "dec", "KO/TKO/DQ": "ko", "Submission": "sub"}.get(str(rr["args"].get("label", "")).rsplit(" ", 1)[-1])
            if rr["rule"] == "bp_mitd": k_ = "itd"
            if k_ and rk in ("dec", "ko", "sub", "itd") and k_ != rk: bad.append((sid, rr["desc"], f"method {k_} shown in row {rk}"))
    hdr = re.search(r'<tr data-row="dec"><th class="rl">(\w+)<small>.*?<tr data-row="ko"><th class="rl">(\w+)<small>.*?<tr data-row="sub"><th class="rl">(\w+)<small>', page, re.S)
    if not V6 and (not hdr or hdr.groups() != ("DEC", "KO", "SUB")): bad.append(("table", "method labels", str(hdr and hdr.groups())))
    # (b) no model comparison / alt-GTD block, no Markov numbers; any Markov mention carries THIN SAMPLE
    if re.search(r"Model comparison|Other GTD numbers|id=\"models\"", page): bad.append(("page", "model comparison", "still present"))
    if any(r["rule"].startswith("mk") for r in reg["rows"]): bad.append(("page", "Markov", "Markov number displayed"))
    for m_ in re.finditer(r"Markov", text):
        if "THIN SAMPLE" not in text[max(0, m_.start() - 200): m_.end() + 200]: bad.append(("page", "Markov mention", "no THIN SAMPLE label nearby"))
    # (c) fight number = bout order (1 = opener); recomputed from the overrides order and from BettingPros start times
    order = [o.split("|") for o in OV["order"]]
    want = len(order) - next(i for i, (x, y) in enumerate(order) if bout(x, y, A, B))
    by_t = sorted(BPO["fights"], key=lambda x: x["scheduled_utc"])
    bp_rank = 1 + next(i for i, x in enumerate(by_t) if bout(x["fighter_a"]["name"], x["fighter_b"]["name"], A, B))
    shown_n = int(re.search(r'fp-fight-num">FIGHT (\d+)<', page).group(1))
    if not (shown_n == want == bp_rank == reg["fight"]): bad.append(("header", "fight number", f"shown {shown_n} order {want} bp {bp_rank}"))
    if any(bout(x, y, A, B) for x, y in OV["cancel"]): bad.append(("page", "cancelled bout", "rendered"))
    # (d) Action Network badge in the header and not hidden by the embed CSS at any width
    if '<div class="ff-brand" aria-label="Action Network"><span class="ff-brand-text">ACTION</span>' not in page: bad.append(("header", "brand", "missing"))
    if re.search(r"\.ff-brand\s*\{[^}]*display:\s*none", page.split("/* v4 embed layout */")[1]): bad.append(("header", "brand", "hidden by embed CSS"))
    # (e) Sean's projection source: the Publish to site export whenever it has this bout; every Sean cell present and from it
    sean_ids = [sid for td in re.findall(r'<td class="proj"[^>]*>(.*?)</td>', page, re.S) for sid in re.findall(r'data-id="(v\d+)"', td)]
    sean_rules = {next(r["rule"] for r in reg["rows"] if r["id"] == sid) for sid in sean_ids}
    src_attr = (re.search(r'data-proj-src="([a-z]+)"', page) or [None, None])[1]
    if V6: src_attr = "publish" if pub is not None else None   # v6 has no merged table to carry the attribute; (e6) covers the cells
    if pub is not None:
        if reg.get("proj_src") != "publish" or src_attr != "publish": bad.append(("proj", "source", f"export has this bout but embed says {reg.get('proj_src')}/{src_attr}"))
        if reg.get("proj_file") != G["PUBF"]: bad.append(("proj", "file", f"{reg.get('proj_file')} != {G['PUBF']}"))
        if not V6 and len(sean_ids) != 22: bad.append(("proj", "Sean cells", f"{len(sean_ids)} Sean numbers shown, want 22 (Win/DEC/KO/SUB/ITD x 2 fighters x price+% and GTD price+%)"))
        if not sean_rules <= {"pub_win", "pub_meth", "pub"}: bad.append(("proj", "Sean rules", f"non-export rules in Sean cells: {sean_rules}"))
    else:
        if reg.get("proj_src") == "publish" or src_attr == "publish": bad.append(("proj", "source", "embed claims the export but the export has no row for this bout"))
        if not sean_rules <= {"evp_sum"}: bad.append(("proj", "Sean rules", f"fallback cells not from the event file: {sean_rules}"))
    # (f) market method cells only when BettingPros has all six fighter/method prices
    if bpf:
        sel = {(x["selection"], j) for x in bpf["markets"].get("method_of_victory", []) for j, nm_ in enumerate((A, B))
               if x["selection"] in SEL.values() and is_(nm_, x["label"].rsplit(" ", 1)[0])}
        full = len(sel) == 6
        if not full and any(r["rule"] in ("bp_mnv", "bp_mitd") for r in reg["rows"]): bad.append(("market", "method", "method no-vig shown from an incomplete method market"))
    print(f"{htmlfile}: fight {shown_n}/{len(order)}; {ok}/{len(reg['rows'])} verified, {len(bad)} mismatches/assertion failures, {len(extra)} unregistered spans")
    for b in bad: print("   ", *b)
    return ok, len(bad) + len(extra)

def card_check(D, G, slug):
    """whole-card assertions: one embed per bout, numbered 1..N by bout order, event file agrees, embed.html roster agrees."""
    bad = []
    order = [o.split("|") for o in G["OV"]["order"]]; N = len(order)
    files = sorted(p.name for p in D.glob("fight_*.html"))
    want = [f"fight_{n:02d}.html" for n in range(1, N + 1)]
    if files != want: bad.append(("card", "files", f"{files} != {want}"))
    cj = json.load(open(D / "card.json"))
    if [c["fight"] for c in cj["card"]] != list(range(N, 0, -1)): bad.append(("card", "card.json numbers", str([c["fight"] for c in cj["card"]])))
    ev = json.load(open(REPO / cj["event"]))
    for i, (x, y) in enumerate(order):
        f = next((f for f in ev["fights"] if bout(f["a"]["name"], f["b"]["name"], x, y)), None)
        if not f or f["n"] != N - i: bad.append(("event", f"{x} vs {y}", f"event file n={f and f['n']} want {N - i}"))
    for x, y in G["OV"].get("cancel", []):
        if any(bout(f["a"]["name"], f["b"]["name"], x, y) for f in ev["fights"]): bad.append(("event", "cancelled", f"{x} vs {y} still in the event file"))
    for p in D.glob("fight_*.registry.json"):
        r = json.load(open(p))
        if any(bout(x, y, *r["pair"]) for x, y in G["OV"].get("cancel", [])): bad.append(("card", p.name, "cancelled bout has an embed"))
    eh = open(REPO / "embed.html").read()
    m = re.search(r"// <v4-roster " + re.escape(slug) + r">(.*?)// </v4-roster>", eh, re.S)
    if not m: bad.append(("embed.html", "roster", "no v4 roster block"))
    else:
        ns = [int(x) for x in re.findall(r"\{ n: (\d+),", m.group(1))]
        if ns != list(range(N, 0, -1)): bad.append(("embed.html", "roster numbers", str(ns)))
    print(f"card {slug}: {len(files)} embeds, {len(bad)} card-level failures")
    for b in bad: print("   ", *b)
    return len(bad)

def run(D, G, slug, quiet=False):
    tot_ok = tot_bad = n_rows = 0
    for f in sorted(p.name for p in D.glob("fight_*.html")):
        ok, nb = check(D, f, G); tot_ok += ok; tot_bad += nb
        n_rows += len(json.load(open(D / f.replace(".html", ".registry.json")))["rows"])
    tot_bad += card_check(D, G, slug)
    return tot_ok, n_rows, tot_bad

def negative(D, G, slug):
    """plant one error per copy; each must make the run fail."""
    import copy, contextlib, io
    def plant_text(name, fn):
        def go(T, G_):
            p = T / name; s_ = p.read_text(); s2 = fn(s_); assert s2 != s_, "plant did not change the file"; p.write_text(s2)
        return go
    def bump_first(rule, fmt):
        def fn(s_):
            reg = json.load(open(D / "fight_13.registry.json"))
            r = next(r for r in reg["rows"] if r["rule"] == rule and r["fmt"] == fmt)
            t = r["text"]; t2 = re.sub(r"(\d)(?!.*\d)", lambda m: str((int(m.group(1)) + 1) % 10), t)
            return s_.replace(f'<span data-id="{r["id"]}">{H.escape(t)}</span>', f'<span data-id="{r["id"]}">{H.escape(t2)}</span>')
        return fn
    def export_shift(T, G_):
        f0 = G_["PUB"]["fights"][0]; f0["sheet"]["true_fav"] += 0.002; f0["sheet"]["true_dog"] -= 0.002
    def export_method(T, G_):
        m = G_["PUB"]["fights"][1]["method"]["dog"]; m["ko"], m["sub"] = m["sub"], m["ko"]
    def export_gtd(T, G_):
        G_["PUB"]["fights"][2]["gtd"] += 0.01
    plants = [
        ("embed: Sean win % text off by 0.1 (fight 13)", plant_text("fight_13.html", bump_first("pub_win", "pct1"))),
        ("embed: Sean KO % text off (fight 13)", plant_text("fight_13.html", bump_first("pub_meth", "pct1"))),
        ("embed: KO and SUB cells swapped in the method stack (fight 07)", plant_text("fight_07.html", lambda s_: s_.replace('<td data-k="ko">', '<td data-k="@@">', 1).replace('<td data-k="sub">', '<td data-k="ko">', 1).replace('<td data-k="@@">', '<td data-k="sub">', 1))),
        ("embed: badge hidden by CSS (fight 02)", plant_text("fight_02.html", lambda s_: s_.replace("/* v4 embed layout */", "/* v4 embed layout */\n.ff-brand{display:none}"))),
        ("embed: wrong FIGHT number (fight 05)", plant_text("fight_05.html", lambda s_: s_.replace('fp-fight-num">FIGHT 5<', 'fp-fight-num">FIGHT 6<'))),
        ("embed: a model cell blanked (fight 10)", plant_text("fight_10.html", lambda s_: re.sub(r'<td class="model"><span class="odds">.*?</td>', '<td class="model dim">n/a</td>', s_, count=1, flags=re.S))),
        ("embed: an edge chip off by 0.1 (fight 13)", plant_text("fight_13.html", bump_first("edge", "spp"))),
        ("embed: flip flag dropped (fight 04)", plant_text("fight_04.html", lambda s_: s_.replace('class="flip"', 'class="flop"', 1))),
        ("embed: striking angle dropped (fight 06)", plant_text("fight_06.html", lambda s_: re.sub(r'<div class="ang">.*?</ul></div>', "", s_, count=1))),
        ("embed: past-fight link to a bout that is not on the site (fight 07)", plant_text("fight_07.html", lambda s_: re.sub(r'(#/fight/[^/"]+/)\d+"', r'\g<1>999"', s_, count=1))),
        ("embed: model renamed 'Sean' (fight 04)", plant_text("fight_04.html", lambda s_: s_.replace("Moneyline · model vs market", "Moneyline · Sean vs market", 1))),
        ("card: one embed missing (fight 09)", lambda T, G_: (T / "fight_09.html").unlink()),
        ("export: Gane/Hokit true % moved 0.2 pts after the build", export_shift),
        ("export: one dog's KO/SUB split swapped after the build", export_method),
        ("export: one GTD moved 1 pt after the build", export_gtd),
    ]
    caught = 0
    for label, fn in plants:
        with tempfile.TemporaryDirectory() as td:
            T = Path(td) / "e"; shutil.copytree(D, T); G_ = copy.deepcopy(G); fn(T, G_)
            with contextlib.redirect_stdout(io.StringIO()):
                _, _, nb = run(T, G_, slug)
        print(f"  NEGATIVE {'CAUGHT ' if nb else 'MISSED '} {nb:>3} failures · {label}"); caught += bool(nb)
    # Block 59i (Kirk check 4): a bug UPSTREAM of the metrics file. The page check trusts that file, so the plant goes into
    # a copy of build_embed_metrics.py (control seconds dropped); the independent CSV recompute must flag the result.
    up = upstream_plant()
    print(f"  NEGATIVE {'CAUGHT ' if up else 'MISSED '} upstream · metrics builder drops control seconds (page check alone cannot see this)")
    caught += bool(up)
    print(f"negative test: {caught}/{len(plants) + 1} planted errors caught")
    return caught == len(plants) + 1


def metrics_check(slug, metrics=None):
    """Independent recompute of the metrics file from the UFCStats CSVs (scripts/verify_embed_metrics.py). None if no CSV cache."""
    cache = REPO / ".form_cache"
    if not (cache / "ufc_fight_stats.csv").exists(): return None
    evf = metrics_event_file()
    r = subprocess.run([sys.executable, "-I", str(REPO / "scripts/verify_embed_metrics.py"), "--event", evf, "--cache", str(cache),
                        "--metrics", metrics or str(FD / "embed_metrics" / f"{slug}.json")], capture_output=True, text=True)
    return r.returncode, r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr.strip()[-300:]


def upstream_plant():
    src = (REPO / "scripts/build_embed_metrics.py").read_text()
    bad_src = src.replace("return int(m.group(1)) * 60 + int(m.group(2)) if m else 0", "return int(m.group(1)) * 60 if m else 0")
    if bad_src == src: return False
    with tempfile.TemporaryDirectory() as td:
        sp = REPO / "scripts" / "_plant_build_embed_metrics.py"; out = Path(td) / "m.json"
        try:
            sp.write_text(bad_src)
            evf = metrics_event_file()
            subprocess.run([sys.executable, "-I", str(sp), "--event", evf, "--cache", str(REPO / ".form_cache"), "--out", str(out)], check=True, capture_output=True)
        finally:
            sp.unlink(missing_ok=True)
        r = metrics_check(G_SLUG[0], str(out))
        return r is not None and r[0] != 0


G_SLUG = ["ufc_334"]
def metrics_event_file():
    """The event file the metrics file was built for (its "event" field)."""
    return str(REPO / "form/data/events" / (json.loads((FD / "embed_metrics" / f"{G_SLUG[0]}.json").read_text())["event"] + ".json"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", default="ufc_334"); ap.add_argument("--dir"); ap.add_argument("--negative", action="store_true")
    a = ap.parse_args(); D = Path(a.dir) if a.dir else REPO / "embeds" / a.slug; G = load_sources(a.slug)
    ok, n_rows, nb = run(D, G, a.slug); G_SLUG[0] = a.slug
    print(f"TOTAL: {ok}/{n_rows} numbers verified; {nb} mismatches/assertion failures")
    mc = metrics_check(a.slug) if (REPO / ".form_cache" / "ufc_fight_stats.csv").exists() else None
    if mc is None: print("METRICS FILE: not rechecked (no .form_cache CSVs on this machine)")
    else:
        print(f"METRICS FILE: {mc[1]}"); nb += mc[0] != 0
    good = nb == 0
    if a.negative: good = negative(D, G, a.slug) and good
    sys.exit(0 if good else 1)
