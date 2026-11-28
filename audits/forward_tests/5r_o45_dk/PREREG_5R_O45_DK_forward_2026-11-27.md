# PREREG: five-round over 4.5 rounds on DraftKings prices, forward test (registered 2026-11-27, before any price is seen)

Fresh forward test. Nothing in the sheet, the bet rules or the engine changes. Sean places every bet himself; this only grades.

## Why, and what is NOT evidence
- The Nov 27 re-check (claude/Recheck_5R_HW, out.json 61824c92) found the standing five-round over (R1: 5R O4.5 priced 50%+)
  positive in every cut but NOT SHOWN on its registered read (n=82, ROI +10.1%, 90% interval -4.1% to +23.2%, 3 of 5 years).
- Its DraftKings-only cut (n=52, ROI +19.9%) was chosen after seeing the books. It is a lead only: it is not pooled with, and
  does not count toward, this test.
- At registration no DraftKings round-total price for Dec 5 (or any later card) has been seen. The Nov 27 BestFightOdds pull
  showed no totals posted by any book and no DraftKings column of any kind.

## Rule under test
- Bout: scheduled for five rounds (main events and title fights), on a UFC card dated 2026-12-05 or later.
- Market: over 4.5 rounds at DraftKings, two-sided (over and under both quoted). No other book, no other line.
- Qualifies when the DraftKings no-vig over probability (multiplicative de-vig of the two DraftKings prices) is 50% or more at the
  entry price. Bouts under 50% are logged as a descriptive group, not scored.
- Entry price: the DraftKings over price in the card's T0 walkout lock (PropSnap row, DraftKings source) or, if T0 did not capture
  it, a DraftKings page read logged with its time before the first bout of the card. Later prices are not used for entry.
- Close: the last DraftKings over/under pair seen before the bout's own start, for CLV only.
- A bout that is cancelled, changed opponent, or changed to three rounds before the walkout is dropped. A draw or no contest that
  reaches round 5 grades by DraftKings settlement (per DraftKings' posted settlement rule for
  the line; a no contest that voids at DraftKings is dropped).

## Units and grading
- Sean's unit rule: minus money bet to win 1u, even or plus money risk 1u. ROI = units / units risked.
- Each qualifying bout is one bet. No sizing changes, no stacking, no correlation adjustments (two five-rounders on one card are
  two bets).
- CLV per bet = DraftKings no-vig over % at close minus at entry, in points.

## When it is scored, and the bars (fixed now)
- Scored once, at the 40th qualifying bet or on 2027-12-31, whichever comes first. Interim lines are logged per card and
  labelled "interim, not scored"; there is no early stop.
- **SUPPORTED** only if all hold: ROI > 0; the 90% bootstrap interval of ROI (10,000 resamples over bets, seed 7) lies above 0;
  mean CLV is 0 or better.
- **NOT SUPPORTED** if ROI < 0.
- **NOT SHOWN** otherwise (positive ROI with an interval that crosses 0, or negative CLV).
- Reported alongside, not scored: hit rate vs mean priced %, the under-50% descriptive group, and the same bets at the all-book
  median (if the T0 lock holds other books) for comparison with the archive cut.

## What follows from each reading
- SUPPORTED: evidence for Sean to keep R1 and to prefer DraftKings for it. Still Sean's decision.
- NOT SUPPORTED or NOT SHOWN: no automatic change; R1's status stays Sean's call, as after the Nov 27 re-check.

## Log format (one JSON line per five-round bout, file audits/forward_tests/5r_o45_dk/log.jsonl, appended per card)
{"card_date","bout","dk_over_entry","dk_under_entry","entry_seen_at","entry_source":"T0 PropSnap|DK page","dk_over_close",
 "dk_under_close","close_seen_at","qualifies":true|false,"result_rounds","went_over":true|false|null,"units","risked","note"}
Entry fields are written before the bout starts; result fields after. A line is never edited after its result is written.
