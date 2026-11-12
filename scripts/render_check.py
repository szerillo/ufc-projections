#!/usr/bin/env python3
"""Rendered page and embeds vs the verified projections file (third link of the chain: sheet -> file -> what visitors see).

verify_projections.py proves the file matches the sheet; it never reads the page. This script opens the card page and every
single-fight embed (?embed=fight&n=N) in headless Chrome, reads the numbers a visitor sees from the DOM, and compares each
one with the value the verified file says it should show, at display precision.

    python3 -I scripts/render_check.py <base_url> <slug> [--embed2]   # e.g. https://szerillo.github.io/ufc-projections ufc_334

--embed2 also checks the per-fight embed v2 (<slug>_fight_embed.html?fight=<last name>): every element with data-k must
show exactly the value formatted from the verified file (Block 50).

Per published fight, 16 shown values on each surface (page, embed): listed no-vig, True % and edge at price for both sides,
Markov (dog), flag, rec, GTD, and the six method % (True % x share). Line-pending bouts must show "Line pending" and no
numbers. Exit 0 = every value matches; 1 = any mismatch (each one listed with surface, bout, field, expected, shown).
"""
from __future__ import annotations

import asyncio
import json
import sys
import urllib.request

from playwright.async_api import async_playwright

JS = '''(n) => { const p = document.getElementById('fp-' + n); if (!p) return null;
  return [...p.querySelectorAll('.fp-proj')].map(sec => ({ head: (sec.querySelector('.fp-proj-header') || {}).textContent || '',
    note: [...sec.querySelectorAll(':scope > div')].map(d => d.innerText).filter(t => /Flag:|Model rec/.test(t)).join(' '),
    tables: [...sec.querySelectorAll('table')].map(tb => [...tb.querySelectorAll('tbody tr')].map(tr => [...tr.children].map(td => {
      const pct = td.querySelector('.pct'); return pct ? pct.innerText.trim() : td.innerText.trim().split('\\n')[0]; }))) })); }'''
pc = lambda x: "—" if x is None else f"{100 * x:.1f}%"
sg = lambda x: "—" if x is None else f"{'+' if x > 0 else ''}{100 * x:.1f}%"


def expected(p: dict) -> dict:
    s, m = p.get("sheet") or {}, p.get("method") or {}
    dogW, favW = s["true_dog"], s["true_fav"]
    e = {"listed fav": pc(1 - s["listed"]), "True % fav": pc(favW), "edge fav": sg(s.get("fav_edge")),
         "listed dog": pc(s["listed"]), "True % dog": pc(dogW), "edge dog": sg(s.get("dog_edge")),
         "Markov dog": pc((p.get("inputs") or {}).get("markov"))}
    if "flag" in s: e["flag"] = str(s["flag"])
    if "rec" in s: e["rec"] = str(s["rec"])
    if p.get("gtd") is not None: e["GTD"] = pc(p["gtd"])
    for side, w in (("fav", favW), ("dog", dogW)):
        for k, lab in (("dec", "DEC"), ("ko", "KO"), ("sub", "SUB")):
            v = (m.get(side) or {}).get(k)
            if v is not None: e[f"{side} {lab}"] = f"{w * v * 100:.1f}%"
    return e


def shown(sec: list, p: dict) -> dict:
    sb = {row[0]: row for row in sec[0]["tables"][0]}
    note = " ".join(sec[0]["note"].split())
    out = {"listed fav": sb[p["fav"]][1], "True % fav": sb[p["fav"]][2], "edge fav": sb[p["fav"]][3],
           "listed dog": sb[p["dog"]][1], "True % dog": sb[p["dog"]][2], "edge dog": sb[p["dog"]][3], "Markov dog": sb[p["dog"]][4]}
    if "Flag: " in note: out["flag"] = note.split("Flag: ")[1].split(" · ")[0]
    if "Model rec: " in note: out["rec"] = note.split("Model rec: ")[1].split(" Outlier excluded")[0]
    if len(sec) > 1 and len(sec[1]["tables"]) > 2:
        out["GTD"] = sec[1]["tables"][1][0][1]
        meth = {row[0]: row for row in sec[1]["tables"][2]}
        for side in ("fav", "dog"):
            for i, lab in ((1, "DEC"), (2, "KO"), (3, "SUB")):
                out[f"{side} {lab}"] = meth[p[side]][i]
    return out


def expected2(p: dict) -> dict:
    """data-k -> text the v2 embed must show for this fight, formatted from the verified file only."""
    s, i, m = p.get("sheet") or {}, p.get("inputs") or {}, p.get("method") or {}
    ml = lambda v: "—" if v is None else (f"+{int(v)}" if v > 0 else str(int(v)))
    e = {"true_fav": pc(s["true_fav"]), "true_dog": pc(s["true_dog"]), "listed_fav": pc(1 - s["listed"]), "listed_dog": pc(s["listed"]),
         "fav_edge": sg(s.get("fav_edge")), "dog_edge": sg(s.get("dog_edge")), "fav_odds": ml(i.get("fav_odds")),
         "dog_odds": ml(i.get("dog_odds")), "gtd": pc(p.get("gtd")), "gtd_listed": pc(p.get("gtd_listed")),
         "open_dog": pc(i.get("open_dog")), "drift": sg(s.get("drift")), "rec": str(s.get("rec") or "-"), "flag": str(s.get("flag") or "")}
    if i.get("markov") is not None:
        e["markov_fav"], e["markov_dog"] = pc(1 - i["markov"]), pc(i["markov"])
    for side, w in (("fav", s["true_fav"]), ("dog", s["true_dog"])):
        for k in ("dec", "ko", "sub"):
            v = (m.get(side) or {}).get(k)
            if v is not None: e[f"{side}_{k}"] = pc(w * v)
    return e


async def embed2(pg, base: str, slug: str, doc: dict) -> tuple[int, list[str]]:
    bad, n = [], 0
    for p in doc.get("fights") or []:
        last = p["fav"].strip().lower().split()[-1]
        await pg.goto(f"{base}/{slug}_fight_embed.html?fight={last}"); await pg.wait_for_timeout(900)
        got = await pg.evaluate("() => [...document.querySelectorAll('[data-k]')].map(e => [e.dataset.k, e.textContent.trim()])")
        exp = expected2(p); seen = set()
        for k, v in got:
            n += 1; seen.add(k)
            if k not in exp: bad.append(f"embed2: {p['fav']} vs {p['dog']}: shows {k} = {v!r}, which the verified file does not define")
            elif v != exp[k]: bad.append(f"embed2: {p['fav']} vs {p['dog']}: {k} expected {exp[k]!r}, shown {v!r}")
        for k in exp.keys() - seen:
            bad.append(f"embed2: {p['fav']} vs {p['dog']}: {k} missing from the embed")
    return n, bad


async def main() -> int:
    base, slug = sys.argv[1].rstrip("/"), sys.argv[2]
    page = f"{base}/{slug}_fight_form.html"
    doc = json.load(urllib.request.urlopen(f"{base}/data/{slug}_projections.json"))
    bad, n_cmp = [], 0
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1100, "height": 1600})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(page); await pg.wait_for_timeout(3000)
        fights = await pg.evaluate("() => FIGHTS.map(f => ({n: f.n, a: f.a.name, b: f.b.name}))")
        def find(p):
            return next((f for f in fights if {f["a"], f["b"]} == {p["dog"], p["fav"]}), None)
        for surface in ("page", "embed"):
            for p in doc.get("fights") or []:
                f = find(p)
                if f is None:
                    bad.append(f"{surface}: {p['fav']} vs {p['dog']}: published bout not on the page"); continue
                if surface == "embed":
                    await pg.goto(f"{page}?embed=fight&n={f['n']}"); await pg.wait_for_timeout(1800)
                sec = await pg.evaluate(JS, f["n"])
                if not sec or "Sheet model" not in sec[0]["head"]:
                    bad.append(f"{surface}: {p['fav']} vs {p['dog']}: no sheet block shown"); continue
                exp, got = expected(p), shown(sec, p)
                for k, v in exp.items():
                    n_cmp += 1
                    if got.get(k) != v:
                        bad.append(f"{surface}: {p['fav']} vs {p['dog']}: {k} expected {v!r}, shown {got.get(k)!r}")
            for lp in doc.get("line_pending") or []:
                f = find(lp)
                if f is None: continue
                if surface == "embed":
                    await pg.goto(f"{page}?embed=fight&n={f['n']}"); await pg.wait_for_timeout(1800)
                txt = (await pg.evaluate("(n) => (document.getElementById('fp-' + n) || {}).textContent || ''", f["n"])).lower()
                n_cmp += 1
                if "line pending" not in txt or "sheet model" in txt:
                    bad.append(f"{surface}: {lp['fav']} vs {lp['dog']}: line pending bout does not show 'Line pending' alone")
        if "--embed2" in sys.argv:
            n2, bad2 = await embed2(pg, base, slug, doc)
            n_cmp += n2; bad += bad2
        await b.close()
    print(f"Rendered vs verified file ({doc.get('verified', {}).get('at')}): {n_cmp} shown values compared, {len(bad)} mismatched; page errors {len(errs)}")
    for x in bad + [f"page error: {e}" for e in errs]:
        print("  -", x)
    return 1 if bad or errs else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
