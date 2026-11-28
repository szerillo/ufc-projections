# Odds-feed guard: merge-ready (branch odds-feed-guard, off main 7cf625ba; Sean approved option A on Nov 27)

What merging this branch changes (4 files plus this note, one step):
- `scripts/odds_feed_guard.py` (new, read-only): checks data/<slug>_odds.json against data/official/<date>.txt for STALE
  (updated_at with no time zone, in the future, or over 4 h old), MISSING (a bout, or one side's consensus price), EXTRA (a
  cancelled bout still in the feed, unless data/card_overrides.json lists it) and SURNAME (a label that fits two card fighters, a
  surname-only label, or a price under the wrong bout). DRAFT lists are refused unless --allow-draft.
  Override: `--override "<reason>"` lets a failing feed through, prints OVERRIDDEN with every failure and appends one JSON line
  (time, slug, reason, failures) to audits/odds_guard/overrides.log. An empty reason never overrides.
- `scripts/friday_refresh.sh`: new step 1b, right after the odds feed is fetched. A bad feed stops the refresh (set -e).
  To go anyway: `ALLOW_BAD_ODDS_FEED="<reason>" scripts/friday_refresh.sh ...` (same pattern as ALLOW_STALE). The header comment
  names the new switch. No other line in the file changed.
- `scripts/test_odds_feed_guard.py` (new): 23/23. Guard cases (stale, missing, cancelled, same surname, draft), the override
  (bad feed passes with a reason and logs one line; empty reason does not; good feed with a reason is unchanged and not logged),
  and the hook itself run in a scratch tree (good feed passes step 1b; bad feed stops it; ALLOW_BAD_ODDS_FEED lets it through and logs).
- `scripts/fixtures/dec5_odds_feed_DRAFT.json` (new test fixture, shaped like the bot's file, Dec 5 draft prices).

Checked: the real Nov 21 and UFC 334 odds files both PASS against their cards (no false alarms). merge_main.sh does not call the
guard; it only runs inside friday_refresh.sh. To run by hand on a card:
`python3 -I scripts/odds_feed_guard.py --odds data/<slug>_odds.json --official data/official/<date>.txt --slug <slug>`

Merge note: main_guard.py fails on this tree only for items already on main since the last MAIN_AT_CHECK pin (the Nov 25
post-card rebuild added result fields to the UFC 334 and Nov 21 event files). This branch touches no served data file. The merge
needs the usual round-18 checks and re-pin, then merge_main.sh with BR=odds-feed-guard.
