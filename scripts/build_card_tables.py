#!/usr/bin/env python3
"""Card-level pages in the fight-preview format (Sean, Nov 13): Full widget, Moneylines table, Props tables.

    python3 -I scripts/build_card_tables.py --slug ufc_334

Reads only the built fight previews (embeds/<slug>/fight_NN.html) and card.json. The header, stylesheet, explainer and
footer are lifted from the main event preview, and every table row is lifted from that fight's own preview, so a number
on these pages is always the same text as on the fight preview (scripts/verify_card_tables.py checks it).
Writes embeds/<slug>/card.html (Fights + Moneylines + Props), moneylines.html and props.html.
Layout follows the old moneyline and prop tables: fight #, Main card / Prelims sections, Favorites / Underdogs,
Fight length and Method of victory, with the preview's Model / Listed / Market / Edge columns added.
"""
import argparse, copy, json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parents[1]
SEG = {"Main event": "Main card", "Main card": "Main card", "Prelims": "Prelims", "Early prelims": "Early prelims"}
SEGS = ["Main card", "Prelims", "Early prelims"]
LABEL = {"card": "Fight Form", "moneylines": "Moneylines", "props": "Props"}


def soup(s): return BeautifulSoup(s, "html.parser")


def clean(node):
    """Copy of a lifted node with the preview's registry hooks (data-id spans) unwrapped; text and classes unchanged."""
    n = copy.copy(node)
    for sp in n.select("span[data-id]"): sp.unwrap()
    return n


def load(slug):
    d = REPO / "embeds" / slug; C = json.loads((d / "card.json").read_text()); F = []
    for c in C["card"]:   # card.json is main event first
        n = c["fight"]; p = d / f"fight_{n:02d}.html"; R = json.loads((d / f"fight_{n:02d}.registry.json").read_text())
        S = soup(p.read_text()); a, b = R["pair"]
        part = {k: S.select_one(f'div.stk[data-part="{k}"]') for k in ("ml", "length", "method")}
        rows = {k: ([clean(tr) for tr in v.select("tbody > tr")] if v and v.select_one("table") else []) for k, v in part.items()}
        side = {}
        for tr in rows["ml"]:
            dot = tr.select_one("i.dot"); nm = tr.select_one("td.nm").get_text(" ", strip=True)
            side["fav" if "fav" in dot["class"] else "dog"] = (nm, tr)
        wt = S.select_one(".fp-weight"); belt = S.select_one(".fp-title-belt")
        F.append(dict(n=n, a=a, b=b, seg=SEG.get(c["segment"], "Prelims"), main=c["segment"] == "Main event", title=bool(belt),
                      weight=wt.get_text(strip=True) if wt else "", pending=R.get("proj_src") == "line_pending", rows=rows, side=side,
                      file=f"fight_{n:02d}.html", soup=S))
    return C, F


def grp(f, cols, link=True):
    t = (' <span class="cg-belt">★ TITLE</span>' if f["title"] else "")
    nm = f'{f["a"]} <span class="vs">vs</span> {f["b"]}'
    if link: nm = f'<a href="{f["file"]}" target="_blank" rel="noopener">{nm}</a>'
    return f'<tr class="cg"><td colspan="{cols}"><b class="cg-n">{f["n"]}</b>{nm}{t}<span class="cg-w">{f["weight"]}</span></td></tr>'


def pend(f, cols, what):
    return (grp(f, cols) + f'<tr><td class="l" colspan="{cols}"><span class="cg-pend">Line pending</span> '
            f'<span class="dim">The sheet\'s price for {f["a"]} vs {f["b"]} did not match this bout, so no {what} are shown until it does.</span></td></tr>')


def sec(name, cols): return f'<tr class="sec"><td colspan="{cols}"><span class="bullet"></span>{name}</td></tr>'


def ml_table(F, which):
    head = '<thead><tr><th class="n">#</th><th class=l>Fighter</th><th>Model</th><th>Listed</th><th>Market</th><th>Edge</th></tr></thead>'
    body = []
    for s_ in SEGS:
        fs = [f for f in F if f["seg"] == s_]
        if not fs: continue
        body.append(sec(s_, 6))
        for f in fs:
            if f["pending"] or which not in f["side"]:
                body.append(f'<tr><td class="n">{f["n"]}</td><td class="l nm" colspan="5">{f["a"]} <span class="vs">vs</span> {f["b"]}'
                            f'<div class="cg-pend-row"><span class="cg-pend">Line pending</span> no numbers until the sheet\'s price matches this bout</div></td></tr>')
                continue
            nm, tr = f["side"][which]; tr = copy.copy(tr)
            opp = f["b"] if nm == f["a"] else f["a"]
            td = tr.select_one("td.nm"); bar = td.select_one("div.nb")
            vs = soup(f'<div class="opp">vs {opp}</div>').div
            (bar.insert_before(vs) if bar else td.append(vs))
            n_td = soup(f'<td class="n">{f["n"]}</td>').td
            tr.insert(0, n_td)
            body.append(str(tr))
    lab = "Favorites" if which == "fav" else "Underdogs"
    return (f'<div class="stk" data-part="ml"><div class="stk-h"><span class="bullet"></span>Moneyline · model vs market · {lab}</div>'
            f'<table class="stk-t ct ct-ml">{head}<tbody>{"".join(body)}</tbody></table></div>')


def props_tables(F, seg):
    fs = [f for f in F if f["seg"] == seg]
    L = ['<thead><tr><th class=l>Outcome</th><th>Model</th><th>Listed</th><th>Market</th><th>Edge</th></tr></thead><tbody>']
    M = ['<thead><tr><th class=l>Fighter</th><th>DEC</th><th>KO</th><th>SUB</th><th>ITD</th></tr></thead><tbody>']
    for f in fs:
        if f["pending"]:
            L.append(pend(f, 5, "fight length numbers")); M.append(pend(f, 5, "method numbers")); continue
        L.append(grp(f, 5) + "".join(map(str, f["rows"]["length"]))) if f["rows"]["length"] else L.append(grp(f, 5) + '<tr><td class="l dim" colspan="5">No fight length numbers for this bout.</td></tr>')
        M.append(grp(f, 5) + "".join(map(str, f["rows"]["method"]))) if f["rows"]["method"] else M.append(grp(f, 5) + '<tr><td class="l dim" colspan="5">No method numbers for this bout.</td></tr>')
    L.append("</tbody>"); M.append("</tbody>")
    return (f'<div class="stk" data-part="length"><div class="stk-h"><span class="bullet"></span>Fight length · GTD and ITD</div><table class="stk-t ct">{"".join(L)}</table></div>'
            f'<div class="stk" data-part="method"><div class="stk-h"><span class="bullet"></span>Method of victory · model vs market</div><table class="stk-t ct">{"".join(M)}</table></div>')


def tabs(group, items, sel=0):
    """items: [(key, label, html)]. Same markup and styling as the fight preview's Projection / Stats / Form tabs."""
    bt = "".join(f'<button type="button" role="tab" id="tb-{group}-{k}" aria-controls="tp-{group}-{k}" aria-selected="{"true" if i == sel else "false"}" tabindex="{0 if i == sel else -1}">{lab}</button>'
                 for i, (k, lab, _) in enumerate(items))
    ps = "".join(f'<section class="tp" id="tp-{group}-{k}" role="tabpanel" aria-labelledby="tb-{group}-{k}" tabindex="0"{"" if i == sel else " hidden"}>{h}</section>'
                 for i, (k, lab, h) in enumerate(items))
    return f'<div class="tabs" role="tablist" data-group="{group}" aria-label="{group}">{bt}</div>{ps}'


def ml_block(F):
    return (tabs("ml", [("fav", "Favorites", ml_table(F, "fav")), ("dog", "Underdogs", ml_table(F, "dog"))]))


def props_block(F):
    segs = [s_ for s_ in SEGS if any(f["seg"] == s_ for f in F)]
    return tabs("pr", [({"Main card": "main", "Prelims": "prelims", "Early prelims": "early"}[s_], s_, props_tables(F, s_)) for s_ in segs])


def fights_block(F):
    chips = "".join(f'<button type="button" class="fchip{" on" if i == 0 else ""}" data-src="{f["file"]}"><b>{f["n"]}</b>{f["a"].split()[-1]} vs {f["b"].split()[-1]}'
                    f'{" <span class=cg-belt>★</span>" if f["title"] else ""}</button>' for i, f in enumerate(F))
    return (f'<div class="fchips" role="group" aria-label="Pick a fight">{chips}</div>'
            f'<iframe id="fprev" class="fprev" src="{F[0]["file"]}" title="Fight preview" scrolling="no"></iframe>')


EXTRA_CSS = """
/* Card-level tables (build_card_tables.py): fight-preview look, old moneyline / prop table layout */
.ct-h{border-radius:6px 6px 0 0;margin:12px 0 0}
.ct-h + .tabs{margin-top:0}
.tp > .stk:first-child{margin-top:10px}
.stk-t.ct td.n,.stk-t.ct th.n{width:22px;color:var(--text-muted);font:700 11px/1 "SF Mono",Menlo,monospace;text-align:center}
.stk-t.ct .opp{font-weight:500;font-size:10.5px;color:var(--text-muted);margin-top:1px}
.stk-t.ct tr.sec td{background:var(--header-bg);color:#fff;font-size:10.5px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;padding:7px 10px;text-align:left}
.stk-t.ct tr.sec .bullet{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--action-green);margin-right:7px;vertical-align:1px}
.stk-t.ct tr.cg td{background:var(--bg-muted);text-align:left;font-size:11.5px;font-weight:800;padding:7px 8px;border-top:2px solid var(--border)}
.stk-t.ct tr.cg a{color:inherit;text-decoration:none}
.stk-t.ct tr.cg a:hover{text-decoration:underline}
.stk-t.ct tr.cg .vs{color:var(--text-muted);font-weight:600;margin:0 2px}
.cg-n{display:inline-block;min-width:18px;font:800 11px/1 "SF Mono",Menlo,monospace;color:var(--text-muted);margin-right:6px}
.cg-w{float:right;font-size:10px;font-weight:700;letter-spacing:.3px;text-transform:uppercase;color:var(--text-muted)}
.cg-belt{display:inline-block;margin-left:6px;font-size:9.5px;font-weight:800;padding:1px 5px;border-radius:3px;background:#c9a54a;color:#1a1a1a;vertical-align:1px}
.cg-pend{display:inline-block;font-size:9.5px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;padding:2px 6px;border-radius:3px;background:var(--bg-muted);color:var(--text-muted);border:1px solid var(--border)}
.cg-pend-row{font-weight:500;font-size:10.5px;color:var(--text-muted);margin-top:4px}
.stk-t.ct .vs{color:var(--text-muted);font-weight:600}
.top-tabs{margin-top:0}
.fchips{display:flex;gap:6px;overflow-x:auto;padding:10px 0 8px;scrollbar-width:none}
.fchips::-webkit-scrollbar{display:none}
.fchip{flex:0 0 auto;font:inherit;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.3px;color:var(--text);background:#fff;border:1px solid var(--border);border-radius:5px;padding:6px 9px;cursor:pointer;white-space:nowrap}
.fchip b{color:var(--text-muted);margin-right:5px;font-family:"SF Mono",Menlo,monospace}
.fchip.on{background:var(--header-bg);color:#fff;border-color:var(--header-bg)}
.fchip.on b{color:var(--action-green)}
.fprev{display:block;width:100%;border:0;min-height:600px}
.cardpage .panel{padding-top:4px}
"""

JS = """<script>(function(){
[].slice.call(document.querySelectorAll('[role=tablist]')).forEach(function(tl){
  var tabs=[].slice.call(tl.querySelectorAll('[role=tab]'));
  function show(i,f){tabs.forEach(function(t,j){var on=j===i;t.setAttribute('aria-selected',on);t.tabIndex=on?0:-1;var p=document.getElementById(t.getAttribute('aria-controls'));if(p)p.hidden=!on;});if(f)tabs[i].focus();post();}
  tabs.forEach(function(t,i){t.addEventListener('click',function(){show(i);});t.addEventListener('keydown',function(e){var k=e.key;if(k==='ArrowRight'||k==='ArrowLeft'){e.preventDefault();show((i+(k==='ArrowRight'?1:tabs.length-1))%tabs.length,true);}});});
});
var fr=document.getElementById('fprev');
function fit(){try{var d=fr.contentDocument;if(!d||!d.body)return;var h=Math.ceil(d.body.getBoundingClientRect().height);if(h&&Math.abs(fr.offsetHeight-h)>2){fr.style.height=h+'px';post();}}catch(e){}}
if(fr){fr.addEventListener('load',function(){try{var d=fr.contentDocument,s=d.createElement('style');s.textContent='.ff-header{display:none!important}';d.head.appendChild(s);
  if(window.ResizeObserver)new ResizeObserver(fit).observe(d.body);}catch(e){}fit();setTimeout(fit,400);});
  [].slice.call(document.querySelectorAll('.fchip')).forEach(function(c){c.addEventListener('click',function(){
    [].slice.call(document.querySelectorAll('.fchip')).forEach(function(x){x.classList.toggle('on',x===c);});fr.src=c.getAttribute('data-src');});});}
var last=0;function post(){var h=Math.ceil(document.body.getBoundingClientRect().height);if(h!==last){last=h;try{window.parent.postMessage({type:"ufc-iframe-height",height:h},"*");}catch(e){}}}
window.addEventListener('load',post);window.addEventListener('resize',post);if(window.ResizeObserver)new ResizeObserver(post).observe(document.body);setInterval(post,1500);
})();</script>"""


def page(kind, C, F, me):
    S = me["soup"]
    css = S.select_one("style").string
    hdr = clean(S.select_one("div.ff-header"))
    t = hdr.select_one(".ff-title"); t.string = t.get_text().replace("· Fight Form", f"· {LABEL[kind]}")
    legend = S.select_one("div.legend"); xpl = S.select_one("details.xpl"); foot = clean(S.select_one("div.ff-foot"))
    note = ('<div class="legend">Every number here is the same as on that fight\'s preview. ' + (legend.get_text(strip=True) if legend else "") + "</div>")
    explain = str(clean(xpl)) if xpl else ""
    if kind == "moneylines": body = ml_block(F)
    elif kind == "props": body = props_block(F)
    else: body = tabs("top", [("fights", "Fights", fights_block(F)), ("ml", "Moneylines", ml_block(F)), ("props", "Props", props_block(F))])
    ev = hdr.select_one(".ff-title").get_text()
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="color-scheme" content="light only"><title>{ev}</title><style>{css}{EXTRA_CSS}</style></head>'
            f'<body class="cardpage" data-kind="{kind}">{hdr}<div class="panel">{body}{note}{explain}</div>{foot}{JS}</body></html>\n')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", default="ufc_334"); a = ap.parse_args()
    C, F = load(a.slug); me = next(f for f in F if f["main"])
    out = REPO / "embeds" / a.slug
    for kind, fn in (("card", "card.html"), ("moneylines", "moneylines.html"), ("props", "props.html")):
        (out / fn).write_text(page(kind, C, F, me))
    pend_ = [f'{f["a"]} vs {f["b"]}' for f in F if f["pending"]]
    print(f"card tables: card.html, moneylines.html, props.html in embeds/{a.slug} from {len(F)} fight previews; line pending: {', '.join(pend_) or 'none'}")


if __name__ == "__main__":
    main()
