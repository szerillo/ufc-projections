#!/usr/bin/env bash
# Nov 19 (Kirk): land a Markov run's final files for a card that opts in (card_overrides "markov") and rebuild its embeds.
#   scripts/markov_land.sh <dir with C4's files> <Name> <bp-slug> <markov-card-slug> "<title>"
#   e.g. scripts/markov_land.sh ~/Downloads/c4 UFC_FN_Prochazka_vs_Stirling fn_prochazka_stirling \
#          ufc-fight-night-prochazka-vs-stirling "UFC Fight Night: Prochazka vs. Stirling"
# Copies <Name>_V41b_Output.md, <Name>_V41b_Output.flags.json and <Name>_Raw_Stats.csv into markov/, prints their sha256
# (compare with the run log), builds data/cards/<markov-card-slug>.json, rebuilds the fight embeds and card tables, and runs
# the verifier and card-table check. Commits nothing. Stops on the first failure.
set -euo pipefail; export EMBED_PIPELINE=1; cd "$(dirname "$0")/.."
SRC="$1"; NAME="$2"; SLUG="$3"; MK="$4"; TITLE="$5"
for f in "${NAME}_V41b_Output.md" "${NAME}_V41b_Output.flags.json" "${NAME}_Raw_Stats.csv"; do
  [ -f "$SRC/$f" ] || { echo "MARKOV LAND FAIL: $SRC/$f missing"; exit 1; }
  cp "$SRC/$f" "markov/$f"; sha256sum "markov/$f"
done
python3 -c "import json,sys; json.load(open(sys.argv[1]))" "markov/${NAME}_V41b_Output.flags.json"
python3 -I scripts/markov_card_build.py "markov/${NAME}_V41b_Output.md" --slug "$MK" --title "$TITLE" | head -2
python3 scripts/build_fight_embeds.py --slug "$SLUG" | tail -1
python3 -I scripts/build_card_tables.py --slug "$SLUG" | tail -1 | cut -c1-120
python3 scripts/verify_fight_embeds.py --slug "$SLUG" > /tmp/_mkland.txt 2>&1 || true
grep -E "^TOTAL|^LOCKS" /tmp/_mkland.txt
grep -qE "^TOTAL: [0-9]+/[0-9]+ numbers verified; 0 mismatches/assertion failures" /tmp/_mkland.txt || { grep -E "^    " /tmp/_mkland.txt | head -10; echo "MARKOV LAND FAIL: verifier not clean"; exit 1; }
python3 -I scripts/verify_card_tables.py --slug "$SLUG" | tail -1 | cut -c1-140
echo "MARKOV LANDED: commit markov/${NAME}_* data/cards/${MK}.json data/manifest.json embeds/${SLUG}"
