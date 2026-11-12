#!/usr/bin/env python3
"""Build a card page (ufc_<slug>_fight_form.html) that reads its projections from the sheet export.

No projections are hard-coded. The page boots, fetches data/<slug>_projections.json (written only by
the "Projections check" workflow after scripts/verify_projections.py passes) and the live odds file,
and renders. Fights without a published projection show "Projections coming".

    python3 -I scripts/build_card_page.py --slug ufc_334 \
        --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json \
        --stats markov/UFC_334_Gane_vs_Hokit_Raw_Stats.csv \
        --title "UFC 334: Gane vs Hokit" --subtitle "Saturday, November 14, 2026 · Madison Square Garden, New York"

Template: the latest hand-built card page (layout, styles, live-odds code). The script swaps in the
card's FIGHTS data (tale of the tape from the raw-stats CSV, bout order and segments from
data/card_overrides.json, prices from data/<slug>_odds.json) and replaces the hand-edited
USER_PROJECTIONS_BY_FIGHT block with a loader.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fighter_names import NAME_MATCH_JS, best_match, bout_slots, name_match, strict_match, tokens  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "ufc_fn_cortes_acosta_walker_fight_form.html"
WC_SHORT = {"Heavyweight": "HW", "Light Heavyweight": "LHW", "Middleweight": "MW", "Welterweight": "WW", "Lightweight": "LW",
            "Featherweight": "FW", "Bantamweight": "BW", "Flyweight": "FLW", "Women's Bantamweight": "WBW",
            "Women's Flyweight": "WFLW", "Women's Strawweight": "WSW", "Women's Featherweight": "WFW", "Catch Weight": "CW"}


def norm(s: str) -> str:
    return " ".join(tokens(s))


# Every name match goes through scripts/fighter_names.py (tested by test_fighter_names.py): one name in a list by
# best_match (strict, else the only loose match), a bout by bout_slots (one fighter strict, the other at least loose).

LIVE_FIND_OLD = """  const aTokens = nameTokens(a.name);
  const bTokens = nameTokens(b.name);
  return (live.fights || []).find(f => {
    const fA = nameTokens(f.fighter_a?.name);
    const fB = nameTokens(f.fighter_b?.name);
    // Match if the pair matches — both A and B find their opponent in one of
    // the two slots (either A↔A/B↔B or A↔B/B↔A).
    return (tokenOverlap(aTokens, fA) && tokenOverlap(bTokens, fB)) ||
           (tokenOverlap(aTokens, fB) && tokenOverlap(bTokens, fA));
  });"""
LIVE_FIND_NEW = """  // the bout matches when one fighter matches strictly and the other at least loosely, in either slot order
  return (Array.isArray(live && live.fights) ? live.fights : []).find(f => fighterBoutSlots(a.name, b.name, f?.fighter_a?.name, f?.fighter_b?.name) != null);"""
WHICH_OLD = """function whichFighter(label, f) {
  const labelTokens = nameTokens(label);"""
WHICH_NEW = """function whichFighter(label, f, lf) {
  // a selection label starts with the feed's spelling of a fighter ("Charlie Radke KO/TKO/DQ"): map that spelling to a or b
  const L = nameTokensRule(label).join(" ");
  for (const fx of [lf && lf.fighter_a, lf && lf.fighter_b]) {
    const t = nameTokensRule(fx && fx.name).join(" ");
    if (t && (L === t || L.startsWith(t + " "))) {
      if (fighterStrictMatch(fx.name, f.a.name)) return "a";
      if (fighterStrictMatch(fx.name, f.b.name)) return "b";
      const ma = fighterNameMatch(fx.name, f.a.name), mb = fighterNameMatch(fx.name, f.b.name);
      if (ma !== mb) return ma ? "a" : "b";
    }
  }
  const labelTokens = nameTokens(label);"""

# Per-record guards (crash audit, Nov 11): one bad record must cost only its own fight, never the rest of the page.
GUARD_JS = r"""
// ============== PER-RECORD GUARDS (scripts/build_card_page.py GUARD_JS; tests: scripts/test_card_guards.py) ==============
const FF_ERRORS = [];
function ffEsc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]); }
function ffErr(where, rec, e) {
  const id = rec && typeof rec === "object" ? (rec.n != null ? "fight " + rec.n : (rec.fav ? rec.fav + " vs " + rec.dog : "")) : "";
  FF_ERRORS.push(where + (id ? " (" + id + ")" : "") + ": " + ((e && e.message) || e));
  try { console.warn("[fight-form]", FF_ERRORS[FF_ERRORS.length - 1]); } catch (_) {}
}
function ffFightOk(f) {
  return !!(f && typeof f === "object" && Number.isFinite(f.n) && f.sim && typeof f.sim === "object" &&
            f.a && f.b && typeof f.a.name === "string" && typeof f.b.name === "string" && f.a.name && f.b.name);
}
// a fight record without names, number or sim block cannot be drawn at all: leave it off and say so
for (let i = FIGHTS.length - 1; i >= 0; i--) if (!ffFightOk(FIGHTS[i])) { ffErr("card data", { n: FIGHTS[i] && FIGHTS[i].n }, "fight record is malformed, left off the page"); FIGHTS.splice(i, 1); }
function ffPanelStub(f, isFirst) {
  const old = document.getElementById("fp-" + f.n); if (old) old.remove();
  const d = document.createElement("div");
  d.className = "fight-panel" + (isFirst ? " active" : ""); d.id = "fp-" + f.n;
  d.innerHTML = `<div class="fp-proj"><div class="fp-proj-header"><span class="bullet"></span>${ffEsc(f.a.name)} vs ${ffEsc(f.b.name)}</div>
    <div style="padding:10px 4px;font-size:12px;color:var(--text-muted);">This fight's numbers could not be shown. The rest of the card is unaffected.</div></div>`;
  panelsEl.appendChild(d);
}
function ffErrRow(f, cols) {
  return `<tr><td colspan="${cols}" style="padding:8px;text-align:center;color:var(--text-muted);font-size:11px;">Fight ${ffEsc(f && f.n)}: numbers could not be shown</td></tr>`;
}
// Names matched with a spelling difference (a loose match confirmed by the opponent). Shown, never hidden: a debut or
// replacement with a near name (Daniel Roberts -> Daniel Robert) cannot be told from a feed typo by the rule alone.
const FF_FUZZY = { proj: [], odds: [] };
function ffNoteFuzzy(kind, pageA, pageB, slots, otherA, otherB) {
  const pairs = slots === "same" ? [[pageA, otherA], [pageB, otherB]] : [[pageA, otherB], [pageB, otherA]];
  pairs.forEach(([x, y]) => { if (!fighterStrictMatch(x, y)) FF_FUZZY[kind].push(x + " = " + y); });
}
function ffFuzzyText(kind) {
  const l = FF_FUZZY[kind];
  return l.length ? ` · <span class="ff-fuzzy">spelled differently: ${ffEsc(l.join("; "))}</span>` : "";
}
function ffReportErrors() {
  if (!FF_ERRORS.length) return;
  const el = document.getElementById("ff-proj-status");
  if (el) { el.className = "ff-odds-status stale"; el.innerHTML += ` · <b>${FF_ERRORS.length} record${FF_ERRORS.length > 1 ? "s" : ""} could not be shown</b>`; }
}
"""


def guard_loops(t: str) -> str:
    """Wrap every per-record loop of the template in try/catch (file:line list in Block 40)."""
    def rep(x, y, n=1):
        nonlocal t
        assert t.count(x) == n, (t.count(x), x[:80])
        t = t.replace(x, y)
    # tabs
    rep("""  withPanels.forEach((f, idx) => {
    const aLast""", """  withPanels.forEach((f, idx) => { try {
    const aLast""")
    rep("""    tabsEl.appendChild(btn);
  });
}""", """    tabsEl.appendChild(btn);
  } catch (e) {  // still give the fight a plain tab so its panel can be reached
    ffErr("tab", f, e);
    const btn = document.createElement("button");
    btn.className = "ff-tab" + (idx === 0 ? " active" : ""); btn.dataset.target = "fp-" + f.n; btn.textContent = "Fight " + f.n;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".ff-tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".fight-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const el = document.getElementById("fp-" + f.n); if (el) el.classList.add("active");
    });
    tabsEl.appendChild(btn);
  } });
}""")
    # panels
    rep("FIGHTS.filter(hasPanel).forEach((f, idx) => renderPanel(f, idx === 0));",
        "FIGHTS.filter(hasPanel).forEach((f, idx) => { try { renderPanel(f, idx === 0); } catch (e) { ffErr(\"panel\", f, e); ffPanelStub(f, idx === 0); } });")
    # live odds: each fight, and each selection inside it
    i = t.index("function mergeLiveOdds(live) {"); j = t.index("\n}\n", i)
    body = t[i:j]
    assert body.count("  FIGHTS.forEach(f => {") == 1 and body.count("\n  });") == 1, "mergeLiveOdds shape"
    assert body.count(".forEach(sel => {") == 4 and body.count("\n    });") == 4, "mergeLiveOdds selection loops"
    body = body.replace("  FIGHTS.forEach(f => {", "  FIGHTS.forEach(f => { try {").replace("\n  });", "\n  } catch (e) { ffErr(\"live odds\", f, e); } });")
    body = body.replace(".forEach(sel => {", ".forEach(sel => { try {").replace("\n    });", "\n    } catch (e) { ffErr(\"live odds selection\", f, e); } });")
    t = t[:i] + body + t[j:]
    # the three projection tables: a row that throws becomes one "could not be shown" row
    rep("  sorted.forEach(f => {", "  sorted.forEach(f => { try {", 3)
    k = 0
    for cols in (7, 5, 5):
        x = "\n  });\n  tbody.innerHTML = html;"
        k = t.index(x, k)
        y = f"\n  }} catch (e) {{ ffErr(\"table\", f, e); html += ffErrRow(f, {cols}); }} }});\n  tbody.innerHTML = html;"
        t = t[:k] + y + t[k + len(x):]; k += len(y)
    # moneyline table: no listed price must show a dash, not throw (same failure as the Radtke panels)
    rep("    const listedOddsTxt = (listedCost > 0 ? \"+\" : \"\") + listedCost;\n    const edge = projPct - listedPct;",
        "    const listedOddsTxt = listedCost == null ? \"—\" : (listedCost > 0 ? \"+\" : \"\") + listedCost;\n    const edge = listedPct == null ? null : projPct - listedPct;")
    rep("<td class=\"proj-cell-pct\">${listedPct.toFixed(1)}%</td>", "<td class=\"proj-cell-pct\">${listedPct == null ? \"—\" : listedPct.toFixed(1) + \"%\"}</td>")
    rep("function fmtSignedPct(n) { return (n > 0 ? \"+\" : \"\") + n.toFixed(1) + \"%\"; }",
        "function fmtSignedPct(n) { return n == null || !Number.isFinite(n) ? \"—\" : (n > 0 ? \"+\" : \"\") + n.toFixed(1) + \"%\"; }")
    # say on the page when anything was skipped
    rep("  renderMethodTable();\n  // No full-ToT fights", "  renderMethodTable();\n  ffReportErrors();\n  // No full-ToT fights")
    return t


def american(p: float) -> int:
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def implied(ml: float) -> float:
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def js(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def fighter_js(name: str, st: dict | None, ml: int | None, mkt: float | None, tab: str | None = None) -> str:
    st = st or {}
    f = lambda k, d=0.0: float(st[k]) if st.get(k) not in (None, "", "--") else d
    ht = st.get("Height") or "—"
    if ht != "—" and not ht.endswith('"'):
        ht += '"'
    pct = lambda k: f"{round(100 * f(k))}%" if st.get(k) not in (None, "", "--") else "—"
    obj = (f'{{ name: {js(name)}, ' + (f'tab: {js(tab)}, ' if tab else "") +
           f'nick: "—", record: {js(st.get("CareerRecord") or "—")}, ml: {js(ml)}, win: {round(100 * mkt, 1) if mkt else 50}, '
           f'mktImp: {round(100 * implied(ml), 1) if ml else 50}, ko: 0, sub: 0, dec: 0, kol: 0, subl: 0, decl: 0, ufc: "—", min: 0, '
           f'age: {f("Age")}, ht: {js(ht)}, reach: {int(f("Reach"))}, stance: {js(st.get("Stance") or "—")}, '
           f'slpm: {f("SLpM"):.2f}, sapm: {f("SApM"):.2f}, sdiff: {f("SLpM") - f("SApM"):.1f}, tdacc: {js(pct("TDAcc"))}, '
           f'tdR5: {f("TDAvg") / 3:.2f}, tdd: {js(pct("TDDef"))}, ctrl: 0, sub_succ: "—", sub_def: "—", dist: 0, gnd: 0, log: [] }}')
    return obj


def build_fights(slug: str, event: dict, stats_rows: list[dict], odds: dict | None) -> tuple[str, list[dict]]:
    ov = json.load(open(REPO / "data" / "card_overrides.json")).get(slug, {})
    seg = ov.get("segments") or {}
    order = [o.split("|") for o in ov.get("order") or []] or [[f["a"]["name"], f["b"]["name"]] for f in event["fights"]]
    by_pair = {}
    for f in event["fights"]:
        by_pair[(f["a"]["name"], f["b"]["name"])] = f
    titled = {tuple(sorted(t)) for t in ov.get("title") or []}
    def stat(nm):
        hit = best_match(nm, [r["Fighter"] for r in stats_rows])
        return next((r for r in stats_rows if r["Fighter"] == hit), None) if hit else None

    def prices(x, y):
        """Moneylines for page bout (x, y): find the feed bout with bout_slots, then read each fighter's selection."""
        for fo in (odds or {}).get("fights", []):
            fa, fb = (fo.get("fighter_a") or {}).get("name"), (fo.get("fighter_b") or {}).get("name")
            slots = bout_slots(x, y, fa, fb)
            if not slots:
                continue
            fx, fy = (fa, fb) if slots == "same" else (fb, fa)
            for pn, fn in ((x, fx), (y, fy)):
                if not strict_match(pn, fn):
                    print(f"note: odds feed spells {pn!r} as {fn!r} (matched through the bout)", file=sys.stderr)
            def cost(feed_name):
                for m in fo["markets"].get("moneyline", []):
                    if strict_match(m["label"], feed_name):
                        b = m["books"]
                        c = (b.get("consensus") or {}).get("cost")
                        return c if c is not None else next((v.get("cost") for v in b.values() if v.get("cost") is not None), None)
                return None
            return cost(fx), cost(fy)
        return None, None

    out, meta = [], []
    n_total = len(order)
    n_main, n_pre = seg.get("main", 5), seg.get("prelims", 0)
    for i, (x, y) in enumerate(order):
        ev = next((f for k, f in by_pair.items() if {norm(k[0]), norm(k[1])} == {norm(x), norm(y)}), None)
        if ev is None:
            raise SystemExit(f"bout {x} vs {y} from card_overrides order is not in the event file")
        mx, my = prices(x, y)
        a, b = (x, y) if (mx is None or my is None or mx <= my) else (y, x)
        ma, mb = (mx, my) if a == x else (my, mx)
        pa = pb = None
        if ma is not None and mb is not None:
            ia, ib = implied(ma), implied(mb)
            pa, pb = ia / (ia + ib), ib / (ia + ib)
        n = n_total - i
        card = "MAIN EVENT" if i == 0 else ("MAIN CARD" if i < n_main else "PRELIMS")
        segname = "Main Event" if i == 0 else ("Main Card" if i < n_main else ("Prelims" if i < n_main + n_pre else "Early Prelims"))
        rounds = f'{ev.get("sched") or 3}R'
        title = "TITLE" if tuple(sorted((x, y))) in titled else None
        wc = ev.get("wc") or "—"
        out.append(
            "  {\n"
            f'    n: {n}, card: {js(card)}, weight: {js(wc)}, rounds: {js(rounds)}, conf: "MED",' + (' title: "TITLE FIGHT",' if title else "") + "\n"
            f"    a: {fighter_js(a, stat(a), ma, pa)},\n"
            f"    b: {fighter_js(b, stat(b), mb, pb)},\n"
            "    sim: { itd: 50, aKO: 0, aSub: 0, aDec: 0, bKO: 0, bSub: 0, bDec: 0 },\n"
            "    noProj: true,\n"
            "    notes: []\n"
            "  }")
        last = lambda s: s.split()[-1]
        meta.append({"n": n, "matchup": f"{last(a)} vs {last(b)}", "meta": f"{segname} · {WC_SHORT.get(wc, wc)} · {rounds}"})
    return "const FIGHTS = [\n" + ",\n".join(out) + "\n];\n", meta


LOADER = r'''// ============== SHEET PROJECTIONS (published from the UFC Model sheet) ==============
// No projections are hard-coded on this page. The sheet's "Publish to site" writes
// data/pending/<slug>_projections.json; the "Projections check" workflow recomputes every number
// with scripts/sheet_v47.py and only then copies it to PROJ_URL. Unpublished fights show
// "Projections coming".
const PROJ_URL = "data/__SLUG___projections.json";
let SHEET_PROJ = null;

// Raw implied probability from an American moneyline (NOT de-vigged).
// Two of these for a fight will sum to > 100% by the book's hold/vig.
function rawImpliedPct(ml) {
  if (ml == null) return null;
  const m = Number(ml);
  if (m > 0) return 100 / (m + 100) * 100;
  return Math.abs(m) / (Math.abs(m) + 100) * 100;
}

// A published bout is matched to a page bout with the shared rule (fighterBoutSlots, from scripts/fighter_names.py): one
// fighter must match strictly and the other at least loosely, so a late replacement with a near name (Josh vs Jake
// Hokit) or a near-namesake (Chris Duncan vs Christian Leroy Duncan) does not inherit the old bout's numbers.

let PROJ_UNMATCHED = [], PROJ_BAD = [];
// A published record is used only if every field it feeds is the right type; anything else is listed in the status line.
function projRecordOk(p) {
  const pr = (x) => x == null || (typeof x === "number" && x >= 0 && x <= 1);
  if (!p || typeof p !== "object" || typeof p.fav !== "string" || typeof p.dog !== "string") return false;
  if (p.sheet != null && (typeof p.sheet !== "object" || !pr(p.sheet.true_dog))) return false;
  if (!pr(p.gtd)) return false;
  for (const side of ["dog", "fav"]) {
    const m = p.method && p.method[side];
    if (m != null && (typeof m !== "object" || !pr(m.dec) || !pr(m.ko) || !pr(m.sub))) return false;
  }
  return true;
}
function applySheetProjections(doc) {
  PROJ_UNMATCHED = []; PROJ_BAD = []; FF_FUZZY.proj = [];
  (Array.isArray(doc && doc.fights) ? doc.fights : []).forEach((p, i) => { try {
    if (!projRecordOk(p)) { PROJ_BAD.push(p && p.fav && p.dog ? p.fav + " vs " + p.dog : "record " + (i + 1)); return; }
    const f = FIGHTS.find(x => fighterBoutSlots(x.a.name, x.b.name, p.dog, p.fav) != null);
    if (f) ffNoteFuzzy("proj", f.a.name, f.b.name, fighterBoutSlots(f.a.name, f.b.name, p.dog, p.fav), p.dog, p.fav);
    if (!f) { PROJ_UNMATCHED.push(p.fav + " vs " + p.dog); return; }   // published but not on this page: a late change the page has not caught up with
    if (!p.sheet || p.sheet.true_dog == null) return;
    const aIsDog = fighterBoutSlots(f.a.name, f.b.name, p.dog, p.fav) === "same";
    const dogW = 100 * p.sheet.true_dog, favW = 100 - dogW;
    const sh = (side, w) => {
      const m = (p.method || {})[side] || {};
      return (m.dec == null || m.ko == null || m.sub == null) ? null : { dec: w * m.dec, ko: w * m.ko, sub: w * m.sub };
    };
    const dm = sh("dog", dogW), fm = sh("fav", favW);
    const A = aIsDog ? { w: dogW, m: dm } : { w: favW, m: fm };
    const B = aIsDog ? { w: favW, m: fm } : { w: dogW, m: dm };
    f.a.win = A.w; f.b.win = B.w;
    if (A.m && B.m) {
      f.sim.aDec = A.m.dec; f.sim.aKO = A.m.ko; f.sim.aSub = A.m.sub;
      f.sim.bDec = B.m.dec; f.sim.bKO = B.m.ko; f.sim.bSub = B.m.sub;
      f.sim.itd = (p.gtd != null) ? 100 - 100 * p.gtd : (A.m.ko + A.m.sub + B.m.ko + B.m.sub);
    } else if (p.gtd != null) {
      f.sim.itd = 100 - 100 * p.gtd;
    }
    f.noMethod = !(A.m && B.m);
    f.proj = p; f.projADog = aIsDog;
    f.noProj = false;
    f.a.mktImp = rawImpliedPct(f.a.ml);
    f.b.mktImp = rawImpliedPct(f.b.ml);
  } catch (e) { ffErr("projections", p, e); PROJ_BAD.push(p && p.fav ? p.fav + " vs " + p.dog : "record " + (i + 1)); } });
}

async function loadSheetProjections() {
  const el = document.getElementById("ff-proj-status");
  try {
    const r = await fetch(PROJ_URL, { cache: "no-store" });
    if (!r.ok) throw new Error("http " + r.status);
    SHEET_PROJ = await r.json();
    applySheetProjections(SHEET_PROJ);
    const n = FIGHTS.filter(f => !f.noProj).length;
    if (el) {
      el.className = "ff-odds-status fresh";
      el.innerHTML = `<span class="dot"></span>Projections · ${n} of ${FIGHTS.length} fights · updated ${fmtAgo(SHEET_PROJ.published_at)}` +
        (PROJ_UNMATCHED.length ? ` · <b>${PROJ_UNMATCHED.length} published fight${PROJ_UNMATCHED.length > 1 ? "s" : ""} not on this card: ${ffEsc(PROJ_UNMATCHED.join("; "))}</b>` : "") +
        (PROJ_BAD.length ? ` · <b>${PROJ_BAD.length} published fight${PROJ_BAD.length > 1 ? "s" : ""} could not be read: ${ffEsc(PROJ_BAD.join("; "))}</b>` : "") +
        ffFuzzyText("proj");
      // a sheet name that differs from the page's is unusual (both come from the same card), so it turns the line amber
      if (PROJ_UNMATCHED.length || PROJ_BAD.length || FF_FUZZY.proj.length) el.className = "ff-odds-status stale";
      // freshness guard: numbers older than 12h stay up but are labelled (prices and news move; Sean re-publishes before the card)
      // the sheet's prices are as old as their last load (Feed "Loaded", published as prices_loaded), not the publish time
      if (SHEET_PROJ.prices_loaded) el.innerHTML += ` · prices loaded ${fmtAgo(SHEET_PROJ.prices_loaded)}`;
      const ageH = (Date.now() - Math.min(Date.parse(SHEET_PROJ.published_at), Date.parse(SHEET_PROJ.prices_loaded || SHEET_PROJ.published_at))) / 36e5;
      if (!(ageH <= 12)) { el.className = "ff-odds-status stale"; el.innerHTML += ` · <b>over 12h old, check before using</b>`; }
    }
  } catch (e) {
    if (el) { el.className = "ff-odds-status stale"; el.innerHTML = `<span class="dot"></span>Projections coming`; }
  }
}

function projComingHTML(f) {
  return `<div class="fp-proj"><div class="fp-proj-header"><span class="bullet"></span>Projections coming</div>
    <div style="padding:10px 4px;font-size:12px;color:var(--text-muted);">Model numbers for ${f.a.name} vs ${f.b.name} post once Sean publishes them from the sheet.</div></div>`;
}

function sheetBlockHTML(f) {
  const p = f.proj, s = p.sheet || {};
  const pc = (x) => x == null ? "—" : (100 * x).toFixed(1) + "%";
  const sg = (x) => x == null ? "—" : (x > 0 ? "+" : "") + (100 * x).toFixed(1) + "%";
  const rows = [[p.fav, 1 - s.listed, s.true_fav, s.fav_edge, null], [p.dog, s.listed, s.true_dog, s.dog_edge, p.inputs && p.inputs.markov]];
  return `<div class="fp-proj">
    <div class="fp-proj-header"><span class="bullet"></span>Sheet model · v4.7</div>
    <table class="fp-proj-table">
      <thead><tr><th class="tleft">Fighter</th><th>Listed (no-vig)</th><th>True %</th><th>Edge at price</th><th>Markov</th></tr></thead>
      <tbody>${rows.map(r => `<tr><td class="tleft">${r[0]}</td><td>${pc(r[1])}</td><td><b>${pc(r[2])}</b></td>
        <td><span class="edge-pill ${projEdgeClass(r[3] == null ? 0 : 100 * r[3])}">${sg(r[3])}</span></td><td>${r[4] == null ? "—" : pc(r[4])}</td></tr>`).join("")}</tbody>
    </table>
    ${s.flag != null || s.rec != null ? `<div style="font-size:11px;padding:4px 2px 8px;color:var(--text-muted);">
      ${s.flag != null ? `Flag: <b>${s.flag}</b>` : ""}${s.flag != null && s.rec != null ? " · " : ""}${s.rec != null ? `Model rec: <b>${s.rec}</b>` : ""}</div>` : ""}
  </div>`;
}
'''


def patch(template: str, slug: str, fights_js: str, title: str, subtitle: str) -> str:
    t = template
    t = re.sub(r"<title>.*?</title>", f"<title>{title} · Fight Form</title>", t, count=1)
    t = re.sub(r'<div class="ff-title">.*?</div>', f'<div class="ff-title">{title} · Fight Form</div>', t, count=1)
    t = re.sub(r'<div class="ff-subtitle">.*?</div>', f'<div class="ff-subtitle">{subtitle}</div>', t, count=1)
    t = t.replace('<div class="ff-odds-status" id="ff-odds-status">Live odds: loading…</div>',
                  '<div class="ff-odds-status" id="ff-odds-status">Live odds: loading…</div>\n'
                  '    <div class="ff-odds-status" id="ff-proj-status" style="margin-top:4px;">Projections: loading…</div>', 1)
    i, j = t.index("const FIGHTS = ["), t.index("// ============== RENDER ==============")
    t = t[:i] + fights_js + "\n" + t[j:]
    i = t.index("// ============== USER PROJECTIONS (overrides) ==============")
    j = t.index("// ============== LIVE ODDS FETCH + MERGE ==============")
    t = t[:i] + NAME_MATCH_JS + GUARD_JS + LOADER.replace("__SLUG__", slug) + "\n" + t[j:]
    t = re.sub(r'const ODDS_URL = "data/[a-z0-9_]+_odds.json";', f'const ODDS_URL = "data/{slug}_odds.json";', t, count=1)
    assert "applyUserProjections();" in t
    t = t.replace("applyUserProjections();", "await loadSheetProjections();", 1)
    assert t.count("const projectionsHTML = `") == 1
    t = t.replace("const projectionsHTML = `", "const projectionsHTML = f.noProj ? projComingHTML(f) : sheetBlockHTML(f) + `", 1)
    n = t.count("applySegmentFilter([...FIGHTS])")
    assert n == 3, n
    t = t.replace("applySegmentFilter([...FIGHTS])", "applySegmentFilter(FIGHTS.filter(x => !x.noProj))")
    t = t.replace('font-size:11px;">No fights in this segment.</td></tr>`',
                  'font-size:11px;">${FIGHTS.some(x => !x.noProj) ? "No fights in this segment." : "Projections coming."}</td></tr>`')
    # embed=fight: highlight the tab for fight n (template picked tabs[n-1], which is the wrong tab when the main event is listed first)
    if "const tab = tabs[fightN - 1];" in t:
        t = t.replace("const tab = tabs[fightN - 1];", 'const tab = document.querySelector(\'.ff-tab[data-target="fp-\' + fightN + \'"]\');', 1)
    # A fight with no listed price (odds feed missing or spelled differently) must not throw: one throw inside the
    # render loop blanked every panel after it (UFC 334 dry run, Nov 11). Show "—" for the price and the edge instead.
    for x, y in (("const projEdgeA = f.a.win - listedPctA;", "const projEdgeA = listedPctA == null ? null : f.a.win - listedPctA;"),
                 ("const projEdgeB = f.b.win - listedPctB;", "const projEdgeB = listedPctB == null ? null : f.b.win - listedPctB;"),
                 ('<div class="pct">${listedPctA.toFixed(1)}%</div>', '<div class="pct">${listedPctA == null ? "—" : listedPctA.toFixed(1) + "%"}</div>'),
                 ('<div class="pct">${listedPctB.toFixed(1)}%</div>', '<div class="pct">${listedPctB == null ? "—" : listedPctB.toFixed(1) + "%"}</div>'),
                 ('${projEdgeA > 0 ? "+" : ""}${projEdgeA.toFixed(1)}%', '${projEdgeA == null ? "—" : (projEdgeA > 0 ? "+" : "") + projEdgeA.toFixed(1) + "%"}'),
                 ('${projEdgeB > 0 ? "+" : ""}${projEdgeB.toFixed(1)}%', '${projEdgeB == null ? "—" : (projEdgeB > 0 ? "+" : "") + projEdgeB.toFixed(1) + "%"}'),
                 # live-odds overlay: match bouts and selections with the shared name rule. Token overlap missed the feed's
                 # "Charlie Radke" and "Alateng Heili" (no live odds for either bout) and let Jake Hokit match Josh Hokit.
                 (LIVE_FIND_OLD, LIVE_FIND_NEW), (WHICH_OLD, WHICH_NEW),
                 ("const which = whichFighter(sel.label || \"\", f);", "const which = whichFighter(sel.label || \"\", f, lf);"),
                 ("const which = whichFighter(label, f);", "const which = whichFighter(label, f, lf);")):
        assert t.count(x) == 1, x
        t = t.replace(x, y)
    t = guard_loops(t)
    rep_ = lambda x, y: (t.count(x) == 1 or (_ for _ in ()).throw(AssertionError(x[:60]))) and t.replace(x, y)
    t = rep_("    const lf = findLiveFight(live, f.a, f.b);\n    if (!lf) return;",
             "    const lf = findLiveFight(live, f.a, f.b);\n    if (!lf) return;\n    ffNoteFuzzy(\"odds\", f.a.name, f.b.name, fighterBoutSlots(f.a.name, f.b.name, lf.fighter_a?.name, lf.fighter_b?.name), lf.fighter_a?.name, lf.fighter_b?.name);")
    t = rep_("  el.innerHTML = `<span class=\"dot\"></span>Live odds · BettingPros · updated ${ago}`;",
             "  el.innerHTML = `<span class=\"dot\"></span>Live odds · BettingPros · updated ${ago}` + ffFuzzyText(\"odds\");")
    for bad in ("USER_PROJECTIONS_BY_FIGHT", "Cortes", "cortes_acosta"):
        assert bad not in t, bad
    return t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--event", required=True)
    ap.add_argument("--stats", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", required=True)
    ap.add_argument("--out")
    ap.add_argument("--meta-out", help="write the embed.html FIGHTS_BY_CARD roster for this card as JSON")
    a = ap.parse_args()
    event = json.load(open(REPO / a.event))
    rows = list(csv.DictReader(open(REPO / a.stats, encoding="utf-8")))
    oddsp = REPO / "data" / f"{a.slug}_odds.json"
    odds = json.load(open(oddsp)) if oddsp.exists() else None
    fights_js, meta = build_fights(a.slug, event, rows, odds)
    html = patch(TEMPLATE.read_text(encoding="utf-8"), a.slug, fights_js, a.title, a.subtitle)
    out = REPO / (a.out or (f"{a.slug}_fight_form.html" if a.slug.startswith("ufc_") else f"ufc_{a.slug}_fight_form.html"))
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)} ({len(meta)} fights)")
    if a.meta_out:
        Path(a.meta_out).write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
