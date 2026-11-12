#!/usr/bin/env python3
"""Corrupted-record test for the card page and the embed builder: one bad record per loop, and the rest must render.

    python3 -I scripts/test_card_guards.py                       # the page and embed.html in this checkout
    python3 -I scripts/test_card_guards.py --page OLD.html --embed OLD_embed.html --no-assert   # compare an older build

Each case corrupts one record (card data, published projections, odds feed or embed roster) with a value the
data could plausibly hold (null, wrong type, missing price) or, where JSON cannot reach the loop, a field whose
read throws. Serves the files from this checkout on a local port; needs playwright and Chrome.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import http.server
import json
import socketserver
import sys
import threading
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fighter_names import name_match  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SLUG = "ufc_334"
MARK = "// ============== FIGHTER NAME RULE"
THROW = "{ toString() { throw new Error('corrupt value'); } }"

# (name, card-page JS run before the page's own code, projections edit, odds edit, expectation)
CASES = [
    ("baseline", "", None, None, {}),
    ("card data: fight record with no B fighter", "FIGHTS[4].b = null;", None, None, {"panels": 12, "tabs": 12, "ml": 12, "length": 12, "method": 12, "proj": 12, "live": 12, "msg": "could not be shown"}),
    ("tab loop: tab label that cannot be read", f"FIGHTS[2].a.tab = {THROW};", None, None, {"tabs": 13, "plain_tab": 1, "len_err": 1}),
    ("panel loop: notes not a list", "FIGHTS[3].notes = 'corrupt';", None, None, {"panels": 13, "stubs": 1}),
    ("projections: true % as text", "", lambda d: d["fights"][1]["sheet"].__setitem__("true_dog", "0.31"), None, {"proj": 12, "ml": 12, "length": 12, "method": 12, "msg": "could not be read"}),
    ("projections: null record", "", lambda d: d["fights"].__setitem__(0, None), None, {"proj": 12, "ml": 12, "length": 12, "method": 12, "msg": "could not be read"}),
    ("projections: fights not a list", "", lambda d: d.__setitem__("fights", {"x": 1}), None, {"proj": 0, "ml": 0, "length": 0, "method": 0}),
    ("live odds: null fight record", "", None, lambda d: d["fights"].__setitem__(0, None), {"live": 12}),
    ("live odds: null moneyline selection", "", None, lambda d: d["fights"][3]["markets"]["moneyline"].__setitem__(0, None), {"live": 13}),
    ("live odds: method label not text", "", None, lambda d: d["fights"][5]["markets"]["method_of_victory"].__setitem__(0, {"label": 5, "selection": "ko"}), {"live": 13}),
    ("ML table: fight with no price anywhere", "FIGHTS[6].a.ml = null; FIGHTS[6].b.ml = null;", None, "drop_fight_6", {"live": 12, "dash": True}),
    ("length table: sim block that cannot be read", "Object.defineProperty(FIGHTS[7].sim, 'itd', { get() { throw new Error('corrupt sim'); }, set(v) {}, configurable: true });", None, None, {"len_err": 1, "stubs": 1}),
    ("method table: method split that cannot be read", "Object.defineProperty(FIGHTS[8].sim, 'aKO', { get() { throw new Error('corrupt sim'); }, set(v) {}, configurable: true });", None, None, {"meth_err": 1, "stubs": 1}),
]
METRICS = """() => {
  cardSegmentFilter = "all"; renderMLTable("favorite"); renderLengthTable(); renderMethodTable();  // count every fight, not just the main card
  const T = s => [...document.querySelectorAll(s)];
  const panels = T('.fight-panel');
  return {
    panels: panels.length,
    stubs: panels.filter(p => /could not be shown/.test(p.innerText)).length,
    blank: panels.filter(p => p.innerText.trim().length < 40).length,
    tabs: T('.ff-tab').length, plain_tab: T('.ff-tab').filter(t => /^fight \\d+$/i.test(t.innerText.trim())).length,
    ml: T('#ml-body tr').filter(r => !r.classList.contains('card-divider') && r.querySelector('.proj-fight-num')).length,
    dash: T('#ml-body tr').some(r => /—/.test(r.innerText)),
    length: T('#length-body tr').filter(r => r.querySelector('.proj-fight-num') || /could not be shown/.test(r.innerText)).length,
    len_err: T('#length-body tr').filter(r => /could not be shown/.test(r.innerText)).length,
    method: T('#method-body tr.fav-row').length + T('#method-body tr').filter(r => /could not be shown/.test(r.innerText)).length,
    meth_err: T('#method-body tr').filter(r => /could not be shown/.test(r.innerText)).length,
    proj: FIGHTS.filter(f => !f.noProj).length,
    live: FIGHTS.filter(f => f.a._liveML || f.b._liveML).length,
    status: (document.getElementById('ff-proj-status') || {}).innerText || '',
    names6: FIGHTS[6] ? [FIGHTS[6].a.name, FIGHTS[6].b.name] : [],
  };
}"""


def serve() -> tuple[socketserver.TCPServer, int]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = partial(Quiet, directory=str(REPO))
    srv = socketserver.TCPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


async def run(page_html: str, embed_html: str, check: bool) -> int:
    from playwright.async_api import async_playwright
    srv, port = serve()
    base = f"http://127.0.0.1:{port}"
    proj0 = json.loads((REPO / "data" / f"{SLUG}_projections.json").read_text())
    odds0 = json.loads((REPO / "data" / f"{SLUG}_odds.json").read_text())
    fails = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ref = None
        for name, js, pe, oe, want in CASES:
            assert page_html.count(MARK) == 1
            html = page_html.replace(MARK, "/* test corruption */ " + js + "\n" + MARK) if js else page_html
            proj, odds = copy.deepcopy(proj0), copy.deepcopy(odds0)
            if pe: pe(proj)
            if oe == "drop_fight_6":  # the fight with no price must not pick one up from the live feed either
                odds["fights"] = [f for f in odds["fights"] if not any(name_match(f["fighter_a"]["name"], x) or name_match(f["fighter_b"]["name"], x) for x in names6)]
            elif oe:
                oe(odds)
            pg = await b.new_page(); errs = []
            pg.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
            for pat, body, ct in ((f"**/{SLUG}_fight_form.html*", html, "text/html"), (f"**/data/{SLUG}_projections.json", json.dumps(proj), "application/json"),
                                  (f"**/data/{SLUG}_odds.json", json.dumps(odds), "application/json")):
                await pg.route(pat, (lambda b_, c_: (lambda r, *_: r.fulfill(status=200, content_type=c_, body=b_)))(body, ct))
            await pg.goto(f"{base}/{SLUG}_fight_form.html"); await pg.wait_for_timeout(2500)
            try:
                m = await pg.evaluate(METRICS)
            except Exception as e:  # noqa: BLE001
                m = {"evaluate_error": str(e)[:120]}
            await pg.close()
            if ref is None:
                ref = m
                names6 = m.get("names6", [])
            exp = {k: ref[k] for k in ("panels", "tabs", "ml", "length", "method", "proj", "live") if k in ref}
            exp.update({"blank": 0, "stubs": 0, "plain_tab": 0, "len_err": 0, "meth_err": 0})
            exp.update(want)
            bad = {k: (m.get(k), v) for k, v in exp.items() if k != "msg" and m.get(k) != v}
            if "msg" in want and want["msg"].lower() not in m.get("status", "").lower():
                bad["status"] = (m.get("status", "")[-90:], want["msg"])
            if errs:
                bad["page errors"] = errs[:2]
            ok = not bad
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name}: panels {m.get('panels')}, stubs {m.get('stubs')}, blank {m.get('blank')}, tabs {m.get('tabs')}, "
                  f"ML rows {m.get('ml')}, length rows {m.get('length')}, method rows {m.get('method')}, projected {m.get('proj')}, live {m.get('live')}"
                  + ("" if ok else f"\n     expected vs got: {bad}"))
        # embed builder: a null roster entry and one without a fight number
        pg = await b.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        mark = "// Populate fight dropdown based on selected card."
        assert embed_html.count(mark) == 1
        eh = embed_html.replace(mark, f"/* test corruption */ $card.value = '{SLUG}'; FIGHTS_BY_CARD['{SLUG}'].splice(1, 0, null, {{ matchup: 'no number' }});\n" + mark)
        await pg.route("**/embed.html*", (lambda b_: (lambda r, *_: r.fulfill(status=200, content_type="text/html", body=b_)))(eh))
        await pg.goto(f"{base}/embed.html"); await pg.wait_for_timeout(800)
        try:
            await pg.evaluate("() => document.getElementById('card').dispatchEvent(new Event('change'))")
            await pg.wait_for_timeout(500)
            em = await pg.evaluate(f"() => ({{ want: FIGHTS_BY_CARD['{SLUG}'].filter(f => f && f.n != null).length, options: document.querySelectorAll('#fight option').length, cards: document.querySelectorAll('.fight-card').length }})")
        except Exception as e:  # noqa: BLE001
            em = {"evaluate_error": str(e)[:120]}
        ok = not errs and em.get("options") == em.get("want") and em.get("cards") == em.get("want")
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} embed builder: null roster entry and one with no fight number: {em}" + (f" page errors {errs[:2]}" if errs else ""))
        await b.close()
    srv.shutdown()
    print(f"{len(CASES) + 1 - fails}/{len(CASES) + 1} cases as expected")
    return 1 if (fails and check) else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=str(REPO / f"{SLUG}_fight_form.html"))
    ap.add_argument("--embed", default=str(REPO / "embed.html"))
    ap.add_argument("--no-assert", action="store_true")
    a = ap.parse_args()
    return asyncio.run(run(Path(a.page).read_text(encoding="utf-8"), Path(a.embed).read_text(encoding="utf-8"), not a.no_assert))


if __name__ == "__main__":
    sys.exit(main())
