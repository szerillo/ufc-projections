# Block 58 item 4 (scripts/public_link_check.py): every rendered link to a UFC 334 fight page, on every route a visitor can reach, resolved against the
# event file: the link's own text, or failing that its table row, must name a fighter of the bout the link opens.
# RED (exit 1) if any link opens a bout it does not name, or a bout number that does not exist.
import asyncio, sys, re, json, unicodedata
from playwright.async_api import async_playwright
S = "2026-11-14-ufc-334-gane-vs-hokit"
fold = lambda s: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower())
async def main(base):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"]); pg = await b.new_page(viewport={"width": 1300, "height": 2400})
        await pg.goto(f"{base}/index.html#/"); await pg.wait_for_timeout(3500)
        ev = await pg.evaluate("(u) => fetch(u, {cache: 'no-store'}).then(r => r.json())", f"{base}/form/data/events/{S}.json")
        byn = {f["n"]: f for f in ev["fights"]}
        labs = ["query", "upsets", "size", "spots", "divisions", "octagon", "metrics", "cardio", "live", "props", "scoring", "rounds", "judges", "refs", "log"]
        routes = ["#/", f"#/card/{S}", f"#/sheet/{S}", "#/cards", "#/duration", "#/duration/ufc-334-gane-vs-hokit", "#/model", "#/research", "#/about", "#/fighters"] + \
                 [f"#/labs/{t}" for t in labs] + [f"#/fight/{S}/{f['n']}" for f in ev["fights"]] + \
                 sorted({f"#/fighter/{f[s]['slug']}" for f in ev["fights"] for s in "ab" if f[s].get("slug")})
        links, bad = 0, []
        for r in routes:
            await pg.evaluate("(h) => { location.hash = h; }", r); await pg.wait_for_timeout(1400)
            got = await pg.evaluate("""(s) => [...document.querySelectorAll('#app a[href*="/fight/' + s + '/"], #app tr[data-href*="/fight/' + s + '/"]')].map(el => {
                const href = el.getAttribute('href') || el.dataset.href; const row = el.closest('tr, li, p, div');
                return [href.split('/').pop(), el.textContent.trim().slice(0, 80), (row ? row.textContent : '').trim().slice(0, 200)]; })""", S)
            for n, txt, row in got:
                links += 1; f = byn.get(int(n)) if n.isdigit() else None
                if not f: bad.append((r, n, txt, "no such bout")); continue
                names = [fold(f[s]["name"].split()[-1]) for s in "ab"]
                own = [x for x in names if x and x in fold(txt)]
                # a link whose text names any UFC 334 fighter must name one of this bout's fighters
                others = [fold(g[s]["name"].split()[-1]) for g in ev["fights"] if g is not f for s in "ab"]
                wrong = not own and any(o and o in fold(txt) for o in others)
                if not own and not wrong:   # text names no fighter (e.g. a number): fall back to the row
                    wrong = not any(x in fold(row) for x in names) and any(o and o in fold(row) for o in others)
                if wrong: bad.append((r, n, txt, f"opens {f['a']['name']} vs {f['b']['name']}"))
        await b.close()
    print(f"{len(routes)} routes, {links} links to UFC 334 fight pages, {len(bad)} open a bout they do not name")
    for x in bad: print("  RED", *x, sep=" | ")
    sys.exit(1 if bad else 0)
asyncio.run(main(sys.argv[1]))
