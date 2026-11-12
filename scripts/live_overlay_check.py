# Block 55: run the site's own overlayLive() (form/app.js) in a headless page on the real files and count the bouts
# that get a live price. RED (exit 1) if N < M, where M = bouts on the card. Also RED if a feed bout lands on two
# site bouts or a site bout gets the wrong fighters' prices.
# Usage: python3 -I scripts/live_overlay_check.py <base_url> [--slug S]
import asyncio, argparse, sys, json
from playwright.async_api import async_playwright

JS = r"""async (slug) => {
  // load the page's own overlayLive() source (app.js keeps it out of global scope) and run it unchanged
  const appUrl = [...document.scripts].map(s => s.src).find(u => /form\/app\.js/.test(u));
  const src = await fetch(appUrl, {cache: 'no-store'}).then(r => r.text());
  const i = src.indexOf('async function overlayLive(ev)'); if (i < 0) throw new Error('overlayLive not found');
  const body = src.slice(i, src.indexOf('\n}\n', i) + 2);
  const lastLine = src.split('\n').filter(l => /^const (last|nm|sameFighter) = /.test(l)).join('\n');
  const overlayLive = new Function(lastLine + '\n' + body + '\nreturn overlayLive;')();
  const ev = await fetch(`form/data/events/${slug}.json`, {cache: 'no-store'}).then(r => r.json());
  await overlayLive(ev);
  const d = await fetch(ev.bp_file, {cache: 'no-store'}).then(r => r.json());
  const nm = (x) => (x || '').toLowerCase().normalize('NFD').replace(/[^a-z]/g, '');
  const out = ev.fights.map(f => ({n: f.n, bout: f.a.name + ' vs ' + f.b.name, live: f.live || null}));
  const prices = {}; for (const bf of d.fights || []) for (const z of ((bf.markets || {}).moneyline || [])) if (z.books && z.books.consensus) prices[nm(z.label)] = z.books.consensus.cost;
  // strict side check, independent of the app's matcher: full-name equality after the alias table
  const al = await fetch('form/data/name_aliases.json', {cache: 'no-store'}).then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const full = {}; for (const bf of d.fights || []) for (const z of ((bf.markets || {}).moneyline || [])) {
    const k = (z.label || '').toLowerCase().normalize('NFD').replace(/[^a-z ]/g, '').replace(/\s+/g, ' ').trim();
    if (z.books && z.books.consensus) full[nm(al[k] || z.label)] = z.books.consensus.cost; }
  for (const r of out) { const f = ev.fights.find(x => x.n === r.n); r.expect = {ma: full[nm(f.a.name)] ?? null, mb: full[nm(f.b.name)] ?? null}; }
  return {updated: d.updated_at, feed_bouts: (d.fights || []).length, rows: out, prices};
}"""

async def run(base, slug):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"]); pg = await b.new_page()
        await pg.goto(f"{base}/index.html#/card/{slug}"); await pg.wait_for_timeout(3000)
        r = await pg.evaluate(JS, slug); await b.close(); return r

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("--slug", default="2026-11-14-ufc-334-gane-vs-hokit")
    a = ap.parse_args(); r = asyncio.run(run(a.base.rstrip("/"), a.slug))
    rows = r["rows"]; N = sum(1 for x in rows if x["live"]); M = len(rows)
    vals = list(r["prices"].values())
    wrong = [x for x in rows if x["live"] and (x["live"]["ma"] != x["expect"]["ma"] or x["live"]["mb"] != x["expect"]["mb"])]
    for x in rows: print(f"  {'ok ' if x['live'] else 'MISS'} #{x['n']} {x['bout']}: {x['live']}" + ('' if not x['live'] or x['live'] == x['expect'] else f"  WRONG SIDE, feed has {x['expect']}"))
    print(f"live prices applied to {N} of {M} bouts (feed {r['updated']}, {r['feed_bouts']} feed bouts); {len(wrong)} with a side price that differs from the feed's price for that fighter")
    red = N < M or wrong
    print("RESULT:", "RED" if red else "GREEN", a.base)
    sys.exit(1 if red else 0)

if __name__ == "__main__":
    main()
