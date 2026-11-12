# Block 55: what a visitor sees for one card, checked headless against the sheet.
#   P1 books: no non-US-regulated book name anywhere on the home page, the card page or any fight page, and every
#      "Best price" / price-board / book-table entry is on the US allowlist.
#   P2 recs:  the rec a visitor sees (home and card-table pills, fight-page pills) has the same action
#      (BET / lean / none) and the same fighter as the sheet rec. Text-only drift such as
#      "[late: fav moved 5%]" vs "6%" is listed but is not red.
#   P3 live: printed for the record only (live_overlay_check.py owns it).
# Usage: python3 -I scripts/public_surface_check.py <base_url> --ref <sheet.xlsx | projections.json> [--slug S] [--json out.json]
# Exit 1 on any red.
import asyncio, json, re, sys, unicodedata, argparse, datetime as dt
from playwright.async_api import async_playwright

NOT_US = ["pinnacle", "betonline", "bovada", "lowvig", "mybookie", "betus", "sportsbetting.ag", "everygame", "heritage", "bookmaker.eu", "betanysports", "xbet"]
US_NAMES = {"draftkings", "fanduel", "betmgm", "caesars", "betrivers", "fanatics", "espnbet", "hardrockbet", "circa"}

def fold(s):
    return re.sub(r"[^a-z ]", "", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower())

def key(text, a, b):
    """'BET Bilal Hasan (80%+ rule)' -> ('BET', 'a'|'b'|None); '-' or '' -> ('none', None)."""
    t = str(text or "").strip()
    m = re.match(r"(?i)^(bet|lean)\b(.*)$", t)
    if not m:
        return ("none", None)
    act = "BET" if m.group(1).lower() == "bet" else "lean"
    rest = fold(m.group(2).split("(")[0].split("[")[0])
    la, lb = fold(a).split()[-1], fold(b).split()[-1]
    sa, sb = la in rest.split(), lb in rest.split()
    return (act, "a" if sa and not sb else "b" if sb and not sa else "?")

def load_ref(path):
    out = []
    if path.endswith(".json"):
        d = json.load(open(path))
        for f in d["fights"]:
            out.append((f["dog"], f["fav"], (f.get("sheet") or {}).get("rec") or "-"))
        return out, d.get("published_at")
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    for t in ("Main Card", "Prelims"):
        for r in list(wb[t].iter_rows(values_only=True))[1:14]:
            if r and r[1] and r[2] and r[1] not in ("Underdog", "Fighter") and r[5] is not None:
                out.append((str(r[1]), str(r[2]), str(r[13] or "-").strip() or "-"))
    return out, None

def match_ref(ref, a, b):
    la, lb = fold(a).split()[-1], fold(b).split()[-1]
    hits = [r for r in ref if {fold(r[0]).split()[-1], fold(r[1]).split()[-1]} == {la, lb}]
    return hits[0] if len(hits) == 1 else None

async def render(base, slug):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await br.new_page(viewport={"width": 1300, "height": 2200})
        await pg.goto(f"{base}/index.html#/card/{slug}"); await pg.wait_for_timeout(4000)
        ev = await pg.evaluate("(u) => fetch(u, {cache: 'no-store'}).then(r => r.json())", f"{base}/form/data/events/{slug}.json")
        card = await pg.evaluate("""() => {
          const o = {rows: {}, board: [], text: document.querySelector('#app').textContent};
          document.querySelectorAll('table').forEach(tb => {
            const head = [...tb.querySelectorAll('thead th')].map(th => th.textContent.trim().toUpperCase());
            const trs = [...tb.querySelectorAll('tbody tr.click')];
            if (head.includes('BOOK')) { const i = head.indexOf('BOOK'); trs.forEach(tr => o.board.push((tr.children[i] || {}).textContent.trim())); }
            else if (head.includes('BOUT') && head.includes('#')) trs.forEach(tr => { o.rows[tr.dataset.href.split('/').pop()] = [...tr.querySelectorAll('.pill')].map(x => x.textContent.trim()); });
          });
          return o; }""")
        await pg.evaluate("(h) => { location.hash = h; }", "#/"); await pg.wait_for_timeout(2500)
        home = await pg.evaluate("""() => { const o = {rows: {}, text: document.querySelector('#app').textContent};
          document.querySelectorAll('tbody tr.click[data-href*="/fight/"]').forEach(tr => { const n = tr.dataset.href.split('/').pop();
            o.rows[n] = (o.rows[n] || []).concat([...tr.querySelectorAll('.pill')].map(x => x.textContent.trim())); });
          return o; }""")
        card["home"] = home
        pages = {}
        for f in ev["fights"]:
            await pg.evaluate("(h) => { location.hash = h; }", f"#/fight/{slug}/{f['n']}"); await pg.wait_for_timeout(1300)
            pages[str(f["n"])] = await pg.evaluate("""() => {
              const app = document.querySelector('#app');
              const best = [...app.querySelectorAll('tr')].filter(tr => /^Best price/.test((tr.children[0] || {}).textContent || '')).flatMap(tr => [...tr.children].slice(1, 3).map(td => td.textContent.trim()));
              const btab = [...app.querySelectorAll('table')].filter(tb => [...tb.querySelectorAll('thead th')].some(th => th.textContent.trim().toUpperCase() === 'BOOK'))
                .flatMap(tb => [...tb.querySelectorAll('tbody tr')].map(tr => tr.children[0].textContent.trim()));
              return {text: app.textContent, pills: [...app.querySelectorAll('.pill')].map(s => s.textContent.trim()), best, btab}; }""")
        await br.close()
    return ev, card, pages

def book_of(cell):
    """'-357 BetOnline' -> 'betonline' ; '—' -> None"""
    m = re.match(r"^[+-]?\d+\s+(.+)$", cell.strip())
    return fold(m.group(1)).replace(" ", "") if m else None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("--ref", required=True)
    ap.add_argument("--slug", default="2026-11-14-ufc-334-gane-vs-hokit"); ap.add_argument("--json")
    a = ap.parse_args(); base = a.base.rstrip("/")
    ref, ref_t = load_ref(a.ref)
    ev, card, pages = asyncio.run(render(base, a.slug))
    red, rows = [], []
    # P1 books
    surfaces = [("home page", card["home"]["text"]), ("card page", card["text"])] + [(f"fight page {n}", pages[n]["text"]) for n in pages]
    p1_text = [(where, b) for where, t in surfaces for b in NOT_US if b in t.lower()]
    named = [("price board", c) for c in card["board"]] + [(f"fight {n} best price", book_of(c) or "") for n in pages for c in pages[n]["best"]] + \
            [(f"fight {n} book table", fold(c).replace(" ", "")) for n in pages for c in pages[n]["btab"]]
    named = [(w, fold(b).replace(" ", "")) for w, b in named if b]
    p1_off = [(w, b) for w, b in named if b not in US_NAMES]
    print(f"P1 books: {len(named)} named book cells, {len(p1_off)} not on the US allowlist; {len(p1_text)} non-US book names in page text")
    for w, b in p1_off: print(f"  RED  {w}: {b}")
    for w, b in sorted(set(p1_text)): print(f"  RED  text {w}: {b}")
    if p1_off or p1_text: red.append("P1")
    # P2 recs
    dis = drift = 0
    print(f"P2 recs vs {a.ref.split('/')[-1]}" + (f" (published {ref_t})" if ref_t else ""))
    for f in ev["fights"]:
        an, bn, n = f["a"]["name"], f["b"]["name"], str(f["n"])
        r = match_ref(ref, an, bn)
        sheet_rec = r[2] if r else None
        sk = key(sheet_rec, an, bn) if r else ("no sheet row", None)
        shown = [x for x in card["rows"].get(n, []) + card["home"]["rows"].get(n, []) + pages.get(n, {}).get("pills", []) if re.match(r"(?i)^(bet|lean)\b", x)]
        keys = {key(x, an, bn) for x in shown} or {("none", None)}
        bad = any(k != sk for k in keys)
        txt = [x for x in shown if len(x) > 20 and x != sheet_rec]
        dis += bad; drift += (not bad and bool(txt))
        rows.append({"n": f["n"], "bout": f"{an} vs {bn}", "shown": shown or ["(none)"], "sheet": sheet_rec, "verdict": "RED" if bad else ("text drift" if txt else "ok")})
        print(f"  {'RED ' if bad else 'ok  '} #{n} {an} vs {bn}: shown {shown or ['(none)']} | sheet {sheet_rec!r}" + ("  [text drift]" if txt and not bad else ""))
    print(f"P2 recs: {dis} of {len(ev['fights'])} bouts show a rec that differs from the sheet; {drift} text-only drift")
    if dis: red.append("P2")
    print("RESULT:", "RED " + ",".join(red) if red else "GREEN", f"({base}, read {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})")
    if a.json: json.dump({"p1_off": p1_off, "p1_text": p1_text, "p2": rows, "red": red}, open(a.json, "w"), indent=1)
    sys.exit(1 if red else 0)

if __name__ == "__main__":
    main()
