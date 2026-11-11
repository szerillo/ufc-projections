"""Scheduled card sync check: compare each upcoming site card against UFC.com and report.

REPORT ONLY. It never edits event files, overrides or the index. Its output is a markdown
diff in the ufc-site-card-sync action vocabulary (CANCEL, REPLACE, ADD, ORDER, TITLE,
ROUNDS, SPLIT) so a person can decide what goes into data/card_overrides.json.

UFC.com is the authority for bout list, order and the main card / prelim split.
Event URL: 'UFC 334: ...' -> /event/ufc-334; Fight Nights -> /event/ufc-fight-night-<month>-<dd>-<yyyy>.

    python3 -I scripts/card_sync_check.py                   # all upcoming cards in form/data/index.json
    python3 -I scripts/card_sync_check.py --html page.html --event form/data/events/<slug>.json
    python3 -I scripts/card_sync_check.py --ufc-slug ufc-fight-night-november-21-2026 --date 2026-11-21

Exit code 0 = in sync, 1 = differences found, 2 = could not read a source.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as htmllib
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from card_overrides import n_main, same  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SECTIONS = [("main-card", "main"), ("prelims-card", "prelims"), ("early-prelims", "early")]
UA = "Mozilla/5.0 (card-sync-check; github.com/szerillo/ufc-projections)"


def ufc_slug_for(name: str, date: str) -> str:
    m = re.match(r"\s*UFC\s+(\d{3})\b", name or "")
    if m:
        return f"ufc-{m.group(1)}"
    d = dt.date.fromisoformat(date)
    return f"ufc-fight-night-{d.strftime('%B').lower()}-{d.day:02d}-{d.year}"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_ufc(page: str) -> list[dict]:
    """Bouts in page order: segment, red, blue, class text. Regex parse of the server HTML
    (no external deps on the Actions runner)."""
    marks = sorted((m.start(), seg) for sid, seg in SECTIONS
                   for m in re.finditer(rf'id="{sid}"', page))
    out = []
    for m in re.finditer(r'<div class="c-listing-fight"[^>]*>', page):
        seg = None
        for pos, s in marks:
            if pos < m.start():
                seg = s
        if seg is None:
            continue
        chunk = page[m.start(): m.start() + 20000]
        nxt = chunk.find('<div class="c-listing-fight"', 10)
        if nxt > 0:
            chunk = chunk[:nxt]
        def corner(c):
            mm = re.search(rf'c-listing-fight__corner-name--{c}"[^>]*>(.*?)</div>', chunk, re.S)
            return _text(mm.group(1)) if mm else ""
        cls = re.search(r'c-listing-fight__class-text">(.*?)</div>', chunk, re.S)
        out.append({"seg": seg, "a": corner("red"), "b": corner("blue"),
                    "cls": _text(cls.group(1)) if cls else ""})
    return out


def bout_is(a, b, x, y):
    return (same(a, x) and same(b, y)) or (same(a, y) and same(b, x))


def diff(real: list[dict], site_fights: list[dict]) -> list[str]:
    rows, used = [], set()
    nm_site = n_main(site_fights)
    for i, r in enumerate(real):
        title_real = "title" in r["cls"].lower()
        j = next((k for k, f in enumerate(site_fights)
                  if k not in used and bout_is(f["a"]["name"], f["b"]["name"], r["a"], r["b"])), None)
        if j is None:
            # one side matches -> replacement
            j = next((k for k, f in enumerate(site_fights) if k not in used and
                      any(same(f[s]["name"], r[t]) for s in "ab" for t in "ab")), None)
            if j is None:
                rows.append(f"ADD | {i+1} | {r['a']} vs {r['b']} | {r['seg']} | {r['cls']}")
                continue
            used.add(j)
            f = site_fights[j]
            rows.append(f"REPLACE | {i+1} | site has {f['a']['name']} vs {f['b']['name']}; real {r['a']} vs {r['b']}")
        else:
            used.add(j)
            f = site_fights[j]
        if j != i:
            rows.append(f"ORDER | {i+1} | {r['a']} vs {r['b']} is site position {j+1}")
        if bool(f.get("title")) != title_real:
            rows.append(f"TITLE | {i+1} | {r['a']} vs {r['b']}: site title={bool(f.get('title'))}, UFC.com '{r['cls']}'")
        want = 5 if (i == 0 or title_real) else 3
        if f.get("sched") and f["sched"] != want:
            rows.append(f"ROUNDS | {i+1} | {r['a']} vs {r['b']}: site {f['sched']}R, expected {want}R")
        site_seg = "main" if j < nm_site else "prelims"
        real_seg = "main" if r["seg"] == "main" else "prelims"
        if site_seg != real_seg:
            rows.append(f"SPLIT | {i+1} | {r['a']} vs {r['b']}: site shows {site_seg}, UFC.com {r['seg']}")
    for k, f in enumerate(site_fights):
        if k not in used:
            rows.append(f"CANCEL | - | {f['a']['name']} vs {f['b']['name']} on site, not on UFC.com")
    n_real_main = sum(1 for r in real if r["seg"] == "main")
    if real and n_real_main != nm_site:
        rows.append(f"SPLIT | - | site heuristic shows {nm_site} main card bouts, UFC.com lists {n_real_main}")
    return rows


def report(label: str, real: list[dict], site: dict | None) -> tuple[str, int]:
    lines = [f"### {label}", ""]
    if not real:
        return "\n".join(lines + ["Could not read any bouts from UFC.com (page layout changed or blocked).", ""]), 2
    if site is None:
        lines.append(f"No site event file yet (the build publishes it once the odds feed lists the card). "
                     f"UFC.com has {len(real)} bouts: " +
                     "; ".join(f"{r['a']} vs {r['b']} ({r['seg']})" for r in real))
        return "\n".join(lines + [""]), 0
    rows = diff(real, site["fights"])
    if not rows:
        lines.append(f"In sync: {len(real)} bouts, order, titles, rounds and main card split match UFC.com.")
        return "\n".join(lines + [""]), 0
    lines += ["| Action | Real order | Detail |", "|---|---|---|"]
    lines += ["| " + r.split(" | ", 1)[0] + " | " + " | ".join(r.split(" | ")[1:]) + " |" for r in rows]
    lines += ["", "Proposed only. Fixes go in data/card_overrides.json after a person checks them."]
    return "\n".join(lines + [""]), 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="saved UFC.com event page (offline test)")
    ap.add_argument("--event", help="site event JSON to compare (default: from index.json)")
    ap.add_argument("--ufc-slug")
    ap.add_argument("--date")
    ap.add_argument("--out", help="write the markdown report here too")
    a = ap.parse_args(argv)
    jobs = []
    if a.html or a.ufc_slug:
        site = json.load(open(a.event)) if a.event else None
        jobs.append((a.ufc_slug or Path(a.html).stem, a.html, a.ufc_slug or Path(a.html).stem, site))
    else:
        idx = json.load(open(REPO / "form" / "data" / "index.json"))
        for u in idx.get("upcoming", []):
            ev = REPO / "form" / "data" / "events" / f"{u['slug']}.json"
            jobs.append((u["name"], None, ufc_slug_for(u["name"], u["date"]),
                         json.load(open(ev)) if ev.exists() else None))
    parts, worst = [f"## Card sync check {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%MZ}", ""], 0
    for label, path, slug, site in jobs:
        try:
            page = open(path, encoding="utf-8").read() if path else fetch(f"https://www.ufc.com/event/{slug}")
        except Exception as e:  # noqa: BLE001
            parts.append(f"### {label}\n\nUFC.com fetch failed for /event/{slug}: {e.__class__.__name__}\n")
            worst = max(worst, 2)
            continue
        text, code = report(f"{label} (ufc.com/event/{slug})", parse_ufc(page), site)
        parts.append(text)
        worst = max(worst, code)
    md = "\n".join(parts)
    print(md)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    return worst


if __name__ == "__main__":
    sys.exit(main())
