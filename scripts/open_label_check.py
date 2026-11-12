#!/usr/bin/env python3
"""Open-line labels on fight pages (pre-registered Block 53, rule O1).

A fight page can show several "open" prices from different sources (the sheet's BFO opener, the archive's first price,
BettingPros' opening line). If a page shows two or more DIFFERENT open values, every one of their labels must name its
source; otherwise a reader takes two numbers for the same thing. RED lists each page and label.

    python3 -I scripts/open_label_check.py <base_url> [event_slug ...]    # default: every event with sheet data
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import urllib.request

from playwright.async_api import async_playwright

SOURCES = ("sheet", "bfo", "bettingpros", "archive", "consensus", "first archived")
OPENISH = re.compile(r"\bopen|first seen|first archived", re.I)
JS = """() => { const out = [];
  document.querySelectorAll('.kv').forEach(k => { const s = k.querySelectorAll('span'); if (s.length >= 2) out.push([s[0].textContent.trim(), s[1].textContent.trim()]); });
  document.querySelectorAll('tr').forEach(tr => { const td = tr.querySelectorAll('td'); if (td.length >= 2) out.push([td[0].textContent.trim(), td[1].textContent.trim()]); });
  return out; }"""


def a_prob(text: str) -> float | None:
    """Fighter A's probability from a shown value: a percent if present, else the no-vig of the two American prices."""
    m = re.search(r"(\d+(?:\.\d+)?)%", text)
    if m:
        return float(m.group(1)) / 100
    ml = [int(x) for x in re.findall(r"(?<![\d.])([+-]\d{3,4})(?![\d.])", text)]
    if len(ml) >= 2:
        imp = lambda o: 100 / (o + 100) if o > 0 else -o / (-o + 100)
        a, b = imp(ml[0]), imp(ml[1])
        return a / (a + b)
    return None


async def main() -> int:
    base = sys.argv[1].rstrip("/")
    slugs = sys.argv[2:]
    pages = []
    idx = json.load(urllib.request.urlopen(f"{base}/form/data/index.json"))
    events = [e["slug"] for e in (idx.get("events") or []) + (idx.get("upcoming") or []) if isinstance(e, dict) and e.get("slug")]
    for slug in slugs or events:
        try:
            ev = json.load(urllib.request.urlopen(f"{base}/form/data/events/{slug}.json"))
        except Exception:  # noqa: BLE001
            continue
        for f in ev.get("fights") or []:
            if (f.get("sheet") or {}).get("open") is not None or slugs:
                pages.append((slug, f["n"]))
    bad, multi = [], 0
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page()
        await pg.goto(f"{base}/index.html"); await pg.wait_for_timeout(1500)
        for slug, n in pages:
            await pg.evaluate("(h) => { location.hash = h; }", f"#/fight/{slug}/{n}"); await pg.wait_for_timeout(700)
            rows = [(lab, val) for lab, val in await pg.evaluate(JS) if OPENISH.search(lab)]
            vals = [(lab, a_prob(val)) for lab, val in rows]
            vals = [(lab, p) for lab, p in vals if p is not None]
            distinct = len({round(p, 3) for _, p in vals}) >= 2 and max(p for _, p in vals) - min(p for _, p in vals) > 0.005
            if distinct:
                multi += 1
                unl = [lab for lab, _ in vals if not any(s in lab.lower() for s in SOURCES)]
                if unl:
                    bad.append(f"{slug} fight {n}: {len(vals)} different open values; unlabelled source: {unl}")
        await b.close()
    print(f"O1: {len(pages)} fight pages read, {multi} show 2+ different open values, {len(bad)} without source labels")
    for x in bad[:40]:
        print("  -", x)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
