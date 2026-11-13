#!/usr/bin/env bash
# Kirk round 22 call 2: the gate for committing Saturday's refreshed embeds to main (after the merge). Checks only; it
# commits and pushes nothing. Run in a main checkout after Sean's Saturday republish and scripts/friday_refresh.sh.
#   scripts/saturday_check.sh
# Passes only if:
#   1 the checkout sits on the current origin/main (fetched now and confirmed with ls-remote), so the push is a fast-forward
#   2 every changed or new file is on the explicit list below (embeds, export, odds, and the refresh's own data files)
#   3 the public scan is clean on the changed files
#   4 the full verifier is clean (0 mismatches) and the Listed report runs
set -euo pipefail; export EMBED_PIPELINE=1; cd /tmp/r35/main
SLUG="${SLUG:-ufc_334}"; EVENT="${EVENT:-form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json}"
git fetch -q origin main
R="$(git ls-remote origin refs/heads/main | cut -f1)"
[ -n "$R" ] && [ "$R" = "$(git rev-parse origin/main)" ] || { echo "SATURDAY CHECK FAIL: cannot confirm origin/main"; exit 1; }
[ "$(git merge-base HEAD $R)" = "$R" ] && [ "$(git rev-list --count $R..HEAD)" = 21 ] || { echo "SATURDAY CHECK FAIL: checkout is at $(git rev-parse --short HEAD), origin/main is ${R:0:8}: pull (or rerun the refresh on the new main) first"; exit 1; }
python3 - "$SLUG" "$EVENT" <<'PY'
import subprocess, sys, re
slug, event = sys.argv[1:3]
# Kirk round 23 call 3: only what a dry-run refresh actually wrote (audits/round23/refresh_writes.txt). The export is not on the
# list: on Saturday it reaches main through Sean's publish, so the refresh copies it unchanged. card.json was not written.
# Kirk round 34: card.json IS written whenever the export changes (its proj_file, published_at and line_pending), so it is listed.
ALLOWED = {f"data/{slug}_odds.json", f"data/embeds/line_history_{slug}.json", f"data/embeds/kalshi_{slug}.json",
           f"form/data/embed_metrics/{slug}.json", event, f"embeds/{slug}/card.json"} | {f"embeds/{slug}/{x}.html" for x in ("card", "moneylines", "props")} | {f"embeds/{slug}/fight_{i:02d}.{x}" for i in range(1, 14) for x in ("html", "registry.json")}
st = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True, check=True).stdout.splitlines()
paths = [l[3:].split(" -> ")[-1] for l in st if l.strip()]
bad = [p for p in paths if p not in ALLOWED]
print(f"  changed files: {len(paths)}; outside the Saturday list: {bad or 'none'}")
open("/tmp/_sat_paths.txt", "w").write("\n".join(paths))
if not paths: sys.exit("SATURDAY CHECK FAIL: nothing changed (did the refresh run?)")
if bad: sys.exit("SATURDAY CHECK FAIL: files outside embeds/export/odds/refresh data changed: " + ", ".join(bad))
PY
# scan_public scans committed changes vs --base; the refresh output is uncommitted here, so pass the changed paths explicitly
python3 -I scripts/scan_public.py --base origin/main --paths $(cat /tmp/_sat_paths.txt) > /tmp/_sat_scan.txt || true
grep -E "PUBLIC SCAN|HIT" /tmp/_sat_scan.txt | head -5
grep -q ", 0 hits" /tmp/_sat_scan.txt || { echo "SATURDAY CHECK FAIL: public scan"; exit 1; }
python3 scripts/verify_fight_embeds.py --slug "$SLUG" > /tmp/_sat_verify.txt 2>&1 || true; grep -E "TOTAL|MISMATCH|^  v" /tmp/_sat_verify.txt | head -4
grep -qE "^TOTAL: [0-9]+/[0-9]+ numbers verified; 0 mismatches/assertion failures" /tmp/_sat_verify.txt || { echo "SATURDAY CHECK FAIL: verifier"; exit 1; }
python3 -I scripts/verify_card_tables.py --slug "$SLUG" > /tmp/_sat_tables.txt 2>&1 || true; tail -1 /tmp/_sat_tables.txt
grep -qE "^CARD TABLES: .* 0 failures$" /tmp/_sat_tables.txt || { echo "SATURDAY CHECK FAIL: card tables"; exit 1; }
python3 -I scripts/listed_price_report.py --slug "$SLUG" --event "$EVENT" | tail -1
echo "SATURDAY CHECK PASS at origin/main ${R:0:8}. On Kirk's go: git add -A data embeds form/data && git commit -m 'Saturday refresh <time>' && git push origin HEAD:main"
