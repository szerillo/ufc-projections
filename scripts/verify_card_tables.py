#!/usr/bin/env python3
"""Check the card-level pages (card.html, moneylines.html, props.html) against the fight previews they were built from.

    python3 -I scripts/verify_card_tables.py --slug ufc_334

Every data row must be, number for number, a row of that fight's own preview (fight_NN.html, same section), and every
fight must appear in every table (as numbers, or as Line pending when its preview is Line pending). Header, odds stamp
and footer must be the main event preview's. Exit 1 on any failure.
"""
import argparse, json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup
REPO = Path(__file__).resolve().parents[1]
NUM = re.compile(r"[+-]?\d[\d.,]*%?|n/a")


def toks(node): return NUM.findall(node.get_text(" ", strip=True))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", default="ufc_334"); a = ap.parse_args()
    d = REPO / "embeds" / a.slug; C = json.loads((d / "card.json").read_text())
    prev, pend = {}, set()
    for c in C["card"]:
        n = c["fight"]; S = BeautifulSoup((d / f"fight_{n:02d}.html").read_text(), "html.parser")
        if json.loads((d / f"fight_{n:02d}.registry.json").read_text()).get("proj_src") == "line_pending": pend.add(n)
        prev[n] = {k: [toks(tr) for tr in S.select(f'div.stk[data-part="{k}"] tbody > tr')] for k in ("ml", "length", "method")}
        if c["segment"] == "Main event": me = S
    fails, checked, nums = [], 0, 0
    hdr_me = me.select_one(".ff-header").get_text(" ", strip=True)
    for fn in ("card.html", "moneylines.html", "props.html"):
        S = BeautifulSoup((d / fn).read_text(), "html.parser")
        h = S.select_one(".ff-header").get_text(" ", strip=True)
        if re.sub(r"· (Fight Form|Moneylines|Props)", "", h) != re.sub(r"· Fight Form", "", hdr_me): fails.append(f"{fn}: header differs from the main event preview")
        if S.select_one(".ff-foot").get_text(" ", strip=True) != me.select_one(".ff-foot").get_text(" ", strip=True): fails.append(f"{fn}: footer stamps differ")
        for st in S.select("div.stk[data-part]"):
            part = st["data-part"]; seen = set(); cur = None
            for tr in st.select("tbody > tr"):
                cls = tr.get("class") or []
                if "sec" in cls: continue
                if "cg" in cls: cur = int(tr.select_one(".cg-n").get_text()); seen.add(cur); continue
                if part == "ml":
                    cur = int(tr.select_one("td.n").get_text()); seen.add(cur)
                    tr.select_one("td.n").decompose(); o = tr.select_one(".opp")
                    if o: o.decompose()
                if tr.select_one(".cg-pend"):
                    if cur not in pend: fails.append(f"{fn} {part} fight {cur}: shows Line pending but its preview has numbers")
                    continue
                t = toks(tr); checked += 1; nums += len(t)
                if cur in pend: fails.append(f"{fn} {part} fight {cur}: numbers shown for a Line pending fight")
                elif t not in prev[cur][part]: fails.append(f"{fn} {part} fight {cur}: row {t} is not a row of fight_{cur:02d}.html")
            want = set(prev) if part == "ml" else None
            if part == "ml":
                miss = want - seen
                if miss: fails.append(f"{fn} ml ({st.select_one('.stk-h').get_text(strip=True)}): fights missing {sorted(miss)}")
        if fn != "moneylines.html":   # props tabs together must cover every fight
            for part in ("length", "method"):
                seen = {int(x.get_text()) for st in S.select(f'div.stk[data-part="{part}"]') for x in st.select(".cg-n")}
                if seen != set(prev): fails.append(f"{fn} {part}: fights missing {sorted(set(prev) - seen)}")
    for f_ in fails: print("  FAIL", f_)
    print(f"CARD TABLES: {checked} rows / {nums} numbers checked against the fight previews; line pending: {sorted(pend) or 'none'}; {len(fails)} failures")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
