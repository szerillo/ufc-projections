# PREREG: UFC point-spread tracker and v1 margin fix (registered 2026-11-24, before any card it is graded on)

## What is tracked
- **Every card from 2026-11-28 on.** For each bout with a posted point spread, `spread_track.py lock` appends one row to `analysis/spread_locks/<card date>.jsonl` before the first bout.
  - The row holds our v0 and v1 prices at -1.5 to -6.5 and the book prices at lock time.
  - Books: best available NY-legal books, plus Kalshi, Novig or Polymarket if they list spreads. Kalshi lists none today.
- **Close:** `--stage close` appends the same rows just before each bout. The script refuses a bout that has started.
- **Append only.** Rows are never edited after a result. A correction is a new row with a reason.
- **No auto-betting.** The tracker reports. Sean decides what to bet.

## Models (frozen in frozen_v1.json; any re-fit needs a new registration)
P(fav covers -s) = P(fav finish) + P(fav decision win) x P(3-judge margin > s | fav decision win)
- **Finish and decision split:** Sean's published export. Never the staging copy.
- **v0:** the margin term is a logistic on logit(closing no-vig fav price).
  - 3R: 617 fav decision wins since 2022. 5R: 64.
- **v1 (the fix):** the 3R margin term adds logit(q).
  - q = log5 of the two fighters' pre-fight Fight Form round-win rates.
  - Round won uses the site rule: a finished round goes to the finisher; otherwise scoring.coef decides.
  - Rates are shrunk toward 50% with 5 pseudo-rounds. A fighter needs 3+ UFC rounds.
  - Fit on 459 fav decision wins. q coefficient z 1.71. Walk-forward log loss better in 3 of 3 years (2024, 2025, 2026).
  - 5R bouts, and bouts where a fighter has under 3 UFC rounds, stay on v0.
- **Not adopted:** q in P(fav wins | decision) was better in only 1 of 4 years, and q in the all-fight cover probability in 1 of 4.
- **Divergence flag:** logit(q) minus its expected value given the price, in residual SDs. A gap of 0.5 SD or more is flagged.

## Grading (after each card, `spread_track.py grade`)
- **Outcomes:** each book row at its lock price. A finish win covers the winner's side. A decision uses the sum of the three cards. Draws and NCs are excluded.
- **Units** (betting-math rule):
  - favorites: bet to win 1u;
  - even or plus money: risk 1u.
- **Report:** hit rate, units and average CLV (close implied minus lock implied), by edge bucket (<0, 0-2, 2-4, 4+), per card and cumulative.

## What would show the edge is real
Evaluated at 150+ graded book prices, or at 15 cards, whichever comes first.
- **Main test:**
  - the 4+ edge bucket has positive units, with a bootstrap 95% CI over cards above 0;
  - **and** average CLV above 0 in the 2+ buckets.
- **For v1 to replace v0:**
  - v1 log loss on cover outcomes is at or below v0's on the graded bouts;
  - **and** v1 is better on at least 60% of cards.
- **Calibration:** predicted vs actual cover rate within 5 points in each of three probability bands.
- **If any fails:** report it as failed. The criteria are not changed after seeing results.

## Pre-tracking
- **Qatar (Nov 21):** graded only as calibration of the v0 prices locked Nov 20 (qatar_v0_calibration.txt). There was one book price, Hooker -3.5 -120.
- **v1 on Qatar is illustration, not evidence.** v1 was registered after those results.
