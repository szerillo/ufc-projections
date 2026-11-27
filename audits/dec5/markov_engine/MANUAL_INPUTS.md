# Dec 5 engine staging: manual inputs (judgment calls)

- Tuchalov pre_ufc 6-0, all finishes (C1 file had 5-0): Sherdog lists 6 pro bouts before the UFC win (Khakimzhonov, Hardcore MMA Aug 2023, was not counted); matches UFCStats 7-0.
- Gnizditskiy pre_ufc 5-0 per UFCStats (Sherdog 7-0 adds a League of Boxing knuckle bout and a 2018 tournament bout). Fewer bouts = less prior weight, the conservative choice.
- Osmanli pre_ufc kept at Sherdog 11-1; UFCStats shows 13-2 overall (2 wins Sherdog does not list). No third source scraped (Tapology is off limits).
- career_context records: Sherdog win-method counts for all 28; Tuchalov and Gnizditskiy use the UFCStats records above. Mairon Santos (Sherdog 17 W vs UFCStats 18) and Hecher Sosa (14 vs 15) use Sherdog counts; both have 2+ UFC bouts so only career KO/sub shares move.

# Open questions for Kirk (conservative default applied)
- **Abdullaev and Modestino Rodrigues KD rates:** 1 knockdown each in 0.3 DWCS minutes gives kd_per15 50.0. After the engine's K=5 regression it is still far above any real rate and will hit the 0.40 P(KD) clamp. Default: left raw, as the kd_scrape recipe says, and labelled ARTIFACT in the output. The alternative is to drop the key (division-mean fallback). That is an input change, so it's your call.
- **Amosov D-code:** his last pre-UFC bout was CFFC (Mar 2025), so the feeder is "minor" under the last-bout rule, even though his record is a Bellator title run. Default: the rule as written (same as Lorenz on Nov 19). It only matters if he is the dog.
- **Modestino Rodrigues D-code:** DWCS is skipped, so his last non-DWCS bout is BCC (minor). Default: D-code applies if he is the dog, same as Lorenz.

# D-code status (applies only to the underdog; prices come Tue/Wed)
| Fighter | Prior UFC/DWCS bouts | Last pre-UFC promotion | Feeder |
|---|---|---|---|
| Akbar Abdullaev | 1 (DWCS) | ONE (Sep 2025) | major: exempt |
| Ivan Gnizditskiy | 0 | Chingi-Tura (Mar 2026) | minor |
| Modestino Rodrigues | 1 (DWCS) | BCC (Jun 2025) | minor |
| Levan Chokheli | 1 | Phoenix FC (May 2025) | minor |
| Magomed Tuchalov | 1 | UAE Warriors (Mar 2026) | minor |
| Pavel Andrusca | 1 | UAE Warriors (Jul 2026) | minor |
| Mahammadali Osmanli | 1 | UAE Warriors (Nov 2025) | minor |
| Abdul Hussein | 1 | Ice Cage (Dec 2025) | minor |
| Yaroslav Amosov | 2 | CFFC (Mar 2025) | minor (see above) |
| Islam Dulatov | 2 | Oktagon (Feb 2024) | minor |
| Uran Satybaldiev | 2 | LFA (Mar 2025) | minor |
| Matthieu Duclos | 2 | Hexagone MMA (Apr 2026) | minor |
| Hecher Sosa | 2 | WOW (Jun 2025) | minor |
| Luke Riley | 3 | Cage Warriors (Mar 2025) | minor |

The other 14 fighters have 4+ UFC bouts, so the D-code does not apply to them.

# Still to do Tue/Wed (odds and props, per Kirk)
- fights_raw (Oddsbreaker event tab), market_odds (BFO 4-book median), props (GTD/ITD, O/U).
- BFO L5 closing history for momentum (career_context momentum is 0.0 for now).
- Then run `PYTHONHASHSEED=0 python3 fn_adesanya_magomedov_sim_v41b.py` and produce the trio, flags JSON and sheet_inputs.
- Confirm the card against UFC.com first. The official list is still a DRAFT; the main/prelim split and start times are unconfirmed.
