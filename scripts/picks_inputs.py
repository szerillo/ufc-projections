#!/usr/bin/env python3
"""Weekly public-picks inputs for the UFC Model sheet (rules v4.7): Tapology + MMA Junkie.

Collect (Sean's Chrome, one page view per site per pull, no logins):
  * Tapology event page, "Tapology Predictions" section. Run TAPOLOGY_JS (below) in a tab on
    the event page; it returns rows [last name, pick %, KO %, SUB %, DEC %]. The method %
    are shares of that fighter's picks (they sum to 100). Save as tapology.json:
        {"source": ..., "pulled_at": ..., "rows": [[name, pick, ko, sub, dec], ...]}
    Paste fallback (if the page is blocked): copy the section text; parse_tapology_text()
    reads "Name NN%" lines. Pasted text carries pick % only (the method bars are graphics).
  * MMA Junkie "Make your predictions" poll post. Paste the poll results text;
    parse_junkie_text() reads "Name ... NN%" lines. Save as junkie.txt.

Fill (no sheet writes here): maps every value to its sheet cell using the sheet's own row
order, read from the Calculator / Main Card / Prelims tabs (names in cols A:B or B:C).

  Calculator  C = Tapology dog pick share (0-1)        D = Junkie dog pick share (0-1)
  Main Card / Prelims  AD, AE = Tapology dog DEC, KO share of dog's wins
                       AH, AI = Tapology fav DEC, KO share of fav's wins   (SUB = 1 - DEC - KO)
                       AP, AQ = Markov dog / fav P(dec | win)
  Calculator  J = Markov dog win % (shrunk)

  python3 scripts/picks_inputs.py --rows rows.json --tapology tapology.json \
      [--junkie junkie.txt] [--markov data/cards/<slug>.json] --out fill.csv
rows.json: {"calc": {"2": ["Josh Hokit","Ciryl Gane"], ...}, "main": {...}, "prelims": {...}}
(row -> [dog, fav]) as read from the sheet.
"""
import argparse, csv, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from card_overrides import same, _norm  # noqa: E402

TAPOLOGY_JS = r"""
const h=[...document.querySelectorAll('h3,h4')].find(e=>/Tapology Predictions/i.test(e.innerText));
const rows=[...h.parentElement.querySelectorAll('.chartRow')];
const w=(r,c)=>{const e=r.querySelector('.total_bar.flex .'+c+'_bar');const m=(e&&e.getAttribute('style')||'').match(/width:\s*([\d.]+)%/);return m?+(+m[1]).toFixed(1):null;};
rows.map(r=>[r.querySelector('.chartLabel').textContent.trim(),parseInt(r.querySelector('.number').textContent),w(r,'tko'),w(r,'sub'),w(r,'dec')]);
"""


def match(last, full):
    """Tapology labels are last names (accents kept); match to a full sheet name."""
    a, b = _norm(last), _norm(full)
    return bool(a) and (b == a or b.endswith(" " + a) or b.split()[-1] == a.split()[-1] or same(last, full))


def parse_tapology_text(txt):
    return [[m.group(1).strip(), int(m.group(2)), None, None, None] for m in re.finditer(r"^\s*([^\d%\n]+?)\s+(\d{1,3})%\s*$", txt, re.M)]


def parse_junkie_text(txt):
    out = {}
    for m in re.finditer(r"([A-Za-z'.\- ]+?)\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*%", txt):
        out[m.group(1).strip()] = float(m.group(2))
    return out


def lookup(rows, name):
    hits = [r for r in rows if match(r[0], name)]
    return hits[0] if len(hits) == 1 else None


def pct(x):
    return None if x is None else round(x / 100.0, 3)


def build(sheet_rows, tap, junk, markov):
    out, issues = [], []
    mk = {}
    if markov:
        for f in markov["fights"]:
            for x in f["fighters"]:
                mk[x["name"]] = x
    for tab in ("calc", "main", "prelims"):
        for row, (dog, fav) in sorted(sheet_rows.get(tab, {}).items(), key=lambda kv: int(kv[0])):
            td, tf = lookup(tap, dog), lookup(tap, fav)
            if not td or not tf:
                issues.append(f"{tab} row {row}: no unique Tapology row for {dog if not td else fav}")
            if tab == "calc":
                if td:
                    out.append([tab, f"C{row}", dog, pct(td[1]), "Tapology dog pick share"])
                if junk:
                    jd = next((v for k, v in junk.items() if match(k, dog)), None)
                    out.append([tab, f"D{row}", dog, pct(jd) if jd is not None else "", "Junkie dog pick share" + ("" if jd is not None else " (not found)")])
                m = next((v for k, v in mk.items() if same(k, dog)), None)
                if m and m.get("model_win_shrunk") is not None:
                    out.append([tab, f"J{row}", dog, round(m["model_win_shrunk"] / 100, 3), "Markov dog win % (shrunk)"])
            else:
                for (col_dec, col_ko, t, nm) in (("AD", "AE", td, dog), ("AH", "AI", tf, fav)):
                    if t and t[2] is not None:
                        out.append([tab, f"{col_dec}{row}", nm, pct(t[4]), "Tapology DEC share of wins"])
                        out.append([tab, f"{col_ko}{row}", nm, pct(t[2]), "Tapology KO share of wins"])
                for col, nm in (("AP", dog), ("AQ", fav)):
                    m = next((v for k, v in mk.items() if same(k, nm)), None)
                    if m and m.get("dec_share_of_wins") is not None:
                        out.append([tab, f"{col}{row}", nm, round(m["dec_share_of_wins"] / 100, 3), "Markov P(dec | win)"])
    return out, issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--tapology", required=True)
    ap.add_argument("--junkie")
    ap.add_argument("--markov")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tp = Path(a.tapology)
    tap = json.load(open(tp))["rows"] if tp.suffix == ".json" else parse_tapology_text(tp.read_text())
    junk = parse_junkie_text(Path(a.junkie).read_text()) if a.junkie and Path(a.junkie).exists() else None
    markov = json.load(open(a.markov)) if a.markov else None
    out, issues = build(json.load(open(a.rows)), tap, junk, markov)
    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tab", "cell", "fighter", "value", "what"])
        w.writerows(out)
    print(f"{len(out)} cells -> {a.out}")
    for i in issues:
        print("ISSUE:", i)


if __name__ == "__main__":
    main()
