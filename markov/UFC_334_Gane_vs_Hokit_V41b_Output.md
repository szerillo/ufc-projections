# UFC 334: GANE vs HOKIT, V4.1b MARKOV OUTPUT
**Nov 14, 2026 | Madison Square Garden, NYC | V4.1b + §1d | 100K sims | market-blind | dual shrunk/RAW archived**
13 bouts, no scratches; 12 priced, plus Alatengheili vs Juan Diaz with no line yet. Five-round bouts: Gane-Hokit (HW title) and Harrison-Nunes (WBW title). Data: 11 real Oddsbreaker matchups, SYN on Sanches-Elder (both sides) and the Alatengheili side. §1d active on 5 fighters: Harrison, Hasan, Mesquita, Diaz, Sanches. Only GTD/ITD props posted so far, so O/U totals and the 5R O4.5 lines are pending a re-scrape.

**Form corrections vs BFO (verified on UFCStats):**
- Harrison and Nunes have NOT fought before. The "Jan 2026" bout on BFO does not exist, so this is a first meeting.
- Nunes is off a ~41-month layoff (retired after Aldana, Jun 2023) and Harrison a ~17-month one.
- Gane-Aspinall (Oct 2025) was a No Contest.
- Mesquita is an LFA product, not a PFL/Bellator vet.
- Off a KO loss: McKinney and Almeida only.
- Layoffs: Thompson ~16 mo, Elder ~19 mo, Sanches ~14 mo (UFC debut).

## SHEET INPUT TABLE: DOG WIN % + DECISION SHARE OF EACH FIGHTER'S WINS

| Fight | Underdog | Dog Win % (shrunk) | Dog Win % (raw sim) | Dog DEC% of wins | Fav DEC% of wins | Flags |
|---|---|---|---|---|---|---|
| 1 | Hokit (+165) | 66.2% | 73.0% | 55% | Gane 31% | artifact (thin pace) |
| 2 | Nunes (+154) | 70.1% | 75.5% | 53% | Harrison 28% | artifact (KD clamp), LAYOFF |
| 3 | Holland (+125) | 44.2% | 43.5% | 9% | Medic 35% | |
| 4 | Gurule (+600) | 40.2% | 17.4% | 40% | Hasan 52% | Hasan §1d, THIN |
| 5 | Belgaroui (+131) | 60.7% | 69.5% | 77% | Borralho 50% | artifact (thin) |
| 6 | Radtke (+133) | 50.8% | 50.9% | 34% | Thompson 40% | |
| 7 | Dober (+128) | 36.8% | 35.4% | 11% | Duncan 30% | |
| 8 | Miller (+161) | 47.2% | 46.8% | 7% | McKinney 37% | KD clamp |
| 9 | Almeida (+137) | 42.0% | 23.2% | 68% | Johnson 26% | Johnson THIN |
| 10 | Gordon (+293) | 57.2% | 58.0% | 70% | Costa 20% | artifact |
| 11 | Chiasson (+208) | 44.8% | 40.5% | 56% | Mesquita 65% | Mesquita §1d, THIN |
| 12 | Elder (+101) [SYN] | 40.7% | 18.9% | 17% | Sanches 54% | Sanches §1d, SYN |
| 13 | No line: Alatengheili vs Diaz | Alatengheili 37.7% / Diaz 62.3% | 24.6% / 75.4% | Alat 69% | Diaz 79% | SYN (Alat), Diaz §1d |

**D-code:** none active on the priced fights, because every fighter with 3 or fewer UFC bouts is the listed favorite. **Conditional:** Juan Diaz (last feeder LUX, minor) gets D-coded if he opens as the underdog. If he opens as the favorite, his code is GF instead (43% pre-UFC finish rate).

## 1. P(DECISION) + ROUND DISTRIBUTION

| Fight | P(dec) | Mkt GTD (devig) | Gap | R1 | R2 | R3 | R4 | R5 | ExpMin |
|---|---|---|---|---|---|---|---|---|---|
| Gane-Hokit (HW 5R) | **47.2** | 34.0 | **+13.2** | 17.3 | 15.0 | 10.0 | 5.7 | 4.7 | 16.7 |
| Harrison-Nunes (WBW 5R) | 45.4 | 38.2 | +7.2 | 18.3 | 15.5 | 10.2 | 5.7 | 4.8 | 16.3 |
| Medic-Holland | 23.5 | 20.0 | +3.5 | 44.7 | 22.5 | 9.3 | | | 7.3 |
| Hasan-Gurule | 47.1 | 17.8 | +29.3 | 26.6 | 17.4 | 8.8 | | | 10.1 |
| Borralho-Belgaroui | 66.4 | 61.8 | +4.6 | 15.5 | 11.5 | 6.6 | | | 12.0 |
| Thompson-Radtke | 37.2 | 56.9 | −19.7 | 33.3 | 20.1 | 9.5 | | | 9.0 |
| Duncan-Dober | 22.9 | 24.5 | −1.6 | 45.6 | 22.3 | 9.2 | | | 7.2 |
| McKinney-Miller | 23.0 | 11.7 | +11.3 | 45.3 | 22.4 | 9.2 | | | 7.3 |
| Johnson-Almeida | 43.7 | 31.0 | +12.7 | 28.8 | 18.2 | 9.3 | | | 9.7 |
| Costa-Gordon | **48.7** | 39.3 | **+9.4** | 25.6 | 17.0 | 8.8 | | | 10.3 |
| Mesquita-Chiasson | **60.6** | 33.3 | **+27.3** | 18.5 | 13.4 | 7.5 | | | 11.5 |
| Sanches-Elder [SYN] | 39.0 | 43.1 | −4.1 | 31.9 | 19.8 | 9.4 | | | 9.2 |
| Alatengheili-Diaz (no line) | 75.5 | — | — | 11.0 | 8.6 | 5.0 | | | 12.9 |

**5R rule check:** neither title fight fires the standing 5R GTD bet, because both have a listed GTD below 40% (34.0% and 38.2%). The O4.5 standing over can't be checked until totals post. The HW GTD lean is paused under v4.7, so it is display only.

**Duration flags (8+ points, with mechanism):**
- **Mesquita-Chiasson GTD +180 (+27.3) [lean].**
  - Mechanism: Mesquita is a BJJ world champion who controls rather than finishes on the feet. Women's BW decides about 63% at base, so the market's 33% is low for the division.
  - Counter: Mesquita has only 13 UFC minutes and her TD outputs are capped. Mesquita by decision is 65% of her win condition.
- **Gane-Hokit GTD +175 (+13.2) [lean].**
  - Mechanism: Hokit's wrestling (5.5 projected TDs, 85%/57% for 1+/2+) makes control time, and the champ rounds thin out the late hazard.
  - Counter: Hokit's pace numbers come from a 36-minute sample and are inflated. Both 5R and HW structure point long, but neither rule formally fires (listed below 40%, HW lean paused).
- **Costa-Gordon GTD +138 (+9.4) [lean].** Gordon is a decision fighter: 70% of his wins in the sim go the distance. Costa is moving up from FW. Clean but small.
- **Sprinkle / artifact:**
  - Hasan-Gurule +29.3: Hasan has an 8-minute sample, so this is an artifact.
  - Johnson-Almeida +12.7: Johnson's confidence is at the 30% floor.
  - McKinney-Miller +11.3: rides the P(KD) clamp.
- **Suppressed (ITD side):** Thompson-Radtke −19.7.

## 2-7. KEY PROPS
- **TD props** (85/57/30 marks a capped output; treat those as "high", not exact):
  - Hokit 5.49 proj (capped)
  - Alatengheili 4.03 (capped)
  - Chiasson 3.57 (capped)
  - Diaz 2.95 (capped)
  - Mesquita 2.59 (capped)
  - McKinney 2.10 (capped)
  - Gordon 1.63 (80/49/23)
  - Duncan 1.48 (77/43/19)
  - Johnson 1.43
  - Harrison 1.39 (75/40/16)
- **Zero TD projections:** Sanches and Elder both project 0.00 because of Sanches's 2-minute DWCS sample. That is an artifact.
- **P(KD):**
  - Nunes 40%, clamped: her KD rate is about 6x the division mean.
  - Hasan 40%, clamped.
  - Miller 40%, clamped, against McKinney's 2.18 KD absorbed per 15 min.
  - Sanches 40%, clamped.
  - Johnson 37%, Medic 32%.
  - Treat every clamped value as "high" and the spreads built on them as artifacts.
- **Violence fights** (method props, not totals):
  - Duncan-Dober: 45.6% ends in R1.
  - McKinney-Miller: 45.3% ends in R1.
  - Medic-Holland: 44.7% ends in R1.
- **SS (5R):** Hokit 96.6 mean and Gane 88.9 mean over 16.7 expected minutes; the Hokit number rides his inflated pace. Mean-set lines: lean the under.
- **Spread dog re-skins:** Gordon +3.5 (64.6% cover), Belgaroui +3.5 (78.2%), Chiasson +3.5 (76.3%).

## 8. ML (weight 0.15; 8+ points + mechanism; sheet rules v4.7)
**Mechanism-backed:**
- **Radtke +133 (model 50.8 / 50.9 vs market 40.7, +10.1) [lean].** Both columns agree.
  - Mechanism: Thompson is 43.8, on an L3, after a 16-month layoff. Radtke has a 93% control rate and wins rounds against a fighter who doesn't wrestle.
  - Counter: Thompson's distance craft and how hard he has been to finish.
- **Miller +161 (47.2 / 46.8 vs 36.3, +10.9) [lean].** Both columns agree.
  - Mechanism: McKinney has absorbed 2.18 KD per 15 min, has 5 KO losses, and is coming off an R1 KO loss.
  - Counter: Miller is 43.2, and his P(KD) of 40% is clamped, so the size of the edge is overstated.

**Artifacts (do not use):**
- Nunes +154 (70.1 / 75.5): her KD rate saturates the KO grid, and her 41-month layoff costs only −0.02 in the engine. The engine can't see how much the layoff matters.
- Hokit +165 (66.2 / 73.0): pace inflated by a thin sample.
- Gordon +293 (57 / 58): no clean mechanism, and Costa's weight change isn't modeled.
- Belgaroui +131 (60.7 / 69.5): 29-minute sample.
- Gurule (raw 17.4 agrees with the market), Almeida (raw 23.2 agrees), Elder (raw 18.9 agrees): shrinkage artifacts.

**Sheet rules (v4.7):**
- **Hasan −1000 is ~86% de-vigged, so it triggers the 80%+ rule: BET Hasan, shop the price.**
- No other favorite is at 80%+. Costa is 75.8%, under the 80% bar.

## ARCHIVE (paste block: fight, P(A) shrunk, P(A) RAW, P(dec), exp_min, R1-R5)
```
Ciryl Gane vs Josh Hokit	33.8	27.0	47.2	16.7	17.3	15.0	10.0	5.7	4.7
Kayla Harrison vs Amanda Nunes	29.9	24.5	45.4	16.3	18.3	15.5	10.2	5.7	4.8
Uros Medic vs Kevin Holland	55.8	56.5	23.5	7.3	44.7	22.5	9.3	0.0	0.0
Bilal Hasan vs Luis Gurule	59.8	82.6	47.1	10.1	26.6	17.4	8.8	0.0	0.0
Caio Borralho vs Yousri Belgaroui	39.3	30.5	66.4	12.0	15.5	11.5	6.6	0.0	0.0
Stephen Thompson vs Charles Radtke	49.2	49.1	37.2	9.0	33.3	20.1	9.5	0.0	0.0
Chris Duncan vs Drew Dober	63.2	64.6	22.9	7.2	45.6	22.3	9.2	0.0	0.0
Terrance McKinney vs Jim Miller	52.8	53.2	23.0	7.3	45.3	22.4	9.2	0.0	0.0
Donte Johnson vs Cesar Almeida	58.0	76.8	43.7	9.7	28.8	18.2	9.3	0.0	0.0
Melquizael Costa vs Jared Gordon	42.8	42.0	48.7	10.3	25.6	17.0	8.8	0.0	0.0
Bia Mesquita vs Macy Chiasson	55.2	59.5	60.6	11.5	18.5	13.4	7.5	0.0	0.0
Samuel Sanches vs Evan Elder	59.3	81.1	39.0	9.2	31.9	19.8	9.4	0.0	0.0
Alatengheili vs Juan Diaz	37.7	24.6	75.5	12.9	11.0	8.6	5.0	0.0	0.0
```

*Card 9 of the 10-card grading window. Files: ufc334_sim_v41b.py + ufc334_* data files.*
