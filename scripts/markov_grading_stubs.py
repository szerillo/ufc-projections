#!/usr/bin/env python3
"""
Grading-only card files for Markov window cards 1-4 and 6, which have no weekly doc in markov/.

Source per card: the ARCHIVE block (pre-registered win %, P(dec), expected minutes, round split) and
the duration table's market GTD, transcribed from the project copies of the weekly docs
(audits/markov_window/archive_inputs.txt), plus each doc's D-code list with its listed dog price.
Sides (dog/fav) and market_odds come from the Fight Form event's pre-start close, because the docs
list only the dog price. Flags were written as prose and are not carried. Files are marked partial.
Existing card files are never overwritten.
Usage: python3 scripts/markov_grading_stubs.py [--write]
"""
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from build_form import name_match  # noqa: E402

SRC = REPO / "audits" / "markov_window" / "archive_inputs.txt"
CARDS = [  # (window index, form event file stem, engine, project doc)
    (1, "2026-09-19-ufc-331-van-vs-pantoja-2", "V4.1", "Markov__UFC_331_Van_vs_Pantoja_2_V41_Output.md"),
    (2, "2026-09-26-ufc-fight-night-rosas-jr-vs-barcelos", "V4.1b", "Markov__UFC_Vegas121_Rosas_vs_Barcelos_V41b_Output.md"),
    (3, "2026-10-03-ufc-332-silva-vs-wang", "V4.1b", "Markov__UFC_332_Silva_vs_Wang_V41b_Output.md"),
    (4, "2026-10-10-ufc-fight-night-allen-vs-duncan", "V4.1b", "Markov__UFC_FN_Allen_vs_Duncan_V41b_Output.md"),
    (6, "2026-10-24-ufc-333-volkanovski-vs-evloev", "V4.1b", "Markov__UFC_333_Volkanovski_vs_Evloev_V41b_Output.md"),
]
DCODE = {2: [("Ilimbek Akylbek Uulu", 228)], 3: [("Alden Coria", 124), ("Lucas Armand", 440), ("Bruce Whitehead", 615)],
         4: [("Otari Tanzilovi", 188), ("Allen Frye Jr.", 258)], 6: [("Losene Keita", 115), ("Colby Thicknesse", 410), ("Noah Gugnon", 130)]}
EXCLUDE = {("Melissa Amaya", "Valesca Machado")}  # opponent changed before the card (audit exclusion)


def blocks():
    out, cur = {}, None
    for line in SRC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"### arch/c(\d+)_\w+\.(tsv|gtd)$", line)
        if m:
            cur = (int(m.group(1)), m.group(2)); out[cur] = []; continue
        if cur and line.strip() and not line.startswith("#"):
            out[cur].append(line)
    return out


def american(p):
    return None if p is None else (round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p))


def build(i, stem, engine, doc, B):
    ev = json.loads((REPO / "form" / "data" / "events" / f"{stem}.json").read_text())
    rows = [l.split("\t") for l in B[(i, "tsv")]]
    gtd = [None if x == "NA" else float(x) for x in " ".join(B[(i, "gtd")]).split()]
    assert len(rows) == len(gtd), (i, len(rows), len(gtd))
    fights, arch, akey, korder = [], [], {}, {}
    for k, (r, g) in enumerate(zip(rows, gtd), 1):
        a, b = [x.strip() for x in r[0].split(" vs ")]
        if (a, b) in EXCLUDE:
            continue
        v = [float(x) for x in r[1:]]
        sh, raw, pdec, expm, rd = (v[0], None, v[1], v[2], v[3:]) if engine == "V4.1" else (v[0], v[1], v[2], v[3], v[4:])
        ff = next((f for f in ev["fights"] if (name_match(f["a"]["name"], a) and name_match(f["b"]["name"], b))
                   or (name_match(f["a"]["name"], b) and name_match(f["b"]["name"], a))), None)
        assert ff, (i, a, b)
        flip = not (name_match(ff["a"]["name"], a) and name_match(ff["b"]["name"], b))
        c = (ff.get("odds") or {}).get("close") or {}
        pa = None if c.get("p") is None else (1 - c["p"] if flip else c["p"])
        oa, ob = (c.get("mb"), c.get("ma")) if flip else (c.get("ma"), c.get("mb"))
        sa = None if pa is None else ("dog" if pa < 0.5 else "fav")
        sb = None if sa is None else ("fav" if sa == "dog" else "dog")
        rounds = ff.get("sched") or (5 if rd[3] or rd[4] else 3)
        na, nb = (ff["b"]["name"], ff["a"]["name"]) if flip else (ff["a"]["name"], ff["b"]["name"])  # Fight Form spellings, so the page joins results
        akey[a] = na; akey[b] = nb; korder[a] = korder[b] = k
        fights.append({"order": k, "bout": f"{a} vs {b}", "weight_class": ff.get("wc"), "rounds": rounds, "is_main_event": k == 1,
                       "fighters": [{"name": na, "side": sa, "market_odds": oa, "model_win_shrunk": round(sh, 1),
                                     "model_win_raw": None if raw is None else round(raw, 1), "dec_share_of_wins": None, "badges": []},
                                    {"name": nb, "side": sb, "market_odds": ob, "model_win_shrunk": round(100 - sh, 1),
                                     "model_win_raw": None if raw is None else round(100 - raw, 1), "dec_share_of_wins": None, "badges": []}],
                       "duration": {"p_dec": pdec, "market_gtd_devig": g, "gap": None if g is None else round(pdec - g, 1),
                                    "round_dist": rd[:rounds], "exp_minutes": expm},
                       "result": None})
        arch.append("\t".join(r))
    vet = []
    for side, odds in DCODE.get(i, []):
        assert side in korder, (i, side)  # exact archive name, never a loose match
        vet.append({"fight_order": korder[side], "side": akey[side], "market_odds": odds, "code": "D",
                    "reason": "D-code: underdog with three or fewer UFC fights from a minor feeder promotion. Automatic no-bet."})
    slug = stem[11:]
    return slug, {"slug": slug, "title": ev["name"], "date": stem[:10], "venue": ev.get("location") or "", "engine_version": engine,
                  "partial": True, "grading_stub": True,
                  "notes": ["Grading stub: built from the ARCHIVE block and duration table of the weekly doc (project copy), which was published before the card.",
                            "Sides and market odds are the Fight Form pre-start close; flags were prose in the doc and are not included."
                            + (" V4.1 card: no raw column." if engine == "V4.1" else "")],
                  "archive_tsv": "\n".join(arch), "fights": fights, "duration_flags": [], "ml_flags": [], "prop_notes": [], "vetoes": vet,
                  "source_doc": "project: " + doc, "grading_window_index": i}


def main():
    B = blocks(); man_p = REPO / "data" / "manifest.json"; man = json.loads(man_p.read_text()); have = {c["slug"] for c in man["cards"]}
    for i, stem, engine, doc in CARDS:
        slug, card = build(i, stem, engine, doc, B)
        p = REPO / "data" / "cards" / f"{slug}.json"
        print(f"card {i}: {slug} {len(card['fights'])} fights, {len(card['vetoes'])} D-code, sides from close on "
              f"{sum(1 for f in card['fights'] if f['fighters'][0]['side'])}")
        if "--write" in sys.argv:
            if p.exists():
                print("  exists, not overwritten"); continue
            p.write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
            if slug not in have:
                man["cards"].append({"slug": slug, "title": card["title"], "date": card["date"], "status": "graded", "fights": len(card["fights"]),
                                     "partial": True, "summary": "grading stub (archive block only)"})
    if "--write" in sys.argv:
        man["cards"].sort(key=lambda c: c["date"], reverse=True)
        man_p.write_text(json.dumps(man, indent=1) + "\n")


if __name__ == "__main__":
    main()
