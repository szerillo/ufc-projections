# PREREG: model-review fix tests (registered 2026-11-24, before any of these is scored)

Nothing here changes the sheet, loader or engine. Each test is scored once, on the data named. Bars are fixed now. A fail is reported as a fail, and the bars are not moved afterwards. Adopting any change still needs Sean's OK.

"Forward cards" means the next 10 graded cards from 2026-12-05 on, snapshotted at first walkout. If the T0 snapshot fix isn't live, forward scoring uses the bot pre-start close and the Snapshots rows as they are, and the report says so.

## T0. Process (no scoring bar; done or not done)
- Snapshot at first walkout through a time trigger, not at grading. Hash each card's Snapshots and PropSnap rows to audit-locks before results.
- Drop PropSnap `exch` and `Polymarket` rows captured after the first walkout from every score.
- Grade the open Qatar PropSnap rows.
- Add columns: parameter version (B42, B43, B44, B45, women term), Markov raw and shrunk, notice days, days since last fight, age, UFC fight count.

## T1. Power de-vig for the listed anchor G (and GTD and method listed %)
- **Change:** G = power de-vig of D/I instead of multiplicative.
- **Score on:**
  - (a) forward cards: Brier and log loss of G_power vs G_mult;
  - (b) the bot pre-start US close set (`close.json` method, 2026 cards), as a second book set.
- **PASS only if all hold:**
  1. Log loss of G_power is at or below G_mult on (a).
  2. Log loss of G_power is at or below G_mult on (b).
  3. The favorite-side calibration gap at favorites priced 70%+ is smaller under power on (a) plus (b) pooled.
- **Context, already seen and not counted as the test:** 2022-2026 archive n=2414, power beats multiplicative by 0.0018 log loss per bout, z -2.87, in 5 of 5 years.

## T2. Markov ML term off vs on
- **Compare:** Q as is vs Q with the 0.15*(H-G) term removed (everything else unchanged), on forward cards.
- **REMOVE only if all hold:**
  - Q-without has Brier at or below Q-with;
  - and is better on 6 or more of 10 cards;
  - and the recommendation units (Sean's unit rule, listed best price) are not lower without it.
- **KEEP if Q-with wins by 0.002 Brier or more.**
- **Otherwise inconclusive:** keep the term and extend 10 more cards.
- Runs alongside the existing k_ML / k_GTD lock (cards 9-18) and doesn't replace it.

## T3. Dog drift veto ("no dog bet (drifting)")
- **Data:** 2022-2026 archive. Every dog with an open and a close, by the archive's own fields. Not yet looked at.
- **Drifting:** close dog % at least 3 points below open dog %.
- **Units:** risk 1u at the close price, power de-vig not needed (units only).
- **KEEP the veto if:** drifting dogs return less than non-drifting dogs in 4 or more of 5 years, and pooled.
- **DROP it if:** drifting dogs return more in 4 or more of 5 years.
- **Otherwise:** keep the veto, and log a shadow of the vetoed dogs on forward cards.

## T4. Women term (-4 points on the dog)
- **Data:** 2022-2026 archive, power close (as T1).
- **Logistic fit:** y ~ logit(close) + women x side, with side +1 for the favorite.
- **KEEP -4 if:** the women coefficient favors favorites in 4 or more of 5 years.
- **RE-FIT the size if:** the walk-forward fitted shift is outside 2 to 6 points in 3 or more years. The re-fit goes to Sean.
- **DROP if:** it favors dogs in 3 or more years.

## T5. Age (older fighter vs close)
- **Feature:** age difference in years, on top of the power close.
- **ADOPT as a proposal only if:**
  - it is the same sign in 5 of 5 years, walk-forward;
  - and log loss improves in 4 or more of 5 years.
- **Otherwise:** drop it.
- **Context, not counted:** multiplicative close z -1.77, walk-forward 3 of 4.

## T6. 80%+ favorite rule: sizing (Sean's decision, no model bar)
- **Shadow:** grade the rule on forward cards under two sizings: to-win 1u, and a risk cap of 2u.
- **Report:** both P/L lines plus the worst single loss. No pass or fail.

## Closed, no test
- **Round-win strength for moneyline:** adds nothing on top of the close.
  - 2022-2026, n=1771: z +0.63, walk-forward better in 1 of 4 years.
  - It stays in the spread margin only (spreads v1, registered 2026-11-24).
