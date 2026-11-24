# Model review tests: run notes (written 2026-11-24 before any T1-T6 scoring; committed before run_tests.py is executed)

The bars are the ones committed in PREREG_model_review_2026-11-24.md (4880836c). This file only fixes how the ambiguous parts are read. It does not change any bar.

## What can run today
- **T1 (b), T3, T4, T5 and the T6 history run now.**
- **T1 (a) and (c), and all of T2, need forward cards** (the next 10 graded cards from 2026-12-05). They are reported as PENDING, not scored.
- **T1 overall cannot pass or fail today.** It needs (a), (b) and (c).

## Common
- **Sample:** 2022-2026 archive, form/data/events. Bouts with a close and a win result; draws and NC are excluded. Same as hist.py.
- **"Power close":** the power de-vig of the close's median price pair (ma, mb). Same code as hist.py.
- **Testable years:**
  - Per-year sign fits use all 5 years (2022-2026).
  - Walk-forward needs a training year, so only 2023-2026 (4 years) are testable.
  - Where a bar says "4 or more of 5" for a walk-forward count, it is read as **all 4 testable years**. That is the only way to meet it without a 2022 training set. This is the stricter reading.

## T1 (b): bot pre-start US close set
- **Bouts:** every bout in close.json (committed) with a best price pair (best_a, best_b).
- **Result:** the archive event file of the same card date, matched by fighter names (fighter_names.name_match).
- **Compared:** G_mult = multiplicative de-vig of the best pair, vs G_power = power de-vig of the best pair. This mirrors how the sheet builds G from D/I.
- **Bar part 2:** log loss of G_power is at or below G_mult.

## T3: drifting-dog veto
- **Dog:** the side with archive close p below 0.5.
- **Open:** the archive's odds.open p, i.e. the first Odds API snapshot. That can be days after the true open; this is disclosed, not corrected.
- **Drifting:** open dog p minus close dog p is 0.03 or more.
- **Units:** risk 1u at the dog's close median price (ma / mb).
- **Compare:** drifting dogs' ROI vs all other dogs with an open, per year and pooled.
- **KEEP:** drifting ROI is lower in 4 or more of 5 years and pooled.
- **DROP:** drifting ROI is higher in 4 or more of 5 years.
- **Otherwise:** keep, plus a shadow log.

## T4: women term
- **Per-year logistic:** y = favorite won ~ logit(power favorite p) + women. A positive women coefficient favors favorites.
- **KEEP / DROP signs:** counted over the 5 per-year fits.
- **Size:** walk-forward for 2023-2026. Fit on all earlier years, then apply to the test year's women bouts.
  - Shift = mean of (dog p without the women term) minus (dog p with it), in points.
  - Re-fit flag: if the shift is outside 2 to 6 points in 3 or more of the 4 testable years.

## T5: age
- **Per-year logistic:** y = a won ~ logit(power a p) + (age a minus age b), years 2022-2026.
- **Bar:** same sign in 5 of 5 years, AND walk-forward log loss improves in all 4 testable years (2023-2026).

## T6: 80%+ favorite sizing (no bar; options for Sean)
- **Rows:** 2022-2026 favorites with a power close of 0.80 or more, bet at the favorite's close median price.
- **Sizings:**
  - A: to-win 1u (current);
  - B: risk capped at 2u;
  - C: skip prices shorter than -500;
  - D: flat risk 1u.
- **Reported per sizing:** bets, record, units, risked, ROI, worst single loss, worst year.
- **Note:** this uses archive close prices, not the sheet's listed best price at rec time. It shows the shape of each sizing, not the sheet's exact P/L.
- **Also shown:** the sheet's own 80%+ recs from the 10-card Snapshots (2 bets), under each sizing.
