# UFC FIGHT NIGHT: PROCHAZKA vs STIRLING, V4.1b MARKOV OUTPUT
**Nov 21, 2026 | ABHA Arena, Doha | V4.1b + §1d | 100K sims | market-blind | dual shrunk/RAW archived**
11 bouts, matching UFC.com and UFCStats (BFO also lists Mitchell vs Yousaf on this event; it is not on the card and was not simmed). Five-round bout: Prochazka-Stirling (LHW main event). Data: 10 real Oddsbreaker matchups plus SYN on Lorenz-Nurgozhay (both sides). §1d active on 4 fighters: Luna, Topuria, Abdullayev, Lorenz. D-code active on 3 dogs: Luna, Abdullayev, Lorenz. GTD/ITD and O/U totals posted on 10 of 11 (none yet on Lorenz-Nurgozhay). Run is reproducible: PYTHONHASHSEED=0, sha256 in the run log.

**Form corrections vs BFO (verified on UFCStats):**
- Ortega has not fought since Sterling (Aug 2025). The two Moicano rows on BFO (Sep 2026) are not bouts on UFCStats, so he is on a ~15-month layoff and an L2.
- Almabayev vs Dijulius (Aug 2026) and Albazi vs Taira (Aug 2025) on BFO are not on UFCStats. Almabayev is on a W3; Albazi on an L2 (Horiguchi, Moreno).
- Sterling vs Benson Henderson (Mar 2026, BFO) is not a UFC bout; his last two are 5R decision wins over Zalal and Ortega at FW.
- Off a KO loss: Prochazka (Ulberg R1), Hooker (Parnasse R1, part of an L3), Horiguchi (Kape R3), Teixeira (Pavlovich R1), Motta (Sadykhov R2, ~17-month layoff).
- Dom Mar Fan: 2 of his 4 UFC-side bouts are Road to UFC; counted UFC-side like DWCS, so §1d is off for him (he is the favorite, so no D-code question).
- Lorenz: 0 UFC bouts, 2 DWCS (L Yakhyaev 2025, W Aly Aug 2026); his last non-DWCS bout is LFA 228.

## SHEET INPUT TABLE: DOG WIN % + DECISION SHARE OF EACH FIGHTER'S WINS

| Fight | Underdog | Dog Win % (shrunk) | Dog Win % (raw sim) | Dog DEC% of wins | Fav DEC% of wins | Flags |
|---|---|---|---|---|---|---|
| 1 | Prochazka (+131) | 34.4% | 20.3% | 8% | Stirling 30% | Stirling side raw only (shrunk -6.8) |
| 2 | Sterling (+108) | 54.2% | 57.6% | 77% | Vallejos 24% | ML lean (Sterling) |
| 3 | Ortega (+155) | 33.5% | 31.7% | 6% | Hooker 47% |  |
| 4 | Almabayev (+162) | 56.9% | 58.1% | 44% | Horiguchi 51% | ML lean (Almabayev); TD capped |
| 5 | Cannonier (+233) | 20.6% | 17.4% | 10% | Aliskerov 36% | Aliskerov side raw only; TD capped |
| 6 | Luna (+225) [D-FLAG] | 57.3% | 74.2% | 47% | Topuria 47% | vetoed (D-code); Luna §1d, Topuria §1d |
| 7 | Teixeira (+163) | 51.8% | 55.9% | 28% | Gaziev 14% | artifact (KO grids clamped, Teixeira THIN) |
| 8 | Costa (-107 pickem) | 61.8% | 70.7% | 56% | Albazi 25% | ML lean (Costa); near pickem |
| 9 | Abdullayev (+198) [D-FLAG] | 39.5% | 31.0% | 35% | Matthews 61% | vetoed (D-code); Abdullayev §1d, THIN |
| 10 | Motta (+125) | 44.5% | 31.8% | 11% | Mar Fan 56% | Fan THIN (conf floor) |
| 11 | Lorenz (+205) [SYN, D-FLAG] | 46.6% | 38.8% | 3% | Nurgozhay 23% | vetoed (D-code) + artifact; SYN both sides, Lorenz §1d |

**D-code vetoes:** Luna +225 (3 UFC bouts, last feeder Tuff-N-Uff), Abdullayev +198 (1 UFC bout, last feeder GFC), Lorenz +205 (2 DWCS bouts, last non-DWCS feeder LFA). Veto only; never a reason to bet the other side. All three show the model above market (Luna 57.3/74.2 vs 29.2, Lorenz 46.6/38.8 vs 31.1, Abdullayev 39.5/31.0 vs 32.0); the vetoes stand and the Archive scores them.

## 1. P(DECISION) + ROUND DISTRIBUTION

| Fight | P(dec) | Mkt GTD (devig) | Gap | R1 | R2 | R3 | R4 | R5 | ExpMin |
|---|---|---|---|---|---|---|---|---|---|
| Prochazka-Stirling (LHW 5R) | 22.6 | 16.7 | +5.9 | 31.5 | 22.5 | 12.7 | 6.2 | 4.5 | 11.7 |
| Sterling-Vallejos | 52.8 | 56.0 | -3.2 | 23.0 | 15.8 | 8.3 |  |  | 10.7 |
| Ortega-Hooker | 33.0 | 49.0 | -16.0 | 36.4 | 20.9 | 9.6 |  |  | 8.5 |
| Almabayev-Horiguchi | 46.8 | 66.7 | -19.9 | 27.0 | 17.4 | 8.8 |  |  | 10.0 |
| Cannonier-Aliskerov | 30.4 | 43.1 | -12.7 | 38.8 | 21.3 | 9.5 |  |  | 8.2 |
| Luna-Topuria | 47.4 | 56.0 | -8.6 | 26.3 | 17.5 | 8.8 |  |  | 10.1 |
| Teixeira-Gaziev | 21.4 | 18.7 | +2.7 | 47.1 | 22.5 | 9.0 |  |  | 7.0 |
| Costa-Albazi | 44.1 | 56.0 | -11.9 | 28.4 | 18.5 | 9.0 |  |  | 9.8 |
| Abdullayev-Matthews | 50.8 | 51.9 | -1.1 | 24.2 | 16.4 | 8.6 |  |  | 10.5 |
| Motta-Mar Fan | 35.8 | 41.5 | -5.7 | 34.3 | 20.2 | 9.7 |  |  | 8.9 |
| Lorenz-Nurgozhay | 13.7 | - | - | 56.1 | 22.4 | 7.8 |  |  | 5.9 |

**5R rule check:** Prochazka-Stirling GTD median +460 (about 18% listed) is below 40%, so the standing 5R GTD bet does not fire. O4.5 median +365 (about 21%) is below 50%, so no standing over. Model P(dec) 22.6% vs 16.7% de-vigged market (+5.9): under the 8-point bar.

**Duration flags (8+ points, with mechanism):** none on the GTD side. Largest GTD-side gap: Prochazka-Stirling +5.9 (not a flag).
- **Suppressed (ITD side, NO ITD/unders rule):** Almabayev-Horiguchi -19.9, Ortega-Hooker -16.0, Cannonier-Aliskerov -12.7, Costa-Albazi -11.9, Luna-Topuria -8.6.
- Lorenz-Nurgozhay: no GTD market yet; model P(dec) 13.7% (SYN, 2.9-minute sample, KO grids clamped: artifact).

## 2-7. KEY PROPS
- **TD props** (85/57/30 marks a capped output; read those as "high", not exact):
  - Almabayev 3.10 proj (85/57/30, capped)
  - Aliskerov 1.88 (85/56/29, capped)
  - Horiguchi 1.57 (79/46/21)
  - Abdullayev 1.23 (71/35/13)
  - Gaziev 1.20 (70/34/12)
  - Nurgozhay 1.16 (69/32/11, SYN)
  - Topuria 1.09 (66/30/10)
- **Zero TD projections:** Luna 0.00 (Topuria 100% TDD, 9 of 9 over 2 bouts), Matthews 0.00 (Abdullayev 100% TDD on 1 bout), Cannonier 0.00 (Aliskerov 100% TDD on 2 attempts faced): artifacts of tiny TDD samples. Motta and Lorenz 0.00 are real (0.00 career TD avg).
- **P(KD):**
  - Vallejos 40%, clamped (1.65 KD/15 over 46 min).
  - Lorenz 40%, clamped (2.9-minute sample).
  - Stirling 28%, Luna 27%, Teixeira 26%, Gaziev 26%, Aliskerov 25%.
  - Treat clamped values as "high" and the spreads built on them as artifacts.
- **Violence fights** (method props, not totals):
  - Lorenz-Nurgozhay: 56.1% ends in R1 (artifact-heavy).
  - Teixeira-Gaziev: 47.1% ends in R1.
  - Cannonier-Aliskerov: 38.8% ends in R1.
- **SS (5R):** Stirling 71.0 mean / 65.6 median and Prochazka 47.8 / 42.4 over 11.7 expected minutes. Mean-set lines: lean the under.
- **Spread dog re-skins (dog +3.5 = 1 minus fav -3.5):** Almabayev +3.5 76.1%, Luna +3.5 75.7% (D-code dog), Abdullayev +3.5 71.8% (D-code dog), Motta +3.5 71.5%, Costa +3.5 69.4%.

## 8. ML (weight 0.15; 8+ points + mechanism; sheet rules v4.7)
**Mechanism-backed:**
- **Almabayev +162 (model 56.9 / 58.1 vs market 36.4, +20.5) [lean].** Both columns agree.
  - Mechanism: Almabayev projects 3.1 takedowns (4.74 TD/15 career, 91% control rate) against Horiguchi's roughly league-average 61% TD defense, and Horiguchi is 36.1 and off an R3 KO loss.
  - Counter: the TD output is capped (85/57/30), 61% TDD is not a weakness, and Horiguchi beat Albazi and Ulanbekov in his last 3; the mechanism is control volume, not a defensive hole.
- **Costa -107 (61.8 / 70.7 vs 49.0, +12.7) [lean].** Both columns agree. Near pickem.
  - Mechanism: Albazi lands 2.47 sig/min at 33% (Oddsbreaker differential -2.2/min) on an L2, so the sim hands Costa the distance rounds; Costa is W3 by finish in 2026.
  - Counter: Albazi stopped Costa in R3 in Dec 2022 (2 KDs); the engine has no head-to-head input.
- **Sterling +108 (54.2 / 57.6 vs 45.8, +8.4) [lean].** Both columns agree.
  - Mechanism: Sterling's distance differential (+2.3/min Oddsbreaker, 2.15 SApM career) wins rounds in a fight the sim sends to decision 52.8% of the time; Vallejos has 28 Oddsbreaker minutes (confidence 55%).
  - Counter: Vallejos's 84% TDD and power (1.65 KD/15, P(KD) clamped at 40%); Sterling is 37.3 and has absorbed 5 KDs in his UFC career.

**Artifacts and vetoes (do not use):**
- Luna +225 (57.3 / 74.2 vs 29.2): VETOED, D-code. Driver is Topuria showing 0 UFC finishes and 0 KDs in 30 minutes against a 33-minute Luna sample; confidence at the 30% floor.
- Lorenz +205 (46.6 / 38.8 vs 31.1): VETOED, D-code, and an artifact: SYN on both sides, 2.9 minutes of DWCS tape, both KO grids pinned at the 2.50 clamp.
- Teixeira +163 (51.8 / 55.9 vs 36.1): artifact. Both KO grids sit at or near the clamp (3.26 / 3.00 after age and off-KO multipliers), Teixeira has 17 minutes, confidence at the 30% floor.

**Raw-column notes (not flags; col J uses shrunk):**
- Prochazka raw 20.3 vs 41.2: the Stirling side is +20.9 on raw but only +6.8 on shrunk (confidence 52%). Mechanism exists (Prochazka 3 KO losses in 9 UFC bouts, off a KO loss, KO grid toward Stirling 2.33), so the grading should note it.
- Cannonier raw 17.4 vs 28.5 (Aliskerov +11.1 raw, +7.9 shrunk) and Motta raw 31.8 vs 42.1 (Fan +10.3 raw but -2.4 shrunk at the 30% floor).
- Abdullayev raw 31.0 agrees with the market 32.0.

**Sheet rules (v4.7):** no favorite reaches 80% de-vigged (highest: Aliskerov 71.5%, Topuria 70.8%), so the 80%+ rule does not fire on this card.

## FIGHT BY FIGHT (first prelim to main event)
### Alik Lorenz vs Diyar Nurgozhay (LHW, 3R)
- P(decision) 13.7%; rounds R1 56.1% / R2 22.4% / R3 7.8%; O1.5 30.8%, O2.5 17.1%
- Finishes: Lorenz 45.0% (KO 38.9 / Sub 6.1), Nurgozhay 41.3% (KO 38.2 / Sub 3.2); ITD 86.3%
- Decision share of own win: Lorenz 3%, Nurgozhay 23%
- Expected minutes: 5.9
- Sig strikes: Lorenz mean 36.6 / median 31.2; Nurgozhay mean 45.6 / median 40.2
- Takedowns: Lorenz proj 0.00, P(>=1) 5% P(>=2) 0% P(>=3) 0%; Nurgozhay proj 1.16, P(>=1) 69% P(>=2) 32% P(>=3) 11%
- P(scores KD): Lorenz 40%, Nurgozhay 23%
- Spreads: fav (Nurgozhay) -3.5 43.8%
- ML: Lorenz shrunk 46.6% / raw 38.8%; market de-vig 31.1% (edge +15.5); confidence 30%

### Nikolas Motta vs Dom Mar Fan (LW, 3R)
- P(decision) 35.8%; rounds R1 34.3% / R2 20.2% / R3 9.7%; O1.5 54.6%, O2.5 40.4%
- Finishes: Motta 39.7% (KO 32.3 / Sub 7.3), Mar Fan 24.5% (KO 22.4 / Sub 2.1); ITD 64.2%
- Decision share of own win: Motta 11%, Mar Fan 56%
- Expected minutes: 8.9
- Sig strikes: Motta mean 28.5 / median 23.1; Mar Fan mean 38.6 / median 33.2
- Takedowns: Motta proj 0.00, P(>=1) 5% P(>=2) 0% P(>=3) 0%; Mar Fan proj 0.46, P(>=1) 37% P(>=2) 8% P(>=3) 1%
- P(scores KD): Motta 19%, Mar Fan 13%
- Spreads: fav (Mar Fan) -3.5 28.5%
- ML: Motta shrunk 44.5% / raw 31.8%; market de-vig 42.1% (edge +2.4); confidence 30%

### Tahir Abdullayev vs Jake Matthews (WW, 3R)
- P(decision) 50.8%; rounds R1 24.2% / R2 16.4% / R3 8.6%; O1.5 67.2%, O2.5 54.8%
- Finishes: Abdullayev 25.7% (KO 20.7 / Sub 5.0), Matthews 23.5% (KO 17.7 / Sub 5.8); ITD 49.2%
- Decision share of own win: Abdullayev 35%, Matthews 61%
- Expected minutes: 10.5
- Sig strikes: Abdullayev mean 26.9 / median 21.5; Matthews mean 30.3 / median 24.9
- Takedowns: Abdullayev proj 1.23, P(>=1) 71% P(>=2) 35% P(>=3) 13%; Matthews proj 0.00, P(>=1) 5% P(>=2) 0% P(>=3) 0%
- P(scores KD): Abdullayev 9%, Matthews 12%
- Spreads: fav (Matthews) -3.5 28.2%
- ML: Abdullayev shrunk 39.5% / raw 31.0%; market de-vig 32.0% (edge +7.6); confidence 55%

### Alessandro Costa vs Amir Albazi (FLW, 3R)
- P(decision) 44.1%; rounds R1 28.4% / R2 18.5% / R3 9.0%; O1.5 61.7%, O2.5 48.3%
- Finishes: Costa 27.1% (KO 19.7 / Sub 7.4), Albazi 28.8% (KO 27.3 / Sub 1.5); ITD 55.9%
- Decision share of own win: Costa 56%, Albazi 25%
- Expected minutes: 9.8
- Sig strikes: Costa mean 37.4 / median 32.0; Albazi mean 30.2 / median 24.8
- Takedowns: Costa proj 0.43, P(>=1) 35% P(>=2) 7% P(>=3) 1%; Albazi proj 0.25, P(>=1) 22% P(>=2) 3% P(>=3) 0%
- P(scores KD): Costa 16%, Albazi 21%
- Spreads: fav (Albazi) -3.5 30.6%
- ML: Costa shrunk 61.8% / raw 70.7%; market de-vig 49.0% (edge +12.7); confidence 57%

### Tallison Teixeira vs Shamil Gaziev (HW, 3R)
- P(decision) 21.4%; rounds R1 47.1% / R2 22.5% / R3 9.0%; O1.5 40.0%, O2.5 25.5%
- Finishes: Teixeira 37.3% (KO 36.3 / Sub 1.0), Gaziev 41.3% (KO 32.9 / Sub 8.3); ITD 78.6%
- Decision share of own win: Teixeira 28%, Gaziev 14%
- Expected minutes: 7.0
- Sig strikes: Teixeira mean 34.1 / median 28.7; Gaziev mean 24.6 / median 19.2
- Takedowns: Teixeira proj 0.48, P(>=1) 38% P(>=2) 8% P(>=3) 1%; Gaziev proj 1.20, P(>=1) 70% P(>=2) 34% P(>=3) 12%
- P(scores KD): Teixeira 26%, Gaziev 26%
- Spreads: fav (Gaziev) -3.5 42.8%
- ML: Teixeira shrunk 51.8% / raw 55.9%; market de-vig 36.1% (edge +15.6); confidence 30%

### Santiago Luna vs Aleksandre Topuria (BW, 3R)
- P(decision) 47.4%; rounds R1 26.3% / R2 17.5% / R3 8.8%; O1.5 64.3%, O2.5 51.7%
- Finishes: Luna 30.1% (KO 25.6 / Sub 4.6), Topuria 22.5% (KO 14.8 / Sub 7.7); ITD 52.6%
- Decision share of own win: Luna 47%, Topuria 47%
- Expected minutes: 10.1
- Sig strikes: Luna mean 37.0 / median 31.6; Topuria mean 28.8 / median 23.4
- Takedowns: Luna proj 0.00, P(>=1) 5% P(>=2) 0% P(>=3) 0%; Topuria proj 1.09, P(>=1) 66% P(>=2) 30% P(>=3) 10%
- P(scores KD): Luna 27%, Topuria 7%
- Spreads: fav (Topuria) -3.5 24.3%
- ML: Luna shrunk 57.3% / raw 74.2%; market de-vig 29.2% (edge +28.1); confidence 30%

### Jared Cannonier vs Ikram Aliskerov (MW, 3R)
- P(decision) 30.4%; rounds R1 38.8% / R2 21.3% / R3 9.5%; O1.5 49.4%, O2.5 34.8%
- Finishes: Cannonier 18.5% (KO 14.7 / Sub 3.7), Aliskerov 51.2% (KO 44.0 / Sub 7.2); ITD 69.6%
- Decision share of own win: Cannonier 10%, Aliskerov 36%
- Expected minutes: 8.2
- Sig strikes: Cannonier mean 33.8 / median 28.4; Aliskerov mean 40.6 / median 35.2
- Takedowns: Cannonier proj 0.00, P(>=1) 5% P(>=2) 0% P(>=3) 0%; Aliskerov proj 1.88, P(>=1) 85% P(>=2) 56% P(>=3) 29%
- P(scores KD): Cannonier 11%, Aliskerov 25%
- Spreads: fav (Aliskerov) -3.5 57.2%
- ML: Cannonier shrunk 20.6% / raw 17.4%; market de-vig 28.5% (edge -7.9); confidence 90%

### Asu Almabayev vs Kyoji Horiguchi (FLW, 3R)
- P(decision) 46.8%; rounds R1 27.0% / R2 17.4% / R3 8.8%; O1.5 63.7%, O2.5 51.0%
- Finishes: Almabayev 31.8% (KO 13.4 / Sub 18.4), Horiguchi 21.3% (KO 20.8 / Sub 0.5); ITD 53.2%
- Decision share of own win: Almabayev 44%, Horiguchi 51%
- Expected minutes: 10.0
- Sig strikes: Almabayev mean 21.9 / median 16.5; Horiguchi mean 28.0 / median 22.6
- Takedowns: Almabayev proj 3.10, P(>=1) 85% P(>=2) 57% P(>=3) 30%; Horiguchi proj 1.57, P(>=1) 79% P(>=2) 46% P(>=3) 21%
- P(scores KD): Almabayev 7%, Horiguchi 12%
- Spreads: fav (Horiguchi) -3.5 23.9%
- ML: Almabayev shrunk 56.9% / raw 58.1%; market de-vig 36.4% (edge +20.5); confidence 86%

### Brian Ortega vs Dan Hooker (LW, 3R)
- P(decision) 33.0%; rounds R1 36.4% / R2 20.9% / R3 9.6%; O1.5 52.1%, O2.5 37.6%
- Finishes: Ortega 31.5% (KO 24.1 / Sub 7.4), Hooker 35.5% (KO 30.8 / Sub 4.7); ITD 67.0%
- Decision share of own win: Ortega 6%, Hooker 47%
- Expected minutes: 8.5
- Sig strikes: Ortega mean 37.5 / median 32.1; Hooker mean 47.8 / median 42.4
- Takedowns: Ortega proj 0.30, P(>=1) 26% P(>=2) 4% P(>=3) 0%; Hooker proj 0.44, P(>=1) 35% P(>=2) 7% P(>=3) 1%
- P(scores KD): Ortega 10%, Hooker 13%
- Spreads: fav (Hooker) -3.5 39.6%
- ML: Ortega shrunk 33.5% / raw 31.7%; market de-vig 37.3% (edge -3.7); confidence 90%

### Aljamain Sterling vs Kevin Vallejos (FW, 3R)
- P(decision) 52.8%; rounds R1 23.0% / R2 15.8% / R3 8.3%; O1.5 68.5%, O2.5 56.9%
- Finishes: Sterling 12.6% (KO 4.3 / Sub 8.3), Vallejos 34.6% (KO 33.9 / Sub 0.7); ITD 47.2%
- Decision share of own win: Sterling 77%, Vallejos 24%
- Expected minutes: 10.7
- Sig strikes: Sterling mean 46.3 / median 40.9; Vallejos mean 44.2 / median 38.8
- Takedowns: Sterling proj 0.72, P(>=1) 52% P(>=2) 16% P(>=3) 4%; Vallejos proj 0.66, P(>=1) 48% P(>=2) 14% P(>=3) 3%
- P(scores KD): Sterling 6%, Vallejos 40%
- Spreads: fav (Vallejos) -3.5 38.2%
- ML: Sterling shrunk 54.2% / raw 57.6%; market de-vig 45.8% (edge +8.4); confidence 55%

### Jiri Prochazka vs Navajo Stirling (LHW, 5R)
- P(decision) 22.6%; rounds R1 31.5% / R2 22.5% / R3 12.7% / R4 6.2% / R5 4.5%; O1.5 56.2%, O2.5 39.1%
- Finishes: Prochazka 31.7% (KO 21.2 / Sub 10.4), Stirling 45.8% (KO 44.6 / Sub 1.2); ITD 77.4%
- Decision share of own win: Prochazka 8%, Stirling 30%
- Expected minutes: 11.7
- Sig strikes: Prochazka mean 47.8 / median 42.4; Stirling mean 71.0 / median 65.6
- Takedowns: Prochazka proj 0.28, P(>=1) 24% P(>=2) 3% P(>=3) 0%; Stirling proj 0.51, P(>=1) 40% P(>=2) 9% P(>=3) 2%
- P(scores KD): Prochazka 11%, Stirling 28%
- Spreads: fav (Stirling) -3.5 50.5%
- ML: Prochazka shrunk 34.4% / raw 20.3%; market de-vig 41.2% (edge -6.7); confidence 52%

## ARCHIVE (paste block: fight, P(A) shrunk, P(A) RAW, P(dec), exp_min, R1-R5)
```
Jiri Prochazka vs Navajo Stirling	34.4	20.3	22.6	11.7	31.5	22.5	12.7	6.2	4.5
Aljamain Sterling vs Kevin Vallejos	54.2	57.6	52.8	10.7	23.0	15.8	8.3	0.0	0.0
Brian Ortega vs Dan Hooker	33.5	31.7	33.0	8.5	36.4	20.9	9.6	0.0	0.0
Asu Almabayev vs Kyoji Horiguchi	56.9	58.1	46.8	10.0	27.0	17.4	8.8	0.0	0.0
Jared Cannonier vs Ikram Aliskerov	20.6	17.4	30.4	8.2	38.8	21.3	9.5	0.0	0.0
Santiago Luna vs Aleksandre Topuria	57.3	74.2	47.4	10.1	26.3	17.5	8.8	0.0	0.0
Tallison Teixeira vs Shamil Gaziev	51.8	55.9	21.4	7.0	47.1	22.5	9.0	0.0	0.0
Alessandro Costa vs Amir Albazi	61.8	70.7	44.1	9.8	28.4	18.5	9.0	0.0	0.0
Tahir Abdullayev vs Jake Matthews	39.5	31.0	50.8	10.5	24.2	16.4	8.6	0.0	0.0
Nikolas Motta vs Dom Mar Fan	44.5	31.8	35.8	8.9	34.3	20.2	9.7	0.0	0.0
Alik Lorenz vs Diyar Nurgozhay	46.6	38.8	13.7	5.9	56.1	22.4	7.8	0.0	0.0
```

*Card 10 of the 10-card grading window (A = BFO underdog on every row). Files: ufcqatar_sim_v41b.py + ufcqatar_* data files; run with PYTHONHASHSEED=0.*
