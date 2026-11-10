# UFC FIGHT NIGHT: CORTES ACOSTA vs WALKER — V4.1b MARKOV OUTPUT
**Nov 7-8, 2026 | APEX | V4.1b + §1d | 100K sims | market-blind | dual shrunk/RAW archived**
11 real Oddsbreaker matchups + 3 synthetic (Raposo-Degli, Lorenco-Petersen, Calderon side). §1d active on 12. Form corrections encoded: Waldo lost to Blaydes (dec, Sep 12 — L2, zero UFC finishes); Walker KO'd Parkin R1 at HW (Oct 3, 5-week turnaround on a WIN); Turman's rumored Dulatov KO loss is phantom — his reality is an L3 and a ~35-month layoff. Off KO loss: Schmid, G.Fernandes, Petroski.

## SHEET INPUT TABLE — DOG WIN % + DECISION SHARE OF EACH FIGHTER'S WINS

| Fight | Underdog | Dog Win % (shrunk) | Dog Win % (raw sim) | Dog DEC% of wins | Fav DEC% of wins |
|---|---|---|---|---|---|
| 1 | Walker (+185) | 20.2% | 16.9% | 5% | Waldo 48% |
| 2 | Jandiroba (+165) | 41.4% | 40.4% | 73% | Suarez 89% |
| 3 | Grant (+243) | 49.8% | 49.6% | 79% | Smith 29% |
| 4 | Elekana (+238) | 45.4% | 34.7% | 24% | Fernando 39% |
| 5 | Cachoeira (+343) | 35.6% | 15.5% | 27% | Milosevic 73% |
| 6 | Raposo (+190) [SYN] | 42.4% | 24.7% | 64% | Degli 67% |
| 7 | Schmid (+265) [D-FLAG] | 38.3% | 11.1% | 21% | Nakamura 50% |
| 8 | Lorenco (+140) [SYN, D-FLAG] | 57.3% | 74.2% | 31% | Petersen 17% |
| 9 | Fernandes (+171) | 50.0% | 49.9% | 91% | K.Silva 44% |
| 10 | Magomedov (−109 pickem) [D-FLAG marginal] | 54.9% | 66.5% | 28% | Delano 73% |
| 11 | Calderon (+335) [D-FLAG] | 46.7% | 38.9% | 56% | Bashi 57% |
| 12 | Petroski (+240) | 40.0% | 29.9% | 32% | Kondratavicius 36% |
| 13 | Turman (+515) | 39.2% | 27.2% | 53% | Ko 83% |
| 14 | Parsons (+188) [D-FLAG] | 56.7% | 72.3% | 58% | Souza 15% |

**D-code vetoes:** Schmid +265, Lorenco +140, Calderon +335, Parsons +188, Magomedov −109 (marginal). Note Lorenco: BOTH columns sit far above market (57/74 vs 39.5) — the veto holds anyway; the Archive will score whether that discipline is right on the most tempting D-code dog yet.

## 1. P(DECISION) + ROUND DISTRIBUTION

| Fight | P(dec) | Mkt GTD | Gap | R1 | R2 | R3 | R4 | R5 | ExpMin |
|---|---|---|---|---|---|---|---|---|---|
| Waldo-Walker (HW 5R) | **39.4** | 24.5 | **+14.9** | 20.9 | 17.4 | 11.1 | 6.1 | 5.0 | 15.2 |
| Suarez-Jandiroba | **82.0** | 70.8 | +11.2 | 7.9 | 6.3 | 3.8 | | | 13.4 |
| Grant-Smith | 53.7 | 44.0 | +9.7 | 22.6 | 15.5 | 8.2 | | | 10.8 |
| Elekana-Fernando | 32.2 | 41.5 | −9.3 | 37.3 | 21.0 | 9.5 | | | 8.4 |
| Cachoeira-Milosevic | 57.0 | 24.5 | +32.5 | 20.6 | 14.5 | 7.9 | | | 11.1 |
| Raposo-Degli [SYN] | 65.9 | 46.2 | +19.7 | 15.6 | 11.8 | 6.7 | | | 12.0 |
| Nakamura-Schmid | 39.0 | 27.5 | +11.5 | 32.0 | 19.4 | 9.6 | | | 9.2 |
| Lorenco-Petersen [SYN, HW] | 25.1 | 37.3 | −12.2 | 43.4 | 22.1 | 9.4 | | | 7.5 |
| K.Silva-Fernandes | **67.5** | 56.9 | +10.6 | 14.8 | 11.2 | 6.4 | | | 12.1 |
| Delano-Magomedov | 48.2 | 43.1 | +5.1 | 26.1 | 17.1 | 8.6 | | | 10.2 |
| Bashi-Calderon | 56.4 | (partial) | — | 20.9 | 14.6 | 8.0 | | | 11.0 |
| Kondratavicius-Petroski | 34.6 | 24.5 | +10.1 | 35.6 | 20.4 | 9.4 | | | 8.7 |
| Ko-Turman | **71.3** | 49.0 | **+22.3** | 13.0 | 10.0 | 5.6 | | | 12.5 |
| Parsons-Souza | 39.3 | (partial) | — | 31.6 | 19.7 | 9.4 | | | 9.3 |

**Duration flags with mechanism:**
- **MAIN EVENT: Waldo-Walker GTD +280** (+14.9) — the HW GTD lean rule fires (HW priced 24.5% to decide vs the division's 44-48% reality) AND the model confirms at 39.4%. Mechanism: Waldo has never finished anyone in the UFC (41% model KO notwithstanding, his last five went the cards), and the 5R structure adds champ-round durability. The regime bet at a regime price.
- **Ko-Turman GTD −110** (+22.3): best price-to-gap on the card. Ko is a 3.6-TD/fight control wrestler; Turman is a 35-month-layoff sub grappler who doesn't finish standing. Near-even money for a model-71% event.
- **Suarez-Jandiroba GTD −315** (+11.2): grappler-vs-grappler, 6% KD each — control cancels into scorecards. Heavy price; "Suarez by decision" (89% of her win condition) is the correlated expression.
- **K.Silva-Fernandes GTD −155** (+10.6): Silva's 1-3 skid is all decisions; Fernandes' win condition is 91% scorecards.
- Grant-Smith +9.7 and Kondratavicius-Petroski +10.1: moderate leans. Cachoeira-Milosevic +32.5 and Raposo-Degli +19.7 ride thin/synthetic data — sprinkle-grade.
- **HW rule vetoed on Lorenco-Petersen**: priced 37.3% GTD (rule territory) but the model says 25.1% — two live finishers, 43% ends R1. This is the "say which HW fights are the grinders" job: Waldo-Walker is the grinder, this one isn't.

## 2-7. KEY PROPS
TD props: **Raposo 3.95 [SYN]**, **Ko 3.62**, Jandiroba 3.02, Degli 2.94 [SYN], Suarez 2.84, Calderon 2.68, Fernando 2.41, Magomedov 2.20 — all 85/57 where marked. Bashi's 11.2 projection is a flagged data artifact (stale Oddsbreaker string) — trust the P(≥1) 85%, not the count.
P(KD): Cachoeira 40%*/Milosevic 40%* (both clamped — the brawl), Nakamura 38% (2 knee-KOs in 3 UFC wins), Waldo 37%, Kondratavicius 30% vs Petroski's 4-KO-loss chin (*clamped).
Violence fights: Lorenco-Petersen (43% R1), Elekana-Fernando (37% R1), Kondratavicius-Petroski (36% R1 — KO-chin vs sub-threat split).
Spread re-skins: Jandiroba +3.5 (89.0%), Grant +3.5 (61.7%), Turman +3.5 (85.1%), Petroski +3.5 (56.3%).

## 8. ML (β=0.15; ≥8pt + mechanism)
**Mechanism-backed flags:**
- **Waldo -235** (79.8 / 83.1 vs market 66.7, +13.2): columns agree. Mechanism: Walker's 0.85 KD-absorbed/15 chin and 57% KO-loss rate against a 37%-KD heavyweight — the Parkin win doesn't repair the chin data. Counter stated: Waldo's zero UFC finishes and L2 form; the model is betting Walker's durability fails before Waldo's volume does. Pairs naturally with GTD+Waldo-by-decision angles.
- **Grant +243** (49.8 / 49.6 vs 29.2, +20.6): columns agree to the decimal. Mechanism: Grant's volume and 10-year-vet durability vs Smith's thin sample. Counter: Grant is 40.9 with four UFC sub losses against a grappler. Flag per rule, size with the age counter.
- Vetoed despite conviction: Lorenco +140 (D-code; raw 74.2), Parsons +188 (D-code + 40-month layoff; raw 72.3), Calderon +335 (D-code; Bashi -480 flagged as way too steep but no playable side), Magomedov pickem (D-code marginal; raw 66.5).
- Artifacts (raw sides with market): Elekana +17.4 (raw 34.7), Cachoeira +14.3 (raw 15.5), Raposo (raw 24.7), Kondr-Petroski shrunk lean (raw 70.1 ≈ market).
- Ko -800: model won't lay it (raw 72.8 vs 84.5) but Turman's layoff kills the dog side — no play; the GTD is the vehicle in that fight.

**Band favorites (70-90%, early + shopped):** Smith (~72.2), Fernando (~72.0), Milosevic (~78.6), Nakamura (~73.9), Degli (~67.3 just under), Bashi (~78.3 — model disagrees hard), Kondratavicius (~71.9). Women's-fav regime: Milosevic, Suarez (67.7 just under band).

## ARCHIVE (paste block — fight, P(A) shrunk, P(A) RAW, P(dec), exp_min, R1-R5)
```
Waldo Cortes Acosta vs Johnny Walker	79.8	83.1	39.4	15.2	20.9	17.4	11.1	6.1	5.0
Tatiana Suarez vs Virna Jandiroba	58.6	59.6	82.0	13.4	7.9	6.3	3.8	0.0	0.0
Davey Grant vs Elijah Smith	49.8	49.6	53.7	10.8	22.6	15.5	8.2	0.0	0.0
Billy Elekana vs Lucas Fernando	45.4	34.7	32.2	8.4	37.3	21.0	9.5	0.0	0.0
Priscila Cachoeira vs Nina Milosevic	35.6	15.5	57.0	11.1	20.6	14.5	7.9	0.0	0.0
Mitch Raposo vs Marcos Degli	42.4	24.7	65.9	12.0	15.6	11.8	6.7	0.0	0.0
Keiichiro Nakamura vs Ollie Schmid	61.7	88.9	39.0	9.2	32.0	19.4	9.6	0.0	0.0
Gabriel Lorenco vs Thomas Petersen	57.3	74.2	25.1	7.5	43.4	22.1	9.4	0.0	0.0
Karine Silva vs Gabriella Fernandes	50.0	50.1	67.5	12.1	14.8	11.2	6.4	0.0	0.0
Jose Delano vs Murtazali Magomedov	45.1	33.5	48.2	10.2	26.1	17.1	8.6	0.0	0.0
Austin Bashi vs Carlos Calderon	53.3	61.1	56.4	11.0	20.9	14.6	8.0	0.0	0.0
Mantas Kondratavicius vs Andre Petroski	60.0	70.1	34.6	8.7	35.6	20.4	9.4	0.0	0.0
Seokhyeon Ko vs Wellington Turman	60.8	72.8	71.3	12.5	13.0	10.0	5.6	0.0	0.0
Jonny Parsons vs Jose Souza	56.7	72.3	39.3	9.3	31.6	19.7	9.4	0.0	0.0
```

*Card 8 of the 10-card grading window. Files: waldo_sim_v41b.py + waldo_* data files.*
