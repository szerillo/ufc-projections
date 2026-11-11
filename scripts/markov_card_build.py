#!/usr/bin/env python3
"""Build a full Duration Model card JSON from the weekly trio.

  markov/<Name>_V41b_Output.md      analysis doc (tables + ARCHIVE)
  markov/<Name>_Raw_Stats.csv       per-fighter tape and projections
  markov/<Name>_V41b_Output.flags.json   flags / vetoes / prop notes (optional)

Writes data/cards/<slug>.json and refreshes data/manifest.json. Numbers come
only from those files; anything they do not carry stays null.

Badges: SYN and §1d from the CSV DataQuality text; THIN SAMPLE for a fighter
whose DataQuality says THIN, or who has 3 or fewer UFC fights on file and no
§1d (pre-UFC Sherdog) data entered.

  python3 scripts/markov_card_build.py markov/UFC_334_Gane_vs_Hokit_V41b_Output.md \
      --slug ufc-334-gane-vs-hokit --title "UFC 334: Gane vs Hokit"
"""
import argparse, csv, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import markov_md_to_json as m2j  # noqa: E402
from card_overrides import same  # noqa: E402


def f_(x):
    try:
        return float(str(x).replace("+", ""))
    except (TypeError, ValueError):
        return None


def ufc_fights(name):
    p = REPO / "form" / "data" / "fighters" / (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") + ".json")
    return len(json.load(open(p)).get("fights") or []) if p.exists() else None


def badges_for(row):
    dq = row.get("DataQuality") or ""
    b = []
    if "SYN" in dq:
        b.append("SYN")
    if "§1d" in dq:
        b.append("§1d")
    nf = ufc_fights(row["Fighter"])
    if "THIN" in dq or ((nf is None or nf <= 3) and "§1d" not in dq):
        b.append("THIN SAMPLE")
    if "D-CODE" in dq.upper() and "CONDITIONAL" not in dq.upper():
        b.append("D-CODE")
    return b


def build(md, slug, title, csv_path=None, flags_path=None):
    card = m2j.convert(md)
    card["slug"], card["title"] = slug, title
    rows = list(csv.DictReader(open(csv_path))) if csv_path and csv_path.exists() else []
    # sheet-input rows with no dog (no line yet) name the fighter in each DEC% cell: "Alat 69%"
    txt = md.read_text(encoding="utf-8")
    srows = [r for r in m2j.table(txt, r"## SHEET INPUT TABLE[^\n]*\n") if r and r[0].isdigit()]
    for f, sr in zip(card["fights"], srows):
        if f["fighters"][0]["side"] is None and len(sr) > 5:
            for cell in sr[4:6]:
                mm = re.match(r"\s*([A-Za-z'.\- ]+?)\s+([\d.]+)%", cell)
                if mm:
                    for x in f["fighters"]:
                        if any(t.lower().startswith(mm.group(1).lower()) for t in x["name"].split()):
                            x["dec_share_of_wins"] = float(mm.group(2))
    for f in card["fights"]:
        for x in f["fighters"]:
            r = next((r for r in rows if same(r["Fighter"], x["name"])), None)
            if not r:
                continue
            f["weight_class"] = f["weight_class"] or r["WeightClass"].replace("Womens", "Women's")
            mo = r.get("MarketOdds", "").strip()
            x["market_odds"] = int(mo.replace("+", "")) if re.fullmatch(r"[+-]?\d+", mo) else x.get("market_odds")
            if r.get("Side") in ("Fav", "Dog"):
                x["side"] = r["Side"].lower()
            x["ss_mean"], x["td_proj"] = f_(r.get("ProjSS")), f_(r.get("ProjTD"))
            x["tape"] = {"age": f_(r["Age"]), "height": r["Height"], "reach": f_(r["Reach"]), "stance": r["Stance"], "record": r["CareerRecord"],
                         "slpm": f_(r["SLpM"]), "sapm": f_(r["SApM"]), "str_acc": f_(r["StrAcc"]), "str_def": f_(r["StrDef"]),
                         "td_avg": f_(r["TDAvg"]), "td_acc": f_(r["TDAcc"]), "td_def": f_(r["TDDef"]), "sub_avg": f_(r["SubAvg"])}
            x["data_quality"] = r.get("DataQuality")
            x["badges"] = sorted(set((x.get("badges") or []) + badges_for(r)))
            for k in ("finish_pct", "finish_ko", "finish_sub", "ss_median", "td_p1", "td_p2", "td_p3", "p_kd"):
                x.setdefault(k, None)
    if flags_path and flags_path.exists():
        fl = json.load(open(flags_path))
        for k in ("duration_flags", "ml_flags", "vetoes", "prop_notes"):
            card[k] = fl.get(k, [])
        card["notes"] = card["notes"][:1] + fl.get("notes_extra", [])
        if fl.get("grading_window_index"):
            card["grading_window_index"] = fl["grading_window_index"]
    full_props = all(x.get("finish_pct") is not None for f in card["fights"] for x in f["fighters"])
    card["partial"] = not full_props
    if card["partial"]:
        card["notes"].append("Per-fighter finish, SS median, TD ladder and P(KD) are in the source doc only; SS mean and TD projection come from the raw-stats CSV.")
    if csv_path:
        card["source_csv"] = f"markov/{csv_path.name}"
    return card


def write_manifest():
    out = REPO / "data" / "cards"
    import datetime as dt
    today = dt.date.today().isoformat()
    cards = []
    for p in out.glob("*.json"):
        d = json.load(open(p))
        cards.append({"slug": d["slug"], "title": d["title"], "date": d["date"], "status": "upcoming" if (d["date"] or "") >= today else "graded",
                      "fights": len(d["fights"]), "partial": bool(d.get("partial")),
                      "summary": f"{len(d.get('duration_flags', []))} duration flags · {len(d.get('ml_flags', []))} ML flags · {len(d.get('vetoes', []))} D-code vetoes"})
    cards.sort(key=lambda c: c["date"] or "", reverse=True)
    json.dump({"cards": cards}, open(REPO / "data" / "manifest.json", "w"), indent=1)
    return cards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--csv")
    ap.add_argument("--flags")
    a = ap.parse_args()
    md = Path(a.md)
    stem = md.name.replace("_V41b_Output.md", "")
    csv_p = Path(a.csv) if a.csv else md.with_name(stem + "_Raw_Stats.csv")
    fl_p = Path(a.flags) if a.flags else md.with_name(md.stem + ".flags.json")
    card = build(md, a.slug, a.title, csv_p, fl_p)
    json.dump(card, open(REPO / "data" / "cards" / f"{a.slug}.json", "w"), indent=1, ensure_ascii=False)
    print(a.slug, len(card["fights"]), "fights; partial" if card["partial"] else "full")
    for c in write_manifest():
        print(" ", c["date"], c["slug"], c["status"], c["summary"])


if __name__ == "__main__":
    main()
