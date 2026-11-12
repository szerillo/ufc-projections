#!/usr/bin/env bash
# One command for Kirk's merge gate (round 7, call 6). Run after Sean republishes the sheet.
#   scripts/rehearse_go_live.sh            (UFC 334 defaults; sharp-tracker checkout at /tmp/st)
# Passes only if: the export is newer than the 01:18 UTC Nov 12 export and under 2 h old; the full Friday refresh is green;
# every planted error is caught; Gordon/Costa/Hasan Listed flags are reported (cleared or still flagged). Changes nothing on main.
set -euo pipefail; export EMBED_PIPELINE=1; cd "$(dirname "$0")/.."   # no lock bless anywhere inside the rehearsal (round 10 B)
CARD="${CARD:-UFC 334: Gane vs. Hokit}"; SLUG="${SLUG:-ufc_334}"; EVENT="${EVENT:-form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json}"; ST="${ST:-/tmp/st}"
OLD="2026-11-12T01:18:40"
bash scripts/friday_refresh.sh "$CARD" "$SLUG" "$EVENT" "$ST" | tee /tmp/_rehearsal.txt
python3 - "$SLUG" "$OLD" <<'PY'
import json, sys, datetime as dt
slug, old = sys.argv[1:3]
x = json.load(open(f"data/pending/{slug}_projections.json")); t = x["published_at"][:19]
age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(t + "+00:00")).total_seconds() / 3600
print(f"export {t} UTC, {age:.1f} h old"); 
if t <= old: sys.exit("FAIL: still the old export; Sean has not republished")
if age > 2: sys.exit("FAIL: export older than 2 h")
lh = json.load(open(f"data/embeds/line_history_{slug}.json"))["fights"]
fl = [f"{k.split('|')[0 if s == 'a' else 1]} {v['listed'][s]['listed']:+d}" for k, v in lh.items() if v.get("listed") for s in "ab" if not v["listed"][s]["ok"]]
print("Listed prices still unverified:", fl or "none")
PY
grep -q "0 mismatches/assertion failures" /tmp/_rehearsal.txt || { echo "FAIL: checks not green"; exit 1; }
python3 -I scripts/verify_fight_embeds.py --slug "$SLUG" --negative | tail -1 | tee /tmp/_neg.txt
python3 -c "import re,sys; m=re.search(r'(\d+)/(\d+) planted errors caught', open('/tmp/_neg.txt').read()); sys.exit(0 if m and m.group(1)==m.group(2) else 'FAIL: negative suite')"
echo "REHEARSAL PASS: ready for Kirk's merge go (nothing merged)"
