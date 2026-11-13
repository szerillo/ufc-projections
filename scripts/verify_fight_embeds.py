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
            elif rule == "bt":   # Block 59n: backtest numbers, from data/embeds/spot_tests.json (sha of the source results.json inside)
                v = json.loads((REPO / "data/embeds/spot_tests.json").read_text())[a["test"]][a["key"]]
                if "i" in a: v = v[a["i"]]
            elif rule == "rs_angle":   # Kirk round 17 D: Labs angle numbers from research.json
                v = {x_["id"]: x_ for x_ in json.loads((FD / "research.json").read_text())["angles"]}[a["id"]][a["key"]]
            elif rule == "dbstat":   # Kirk round 18: debut box CIs; the stats file must describe the published research.json set
                ds_ = json.loads((REPO / "data/embeds/debut_angle_stats.json").read_text()); rs_ = {x_["id"]: x_ for x_ in json.loads((FD / "research.json").read_text())["angles"]}[ds_["angle"]]
                if ds_["n"] != rs_["n"] or abs(ds_["act"] - rs_["act"]) > 1e-4 or abs(ds_["roi"] - rs_["roi_c"]) > 1e-4: raise ValueError("debut_angle_stats.json does not match research.json")
                lo_, hi_ = ds_["win_ci"]; se_ = (rs_["act"] * (1 - rs_["act"]) / rs_["n"]) ** 0.5   # win CI recomputed here from act and n
                if abs(lo_ - (rs_["act"] - 1.96 * se_)) > 2e-4 or abs(hi_ - (rs_["act"] + 1.96 * se_)) > 2e-4: raise ValueError("win CI does not follow from act and n")
                if abs(ds_["roi_ci"][0] - (ds_["roi"] - 1.96 * ds_["roi_se"])) > 2e-4 or abs(ds_["roi_ci"][1] - (ds_["roi"] + 1.96 * ds_["roi_se"])) > 2e-4: raise ValueError("ROI CI does not follow from roi and se")
                if a["key"].startswith("roi_ci_boot") and not (ds_[a["key"]][0] < ds_["roi"] < ds_[a["key"]][1]): raise ValueError("bootstrap ROI range does not contain the ROI")
                v = ds_[a["key"]]; v = v[a["i"]] if "i" in a else v
            elif rule == "angstat":   # Kirk round 21: southpaw box v2 = Labs' published set plus the listed corrected bouts
                as_ = json.loads((REPO / "data/embeds/angle_stats.json").read_text())[a["angle"]]; rs_ = {x_["id"]: x_ for x_ in json.loads((FD / "research.json").read_text())["angles"]}[a["angle"]]
                if as_["published_n"] != rs_["n"] or as_["n"] != rs_["n"] + len(as_["added"]): raise ValueError("angle_stats.json is not Labs' set plus the listed bouts")
                if abs(as_["act"] - as_["w"] / as_["n"]) > 1e-4: raise ValueError("act does not follow from w and n")
                se_ = (as_["act"] * (1 - as_["act"]) / as_["n"]) ** 0.5
                if abs(as_["win_ci"][0] - (as_["act"] - 1.96 * se_)) > 2e-4 or abs(as_["win_ci"][1] - (as_["act"] + 1.96 * se_)) > 2e-4: raise ValueError("win CI does not follow from act and n")
                if not (as_["roi_ci_boot_cards"][0] < as_["roi"] < as_["roi_ci_boot_cards"][1]): raise ValueError("bootstrap ROI range does not contain the ROI")
                sp_ = as_["split"]
                if sp_["favorite"]["n"] + sp_["underdog"]["n"] != as_["n"] or abs((sp_["favorite"]["roi"] * sp_["favorite"]["n"] + sp_["underdog"]["roi"] * sp_["underdog"]["n"]) / as_["n"] - as_["roi"]) > 2e-4: raise ValueError("favorite/underdog split does not add up")
                src_ = as_["split"][a["sub"]] if a.get("sub") else as_
                v = src_[a["key"]]; v = v[a["i"]] if "i" in a else v
            elif rule == "drift":   # Kirk round 24 E: drift box, recomputed from drift_stats.json and the line history file
                ds3_ = json.loads((REPO / "data/embeds/drift_stats.json").read_text()); mv3_ = ds3_["moves"]
                if len(mv3_) != ds3_["n"] or abs(sum(mv3_) / len(mv3_) * 100 - ds3_["mean_pts"]) > 0.006 or abs(sum(m_ > 0.005 for m_ in mv3_) / len(mv3_) - ds3_["shorter"]) > 3 / len(mv3_) or abs(sum(m_ < -0.005 for m_ in mv3_) / len(mv3_) - ds3_["longer"]) > 3 / len(mv3_): raise ValueError("drift_stats.json not self-consistent")   # stored moves are rounded; moves sitting on the 0.5-pt edge may flip
                rs3_ = json.loads((FD / "research.json").read_text())["drift"]
                if (ds3_["n"], ds3_["shorter"], ds3_["longer"]) != (rs3_["n"], rs3_["shorter"], rs3_["longer"]): raise ValueError("drift_stats.json is not Labs' drift set")
                LH3_ = json.loads((REPO / a["lh"]).read_text())["fights"]; lr3_ = LH3_[next(k_ for k_ in LH3_ if bout(*k_.split("|"), *a["pair"]))]; po3_, pc3_ = lr3_["open"]["p"], lr3_["current"]["p"]
                fo3_, fc3_ = (po3_, pc3_) if po3_ >= 0.5 else (1 - po3_, 1 - pc3_); m3_ = fc3_ - fo3_
                k3_ = sum(1 for x_ in mv3_ if (x_ <= m3_ + 1e-9 if m3_ < 0 else x_ >= m3_ - 1e-9))
                v = {"po": fo3_, "pc": fc3_, "mv_abs": abs(m3_) * 100, "n": ds3_["n"], "k": k3_, "share": k3_ / ds3_["n"], "shorter": ds3_["shorter"], "longer": ds3_["longer"]}[a["key"]]
            elif rule == "ufc_n":   # UFC fights before the card, from the fighter file (0 if no file: a debut)
                fx_ = next((json.loads(p_.read_text()) for p_ in (FD / "fighters").glob("*.json") if json.loads(p_.read_text()).get("name") == a["fighter"]), None)
                v = len([x_ for x_ in (fx_ or {}).get("fights", []) if x_["d"] < a["date"]])
            elif rule == "labs_wf":
                cw_ = json.loads((FD / "labs.json").read_text())["cardio"]; v = cw_["base_lost1_won3"] if a["key"] == "base_lost1_won3" else cw_["wf"][a["key"]]
            elif rule in ("lh_p", "lh_open_ml", "lh_drift_abs"):   # Block 59n: embed line history file, keyed by the pair
                LHd = json.loads((REPO / a["lh"]).read_text())["fights"]
                k_ = next(k_ for k_ in LHd if bout(*k_.split("|"), *a["pair"])); rec_ = LHd[k_]; first_ = is_(k_.split("|")[0], a["pair"][0])
                if rule == "lh_p":
                    v = rec_[a["at"]]["p"]; v = v if (a["side"] == "a") == first_ else 1 - v
                elif rule == "lh_open_ml":
                    v = rec_["open"]["m" + (a["side"] if first_ else ("b" if a["side"] == "a" else "a"))]
                else: v = abs(rec_["current"]["p"] - rec_["open"]["p"])
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
        # Block 59n (Kirk round 6): Spot to watch recomputed (Round6_PREREG.md A); the page must show exactly these, in order
        EMv = json.loads((FD / "embed_metrics" / f"{G['SLUG']}.json").read_text())["fighters"]
        pa_, pb_ = (EMv.get(x_, {}) for x_ in reg["pair"]); want = []
        STt = json.loads((REPO / "data/embeds/spot_tests.json").read_text())
        def td_(r): t = r.get("target_diff") or {}; return None if t.get("head") is None else t["head"] + t["body"] + t["leg"]
        ok4 = pa_.get("ufc_fights", 0) >= 4 and pb_.get("ufc_fights", 0) >= 4
        if ok4 and td_(pa_) is not None and td_(pb_) is not None and abs(td_(pa_) - td_(pb_)) >= STt["T1"]["cut"]: want.append(("T1", reg["pair"][0] if td_(pa_) > td_(pb_) else reg["pair"][1]))
        ra_, rb_ = (pa_.get("rounds") or [{}] * 3)[2], (pb_.get("rounds") or [{}] * 3)[2]
        if ok4 and ra_.get("diff_pm") is not None and rb_.get("diff_pm") is not None and ra_.get("fights", 0) >= 3 and rb_.get("fights", 0) >= 3 and abs(ra_["diff_pm"] - rb_["diff_pm"]) >= STt["T17"]["cut"]:
            want.append(("T17", reg["pair"][0] if ra_["diff_pm"] > rb_["diff_pm"] else reg["pair"][1]))
        cu_ = {x_.get("s"): x_ for u_ in json.loads((FD / "labs.json").read_text())["cardio"].get("upcoming", []) for x_ in (u_["a"], u_["b"])}
        sl_ = {is_(fight["a"]["name"], reg["pair"][0]) and "a" or "b": None}
        ca_, cb_ = (cu_.get(fight[s_].get("slug")) for s_ in (("a", "b") if is_(fight["a"]["name"], reg["pair"][0]) else ("b", "a")))
        if ca_ and cb_ and ca_.get("sw") is not None and cb_.get("sw") is not None and ca_["n"] >= 3 and cb_["n"] >= 3 and abs(ca_["sw"] - cb_["sw"]) >= 3:
            want.append(("CB", reg["pair"][0] if ca_["sw"] > cb_["sw"] else reg["pair"][1]))
        got = re.findall(r'<li data-spot="(T1|T17|CB)">(?:If )?<b>([^<]+)</b>', page)
        if [(k_, g_.split()[-1]) for k_, g_ in got] != [(k_, w_.split()[-1]) for k_, w_ in want]: bad.append(("spot", "to watch", f"page {got} vs recomputed {want}"))
        if any(k_ == "T1" for k_, _ in want) and "Never confirmed on new cards" not in page: bad.append(("spot", "T1 label", "T1 note must say it was never confirmed on new cards"))
        # Block 59o: round-trend chart. Present iff both fighters have 2+ of R1-R3 with 1+ fight; the plotted y of every point
        # must equal the metrics file's rounds.N.diff_pm on the chart's own scale (recomputed from the SVG coordinates)
        tp_ = [[(i_, rr_["diff_pm"]) for i_, rr_ in enumerate((x_.get("rounds") or [])[:3]) if (rr_ or {}).get("fights", 0) >= 1 and rr_.get("diff_pm") is not None] for x_ in (pa_, pb_)]
        TF_ = 15.0   # Round_Trend_Floor_PREREG sha 55e79839
        okm_ = [[i_ for i_, rr_ in enumerate((x_.get("rounds") or [])[:3]) if (rr_ or {}).get("fights", 0) >= 1 and (rr_.get("mins") or 0) >= TF_] for x_ in (pa_, pb_)]
        want_tr = all(len(t_) >= 2 for t_ in okm_)
        if want_tr:
            nthin_ = sum(1 for t_, o_ in zip(tp_, okm_) for i_, _ in t_ if i_ not in o_)
            if page.split('data-part="trend"')[1].split("</svg>")[0].count('class="thin"') != nthin_: bad.append(("trend", "floor", f"hollow dots != {nthin_} rounds under {TF_} min"))
        if want_tr:   # Kirk round 9 call 1: a joined round within 1 minute of the floor carries the thin-sample note
            want_near = sorted(f'{n_.split()[-1]}: R{i_ + 1}' for n_, x_ in zip(reg["pair"], (pa_, pb_)) for i_, rr_ in enumerate((x_.get("rounds") or [])[:3]) if (rr_ or {}).get("fights", 0) >= 1 and TF_ <= (rr_.get("mins") or 0) < TF_ + 1)
            got_near = sorted(re.findall(r'([A-Za-z\-\']+): (R\d) sits right at the 15-minute floor', page))
            if [f"{a_}: {b_}" for a_, b_ in got_near] != want_near: bad.append(("trend", "near floor", f"note {got_near} vs {want_near}"))
        if (bool(re.search(r'data-spot="', page)) and want_tr) != ("See round trend" in page): bad.append(("spot", "pointer", "'See round trend' pointer must show exactly when both Spot to watch and the chart show"))
        if want_tr != ('data-part="trend"' in page): bad.append(("trend", "presence", f"page {'data-part=\"trend\"' in page} vs recomputed {want_tr}"))
        if want_tr:
            vals_ = [v_ for t_ in tp_ for _, v_ in t_]; lo_, hi_ = min(vals_ + [0]), max(vals_ + [0]); pad_ = max(0.5, (hi_ - lo_) * 0.12); lo_ -= pad_; hi_ += pad_
            ys_ = [float(y_) for y_ in re.findall(r'<circle (?:class="thin" )?cx="[\d.]+" cy="([\d.]+)" r="4"', page.split('data-part="trend"')[1].split("</svg>")[0])]
            want_ys = [round(12 + (hi_ - v_) / (hi_ - lo_) * (150 - 12 - 24), 1) for t_ in tp_ for _, v_ in t_]
            if sorted(ys_) != sorted(want_ys): bad.append(("trend", "points", f"plotted y {ys_} vs recomputed {want_ys}"))
        if re.search(r'class="(flip|ang)"|Live guide|Striking angle', page): bad.append(("spot", "old", "live guide, flip flag or angle box still on the page"))
        # Block 59n: edge colour rule (coloured only at |shown edge| >= 2.0) and the Listed-price check (flagged = neutral + label)
        LHall = json.loads((G.get("LH_PATH") or REPO / f"data/embeds/line_history_{G['SLUG']}.json").read_text())["fights"]
        lk_ = next((k_ for k_ in LHall if bout(*k_.split("|"), *reg["pair"])), None); lrec = LHall.get(lk_) if lk_ else {}
        unver = set()
        for sd_, c_ in (lrec.get("listed") or {}).items():
            if not c_["ok"]: unver.add(lk_.split("|")[0 if sd_ == "a" else 1])
        for m_ in re.finditer(r'<span class="ech (pos|neg|flat)"><span data-id="(v\d+)">([^<]*)</span></span>(<span class="unv">price unverified</span>)?', page):
            cls_, id_, t_, uv_ = m_.groups(); e_ = float(t_.replace("%", ""))
            r_ = next(r_ for r_ in reg["rows"] if r_["id"] == id_)
            is_ml = r_["desc"].startswith("Edge ML "); who = r_["desc"].replace("Edge ML ", "")
            want_uv = is_ml and any(is_(who, u_) for u_ in unver)
            want_cls = "flat" if want_uv else "pos" if e_ >= 2.0 else "neg" if e_ <= -2.0 else "flat"
            if cls_ != want_cls: bad.append(("edge", "colour", f"{r_['desc']} {t_} is {cls_}, rule says {want_cls}"))
            if bool(uv_) != want_uv: bad.append(("edge", "unverified", f"{r_['desc']}: 'price unverified' {'missing' if want_uv else 'not expected'}"))
        # Block 59n: no book or offshore name anywhere on the page
        for bk_ in ("Pinnacle", "BetOnline", "LowVig", "Bovada", "DraftKings", "FanDuel", "BetMGM", "Caesars", "BetRivers", "Circa", "Kalshi", "Polymarket", "Novig"):
            if bk_.lower() in text.lower(): bad.append(("page", "book name", f"{bk_} named on the page"))
        # Block 59j: feed sanity, recomputed here: a broken method or distance market must show "price unavailable" and no number
        cz = lambda s_: sq(ALIAS.get(sq(s_), s_))
        of_ = next((x for x in G["ODDS"]["fights"] if {cz(x["fighter_a"]["name"]), cz(x["fighter_b"]["name"])} == {cz(reg["pair"][0]), cz(reg["pair"][1])}), None)
        if of_:
            ip = lambda m: 100 / (m + 100) if m > 0 else -m / (-m + 100)
            mv_ = of_["markets"].get("method_of_victory") or []
            nm_ = [of_["fighter_a"]["name"], of_["fighter_b"]["name"]]   # rule v3: only the bout's own rows + draw
            ex_ = [x for x in mv_ if x["label"] == "Draw" or any(x["label"] == f"{n_} {m_}" for n_ in nm_ for m_ in ("KO/TKO/DQ", "Submission", "Points"))]
            tt_ = sum(ip(x["books"]["consensus"]["cost"]) for x in ex_)
            mbad = (tt_ > 1.40 or (len(ex_) >= 7 and tt_ < 1.0) or any(x["label"] == "Draw" and x["books"]["consensus"]["cost"] < 1000 for x in ex_)
                    or sum(1 for x in ex_ if x.get("opening_cost") == 100) >= 2)
            dbad = {x["label"] for x in (of_["markets"].get("fight_distance") or [])} != {"Yes", "No"}
            used = {r_["args"].get("market") for r_ in reg["rows"] if r_["rule"] in ("bp", "bp_imp", "bp_imp_sum")}
            if mbad and "method_of_victory" in used: bad.append(("feed", "method", "number shown from a market that fails the sanity rule"))
            if dbad and "fight_distance" in used: bad.append(("feed", "distance", "number shown from a market that fails the sanity rule"))
            npu = page.count(">price unavailable<"); want_pu = (8 if mbad else 0) + (2 if dbad else 0)
            if npu != want_pu: bad.append(("feed", "label", f"{npu} 'price unavailable' cells, want {want_pu}"))
        # Block 59k: the line move must carry its own "as of" time, equal to the event file's last snapshot
        f_ev = next((x for x in EV[reg["event"]]["fights"] if {sq(ALIAS.get(sq(x["a"]["name"]), x["a"]["name"])), sq(ALIAS.get(sq(x["b"]["name"]), x["b"]["name"]))} == {sq(ALIAS.get(sq(p_), p_)) for p_ in reg["pair"]}), None) if reg.get("event") in EV else None
        if lrec.get("open") and lrec.get("current"):
            want_as = lrec["current"]["t"][5:16].replace("-", "/").replace("T", " ")
            if f"line data as of {want_as} UTC" not in page: bad.append(("move", "as-of", f"line move missing 'as of {want_as} UTC'"))
            want_q = abs(lrec["current"]["p"] - lrec["open"]["p"]) < 0.01   # Kirk round 11 D: one-line "Steady" under 1 pt, bar otherwise
            # Sean Nov 13: the dated price path (its opener / now row) replaced the opener-to-now bar
            if want_q != ('class="mvrow mvq"' in page) or want_q == ('class="mvends"' in page): bad.append(("move", "steady", f"one-line form {'expected' if want_q else 'not expected'}"))
        elif lrec.get("open"):
            if "current line not available" not in page: bad.append(("move", "opener only", "opener-only bout must say 'current line not available'"))
        # Block 59k (Kirk check 5): cross-source side check. The bp rule trusts the builder's choice of feed row for each
        # fighter; a wrong-side match would pass it. The shown moneyline split must agree with the line-history close
        # (a different feed, matched by different code) within 8 points; a swap shows as about 20+.
        if lrec.get("current"):
            mk_ = {r_["args"].get("label"): r_ for r_ in reg["rows"] if r_["desc"].startswith("Market ML ")}
            shown = {r_["desc"].replace("Market ML ", ""): float(re.sub(r"[^0-9+-]", "", r_["text"])) for r_ in reg["rows"] if r_["desc"].startswith("Market ML ")}
            if len(shown) == 2:
                ia = {k: (100 / (v + 100) if v > 0 else -v / (-v + 100)) for k, v in shown.items()}
                first = reg["pair"][0]
                if first in ia:
                    nv = ia[first] / sum(ia.values())
                    lh = lrec["current"]["p"] if is_(lk_.split("|")[0], first) else 1 - lrec["current"]["p"]
                    # side check v2 (claude/Side_Check_v2_PREREG_2026-11-12.md): flag when the split sits 4+ pts closer to the
                    # mirror of the line-history close than to the close itself; bouts within 4 pts of 50% cannot be told
                    if abs(lh - 0.5) < 0.04: G.setdefault("SIDE_UNCHECKED", []).append(first)
                    elif abs(nv - lh) - abs(nv - (1 - lh)) > 0.04: bad.append(("market", "side", f"{first}: market split {nv:.3f} is nearer the mirror of the line history {lh:.3f}, likely side swap"))
        # Block 59n (Kirk round 6, 4a): one "Data as of" line with the sources' own times and nothing else
        st_ = re.search(r'<div class="stamps">(.*?)</div>', page)
        sh_ = lambda t_: t_[5:16].replace("-", "/").replace("T", " ") + " UTC"
        if not st_: bad.append(("footer", "stamps", "no Data as of line"))
        else:
            exp_pub = json.loads(Path(REPO / reg["proj_file"]).read_text()).get("published_at") if reg.get("proj_file", "").endswith("projections.json") else None
            lm_ = sh_(lrec["current"]["t"]) if lrec.get("current") and lrec.get("open") else (sh_(lrec["open"]["t"]) + " (opener only)" if lrec.get("open") else "n/a")
            want_line = f'Data as of: sheet {sh_(exp_pub) if exp_pub else "n/a"} · odds {sh_(G["ODDS"]["updated_at"])} · line move {lm_}'
            want_line += ' · <a href="https://szerillo.github.io/ufc-projections/form/corrections.html" target="_blank" rel="noopener">Corrections</a>'
            if not (REPO / "form/corrections.html").exists(): bad.append(("footer", "corrections", "form/corrections.html missing"))
            if H.unescape(st_.group(1)) != want_line: bad.append(("footer", "stamps", f"{H.unescape(st_.group(1))!r} != {want_line!r}"))
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
        lp_ = next((x for x in (G["PUB"].get("line_pending") or []) if bout(x.get("dog", ""), x.get("fav", ""), A, B)), None)
        if reg.get("proj_src") == "publish" or src_attr == "publish": bad.append(("proj", "source", "embed claims the export but the export has no row for this bout"))
        if lp_:   # Kirk round 34: Line pending in the live file -> the card page's state, no sheet numbers of any vintage
            if reg.get("proj_src") != "line_pending": bad.append(("pending", "source", f"bout is Line pending in {G['PUBF']} but the embed says {reg.get('proj_src')}"))
            if reg.get("proj_file") != G["PUBF"]: bad.append(("pending", "file", f"{reg.get('proj_file')} != {G['PUBF']}"))
            sheet_rows = [r["id"] for r in reg["rows"] if r["rule"] in ("pub_win", "pub_meth", "pub", "pub_ml", "pub_ml_imp", "evp_sum")]
            if sean_ids or sheet_rows: bad.append(("pending", "numbers", f"Line pending bout shows sheet numbers: {sean_ids or sheet_rows}"))
            if 'data-state="pending"' not in page or "did not match this bout, so no numbers are shown until it does." not in page:
                bad.append(("pending", "state", "embed does not show the card page's Line pending note"))
        else:
            if reg.get("proj_src") == "line_pending" or 'data-state="pending"' in page: bad.append(("pending", "source", "embed shows Line pending but the live file does not hold this bout back"))
            if not sean_rules <= {"evp_sum"}: bad.append(("proj", "Sean rules", f"fallback cells not from the event file: {sean_rules}"))
    # Kirk round 34: every embed carries the pending guard (a later publish that holds this bout back hides the built numbers)
    if 'id="sean-proj"' not in page or "getElementById('sean-proj')" not in page or "line_pending" not in page.split("getElementById('sean-proj')", 1)[-1]:
        bad.append(("pending", "guard", "pending guard script or #sean-proj block missing"))
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

def hold_check(D, G, slug, quiet=False):
    """Kirk round 28 (call 1, A, D): a held number must be gone from every place the site shows it. The holds file names
    what is held; the pulled values live only in the audit record (audits/round28/hold_values.json), which this check
    reads to search the event file, the embeds, embed.html, index.html, the card's data files and the rendered pages
    (card, held fight pages, sheet, held fighters' pages, compare, Labs size tab) for any leftover copy."""
    import importlib.util
    bad = []
    hp = FD / "form_holds.json"
    if not hp.exists(): return 0
    sp_ = importlib.util.spec_from_file_location("form_holds", REPO / "scripts/form_holds.py"); FH = importlib.util.module_from_spec(sp_); sp_.loader.exec_module(FH)
    bad += [("hold", "data", x) for x in FH.problems()]
    H_ = json.loads(hp.read_text()); recp = REPO / "audits/round28/hold_values.json"
    rec = json.loads(recp.read_text()) if recp.exists() else {"form_line": {}, "bio": {}}
    evs = H_["form_line"]["events"]; cj = json.loads((D / "card.json").read_text()); evslug = Path(cj["event"]).stem
    held_n = evs.get(evslug, [])
    toks = []
    for n in held_n:
        r_ = rec["form_line"].get(f"{evslug}#{n}")
        if not r_: bad.append(("hold", f"fight {n}", "no audit record of the held value (cannot search for leftovers)")); continue
        p_ = r_["p"]; toks += [f"{p_:.4f}", f"{1 - p_:.4f}", f"{p_ * 100:.1f}%", f"{(1 - p_) * 100:.1f}%", f"{p_ * 100:.0f}%", f"{(1 - p_) * 100:.0f}%", f"{p_ * 100:.2f}", f"{(1 - p_) * 100:.2f}"]
    files = [REPO / cj["event"], REPO / "embed.html", REPO / "index.html", FD / "reach_notes.json", FD / "form_holds.json",
             FD / "embed_metrics" / f"{slug}.json"] + sorted(D.glob("*.html")) + sorted(D.glob("*.json")) + sorted((REPO / "data/embeds").glob(f"*{slug}*"))
    for fp in files:
        if not fp.exists(): continue
        t_ = fp.read_text(encoding="utf-8", errors="ignore")
        # 4-decimal copies anywhere in these files; percent copies only in the held fight's own embed (a "63.3%" elsewhere can be another stat)
        own = any(fp.name == f"fight_{n:02d}.html" for n in held_n)
        for tk in toks:
            if (tk in t_) if (own or tk.startswith("0.")) else (tk.endswith("%") and re.search(r"Form[^<>]{0,40}?(?<![\d.])" + re.escape(tk), t_)): bad.append(("hold", str(fp.relative_to(REPO)) if str(fp).startswith(str(REPO)) else fp.name, f"held Form Line value {tk} still present"))
    # held bio fields: the pulled value must not appear next to the fighter anywhere it is shown
    hts = {}
    for k_, v_ in rec.get("bio", {}).items():
        sl, key = k_.split("."); m_ = re.match(r"(\d+)'\s*(\d+)", str(v_))
        if m_: hts[sl] = [f"{m_.group(1)}'{m_.group(2)}", f"{m_.group(1)}' {m_.group(2)}", f"{m_.group(1)}&#x27;{m_.group(2)}", f"{m_.group(1)}&#39;{m_.group(2)}"]
    ev = json.loads((REPO / cj["event"]).read_text())
    for sl, tk_ in hts.items():
        f_ = next((f for f in ev["fights"] if sl in (f["a"].get("slug"), f["b"].get("slug"))), None)
        if f_ is None: continue
        for fp in D.glob("fight_*.registry.json"):
            r_ = json.loads(fp.read_text())
            if bout(f_["a"]["name"], f_["b"]["name"], *r_["pair"]):
                t_ = (D / fp.name.replace(".registry.json", ".html")).read_text()
                if any(x in t_ for x in tk_): bad.append(("hold", fp.name.replace(".registry.json", ".html"), f"held height of {sl} still shown"))
    # rendered pages
    routes = [f"#/card/{evslug}", f"#/sheet/{evslug}", "#/labs/size"] + [f"#/fight/{evslug}/{n}" for n in held_n]
    for sl in hts:
        f_ = next((f for f in ev["fights"] if sl in (f["a"].get("slug"), f["b"].get("slug"))), None)
        routes += [f"#/fighter/{sl}"] + ([f"#/fight/{evslug}/{f_['n']}", f"#/compare/{f_['a']['slug']}/{f_['b']['slug']}"] if f_ else [])
    rr = subprocess.run(["node", str(REPO / "scripts/site_render.js")] + routes, capture_output=True, text=True)
    if rr.returncode != 0: bad.append(("hold", "render", rr.stderr.strip()[-200:]))
    else:
        P_ = json.loads(rr.stdout)
        for rt, h_ in P_.items():   # 4-decimal copies anywhere on a page
            for tk in toks:   # 4-decimal copies anywhere; percent copies when a "Form" label sits just before them
                if (tk in h_) if tk.startswith("0.") else (tk.endswith("%") and re.search(r"Form[^<>]{0,40}?(?<![\d.])" + re.escape(tk), h_)): bad.append(("hold", rt, f"held Form Line value {tk} shown"))
        card = P_[f"#/card/{evslug}"]; sheet = P_[f"#/sheet/{evslug}"]
        for n in held_n:
            m_ = re.search(r'href="#/fight/' + re.escape(evslug) + "/" + str(n) + r'".*?</tr>', card, re.S) or re.search(r'data-href="#/fight/' + re.escape(evslug) + "/" + str(n) + r'".*?</tr>', card, re.S)
            row = m_.group(0) if m_ else ""
            if not row or "held<sup>" not in row: bad.append(("hold", "card page", f"fight {n} Form cell not held"))
            seg = sheet.split(f'href="#/fight/{evslug}/{n}"', 1)[1].split('<div class="sub">', 1)[-1].split("</div>", 1)[0] if f'href="#/fight/{evslug}/{n}"' in sheet else ""   # the fight's summary line
            if not seg or H_["form_line"]["text"] not in seg or re.search(r"· Form \d+%", seg): bad.append(("hold", "sheet", f"fight {n} Form Line not held"))
            fp_ = P_[f"#/fight/{evslug}/{n}"]
            fseg = fp_.split("<h3>Form numbers</h3>", 1)[1].split("</table>", 1)[0] if "<h3>Form numbers</h3>" in fp_ else ""
            pct_ = [t for t in toks if t.endswith("%")] + [f"{float(t[:-1]):.0f}%" for t in toks if t.endswith("%")]
            for zone, seg_ in (("fight page Form numbers", fseg), ("card page row", row), ("sheet line", seg)):
                for tk in pct_:
                    if re.search(r"(?<![\d.])" + re.escape(tk), seg_): bad.append(("hold", zone, f"fight {n}: held value {tk} shown"))
            if "Form Line 5+ pts" in fp_ or "Form Line 10+ pts" in fp_ or "Form Line likes" in fp_: bad.append(("hold", f"fight {n} page", "Form Line angle still in play"))
            if H_["form_line"]["text"] not in fp_: bad.append(("hold", f"fight {n} page", "held text missing"))
        for sl, tk_ in hts.items():
            for rt, h_ in P_.items():
                if rt.startswith("#/labs") or rt.startswith("#/card"): continue
                if rt.startswith("#/sheet"):
                    nm = next((f[s]["name"] for f in ev["fights"] for s in "ab" if f[s].get("slug") == sl), None)
                    h_ = h_.split(f"<b>{H.escape(nm)}</b>", 1)[1].split("<br>", 1)[0].split("</div>", 1)[0] if nm and f"<b>{H.escape(nm)}</b>" in h_ else ""
                if any(x in h_ for x in tk_): bad.append(("hold", rt, f"held height of {sl} shown"))
        lab = P_["#/labs/size"]
        for sec, labels in H_["labs"]["rows"].items():
            for lb in labels:
                if not re.search(r"<td class=\"l b\">" + re.escape(lb) + r"</td><td colspan=\"6\" class=\"l dim\">" + re.escape(H_["labs"]["text"]), H.unescape(lab)): bad.append(("hold", "labs size", f"{sec} {lb} not held on the page"))
    bad = list(dict.fromkeys(bad))
    if bad or not quiet: print(f"holds: {len(bad)} failures ({len(toks)} Form Line tokens, {sum(len(v) for v in hts.values())} height tokens, {len(routes)} pages rendered)")
    for b in bad: print("   ", *b)
    return len(bad)

def run(D, G, slug, quiet=False):
    tot_ok = tot_bad = n_rows = 0
    for f in sorted(p.name for p in D.glob("fight_*.html")):
        ok, nb = check(D, f, G); tot_ok += ok; tot_bad += nb
        n_rows += len(json.load(open(D / f.replace(".html", ".registry.json")))["rows"])
    lp_all = G["PUB"].get("line_pending") or []
    if lp_all or not quiet:
        print(f"LINE PENDING in {G['PUBF']}: {len(lp_all)} bout(s), sheet-number checks excluded" + (": " + "; ".join(f"{x['dog']} vs {x['fav']}" for x in lp_all) if lp_all else ""))
    tot_bad += card_check(D, G, slug)
    tot_bad += lh_recheck(G, slug, quiet)
    tot_bad += spot_pin(G)
    tot_bad += hold_check(D, G, slug, quiet)   # Kirk round 28
    lk_ = subprocess.run([sys.executable, "-I", str(REPO / "scripts/embed_locks.py"), "check", "--slug", slug], capture_output=True, text=True)
    if lk_.returncode != 0: print(lk_.stdout.strip()); tot_bad += 1
    elif not quiet: print(lk_.stdout.strip().splitlines()[-1])
    return tot_ok, n_rows, tot_bad

# Kirk round 8 D: the builder and this checker both read data/embeds/spot_tests.json, so an edit there moved the page and the
# check together and nothing caught it. The file is a frozen copy of the backtest's out/results.json (sha d32f35bf...), so its
# own hash is pinned here; changing a backtest number now needs a deliberate edit of this line.
SPOT_TESTS_SHA = "090bf40ed0b292db88a7db2deac0b685ddf78377026b421dbbf2b703b63cbb56"
def spot_pin(G):
    import hashlib
    b_ = (REPO / "data/embeds/spot_tests.json").read_bytes() if not G.get("ST_OVERRIDE") else G["ST_OVERRIDE"]
    if hashlib.sha256(b_).hexdigest() != SPOT_TESTS_SHA: print("  SPOT TESTS: data/embeds/spot_tests.json differs from the pinned backtest copy"); return 1
    return 0

def lh_recheck(G, slug, quiet=False):
    """Block 59n: recompute the embed line history and the Listed-price check from the raw archive with this file's own
    code (Round6_PREREG.md C and D), and compare with data/embeds/line_history_<slug>.json. Skipped (with a note) without
    the archive cache. Also: no offshore book may sit in any current line."""
    import gzip, glob, statistics, datetime as dt_
    LHp = G.get("LH_PATH") or REPO / f"data/embeds/line_history_{slug}.json"; LHd = json.loads(LHp.read_text())
    if G.get("LH_OVERRIDE"): LHd = G["LH_OVERRIDE"]
    REG_ = {"draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "circasports"}
    LIST_ = {"pinnacle", "draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "betonlineag", "lowvig", "bovada", "circasports"}
    nb_ = 0
    for k_, r_ in LHd["fights"].items():
        if r_.get("current") and set(r_["current"]["books"]) - REG_ and not (r_.get("current_source") == "kalshi_fallback" and r_["current"]["books"] == ["kalshi"]):
            print(f"  LH {k_}: offshore book in the current line"); nb_ += 1
    cache = G.get("ARCHIVE") or (REPO / ".form_cache")
    if not (cache / "oddsapi" / "compact" / "mma.jsonl.gz").exists():
        print("LINE HISTORY RECHECK: skipped (no archive cache)"); return nb_
    snaps = {}
    def add(eid, t, st, h, a, books):
        snaps.setdefault(eid, []).append((t, st, h, a, books))
    with gzip.open(cache / "oddsapi" / "compact" / "mma.jsonl.gz", "rt") as fh:
        for line in fh:
            r = json.loads(line); add(r["id"], r["t"], r["start"], r["home"], r["away"], {b: m["h2h"] for b, m in r["books"].items() if m.get("h2h")})
    for fp in sorted(glob.glob(str(cache / "oddsapi" / "mma" / "*.json.gz"))):
        try: d = json.load(gzip.open(fp))
        except Exception: continue
        for ev in d.get("data", []):
            bk = {}
            for bm in ev.get("bookmakers", []):
                for m in bm.get("markets", []):
                    px = {o["name"]: o["price"] for o in m.get("outcomes", [])}
                    if m["key"] == "h2h" and ev["home_team"] in px and ev["away_team"] in px: bk[bm["key"]] = [px[ev["home_team"]], px[ev["away_team"]]]
            if bk: add(ev["id"], d.get("timestamp"), ev["commence_time"], ev["home_team"], ev["away_team"], bk)
    lp = cache / "mma" / "oddsapi_live.jsonl"
    if lp.exists():
        for line in open(lp):
            try: r = json.loads(line)
            except Exception: continue
            bk = {b: v for b, v in (r.get("books") or {}).items() if isinstance(v, list) and len(v) == 2}
            if bk: add(r["id"], r["t"], r["start"], r["home"], r["away"], bk)
    T = lambda x: dt_.datetime.fromisoformat(x.replace("Z", "+00:00"))
    for k_, r_ in LHd["fights"].items():
        eid = r_.get("event_id")
        if not eid or eid not in snaps: continue
        an_ = k_.split("|")[0]; ss = sorted(snaps[eid], key=lambda x: x[0]); start = ss[-1][1]; pre = [x for x in ss if x[0] <= start] or ss
        def orient(x):
            t, st, h, a, books = x
            sc = lambda y: 2 if is_(an_, y) else difflib.SequenceMatcher(None, "".join(sorted(sq(an_))), "".join(sorted(sq(y)))).ratio()
            amh = sc(h) >= sc(a)
            return {b: ((v[0], v[1]) if amh else (v[1], v[0])) for b, v in books.items() if b in LIST_}
        rows = [(x[0], orient(x)) for x in pre]; rows = [x for x in rows if x[1]]
        nv_ = lambda da, db: (1 / da) / (1 / da + 1 / db)
        op = next((x for x in rows if len(x[1]) >= 3), None)
        regs = [x for x in rows if set(x[1]) & REG_ and (op is None or x[0] >= op[0])]
        cur = regs[-1] if regs and (T(rows[-1][0]) - T(regs[-1][0])).total_seconds() <= 6 * 3600 else None
        def med(x, bks): return round(statistics.median(nv_(*x[1][b]) for b in bks), 3)
        want_o = (op[0], med(op, list(op[1]))) if op else None
        want_c = (cur[0], med(cur, [b for b in cur[1] if b in REG_])) if cur else None
        got_o = (r_["open"]["t"], r_["open"]["p"]) if r_.get("open") else None
        got_c = (r_["current"]["t"], r_["current"]["p"]) if r_.get("current") and r_.get("current_source") != "kalshi_fallback" else None
        if r_.get("current_source") == "kalshi_fallback" and want_c is not None: print(f"  LH {k_}: Kalshi fallback used although a regulated price exists"); nb_ += 1
        if got_o != want_o: print(f"  LH {k_}: opener {got_o} vs recomputed {want_o}"); nb_ += 1
        if got_c != want_c: print(f"  LH {k_}: current {got_c} vs recomputed {want_c}"); nb_ += 1
        if r_.get("listed"):
            hi = T(LHd["export_published_at"]); lo = hi - dt_.timedelta(hours=24)
            am_ = lambda d: round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))
            dec = lambda m: 1 + (m / 100 if m > 0 else 100 / -m)
            for sd_, i_ in (("a", 0), ("b", 1)):
                L_ = r_["listed"][sd_]["listed"]; ok_ = False
                for t, pr in rows:
                    if not (lo <= T(t) <= hi): continue
                    for b, v in pr.items():
                        if b in REG_:
                            x = am_(v[i_])
                            if dec(x) >= dec(L_) or ((x > 0) == (L_ > 0) and abs(x - L_) <= 2): ok_ = True
                if ok_ != r_["listed"][sd_]["ok"]: print(f"  LISTED {k_} {sd_} {L_}: file ok={r_['listed'][sd_]['ok']}, recomputed {ok_}"); nb_ += 1
    # Kirk round 10 A: the event file's odds block (the public fight page's open/close) is rewritten every Friday and is not
    # locked, so it is recomputed here from the raw archive with this file's own matching (bout found by names and date, not
    # by the builder's event id) and its own summary (all listed books, no-vig median per snapshot, lone-book opener dropped).
    evp_ = next((REPO / "form/data/events" / f'{u["slug"]}.json' for u in json.loads((FD / "index.json").read_text()).get("upcoming", [])
                 if json.loads((FD / "events" / f'{u["slug"]}.json').read_text()).get("bp_file") == f"data/{slug}_odds.json"), None)
    nev_ = 0
    if evp_:
        EVd = json.loads(evp_.read_text()); d0 = date.fromisoformat(EVd["date"])
        msc = lambda x, y: 2 if is_(x, y) else difflib.SequenceMatcher(None, "".join(sorted(sq(x))), "".join(sorted(sq(y)))).ratio()
        heads = {e: (v[-1][2], v[-1][3], v[-1][1]) for e, v in snaps.items()}
        for f in EVd["fights"]:
            an_, bn_ = f["a"]["name"], f["b"]["name"]
            # Date_Window_PREREG (round 12): archive start date minus card date was -1, 0 or +1 on all 2,302 past bouts
            cands = [e for e, (h, w, st) in heads.items() if -1 <= (date.fromisoformat(st[:10]) - d0).days <= 1
                     and max(min(msc(an_, h), msc(bn_, w)), min(msc(an_, w), msc(bn_, h))) >= 0.85]
            o_ = f.get("odds")
            if not cands:
                if o_: print(f"  EVENT ODDS {an_} vs {bn_}: odds block present but no archive bout found"); nev_ += 1
                continue
            e = max(cands, key=lambda e: len(snaps[e])); ss = sorted(snaps[e], key=lambda x: x[0]); start = ss[-1][1]
            pre = [x for x in ss if x[0] <= start] or ss
            pts = []; rpts = []
            for t, st, h, w, books in pre:
                amh = msc(an_, h) >= msc(an_, w)
                prb = {b: ((v[0], v[1]) if amh else (v[1], v[0])) for b, v in books.items() if b in LIST_}
                pr = list(prb.values()); nv = [(1 / x) / (1 / x + 1 / y) for x, y in pr]
                if nv: pts.append((t, statistics.median(nv), len(nv), statistics.median(x for x, _ in pr), statistics.median(y for _, y in pr)))
                rg = [v for b, v in prb.items() if b in REG_]
                if rg: rpts.append((t, statistics.median((1 / x) / (1 / x + 1 / y) for x, y in rg), len(rg), statistics.median(x for x, _ in rg), statistics.median(y for _, y in rg)))
            while len(pts) > 2 and pts[0][2] <= 1 and abs(pts[0][1] - pts[1][1]) > 0.12: pts.pop(0)
            if not pts: continue
            if not o_: print(f"  EVENT ODDS {an_} vs {bn_}: archive has the bout, the event file has no odds block"); nev_ += 1; continue
            # Consensus_US_PREREG (round 12): opener from every listed book; current/close from US-regulated books only, none if none
            rpts = [x for x in rpts if x[0] >= pts[0][0]]
            if set(o_.get("books") or {}) - REG_: print(f"  EVENT ODDS {an_} vs {bn_}: offshore book in the published book list"); nev_ += 1
            if not rpts:
                if o_.get("close"): print(f"  EVENT ODDS {an_} vs {bn_}: a close is published but no US-regulated price exists"); nev_ += 1
                continue
            if not o_.get("close"): print(f"  EVENT ODDS {an_} vs {bn_}: US-regulated price exists but no close is published"); nev_ += 1; continue
            for k, pt in (("open", pts[0]), ("close", rpts[-1])):
                amx = lambda d: round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))
                if o_[k]["t"][:19] != pt[0][:19] or abs(o_[k]["p"] - pt[1]) > 0.0006 or abs(o_[k]["ma"] - amx(pt[3])) > 1 or abs(o_[k]["mb"] - amx(pt[4])) > 1:
                    print(f"  EVENT ODDS {an_} vs {bn_}: {k} {o_[k]['t'][:16]} {o_[k]['p']} vs recomputed {pt[0][:16]} {pt[1]:.4f}"); nev_ += 1
        if not quiet: print(f"EVENT ODDS RECHECK: {len(EVd['fights'])} bouts, {nev_} mismatches")
    nb_ += nev_
    if not quiet: print(f"LINE HISTORY RECHECK: {len(LHd['fights'])} bouts, {nb_} mismatches")
    return nb_

def negative(D, G, slug):
    """plant one error per copy; each must make the run fail."""
    import copy, contextlib, io
    def plant_text(name, fn):
        def go(T, G_):
            p = T / name; s_ = p.read_text(); s2 = fn(s_); assert s2 != s_, "plant did not change the file"; p.write_text(s2)
        return go
    def plant_any(fn):   # Kirk round 22: data-dependent plants pick the first fight page where they apply (fresh data moves targets)
        def go(T, G_):
            for p in sorted(T.glob("fight_*.html")):
                s_ = p.read_text(); s2 = fn(s_)
                if s2 != s_: p.write_text(s2); return
            raise AssertionError("plant applied to no fight page")
        return go
    def unv_flip(s_):   # remove a 'price unverified' marker if the card has one; otherwise add one where none is due
        if '<span class="unv">price unverified</span>' in s_: return s_.replace('<span class="unv">price unverified</span>', "", 1)
        return re.sub(r'(<span class="ech (?:pos|neg|flat)"><span data-id="v\d+">[^<]*</span></span>)(?!<span class="unv">)', r'\1<span class="unv">price unverified</span>', s_, count=1)
    def bump_first(rule, fmt):
        def fn(s_):
            reg = json.load(open(D / "fight_13.registry.json"))
            r = next(r for r in reg["rows"] if r["rule"] == rule and r["fmt"] == fmt)
            t = r["text"]; t2 = re.sub(r"(\d)(?!.*\d)", lambda m: str((int(m.group(1)) + 1) % 10), t)
            return s_.replace(f'<span data-id="{r["id"]}">{H.escape(t)}</span>', f'<span data-id="{r["id"]}">{H.escape(t2)}</span>')
        return fn
    def lock_edit(T, G_):   # a shared, locked file changed after the bless (card_overrides.json, one byte), restored right after the check
        p_ = REPO / "data/card_overrides.json"; G_["RESTORE"] = (p_, p_.read_bytes()); p_.write_bytes(p_.read_bytes() + b"\n")
    def ev_edit(which):   # Kirk round 10 A: the event file's Form block (locked) and odds block (recomputed from the archive)
        def go(T, G_):
            p_ = next((REPO / "form/data/events" / f'{u["slug"]}.json' for u in json.loads((FD / "index.json").read_text())["upcoming"]
                       if json.loads((FD / "events" / f'{u["slug"]}.json').read_text()).get("bp_file") == f"data/{slug}_odds.json"))
            G_["RESTORE"] = (p_, p_.read_bytes()); d_ = json.loads(p_.read_bytes()); f_ = max(d_["fights"], key=lambda x: x["n"])
            if which == "form": f_["form"]["p"] = round(1 - f_["form"]["p"], 4)
            else: f_["odds"]["close"]["p"] = round(f_["odds"]["close"]["p"] + 0.02, 4)
            p_.write_text(json.dumps(d_, separators=(",", ":"), ensure_ascii=False))
        return go
    def st_edit(T, G_):
        d_ = json.loads((REPO / "data/embeds/spot_tests.json").read_text()); d_["T1"]["win"] = 0.718; G_["ST_OVERRIDE"] = json.dumps(d_, indent=1).encode()
    def lh_shift(T, G_):
        d_ = json.loads((REPO / f"data/embeds/line_history_{slug}.json").read_text()); k_ = next(k for k in d_["fights"] if "Harrison" in k)
        d_["fights"][k_]["current"]["p"] = round(d_["fights"][k_]["current"]["p"] + 0.01, 3); G_["LH_OVERRIDE"] = d_
    def export_shift(T, G_):
        f0 = G_["PUB"]["fights"][0]; f0["sheet"]["true_fav"] += 0.002; f0["sheet"]["true_dog"] -= 0.002
    def export_method(T, G_):
        m = G_["PUB"]["fights"][1]["method"]["dog"]; m["ko"], m["sub"] = m["sub"], m["ko"]
    def export_gtd(T, G_):
        G_["PUB"]["fights"][2]["gtd"] += 0.01
    # Kirk round 28 D: a held number left behind somewhere the site shows it
    REC_ = json.loads((REPO / "audits/round28/hold_values.json").read_text()) if (REPO / "audits/round28/hold_values.json").exists() else {"form_line": {}}
    def held_key():
        k_ = next(iter(REC_["form_line"])); return k_.split("#")[0], int(k_.split("#")[1]), REC_["form_line"][k_]["p"]
    def hold_rebuilt(T, G_):   # a rebuild writes the Form Line back and drops the hold flag: card, fight page and sheet show it
        es, n_, p_ = held_key(); fp = FD / "events" / f"{es}.json"; G_["RESTORE"] = (fp, fp.read_bytes()); d_ = json.loads(fp.read_bytes())
        f_ = next(x for x in d_["fights"] if x["n"] == n_); f_["form"]["p"] = p_; f_["form"].pop("held", None)
        fp.write_text(json.dumps(d_, separators=(",", ":"), ensure_ascii=False))
    def hold_card_json(T, G_):   # a leftover copy in the embed JSON
        es, n_, p_ = held_key(); c_ = json.loads((T / "card.json").read_text()); next(x for x in c_["card"] if x["fight"] == n_)["form_line"] = p_
        (T / "card.json").write_text(json.dumps(c_, indent=1))
    def hold_og(T, G_):   # a leftover copy in page head text (the site has no OG tags today; this plants one)
        es, n_, p_ = held_key(); fp = REPO / "index.html"; G_["RESTORE"] = (fp, fp.read_bytes())
        fp.write_text(fp.read_text().replace("<head>", f'<head><meta property="og:description" content="UFC 334: Macy Chiasson Form Line {p_ * 100:.1f}%">', 1))
    def hold_labs(T, G_):   # a held Labs row gets its number back
        fp = FD / "labs.json"; G_["RESTORE"] = (fp, fp.read_bytes()); d_ = json.loads(fp.read_bytes())
        r_ = next(x for x in d_["height_gap"] if x.get("held")); r_["wp"] = 0.526; fp.write_text(json.dumps(d_, separators=(",", ":")))
    plants = [
        ("hold: Form Line written back by a rebuild, hold flag dropped (card, fight page, sheet)", hold_rebuilt),
        ("hold: leftover Form Line copy in the embed JSON (card.json)", hold_card_json),
        ("hold: leftover Form Line copy in page head text (OG description)", hold_og),
        ("hold: Belgaroui's held height back on the fight 11 embed", plant_text("fight_11.html", lambda s_: s_.replace('<span class="dim">held</span>', "6&#x27;5&quot;", 1))),
        ("hold: a held Labs row gets its number back (labs.json)", hold_labs),
        ("embed: Sean win % text off by 0.1 (fight 13)", plant_text("fight_13.html", bump_first("pub_win", "pct1"))),
        ("embed: Sean KO % text off (fight 13)", plant_text("fight_13.html", bump_first("pub_meth", "pct1"))),
        ("embed: KO and SUB cells swapped in the method stack (fight 07)", plant_text("fight_07.html", lambda s_: s_.replace('<td data-k="ko">', '<td data-k="@@">', 1).replace('<td data-k="sub">', '<td data-k="ko">', 1).replace('<td data-k="@@">', '<td data-k="sub">', 1))),
        ("embed: badge hidden by CSS (fight 02)", plant_text("fight_02.html", lambda s_: s_.replace("/* v4 embed layout */", "/* v4 embed layout */\n.ff-brand{display:none}"))),
        ("embed: wrong FIGHT number (fight 05)", plant_text("fight_05.html", lambda s_: s_.replace('fp-fight-num">FIGHT 5<', 'fp-fight-num">FIGHT 6<'))),
        ("embed: a model cell blanked (fight 10)", plant_text("fight_10.html", lambda s_: re.sub(r'<td class="model"><span class="odds">.*?</td>', '<td class="model dim">n/a</td>', s_, count=1, flags=re.S))),
        ("embed: an edge chip off by 0.1 (fight 13)", plant_text("fight_13.html", bump_first("edge", "spp"))),
        ("embed: Spot to watch dropped (fight 06)", plant_text("fight_06.html", lambda s_: re.sub(r'<div class="stk spot".*?</ul></div>', "", s_, count=1, flags=re.S))),
        ("embed: Spot to watch added where no test fires (fight 05)", plant_text("fight_05.html", lambda s_: s_.replace('<div class="legend">', '<div class="stk spot" data-part="spot"><ul class="lvl"><li data-spot="T1"><b>Johnson</b> x</li></ul></div><div class="legend">', 1))),
        ("embed: an edge under 2.0 coloured (first fight with one)", plant_any(lambda s_: re.sub(r'<span class="ech flat">(<span data-id="v\d+">[+-][01]\.\d%</span>)', r'<span class="ech pos">\1', s_, count=1))),
        ("embed: 'price unverified' removed where due, or added where not due (first fight it applies to)", plant_any(unv_flip)),
        ("embed: an offshore book named on the page (fight 07)", plant_text("fight_07.html", lambda s_: s_.replace('<span class="mvl">Line', 'Pinnacle <span class="mvl">Line', 1))),
        ("line history: a current line moved 1 pt in the file (fight 12)", lh_shift),
        ("shared input: a backtest number edited in spot_tests.json (builder and checker both read it)", st_edit),
        ("shared input: a locked file changed without a bless (card_overrides.json)", lock_edit),
        ("event file: one fighter's Form line swapped (main event)", ev_edit("form")),
        ("event file: odds close moved 2 pts (main event)", ev_edit("odds")),
        ("embed: one round-trend point moved (fight 07)", plant_text("fight_07.html", lambda s_: re.sub(r'(<circle cx="[\d.]+" cy=")([\d.]+)(" r="4")', lambda m: m.group(1) + f"{float(m.group(2)) + 9:.1f}" + m.group(3), s_, count=1))),
        ("embed: a steady line drawn as 'Steady' where it moved 7 pts (fight 13)", plant_text("fight_13.html", lambda s_: s_.replace('class="mvrow"', 'class="mvrow mvq"', 1))),
        ("embed: Duncan's at-the-floor note removed (fight 07)", plant_text("fight_07.html", lambda s_: s_.replace("Duncan: R3 sits right at the 15-minute floor; thin sample.", "", 1))),
        ("embed: Corrections link dropped from the footer (fight 03)", plant_text("fight_03.html", lambda s_: s_.replace('>Corrections</a>', '></a>', 1))),
        ("embed: a below-floor round drawn as a full dot (fight 08)", plant_text("fight_08.html", lambda s_: s_.replace('<circle class="thin" ', '<circle ', 1))),
        ("embed: T1 'never confirmed' line removed (fight 06)", plant_text("fight_06.html", lambda s_: s_.replace("Never confirmed on new cards", "Confirmed", 1))),
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
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    _, _, nb = run(T, G_, slug)
            finally:
                if G_.get("RESTORE"): G_["RESTORE"][0].write_bytes(G_["RESTORE"][1])
        nh = sum(1 for l_ in buf.getvalue().splitlines() if l_.startswith("    hold "))   # failures from the hold check alone
        print(f"  NEGATIVE {'CAUGHT ' if nb else 'MISSED '} {nb:>3} failures{f' ({nh} from the hold check)' if label.startswith('hold:') else ''} · {label}"); caught += bool(nb)
        if label.startswith("hold:"): print("        " + " | ".join(l_.strip()[5:] for l_ in buf.getvalue().splitlines() if l_.startswith("    hold "))[:500])
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
    ap.add_argument("--archive", help="odds archive cache to recheck against (default .form_cache); round 12 C, for scratch tests")
    ap.add_argument("--line-history", help="line history file to check (default data/embeds/line_history_<slug>.json)")
    a = ap.parse_args(); D = Path(a.dir) if a.dir else REPO / "embeds" / a.slug; G = load_sources(a.slug)
    if a.archive: G["ARCHIVE"] = Path(a.archive)
    if a.line_history: G["LH_PATH"] = Path(a.line_history)
    ok, n_rows, nb = run(D, G, a.slug); G_SLUG[0] = a.slug
    print(f"TOTAL: {ok}/{n_rows} numbers verified; {nb} mismatches/assertion failures")
    if G.get("SIDE_UNCHECKED"): print(f"SIDE CHECK: not checkable (line within 4 pts of 50%): {', '.join(G['SIDE_UNCHECKED'])}")
    mc = metrics_check(a.slug) if (REPO / ".form_cache" / "ufc_fight_stats.csv").exists() else None
    if mc is None: print("METRICS FILE: not rechecked (no .form_cache CSVs on this machine)")
    else:
        print(f"METRICS FILE: {mc[1]}"); nb += mc[0] != 0
    good = nb == 0
    if a.negative: good = negative(D, G, a.slug) and good
    sys.exit(0 if good else 1)
