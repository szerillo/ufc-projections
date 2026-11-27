# Dec 5 2026 card check (UFC Fight Night: Adesanya vs. Magomedov, Riyadh), Nov 27

Built by C1 for Kirk. The UFC.com event page was not read: the fetch needed an approval nobody was there to give. Everything below needs a UFC.com check before it becomes `data/official/2026-12-05.txt`.

## Bouts (UFCStats event a1bf037613180253 order, read in Sean's Chrome Nov 27)
| # | Bout | Weight | Rounds | Segment (sources) | Notes |
|---|---|---|---|---|---|
| 1 | Israel Adesanya vs Shara Magomedov | MW | 5 | Main (all) | UFC.com snippet: #9 vs #14, -160 / +135 |
| 2 | Ian Machado Garry vs Yaroslav Amosov | WW | 5 | Main (all) | Moved from UFC 335 (Wikipedia) |
| 3 | Serghei Spivac vs Mario Pinto | HW | 3 | Main (MMA News, Yahoo) | |
| 4 | Levan Chokheli vs Islam Dulatov | WW | 3 | Main (MMA News, fight.tv) | |
| 5 | Mairon Santos vs Akbar Abdullaev | LW | 3 | Main (fight.tv, ESPN) | |
| 6 | Magomed Tuchalov vs Ion Cutelaba | LHW | 3 | Main per ESPN; unclear elsewhere | |
| 7 | Bruno Silva vs Jafel Filho | FLW | 3 | Prelims (ESPN) | |
| 8 | Uran Satybaldiev vs Ivan Gnizditskiy | LHW | 3 | Prelims (likely) | Gnizditskiy UFC debut |
| 9 | Marco Tulio vs JunYong Park | MW | 3 | Prelims (likely) | |
| 10 | Pavel Andrusca vs Mahammadali Osmanli | BW | 3 | Prelims (likely) | |
| 11 | Modestino Rodrigues vs Matthieu Duclos | MW | 3 | Prelims (likely) | |
| 12 | Abdul Hussein vs Hecher Sosa | BW | 3 | Prelims (likely) | |
| 13 | Luke Riley vs Gabriel Santos | FW | 3 | **Conflict:** Wikipedia main card | **Changed in the last 7 days:** moved from UFC 335; not on the Nov 23 12-bout lists |
| 14 | Mateusz Rebecki vs Elves Brener | LW | 3 | **Conflict:** Wikipedia main card | **Changed in the last 7 days:** as above |

- **No bout is marked TBA in any source.** Nov 23 sources had 12 bouts; UFCStats now has 14.
- **Main card / prelim split is unresolved.** ESPN shows 6 main-card bouts. Wikipedia puts the two late additions on the main card. Only UFC.com settles it.
- **Start times conflict:**
  - UFC.com event page: main card 1:00 PM ET (18:00Z).
  - ESPN: prelims 10:00 AM ET (15:00Z).
  - Yahoo: prelims 1 PM / main card 4 PM ET.
  - UFC.com events index (likely a stale template): 5 / 7 / 9 PM ET.
  - cards.yml on this branch uses first bout 15:00Z, main event 21:00Z.
  - **Confirm before merge.** With 14 bouts there may be early prelims before 15:00Z.

## Gradeability (UFCStats fighter pages Nov 27; site fighter files on main)
| Fighter | UFC bouts (UFCStats) | Site file | Flag |
|---|---|---|---|
| Ivan Gnizditskiy | 0 | none | **UFC debut:** Markov thin sample; D-code check needs the last pre-UFC promotion (Sherdog) |
| Akbar Abdullaev | 1 (Sep 15 2026, a Tuesday: DWCS) | none | **UFC debut** (DWCS exempt from D-code); no site file |
| Modestino Rodrigues | 1 (Sep 1 2026, DWCS) | none | **UFC debut** (DWCS); SLpM 32.0 is a 1-bout artifact |
| Chokheli, Tuchalov, Andrusca, Osmanli, Hussein | 1 each | yes | Thin sample (3 or fewer UFC bouts) |
| Amosov, Dulatov, Satybaldiev, Duclos, Sosa | 2 each | yes | Thin sample |
| Luke Riley | 3 | yes | Thin sample |
| Gabriel Santos | 4 | yes | **Layoff:** last fight Feb 8 2025 (about 22 months) |
| Islam Dulatov | 2 | yes | **Layoff:** about 16 months |
| Uran Satybaldiev | 2 | yes | **Layoff:** about 15 months |
| JunYong Park | 13 | yes | **Layoff:** about 13.5 months |
| Mairon Santos | 4 | yes | **Layoff:** about 12 months |

- **Site files behind UFCStats** (the UFCStats cache ends Nov 7): Pinto 4 vs 5, Dulatov 1 vs 2, Marco Tulio 4 vs 6, Duclos 1 vs 2, Sosa 1 vs 2, Rebecki 9 vs 10.
  - The embeds' Fight Form numbers would be stale until the cache and build_form are refreshed.
- **Card guard G2:** no fighter on this card has a UFC bout after Nov 5. The latest is Sep 26 (Osmanli, Brener).
