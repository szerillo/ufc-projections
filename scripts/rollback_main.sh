#!/usr/bin/env bash
# Kirk round 23 D: undo a bad merge on main without losing anything the bot pushed since. Local only: prints the push.
#   scripts/rollback_main.sh            (reverts the newest merge commit on origin/main, and any merge_main.sh rebuild on top)
# A revert is a new commit, so later bot pushes stay. If the revert conflicts in data/<slug>_odds.json (the bot pushed after
# the merge), main's latest copy is kept. Any other conflict stops the script.
set -euo pipefail; cd "$(dirname "$0")/.."
SLUG="${SLUG:-ufc_334}"; ODDS="data/${SLUG}_odds.json"
git fetch -q origin main
git checkout -q -B _rollback origin/main
MC="$(git log --merges -1 --format=%H)"
echo "  reverting merge ${MC:0:8}: $(git log -1 --format=%s "$MC")"
for c in $(git log --format=%H "$MC"..HEAD --grep="merge_main.sh"); do git revert --no-edit "$c" >/dev/null; echo "  reverted rebuild ${c:0:8}"; done
if ! git revert -m 1 --no-edit "$MC" >/tmp/_rollback.txt 2>&1; then
  U="$(git diff --name-only --diff-filter=U)"
  [ "$U" = "$ODDS" ] || { echo "ROLLBACK FAIL: conflicts outside the odds file: $U"; git revert --abort; exit 1; }
  git checkout --ours -- "$ODDS"; git add "$ODDS"; git -c core.editor=true revert --continue >/dev/null
  echo "  odds file: kept main's latest (bot) copy"
fi
echo "  files that still differ from main before the merge: $(git diff --name-only "$MC^1" HEAD | tr '\n' ' ')"
echo "ROLLBACK READY: local branch _rollback at $(git rev-parse --short HEAD). On Kirk's go: git push origin _rollback:main"
