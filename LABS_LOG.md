# Labs research log

Updated 2026-11-10. One row per test so nothing is run twice. Status: done, proxy (approximate), blocked (needs data), idea (not started).

| Area | Test | Status | Result | Where on site | Data / notes |
|---|---|---|---|---|---|
| Market | Closing-line calibration and favorite-longshot bias | done | Favorites won 69.1% vs 66.3% implied; slope about 1.2. 70%+ favorites +3.0% at best price; underdogs -14.1%. | Research | Odds archive 2022-2026 (2,388 fights) |
| Market | Steam / line movement | done | Moves are priced in; no edge following or fading. | Research; Labs > Query | Open vs close |
| Market | Totals and books | done | Totals tight; best-price shopping worth about 1.8 pts of ROI on favorites. | Research | Odds archive |
| Market | Query tool (division, price, move, slot, rounds, venue, year) | done | Interactive; any filter combination. | Labs > Query | 2,388 fights with closes |
| Market | Biggest upsets; underdog win rate by year | done | Top: Sharaf +850 over Steveson. | Labs > Upsets | Closing consensus |
| Physical | Age gap | done | 10+ years younger wins 68.8%; market mostly prices it. | Labs > Age & size | UFCStats DOB, since 2010 |
| Physical | Reach and height advantage | done | 6+ in reach wins 59.0%; height adds almost nothing. | Labs > Age & size | UFCStats |
| Spots | Coming off a KO/TKO loss | done | 42.9% wins; -16.0% ROI (394 with lines). | Labs > Spots |   |
| Spots | 400+ day layoff vs active opponent | done | 41.1% wins; -15.5% ROI. | Labs > Spots |   |
| Spots | UFC debut vs veteran | done | 44.3% wins; -13.9% ROI. | Labs > Spots |   |
| Spots | Southpaw vs orthodox | done | 52.7% wins; -4.2% ROI. Priced. | Labs > Spots |   |
| Spots | Quick turnaround (60 days or fewer) | done | 48.0% wins; -20.0% ROI on only 83 fights. | Labs > Spots | Small sample |
| Spots | Weight-class moves | done | Down: 47.7% wins, -17.7% ROI (143). Up: 54.1%, +4.0% (109). | Labs > Spots |   |
| Spots | Win/lose streaks, experience gap, rematches | done | All near the market except 10+ UFC fights vs 1-3: 44.5% wins, -13.6% ROI. | Labs > Spots |   |
| Spots | Chin: 2+ prior UFC KO losses | done | Knocked out again 26.1% vs 16.2% base; market prices it (-2.2% ROI). | Labs > Spots |   |
| Spots | Cardio as a pre-fight bet (better R1-to-R3 swing) | done | 54.0% wins vs 51.2% implied; -2.4% ROI. Not a pre-fight edge. | Labs > Spots | Walk-forward |
| Spots | Short-notice replacements | proxy | Late-posted lines: favorites 75.6% vs 70.0% implied, +3.6% (201). Cannot tell who stepped in. | Labs > Spots | NEEDS a replacement list (Wikipedia event pages or Tapology) |
| Spots | Favorites by card slot / five-rounders / title fights | done | Main-event favorites -9.5%; title-fight favorites -11.3%. | Labs > Spots | Slot counted from top of card |
| Venue | APEX vs full-size cage | done | Finish rate 51.3% both; favorites 69% both. No cage-size effect. | Labs > Octagon | Venue log from Wikipedia (data/venues_vegas.csv) |
| Venue | Altitude (Mexico City, Denver, Salt Lake City) | done | Finish rate normal; R3 output does not drop; favorites 75% vs 68% on 92 fights. | Labs > Octagon | Small sample |
| Venue | Home country, pre-fight | done | Outside USA: 62.1% vs 57.5% implied, +8.0% ROI (145). In USA: -9.8% (532). | Labs > Round scoring | Birthplace from scorecard pages; 1,451 fighters |
| Venue | Home cooking on the scorecards | done | Overall none (49.9% vs 49.3% expected, 1,191). Outside USA 58.9% vs 52.2% (370). | Labs > Round scoring | CORRECTED: an earlier build mis-assigned birthplaces and overstated this |
| Divisions | Yearly outcome rates and 12-month rolling baselines | done | Flags divisions 12%+ off their 3-year baseline. | Labs > Divisions | Cross-checks with Fight Matrix yearly tables |
| Fighters | Custom metrics: control per takedown, KD rates, chin, head/body/leg defense, distance and target differentials | done | 487 active fighters, sortable. | Labs > Fighter metrics | Head-at-distance cannot be isolated (UFCStats does not cross target with position) |
| Fighters | Form Figure and power rankings | done | Opponent-adjusted performance rating; rankings by division. | Rankings; fighter pages |   |
| Cardio | R1 vs R3 swing, output, takedown attempts, control | done | Swing is a stable trait (split-half r 0.33); raw output is not (0.06). Better-history fighter out-lands in R3 59%. | Labs > Cardio |   |
| Live | What round 1 tells you | done | Out-landed by 10+: 75% win. Out-landed but lost 2+ min control: 45%. Dog up 10+ after R1: 55%. | Labs > Live | No live odds archive, so baselines only |
| Live | Comeback spot (behind after R1, better late history) | done | Wins R3 on strikes 44% vs 35% base (432). | Labs > Cardio |   |
| Judging | Fight-level scoring model | done | Stat sheet picks the decision winner 84.6%. | Labs > Scoring | UFCStats totals since 2010 |
| Judging | Round-level scoring model | done | Picks round winner 84%; KD = 10.4 head strikes, sub attempt 3.9, control minute 2.6, takedown 1.8, body 0.7, leg 0.6. | Labs > Round scoring | MMADecisions round scores 2010-2026: 3,268 decisions, 10,293 rounds; 265 unmatched |
| Judging | Calibration of the round model | done | 55% predicted -> 58% actual; 99% -> 98%. | Labs > Round scoring | In-sample |
| Judging | Per-judge weights, 10-8 rates, control-vs-strikes lean, lone rounds | done | McCarthy 1.9x pool on control; Chris Lee most head-strike driven. | Labs > Round scoring; judge pages | Shrunk toward pool |
| Judging | Split disputes, outlier rounds, outlier cards, lone 10-8s | done | 627 disputed decisions; 343 lone 10-8s. | Labs > Round scoring |   |
| Judging | Media vs judges | done | Media disagreed with 327 of 3,227 decisions. | Labs > Round scoring |   |
| Judging | Next fight after a disputed decision | done | 'Robbed' by the stats: -19.6% backing, +13.4% fading (97). Won a lopsided decision: -12.0% backing, +8.4% fading (325). | Labs > Round scoring |   |
| Judging | Referees: KO/sub rates vs expected | done | Miragliotta and Herzog run high on KO/TKO. | Labs > Referees | No data on early/late stoppages |
| Models | Form Line, method and distance models | done | Form Line 63.0% vs close 69.3%; GTD runs high in five-rounders. | Model |   |
| Models | Sheet model reproduction and tracker | done | Formula reproduced on 103 fights; Brier 0.2214 vs close 0.2269 (86). | Fight pages; Model |   |
| Props | Finish profiles per fighter and fight-length profile for the next card | done | 485 active fighters; next-card averages vs division baseline. | Labs > Props & pace | Simple averages, not matchup-adjusted |
| Props | When fights end (round-by-round finish rate) | done | Three-rounders: 26% end in R1, then 22%, then 14% of those still going. | Labs > Props & pace |   |
| Cardio | Pace by round (3- and 5-round fights going the distance) | done | Output rises every round; TD attempts rise; TD accuracy falls (37% R1 to 34% R3; 32% to 30% over five). | Labs > Props & pace |   |
| Physical | Age curves by weight group | done | Lighter men peak under 28 and fall hardest after 34; heavyweights peak 28-30. | Labs > Props & pace |   |
| Models | Markov duration model grading | done | 39 fights: market ahead on both channels so far. | Markov > Grading | Small sample |
| Judging | Before/after the 2017 criteria revision; 10-8 rate by year | done | Knockdown 8.2 -> 11.9 head strikes; takedown 2.6 -> 1.4; control unchanged. 10-8s doubled in 2017-2020 (6%) and are back near 2% since 2024. | Labs > Round scoring |   |
| Fighters | Strength-of-schedule adjusted strike differential | done | Every 100 Elo of opponent costs 0.34 strikes/min of differential; adjusted column and average opponent Elo added. | Labs > Fighter metrics |   |
| Spots | Camps by 'fighting out of' city | done | Line-era samples too small to bet; Denver/Englewood, Auckland, London, Philadelphia positive, Rio, Sacramento, Albuquerque negative. | Labs > Round scoring | City is a proxy for gym; latest city only; 1,178 fighters |
| Spots | Style matchups, walk-forward | done | Career strike differential 2+/min better than opponent: 70.6% vs 62.4% implied, +10.1% ROI (221). Wrestler vs weak TDD, power vs chin, volume edge, control edge: all priced. Positive 4 of 5 years (2022 +8.6%, 2023 +16.0%, 2024 +26.8%, 2025 -3.3%, 2026 +4.8%). UFC 334 qualifier: McKinney over Miller. | Labs > Spots | BEST PRE-FIGHT SIGNAL SO FAR; needs out-of-sample confirmation |
| Spots | Aged 35+ and off a year or more | done | 34.8% vs 40.1% implied; -24.8% ROI (115). | Labs > Spots |   |
| Market | Round totals vs fighters' distance histories | done | No edge. Unders lose in every group (-7.7% overall); overs about break-even. | Labs > Spots | sharpest-book totals, 1,059 fights |
| Blocked | Regional Elo by promotion | blocked | No regional fight data. | - | NEEDS Tapology/Sherdog export or Fight Matrix licence |
| Blocked | Live-odds backtests | blocked | No in-fight price archive. | - | NEEDS live odds source |
| Blocked | Tipster consensus vs close | blocked | betmma.tips returned nothing to the fetcher. | - | Try through the browser |
| Ideas | Fan scoring vs judges vs media | idea |   |   | Fan round percentages were collected for 2024-2026 only |
| Ideas | Our Elo vs public Elo sites | idea |   |   | Three bookmarked sites; manual comparison |
