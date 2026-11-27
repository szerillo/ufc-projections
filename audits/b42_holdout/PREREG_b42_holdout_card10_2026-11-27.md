# PREREG: B42 card-anchoring backtest on one more holdout slice (registered 2026-11-27, before scoring)

Registered on branch b42-holdout-card10 and pushed before the scoring script is run. Nothing here changes the sheet.
The bars are fixed now and are not moved after scoring.

## Question
The Nov 19 backtest (claude/UFC_Sheet_B42_Card_Anchoring_2026-11-19.md) compared seven ways to set the Markov shift on
cards 2-9 (walk-forward) and recommended Option A, a fixed offset from graded cards. Sean adopted it as v4.8 (B42 = 0.1086).
Does Option A still hold against the old live per-card average (S0) on a card the Nov 19 backtest never saw?

## Holdout slice
- **Card 10, UFC Fight Night Prochazka vs Stirling (Nov 21 2026)**, Snapshots pk 4440: 12 rows, all with Markov J, all graded.
  It is the first card graded after the Nov 19 backtest and the first run live under v4.8. No other card is unseen.
- **Data:** the model sheet's graded archive tab, xlsx export read 2026-11-24 (sha256 bee567ba756bffa9...). Private:
  not committed; only aggregates are reported.
- **Already seen, disclosed:** card 10's results and its Markov grading (claude/Markov_Grading_Card10). The B42 option
  comparison on card 10 has not been computed by anyone in this project.

## Method (unchanged from Nov 19)
- The same code: common_nov19.py and bt_nov19.py in this folder (copies of the Nov 19 scripts: common.py sha256 af99aa054a8747a3..., bt.py f0d041b65d0a6101...;
  unchanged), driven by score_holdout.py, which only adds the xlsx reader and the card-10 slice.
- Q is recomputed for every row with the v4.7 chain (0.15 Markov weight, 0.15 / 0.075 fade, women and K codes), changing only
  the shift. Manual adjustments are not stored, so none are used (same as Nov 19).
- Walk-forward: A, A2 and B learn only from cards 1-9. S0 is the card's own average of (J - G), as the pre-v4.8 sheet did.
- Options scored: S0, A, B, A2, C, D, and Markov off (reference), as on Nov 19.
- Recs: the Nov 19 rule function (v4.7 rules, 1u per rec, snapshot prices), for continuity. Reported only; no bar.

## Primary measure and fixed reading
- **Primary:** Brier difference A minus S0 on card 10's 12 fights, with a 95% bootstrap CI over fights (10,000 resamples, seed 7).
- **A holds** if the difference is +0.002 or lower (0.002 is the card-to-card noise level stated on Nov 19).
- **A worse** if the difference is above +0.002 AND the CI lies entirely above 0.
- **Inconclusive** otherwise (above +0.002 with a CI that crosses 0).
- Also reported, not scored against a bar: log loss, every option's Brier, the pooled walk-forward cards 2-10 (113 + 12 fights),
  and the rec records.

## What follows from each reading
- A holds or inconclusive: no change; note it in SHEET_MAP's B42 history.
- A worse: a note to Sean with the numbers. No revert from one card; v4.8 stays unless Sean decides otherwise.
- Power: 12 fights cannot separate options whose Nov 19 gaps were about 0.0005 per fight. This is a sign and sanity check
  on unseen data, not a test that can confirm A.
