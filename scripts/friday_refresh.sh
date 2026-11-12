#!/usr/bin/env bash
# Fight-night refresh for one card's embeds (Block 59k). One command; stops on the first failure.
#   scripts/friday_refresh.sh <card-name> <bp-slug> <event-file> <sharp-tracker-checkout> [compare-ref]
# 1 fresh odds feed  2 newest sheet export from origin/main  3 line history from the sharp-tracker archive
# 4 stats file  5 all embeds  6 page check + independent CSV recompute  7 number diff vs compare-ref (default HEAD)
set -euo pipefail   # ALLOW_STALE=1 overrides the sheet-export age block (step 2b)
CARD="$1"; SLUG="$2"; EVENT="$3"; ST="$4"; REF="${5:-HEAD}"; cd "$(dirname "$0")/.."
t0=$(date +%s); step(){ echo "== $(( $(date +%s) - t0 ))s  $*"; }
step "1 odds feed";        python3 scripts/fetch_odds.py --card "$CARD" --out "data/${SLUG}_odds.json" 2>&1 | tail -1
step "2 sheet export";     git fetch -q origin main && for p in "data/${SLUG}_projections.json" "data/pending/${SLUG}_projections.json"; do
                             git cat-file -e "origin/main:$p" 2>/dev/null && git show "origin/main:$p" > "$p" && echo "  $p from origin/main ($(python3 -c "import json;print(json.load(open('$p'))['published_at'])"))"; done
step "2b sheet export age"
# Block 59l (Kirk): model numbers only move when Sean's Publish to site export reaches origin/main. Loud warning at
# 12 h; block go-live (exit 2) at 24 h, or when any bout on the card is missing from the export. --allow-stale overrides.
python3 - "$SLUG" "$EVENT" "${ALLOW_STALE:-0}" <<'PY'
import json, sys, datetime as dt, re, unicodedata
slug, evp, allow = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
p = next(x for x in (f"data/{slug}_projections.json", f"data/pending/{slug}_projections.json") if __import__("os").path.exists(x))
X = json.load(open(p)); t = dt.datetime.fromisoformat(X["published_at"].replace("Z", "+00:00"))
age = (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600
fold = lambda s: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().split()[-1]) if s else ""
ev = json.load(open(evp)); have = {frozenset((fold(f["dog"]), fold(f["fav"]))) for f in X["fights"]}
miss = [f"{f['a']['name']} vs {f['b']['name']}" for f in ev["fights"] if frozenset((fold(f["a"]["name"]), fold(f["b"]["name"]))) not in have]
bar = "!" * 70
msg = f"SHEET EXPORT IS {age:.1f} HOURS OLD (published {X['published_at']})"
if age >= 12 or miss: print(bar); print(msg)
else: print("  " + msg)
if miss: print("BOUTS MISSING FROM THE EXPORT: " + "; ".join(miss))
if age >= 12 or miss: print(bar)
if (age >= 24 or miss) and not allow:
    print("GO-LIVE BLOCKED: republish the sheet (Publish to site) or rerun with ALLOW_STALE=1"); sys.exit(2)
PY
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
step "3b embed line history + Listed check"
python3 -I scripts/fetch_kalshi_ufc.py --out "data/embeds/kalshi_${SLUG}.json"   # dormant fallback input only
python3 -I scripts/build_line_history.py --slug "$SLUG" --event "$EVENT" --kalshi "data/embeds/kalshi_${SLUG}.json" | tail -1
python3 -c "import json,sys; d=json.load(open('data/embeds/line_history_${SLUG}.json')); k=[x for x,v in d['fights'].items() if v.get('current_source')=='kalshi_fallback']; print('  Kalshi fallback used for:', k or 'none')"
step "4 stats file";       python3 -I scripts/build_embed_metrics.py --event "$EVENT" --cache .form_cache --out "form/data/embed_metrics/${SLUG}.json"
step "5 embeds";           python3 scripts/build_fight_embeds.py | tail -1
step "6 checks";           python3 scripts/verify_fight_embeds.py --slug "$SLUG" | tail -3
step "7 diff vs $REF";     rm -rf /tmp/_cmp && mkdir -p /tmp/_cmp && git archive "$REF" "embeds/${SLUG}" | tar -x -C /tmp/_cmp && python3 -I scripts/diff_embed_numbers.py "/tmp/_cmp/embeds/${SLUG}" "embeds/${SLUG}" | tail -4
step "done"
