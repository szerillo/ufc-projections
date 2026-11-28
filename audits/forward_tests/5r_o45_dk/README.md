# DraftKings five-round over 4.5 forward test: tools (2026-11-28)

Registration: PREREG_5R_O45_DK_forward_2026-11-27.md, then AMEND1_entry_source_2026-11-28.md (entry/close come from the odds-bot
feed's DraftKings round totals as committed to main; PropSnap has no per-book rows). Tools only apply the registered bars.

Per card (after results land on the site event file):
1. `python3 -I audits/forward_tests/5r_o45_dk/dk_5r_o45.py extract --slug <bp-slug> --event form/data/events/<card>.json --log audits/forward_tests/5r_o45_dk/log.jsonl`
   Entry = last feed commit before the card's first bout; close = last commit before the bout's own start. Safe to run late:
   it only reads commits made before each cutoff. If the feed had no DraftKings 4.5 pair, log a timed DK page read instead
   (`manual ... --source "DK page"`), or the BestFightOdds DraftKings column (`--source "BFO DK column"`).
2. `... grade --event form/data/events/<card>.json --log .../log.jsonl` (decision or R5 after 2:30 = over; NC void).
3. `... score --log .../log.jsonl` (interim until 40 qualifying bets or 2027-12-31).

Tests: `python3 -I audits/forward_tests/5r_o45_dk/test_dk_5r_o45.py` 18/18 (synthetic git repo with set commit times).
Real-data check: the Nov 21 card (before the test window) extracts from feed history; its one five-rounder had a DraftKings
line of 2.5, not 4.5, so it would not have entered. Five-rounders with a short DraftKings line stay out by registration, which
can slow the sample.
