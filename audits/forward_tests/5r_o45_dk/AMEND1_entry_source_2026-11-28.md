# Amendment 1 to PREREG_5R_O45_DK_forward_2026-11-27.md: entry and close source (registered 2026-11-28, before any price is seen)

Only the price SOURCE changes. The rule, the 50% qualification, units, CLV definition, bars, sample size and dates are unchanged.

## Why
The registration named "the DraftKings over price in the card's T0 walkout lock (PropSnap row, DraftKings source)" first.
PropSnap has no per-book rows: its sources are books (consensus), best-book, exch, Kalshi and Polymarket (checked 2026-11-28 on the
Nov 24 export). That source cannot exist. The odds bot's feed file does carry DraftKings round totals
(markets.total_rounds, Over/Under, books.draftkings: line, cost, no_vig_pct, updated) and is committed to main every 30 minutes,
so git history gives a timestamped record that nobody can edit after the fact.

What was looked at to write this: the feed's market and key names only (on a scratch pull of the Dec 5 feed, 2026-11-28 ~06:23Z).
No DraftKings price, line value or no-vig value for any Dec 5 bout was printed or read.

## Sources, in order (the first that has a two-sided DraftKings 4.5 line is used)
1. **Entry:** data/<slug>_odds.json as committed to origin/main in the last commit whose commit time is before the card's first
   scheduled bout; the bout's markets.total_rounds Over and Under with books.draftkings.line == 4.5 and a cost on both sides.
   **Close:** the same file in the last commit before that bout's own scheduled start.
2. A DraftKings page read in Sean's Chrome, logged with its UTC time before the first bout (entry) or the bout start (close).
3. The DraftKings column of the BestFightOdds event page, logged with its UTC time the same way.
- A DraftKings line other than 4.5 at entry means the bout does not enter the test (logged as "line not 4.5").
- No-vig over % = multiplicative de-vig of the two DraftKings costs (as registered), recomputed from cost, not the feed's own
  no_vig_pct.

## Settlement used by the grader (from DraftKings' posted rule for round totals)
- Over 4.5 rounds wins when the fight lasts more than 4.5 rounds: a decision, or a finish in round 5 after 2:30. A finish at or
  before 2:30 of round 5, or in rounds 1-4, is under. A no contest is void (dropped). A draw that goes the distance is over.
- If DraftKings' posted rule differs on a given bout, DraftKings' settlement wins and the line is noted.
