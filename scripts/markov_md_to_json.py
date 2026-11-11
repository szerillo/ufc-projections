#!/usr/bin/env python3
"""
Turn a weekly Markov output doc (markov/*_V41b_Output.md) into a card JSON in the
Duration Model contract (data/cards/{slug}.json + data/manifest.json).

Only what the doc states is carried over: the sheet-input table (dog odds, shrunk / raw
dog win %, decision shares), the duration table (P(dec), market GTD, gap, round split,
expected minutes) and the ARCHIVE block. Per-fighter prop projections and the flag lists
are NOT in a parseable form in the doc, so cards built this way are marked partial.
A full card JSON from the model pipeline always wins: existing non-partial files are never overwritten.
"""
import json, re, sys, datetime as dt
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from build_form import norm, slugify, name_match  # noqa: E402

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def num(s):
    s = re.sub(r"[*%\s]", "", s or "").replace("−", "-").replace("+", "")
    try:
        return float(s)
    except ValueError:
        return None


def table(txt, start_pat):
    m = re.search(start_pat, txt)
    if not m:
        return []
    rows = []
    for line in txt[m.end():].splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            rows.append(cells)
        elif rows and line.strip() and not line.startswith("|"):
            break
    return rows


def convert(fp: Path):
    txt = fp.read_text(encoding="utf-8")
    title = re.sub(r"\s+—.*", "", txt.splitlines()[0].lstrip("# ").strip()).title().replace("Ufc", "UFC").replace(" Vs ", " vs ")
    head = txt.splitlines()[1]
    m = re.search(r"([A-Z][a-z]{2})[a-z]*\s+(\d{1,2}).*?(\d{4})", head)
    date = dt.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))).isoformat() if m else None
    venue = (head.strip("*").split("|")[1].strip() if "|" in head else "")
    eng = "V4.1b" if "V4.1b" in head else ""
    arch = re.search(r"## ARCHIVE.*?```\n(.*?)```", txt, re.S)
    arch_lines = [l for l in arch.group(1).strip().splitlines() if "\t" in l] if arch else []
    sheet = [r for r in table(txt, r"## SHEET INPUT TABLE[^\n]*\n") if r and r[0].isdigit()]
    dur = [r for r in table(txt, r"## 1\. P\(DECISION\)[^\n]*\n") if r and r[0] != "Fight"]
    fights = []
    for i, line in enumerate(arch_lines):
        p = line.split("\t")
        a, b = [x.strip() for x in p[0].split(" vs ", 1)]
        sh, raw, pdec, exp = [float(x) for x in p[1:5]]
        rd = [float(x) for x in p[5:10]]
        srow = sheet[i] if i < len(sheet) else None
        drow = dur[i] if i < len(dur) else None
        five = bool(drow and "5R" in drow[0]) or (rd[3] + rd[4] > 0)
        dog_name = dog_odds = None; badges = []; dog_dec = fav_dec = None
        if srow:
            mm = re.match(r"(.+?)\s*\(([^)]*)\)\s*(\[.*\])?", srow[1])
            if mm:
                short = mm.group(1).strip()
                o = re.search(r"[+\-−]\d+", mm.group(2)); dog_odds = int(o.group(0).replace("−", "-")) if o else None
                tags = (mm.group(3) or "")
                if "SYN" in tags: badges.append("SYN")
                if "D-FLAG" in tags: badges.append("D-CODE")
                la, lb = norm(a).split(), norm(b).split()
                s = norm(short).split()[-1]
                dog_name = a if s in la and s not in lb else b if s in lb and s not in la else (a if sh < 50 else b)
            dog_dec = num(srow[4]); fav_dec = num(re.sub(r"^[^\d]*", "", srow[5]))
        pick = "pickem" if srow and "pickem" in srow[1] else None

        def fighter(nm, win_s, win_r):
            is_dog = dog_name == nm
            return {"name": nm, "side": (pick or ("dog" if is_dog else "fav")) if dog_name else None,
                    "market_odds": dog_odds if is_dog else None, "model_win_shrunk": round(win_s, 1), "model_win_raw": round(win_r, 1),
                    "dec_share_of_wins": dog_dec if is_dog else fav_dec, "badges": [x for x in badges if is_dog or x == "SYN"]}
        f = {"order": i + 1, "bout": f"{a} vs {b}", "weight_class": None, "rounds": 5 if five else 3, "is_main_event": i == 0,
             "fighters": [fighter(a, sh, raw), fighter(b, 100 - sh, 100 - raw)],
             "duration": {"p_dec": pdec, "market_gtd_devig": num(drow[2]) if drow else None, "gap": num(drow[3]) if drow else None,
                          "round_dist": rd if five else rd[:3], "exp_minutes": exp}, "result": None}
        fights.append(f)
    notes = [re.sub(r"\s+", " ", txt.splitlines()[2]).strip()] if len(txt.splitlines()) > 2 and txt.splitlines()[2].strip() else []
    vet = re.search(r"\*\*D-code vetoes:\*\*\s*(.+)", txt)
    vetoes = []
    if vet:
        for f in fights:
            for x in f["fighters"]:
                if "D-CODE" in x["badges"] and x["side"] in ("dog", "pickem"):
                    vetoes.append({"fight_order": f["order"], "side": x["name"], "market_odds": x["market_odds"], "code": "D",
                                   "reason": "D-code: underdog with three or fewer UFC fights from a minor feeder promotion. Automatic no-bet."})
    slug = slugify(title)[:70]
    return {"slug": slug, "title": title, "date": date, "venue": venue, "engine_version": eng, "partial": True,
            "notes": notes + ["Built from the weekly output doc: per-fighter prop projections and flag write-ups are in the source doc, not on this page."],
            "archive_tsv": "\n".join(arch_lines), "fights": fights, "duration_flags": [], "ml_flags": [], "prop_notes": [], "vetoes": vetoes,
            "source_doc": f"markov/{fp.name}"}


def main():
    out = REPO / "data" / "cards"
    out.mkdir(parents=True, exist_ok=True)
    for fp in sorted((REPO / "markov").glob("*.md")):
        card = convert(fp)
        existing = [p for p in out.glob("*.json") if json.load(open(p)).get("date") == card["date"]]
        full = [p for p in existing if not json.load(open(p)).get("partial")]
        if any(json.load(open(p)).get("source_csv") for p in existing):
            continue  # built by markov_card_build.py from the full trio; never downgrade it
        if full:
            # merge: keep the full card, add any fights it is missing from the doc (marked partial)
            d = json.load(open(full[0]))
            have = {norm(f["bout"]) for f in d["fights"]}
            add = [dict(f, partial=True) for f in card["fights"] if norm(f["bout"]) not in have]
            if add and not d.get("_merged_from_doc"):
                d["fights"] = sorted(d["fights"] + add, key=lambda f: f["order"]); d["_merged_from_doc"] = card["source_doc"]
                json.dump(d, open(full[0], "w"), indent=1)
            continue
        json.dump(card, open(out / f"{card['slug']}.json", "w"), indent=1)
    today = dt.date.today().isoformat()
    cards = []
    for p in out.glob("*.json"):
        d = json.load(open(p))
        cards.append({"slug": d["slug"], "title": d["title"], "date": d["date"], "status": "upcoming" if (d["date"] or "") >= today else "graded",
                      "fights": len(d["fights"]), "partial": bool(d.get("partial")),
                      "summary": f"{len(d.get('duration_flags', []))} duration flags · {len(d.get('ml_flags', []))} ML flags · {len(d.get('vetoes', []))} D-code vetoes"})
    cards.sort(key=lambda c: c["date"] or "", reverse=True)
    json.dump({"cards": cards}, open(REPO / "data" / "manifest.json", "w"), indent=1)
    print("cards:", [(c["slug"], c["fights"], c["partial"]) for c in cards])


if __name__ == "__main__":
    main()
