# PREREG addendum: how T1 and T2 are scored on forward cards (registered 2026-11-27, before any forward card exists)

The bars for T1 (power de-vig) and T2 (Markov moneyline term off vs on) are in PREREG_model_review_2026-11-24.md on audit-locks
(4880836c) and are not changed here. This addendum fixes the scoring details the bars leave open, so they cannot be chosen after
seeing Dec 5. No forward card has been scored or snapshotted when this is committed (first forward card: Dec 5 2026).

## Code, frozen at this commit
- audits/forward_scoring/forward_score.py sha256 f503c5fd745e51eb... (T1, T2, T3/T6 shadows, T4), test_forward_score.py 11/11.
- scripts/sheet_v47.py sha256 ed0e84932a85507d... (the sheet mirror used for T2's "without" Q and the recs).
- A code change after this point is allowed only to fix a bug that the fixture tests can show, and is logged with its diff
  before the next score; a change made after seeing a forward result is reported as such.

## What counts as a forward card
- The card is dated 2026-12-05 or later and its T0 walkout lock CSV (snapshot_t0.gs, Drive copy, then audit-locks
  analysis/snap_locks/<date>.csv) was committed before the card's first bout.
- If T0 did not fire, the card does not count for T1/T2 (the PREREG fallback to the bot close + Snapshots rows is reported
  separately and labelled, not pooled).
- Results come from the site event file (UFCStats), matched by both fighter names (one-sided match only when exactly one bout
  fits). Draws, no contests and unmatched bouts are dropped and listed. A bout without both listed prices (D and I) is dropped.
- "10 graded cards" = the first 10 counting cards in date order. No card is skipped by choice.

## T1 (power vs multiplicative de-vig of the snapshot's best prices D/I)
- (a) per bout: G_mult = mult(D, I), G_power = power(D, I) for the dog; Brier and log loss pooled over all counted bouts.
- (b) the bot-close part was scored on 2026-11-24 (n=158, power better by 0.00147, MET). That verdict is frozen; the rows are
  rebuilt only to pool part (c) (the rebuild reproduces n=158 and -0.00147 exactly).
- (c) favorites priced 70%+ under power, forward (a) plus (b) pooled; gap = |mean priced favorite % minus favorite win rate|,
  power vs multiplicative.
- PASS only if (a) log loss power <= mult, (b) met, and (c) power gap < mult gap. Scored once, at the 10th counting card.

## T2 (Q with vs without the 0.15*(H - G) term)
- Q-with = the stored model Q in the lock row.
- Q-without = the sheet mirror with Markov blank (H = G, so the term is exactly zero), all other inputs from the lock row and the
  card's own params (B42 from the lock's params string). Manual adjust is not stored and is taken as 0.
- Where the mirror does not reproduce the stored Q within 0.15 points, Q-without = clamp(stored Q - 0.15*(H - G)) and the row
  is counted and reported.
- Brier per card and pooled; "better on a card" = lower card Brier.
- Units: BET recs only, from the mirror's rule text with and without the term, 1u by Sean's unit rule (favorites to win 1u, even
  or plus money risk 1u) at the lock's listed best price; leans and PASS do not count.
- REMOVE only if all hold at the 10th counting card: pooled Brier without <= with; without better on 6+ of 10 cards; units
  without >= with. KEEP if with beats without by 0.002 Brier or more. Otherwise INCONCLUSIVE: keep the term, extend 10 cards.
- T1 and T2 are scored from the same cards file in the same run; T2 uses the sheet's G as stored (multiplicative), whatever T1 finds.

## Interim reporting
- Every card prints interim lines, labelled "interim, not scored". No verdict, no change and no early stop before card 10.
