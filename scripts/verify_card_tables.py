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
                if part == "length" and "lrow" in cls:   # compact row: GTD over ITD in each cell = the preview's two fight length rows
                    cur = int(tr.select_one(".cg-n").get_text()); seen.add(cur)
                    if tr.select_one(".cg-pend"): continue
                    cells = tr.find_all("td", recursive=False)[2:]
                    t = toks(tr.select_one(".lab")) and []   # labels carry no numbers
                    got = [[x for x in toks(BeautifulSoup(str(c.select(".l2")[k]), "html.parser")) if x != "n/a"] for k in (0, 1) for c in cells]
                    want = [[x for x in row if x != "n/a"] for row in prev[cur]["length"]]
                    flat = lambda rows: [x for r in rows for x in r]
                    g_ = [x for x in flat(got[:4])], [x for x in flat(got[4:])]
                    checked += 1; nums += sum(len(x) for x in g_)
                    if cur in pend: fails.append(f"{fn} length fight {cur}: numbers shown for a Line pending fight")
                    elif list(g_) != want: fails.append(f"{fn} length fight {cur}: {list(g_)} differs from fight_{cur:02d}.html {want}")
                    continue
                if part == "method" and "mrow" in cls:   # merged row = the preview's model row then its market row, cell by cell
                    cells = tr.find_all("td", recursive=False)[1:]
                    m_ = [x for c in cells for x in toks(c.select_one(".m1"))]
                    k_ = [x for c in cells for x in toks(c.select_one(".m2")) + (toks(c.select_one(".ech")) if c.select_one(".ech") else [])]
                    checked += 1; nums += len(m_) + len(k_)
                    if cur in pend: fails.append(f"{fn} method fight {cur}: numbers shown for a Line pending fight")
                    else:
                        rows_ = prev[cur]["method"]
                        if not any(m_ == rows_[i] and k_ == rows_[i + 1] for i in range(0, len(rows_) - 1, 2)):
                            fails.append(f"{fn} method fight {cur}: {m_} / {k_} is not a model + market row pair of fight_{cur:02d}.html")
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
