# PREREG: ex-champions after losing the belt vs the market (registered 2026-11-25, before any odds are attached)

Request: C1 from Kirk, for Sean. The prompt is A. Feldman's Nov 24 2026 post: ex-champs are 261-283 after losing the title; 103 title losses by 87 champions since 2001.

**Rules:** profit and calibration decide, and CLV never does. No filter beyond the ones listed here.

## 1. Sample (fixed before odds)
- **Source:** UFCStats CSVs (`.form_cache`, through 2026-11-07), plus the Nov 21 2026 Qatar results (`qatar_results.json`, Sherdog official).
- **Title bouts:** WEIGHTCLASS of the form "UFC [Interim] <division> Title Bout". TUF, Road to UFC, BMF and tournament bouts are excluded.
- **Holder tracking, per division (undisputed and interim are separate belts):**
  - The winner of a title bout becomes the holder of that belt.
  - If the holder is not in a title bout of his own belt, he is cleared with no title loss (vacated, stripped, or moved on).
  - An undisputed title bout in a division clears the interim belt, unless the interim holder is in it.
  - Draws and NCs leave the holder unchanged.
- **Title loss:** the holder loses a title bout for his own belt, by any method, injury stoppages included. The interim holder losing a unification bout counts as an interim title loss.
- **Definition choice, made before odds are attached:**
  - (A) undisputed title losses only, or (B) undisputed plus interim.
  - Whichever is closer to Feldman's 103 losses / 87 champions is primary. The other is reported as a sensitivity.
  - The choice uses counts only, never results vs price.
- **Dates:** title losses from 2001-01-01.
- **Fights scored:** every UFC fight a fighter has after his first title loss, counted once, including later title fights and comebacks. Draws and NCs are excluded from win%.
- **Record check:** the overall W-L of the sample is compared to Feldman's 261-283 and the gap is explained. It is never tuned to match.

## 2. Market
- **Odds:** archive close in form/data/events, 2022-2026 bouts only. That is the only odds history we hold, so the market sample is the post-loss fights from 2022 on.
- **Primary price:** power de-vig of the close median price pair (ma, mb). Multiplicative de-vig (the archive p) is the sensitivity.
- **Units, Sean's rule, at the close median price:**
  - Ex-champ: favorite = bet to win 1u; dog = risk 1u.
  - Fade: the opponent under the same rule.
  - ROI = units / risked.
- **Metrics:**
  - won minus priced (points), with z;
  - Brier of the close;
  - ROI ex-champ vs ROI fade;
  - 90% bootstrap CIs, resampling fighters (cluster), 4,000 draws, seed 20261125.

## 3. Splits (the only ones)
- **Fight back:** first fight after the title loss vs later.
- **Age at the fight:** under 35 vs 35+ (dob from site fighter files).
- **Time since the title loss:** under 1 year, 1-2 years, 2+ years.
- **Role:** ex-champ favorite vs underdog at the close.
- **Opponent:**
  - "prospect" = 5 or fewer prior UFC fights;
  - "vet" = 8 or more;
  - 6-7 is reported as "middle".
  - We hold no rankings, so this is a proxy and is labelled as one.

## 4. Placebo
- **Pool:** every 2022-2026 archive bout side whose fighter is not an ex-champ at that date.
- **Matching:** exact match on three bins:
  - power close (5-point bins of the side's win prob);
  - age (<30, 30-34, 35+);
  - prior UFC fights (<8, 8-14, 15+).
- **Weighting:** cell means are weighted to the ex-champ sample's cell counts. Cells with no placebo match drop out and are reported.
- **Champion effect:** ex-champ (won minus priced) minus placebo (won minus priced), with a 90% bootstrap CI.

## 5. Our model
- **Sheet Q and Markov J:** Snapshots rows (10 graded cards) where an ex-champ fought. Brier vs close. Descriptive only, because n is tiny.
- **Round model:** Fight Form round-win q added on top of the power close, for ex-champ fights vs all fights (logistic coefficient). Descriptive.

## 6. Mechanism checks (descriptive)
- **Open to close drift** on ex-champs: does money move toward the name? That is the name-value inflation story.
- **Residual (won minus priced) by age and by time since loss:** does the market already discount the decline?
- **Placebo comparison** (section 4).

## 7. Verdict bars (fixed now)
"Fade ex-champs" (overall) is a **bettable angle** only if all hold:
1. Fade ROI is above 0 pooled, and its 90% bootstrap CI lower bound is above 0.
2. Fade ROI is positive in every archive year with 5 or more bets. This adapts Sean's "5 of 6 years" bar to the 5-year archive.
3. The champion effect (section 4) has a 90% CI that excludes 0 in the fade direction.
4. n is 50 or more priced fights.

**Subsets:**
- A split subset can be called bettable only if it passes bars 1-3 on its own with n of 30 or more.
- Every subset call is labelled **exploratory** (13 splits are tested) until it is confirmed on forward cards.
- No new cuts are added after seeing results.

If the bars fail, the verdict is "market already prices it", or "not enough data", whichever fits.
