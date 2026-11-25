# PREREG: T4 women-term re-fit, forward test (registered 2026-11-24, before any forward card)

Sean's decision (via Kirk, Nov 24 19:38 ET): keep the women -4 term as it is. Register a re-fit test scored on forward cards from Dec 5, walk-forward, with bars committed before scoring. Nothing changes in the sheet now.

## Data
- **Forward cards:** every graded card from 2026-12-05 on, from walkout snapshots (T0) where they exist.
- **Women's bouts only:** Snapshots tag starts with "w".
- **Training base:** the 2022-2026 archive (form/data/events, power close, same as run_tests.py T4), plus every forward card graded before the card being scored.

## Walk-forward procedure (per forward card, in date order)
1. **Fit** on everything before the card: y = favorite won ~ logit(power favorite close p) + women.
2. **Fitted size:** the mean over that card's women's bouts of (dog p without the women term) minus (dog p with it), in points.
3. **Score the card's women's bouts** under two candidates, each as the sheet's Q:
   - A: Q as stored (women term -4);
   - B: Q with the women term replaced by minus the fitted size.
   - Use log loss and Brier on dog won.
4. **Reference only, not adoptable:** C = Q with no women term.

## When it is scored
- **At 30 graded women's bouts or 20 forward cards, whichever comes first.**
- No interim adoption. Interim numbers are logged, not acted on.

## Bars (all fixed now)
- **RE-FIT (B replaces A, size = the last fitted size rounded to 0.5 pt, capped at 0 to 8 points) only if all three hold:**
  1. Pooled log loss of B is below A on the forward women's bouts.
  2. B beats A on more than half of the cards that had women's bouts.
  3. The last fitted size is outside 2 to 6 points.
- **KEEP -4** if any of 1-3 fails.
- **DROP the term** cannot be adopted from this test. If C beats both A and B on log loss, it is reported and needs a new registration.
- **Reported in every case:** n, the fitted size per card, the log loss and Brier of A, B and C, and units at listed best prices for women's-bout recs under A vs B (Sean's unit rule).

## Why these bars
The archive run (05cb7469) found the women coefficient unstable: favorites helped in 3 of 5 years, and the walk-forward size ranged from +6.3 to -0.6 points. A forward test with a stability bar (2) and a size bar (3) guards against moving -4 on one or two cards of noise.
