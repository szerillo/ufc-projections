# Southpaw box v2: pre-registration (Kirk round 21, call 2)

Written before the v2 confidence ranges, the favorite/underdog split and the five new fights were computed. Already seen when
this was written: the corrected n, win rate and ROI (605 / 53.4% / -4.5%, from `labs_fix_effect.py`).

## Numbers
1. The box uses the **corrected** southpaw set: main's published set (603) with the right namesake row for the five shared
   UFCStats names (fighter ID read from each bout's UFCStats fight-details page). That adds 2 bouts: 2024-03-16 Natan Levy
   vs Mike Davis and 2026-10-03 Anthony Romero vs Marcus McGhee. Removes none.
2. Prices, no-vig chance and winners come from main's own event files, so the other 603 bets are exactly what Labs shows.
3. The box says in one line that the Labs table still shows 603 until the rebuild after UFC 334.
4. Ranges: win rate normal 95%; ROI 95% by bootstrap clustered by card (10,000 draws, seed 20261112), as in round 20.

## Framing (fixed before writing the text)
- The headline is the return, not the win rate: "Betting every southpaw in this matchup at the closing price lost X% per bet."
- "Expected" is renamed: "the no-vig closing line implied Y%". It is no-vig (per-book proportional de-vig, then the median).
- One sentence says why more wins did not mean a profit, only if the favorite/underdog split shows it.
- One sentence: "This is one of 46 angles on Labs. With that many, one or two look good by luck." No z-score on the box.
- Closing words stay "Context, not a pick."

## Which fights
Kirk's list: 12, 11, 7, 5, 4 (plus 10 already). The box shows on a fight only if BOTH checks pass:
- Check 1: the fight's UFCStats fighter IDs (from the fighter pages linked to the fighter files) give Southpaw for one side and
  Orthodox for the other, from the fighter-details page itself, not the tott CSV.
- Check 2: a second, independent source: the UFC.com athlete page stance field, read for both fighters.
  If UFC.com has no stance or disagrees with UFCStats, the box does not show on that fight and the reason is logged.
- The numbers on each box are hand-checked twice: once from the stats file, once by recomputing from the per-bet list.

No other change to the box. If the box would mislead on any fight (for example the southpaw is the one being described as
the underdog angle while the market already prices the stance), that is reported, not tuned.
