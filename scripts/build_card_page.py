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

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "ufc_fn_cortes_acosta_walker_fight_form.html"
WC_SHORT = {"Heavyweight": "HW", "Light Heavyweight": "LHW", "Middleweight": "MW", "Welterweight": "WW", "Lightweight": "LW",
            "Featherweight": "FW", "Bantamweight": "BW", "Flyweight": "FLW", "Women's Bantamweight": "WBW",
            "Women's Flyweight": "WFLW", "Women's Strawweight": "WSW", "Women's Featherweight": "WFW", "Catch Weight": "CW"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(w for w in re.sub(r"[^a-z ]", " ", s).split() if w not in ("jr", "ii", "iii"))


def same(a: str, b: str) -> bool:
    ta, tb = norm(a).split(), norm(b).split()
    if not ta or not tb:
        return False
    if " ".join(ta) == " ".join(tb) or "".join(ta) == "".join(tb):
        return True
    return ta[-1] == tb[-1] and ta[0][0] == tb[0][0]


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
    stat = lambda nm: next((r for r in stats_rows if same(r["Fighter"], nm)), None)

    def price(nm):
        for fo in (odds or {}).get("fights", []):
            for m in fo["markets"].get("moneyline", []):
                if same(m["label"], nm):
                    b = m["books"]
                    c = (b.get("consensus") or {}).get("cost")
                    return c if c is not None else next((v.get("cost") for v in b.values() if v.get("cost") is not None), None)
        return None

    out, meta = [], []
    n_total = len(order)
    n_main, n_pre = seg.get("main", 5), seg.get("prelims", 0)
    for i, (x, y) in enumerate(order):
        ev = next((f for k, f in by_pair.items() if {norm(k[0]), norm(k[1])} == {norm(x), norm(y)}), None)
        if ev is None:
            raise SystemExit(f"bout {x} vs {y} from card_overrides order is not in the event file")
        mx, my = price(x), price(y)
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

function projNameMatch(x, y) {
  const t = (s) => (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z ]/g, " ").split(/\s+/).filter(w => w && !["jr", "ii", "iii"].includes(w));
  const a = t(x), b = t(y);
  if (!a.length || !b.length) return false;
  if (a.join(" ") === b.join(" ") || a.join("") === b.join("")) return true;
  return a[a.length - 1] === b[b.length - 1] && a[0][0] === b[0][0];
}

function applySheetProjections(doc) {
  (doc.fights || []).forEach(p => {
    const f = FIGHTS.find(x => (projNameMatch(x.a.name, p.dog) && projNameMatch(x.b.name, p.fav)) ||
                               (projNameMatch(x.a.name, p.fav) && projNameMatch(x.b.name, p.dog)));
    if (!f || !p.sheet || p.sheet.true_dog == null) return;
    const aIsDog = projNameMatch(f.a.name, p.dog);
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
  });
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
      el.innerHTML = `<span class="dot"></span>Projections · ${n} of ${FIGHTS.length} fights · updated ${fmtAgo(SHEET_PROJ.published_at)}`;
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
    t = t[:i] + LOADER.replace("__SLUG__", slug) + "\n" + t[j:]
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
