#!/usr/bin/env bash
# Kirk round 22 call 1: the merge, done locally and checked, never pushed by this script.
#   scripts/merge_main.sh            (branch go-live-334, slug ufc_334; BR=<branch> to override)
# 1 main_guard with the export/odds-bot allowlist  2 --no-ff merge of the branch onto origin/main in a local branch _merge
# 3 an odds-file conflict (the only one allowed) goes to the copy with the later "updated_at"; if that is main's (the bot's),
#   the embeds are rebuilt on it so served prices never roll back  4 full verifier on the merge result, 0 mismatches
# 5 prints the one push command for Kirk's go. Exits non-zero on anything else.
set -euo pipefail; export EMBED_PIPELINE=1; cd "$(dirname "$0")/.."
BR="${BR:-go-live-334}"; SLUG="${SLUG:-ufc_334}"; ODDS="data/${SLUG}_odds.json"
git fetch -q origin
python3 -I scripts/main_guard.py --allow-publish-and-bot --slug "$SLUG"
git checkout -q -B _merge origin/main
if ! git merge --no-ff --no-edit -m "Merge $BR into main (scripts/merge_main.sh)" "$BR" >/tmp/_merge.txt 2>&1; then
  U="$(git diff --name-only --diff-filter=U)"
  if [ "$U" != "$ODDS" ]; then echo "MERGE FAIL: conflicts outside the odds file: $U"; git merge --abort; exit 1; fi
  git show ":2:$ODDS" > /tmp/_odds_main.json; git show ":3:$ODDS" > /tmp/_odds_branch.json
  # Kirk round 26 C: times compared as times, and the data inside must agree (scripts/odds_newer.py)
  W="$(python3 -I scripts/odds_newer.py /tmp/_odds_main.json /tmp/_odds_branch.json)" || { git merge --abort; echo "MERGE FAIL: newer odds file unknown"; exit 1; }
  W="$( [ "$W" = A ] && echo ours || echo theirs )"
  git checkout --"$W" -- "$ODDS"; git add "$ODDS"
  git commit -q --no-edit
  echo "  odds file resolved to $( [ "$W" = ours ] && echo "MAIN's (bot) copy, the newer" || echo "the BRANCH copy, the newer")"
fi
if ! git diff --quiet "$BR" HEAD -- "$ODDS"; then
  echo "  served odds file differs from the one the embeds were built on: rebuilding the embeds on it"
  python3 scripts/build_fight_embeds.py | tail -1
  git add -A "embeds/${SLUG}"
  git commit -q -m "Rebuild ${SLUG} embeds on main's newer odds file (merge_main.sh)" || true
fi
python3 scripts/verify_fight_embeds.py --slug "$SLUG" | tee /tmp/_merge_verify.txt | tail -3
grep -qE "^TOTAL: [0-9]+/[0-9]+ numbers verified; 0 mismatches/assertion failures" /tmp/_merge_verify.txt || { echo "MERGE FAIL: verifier not clean on the merge result"; exit 1; }
python3 -I scripts/scan_public.py --base origin/main | tail -1
echo "MERGE READY: local branch _merge at $(git rev-parse --short HEAD) (nothing pushed). On Kirk's go: git push origin _merge:main"
