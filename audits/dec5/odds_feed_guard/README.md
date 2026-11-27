# Odds-feed input guard for the Dec 5 card (2026-11-27, branch dec5-odds-feed-guard, not merged)

There was no guard on the odds bot's feed file itself (the sheet's stale-input guard covers hand inputs on sheet rows;
check_price_freshness.py covers the archive's price age). New: `scripts/odds_feed_guard.py` (read-only) checks
data/<slug>_odds.json against the official bout list for STALE (updated_at time zone, future, older than 4 h), MISSING
(bout or one side's consensus price), EXTRA (cancelled bout still in the feed, unless card_overrides lists it) and SURNAME
(a label fits two card fighters, a surname-only label, or a price filed under the wrong bout). A .DRAFT.txt list is refused
without --allow-draft, and draft output is labelled DRAFT.

Tests: `python3 -I scripts/test_odds_feed_guard.py`, 15/15, on a Dec 5 DRAFT fixture (scripts/fixtures/dec5_odds_feed_DRAFT.json,
shaped like the bot's file, prices from the BFO draft medians). Same-surname case: Mairon Santos's price filed under
Riley vs Gabriel Santos is caught; the feed's "Junyong Park" spelling passes.
No false alarms on two real feeds: the Nov 21 and UFC 334 odds files both PASS against their cards (lists built from the
site event files, checked at each file's own updated_at).
Not wired into friday_refresh.sh or merge_main.sh yet: wiring changes the merge path, which is a separate call.
