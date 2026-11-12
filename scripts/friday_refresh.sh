#!/usr/bin/env bash
# Fight-night refresh for one card's embeds (Block 59k). One command; stops on the first failure.
#   scripts/friday_refresh.sh <card-name> <bp-slug> <event-file> <sharp-tracker-checkout> [compare-ref]
# 1 fresh odds feed  2 newest sheet export from origin/main  3 line history from the sharp-tracker archive
# 4 stats file  5 all embeds  6 page check + independent CSV recompute  7 number diff vs compare-ref (default HEAD)
set -euo pipefail
CARD="$1"; SLUG="$2"; EVENT="$3"; ST="$4"; REF="${5:-HEAD}"; cd "$(dirname "$0")/.."
t0=$(date +%s); step(){ echo "== $(( $(date +%s) - t0 ))s  $*"; }
step "1 odds feed";        python3 scripts/fetch_odds.py --card "$CARD" --out "data/${SLUG}_odds.json" 2>&1 | tail -1
step "2 sheet export";     git fetch -q origin main && for p in "data/${SLUG}_projections.json" "data/pending/${SLUG}_projections.json"; do
                             git cat-file -e "origin/main:$p" 2>/dev/null && git show "origin/main:$p" > "$p" && echo "  $p from origin/main ($(python3 -c "import json;print(json.load(open('$p'))['published_at'])"))"; done
step "3 line history"
# (rehearsal bug: "git pull && python ..." let a failed pull pass silently, since set -e ignores non-final && commands;
#  each command now stands alone, and the archive's newest snapshot must be under 3 hours old)
git -C "$ST" fetch -q origin main
git -C "$ST" checkout -q origin/main -- data/oddsapi/compact/mma.jsonl.gz data/mma/oddsapi_live.jsonl data/oddsapi/mma
python3 -I scripts/refresh_event_odds.py --event "$EVENT" --archive "$ST" > /tmp/_refresh_odds.txt
head -1 /tmp/_refresh_odds.txt
python3 - <<'PY'
import datetime as dt, re, sys
t = re.search(r"newest snapshot (\S+)", open("/tmp/_refresh_odds.txt").read()).group(1)
age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(t.replace("Z", "+00:00"))).total_seconds() / 3600
print(f"  archive age {age:.1f} h"); sys.exit(0 if age < 3 else "line-history archive is more than 3 hours old")
PY
step "4 stats file";       python3 -I scripts/build_embed_metrics.py --event "$EVENT" --cache .form_cache --out "form/data/embed_metrics/${SLUG}.json"
step "5 embeds";           python3 scripts/build_fight_embeds.py | tail -1
step "6 checks";           python3 scripts/verify_fight_embeds.py --slug "$SLUG" | tail -2
step "7 diff vs $REF";     rm -rf /tmp/_cmp && mkdir -p /tmp/_cmp && git archive "$REF" "embeds/${SLUG}" | tar -x -C /tmp/_cmp && python3 -I scripts/diff_embed_numbers.py "/tmp/_cmp/embeds/${SLUG}" "embeds/${SLUG}" | tail -4
step "done"
