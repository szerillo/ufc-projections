# Embeds: Kirk round 13 (2026-11-12)

Nothing merged or published. Nothing touched main, the live sheet or X.

- **Branch `embeds-v5`** is now at **5d309249 (v25)**. It adds the call 2 card flag; no published number changes.
- **Call 1 is on a separate branch, `embeds-v5-r13-cut` (fe6b4cba).** It failed pass-bar item 2, so `embeds-v5` does not carry it. Kirk decides.

## Call 1. Cut the published close at the earlier start estimate

**Pre-registered first:** `Earlier_Start_PREREG`, sha 5c667602. It was saved to the project before the run and run once.

**Rule.** The cut is the earliest of three start estimates:
- **E1:** the commence time on the bout's last archive snapshot (the old rule).
- **E2:** the BettingPros scheduled time, where the repo has one.
- **E3:** the earliest archive commence time within 12 h before E1.

Only snapshots strictly before the cut count toward the published close and chart. The opener, research, Form fits and backtests are unchanged.

```
published odds blocks: 2469; recomputed: 2469; not equal to v24 recompute (left alone): 0
close unchanged: 1927; close moved to an earlier snapshot: 533; close lost (opener only): 9; opener after cut: 8
change in close, pts (moved only): median 0.90, p95 6.55, max 29.63; over 1 pt: 241; over 3: 94
independent recompute (own cut, own median): 2469 published blocks, 2455 with a close, 0 mismatches
UFC 334 checker: EVENT ODDS RECHECK 13 bouts, 0 mismatches; negatives 30/30
```

**Pass bar**

| Item | Result |
|---|---|
| 1. Blanchfield vs Jasudavicius near its pre-fight median | PASS on the registered definition: 0.6887 vs 0.6868, 0.19 pts (see caveat) |
| 2. No bout loses all its US prices | **FAIL: 9 bouts** lose their only US close and go opener-only, per the call |
| 3. Site-wide diff | Reported above; independent recompute 0 mismatches |

The 9 bouts that lose their close are all early prelims whose only US price was the 21:55 UTC fight-day snapshot:
- Pearce vs Rodriguez, 2022
- Argueta vs Aguirre, 2023
- Fletcher vs Gorimbo, 2023
- McKinney vs Marotte, 2023
- Shahbazyan vs Chokheli, 2026
- Basharat vs Garza, 2026
- Johns vs Vazquez, 2026
- Barbosa vs Kuse, 2026
- Young vs Dorsainvil, 2026

**What the result shows (I did not change the rule after seeing it):**
- **E3 is often the card's start time, not the bout's.** For Blanchfield, E3 was 21:00 on Oct 17. That cut the clean fight-day snapshot at 21:55 (US median about 0.739) as well as the in-fight one at 01:55. Her close is now a week old (Oct 11). The pre-registered reference also sits before the cut, so item 1 passes on paper. Against her fight-day price, the gap is about 5 pts.
- **Brady vs Buckley moves 29.6 pts.** E3 is 20:00, so the cut drops a 21:55 snapshot where every book agreed at about 0.33. That price is not an in-fight split.
- **E3 was my addition.** Kirk's call named two estimates. With E1 and E2 only, the cut would change just the 225 bouts that have a BettingPros time. Running that variant now would be picking a rule after seeing the results. It needs a new pre-registration and Kirk's go.

## Call 2. Non-title five-round bouts

- **The scrape has the field for past bouts.** `ufc_fight_results.csv` (Greco1899 UFCStats scrape) carries TIME FORMAT on all 9,015 past bouts. Past Form already reads rounds from it, so no past published number depends on the main-or-title rule.
- **Upcoming bouts have no field.** I checked in Chrome: UFC 334's upcoming fight-details pages have no "Time format" line. They do show "Title Bout".
- **So the manual card flag is the fallback.** `card_overrides.json` now takes an optional `"five_rounds": [["A","B"]]` list. It is empty for UFC 334, so no number changes. The match test passes in either corner order and does not match Harrison-Nunes.
- **Flip count.** These are past bouts the upcoming rule (title or main event) would build as 3 rounds but UFCStats lists as 5:
  - 16 in total, 14 of them since 2022. Examples: Muhammad-Burns 2023, Poirier-Saint Denis 2024, Whittaker-Chimaev 2024, Tsarukyan-Ruffy 2026.
  - The reverse error (rule says 5, actual 3): 14 since 2022, mostly main events booked as three-rounders.

## Call 3. Harrison-Nunes correction

**Confirmed.** `form/corrections.html` has a "November 12, 2026" entry. It names Kayla Harrison vs Amanda Nunes and gives both numbers: 50.4% as shown and 43.0% on the five-round basis. It gives the cause: "built as a three-round fight". It says the numbers were public since November 10.

The file is committed on `embeds-v5` (bbb37be1) and is not on main, so it ships with the merge. It is linked from every embed footer and from the Model page.

## A. Is 12.7 pts the only in-fight leak?

Under the earlier-start rule, **542 of the 2,464 v24 published closes** included a price at or after a start estimate:
- **29 after the BettingPros bout time (E2).** 2 of these (6.9%) show a US-book split over 15 pts, which is the in-fight signature: Blanchfield and Basharat.
- **513 only after E3, the card-level time.** None of them shows a split over 15 pts. That matches the 1,898 clean closes (0%). These look like legitimate fight-day prices, not leaks.

**Hand checks:**

| Bout | What the snapshot shows | Verdict |
|---|---|---|
| Blanchfield vs Jasudavicius, 01:55 | DraftKings 0.37 and BetMGM 0.48 vs the others at about 0.73 | In-fight |
| Basharat vs Garza, 21:55, BP start 21:40 | DraftKings 0.53, BetMGM 0.72, Caesars (William Hill) 0.87 | In-fight |
| Anheliger vs Koslow, 21:55, BP start 21:40 | All books agree at about 0.37 after 0.54 the week before | Likely in-fight (15 min after the scheduled start), but books agree, so not certain |

**Answer:** 12.7 pts was not the only leak. The confirmed leaks sit in the 29 bouts that have a bout-level time. The archive alone cannot tell a card start from a bout start.

## B. Do any of the 657 moved distance numbers feed an edge, pick, graded record or Spot to watch?

**Perturbation test.** I set every `form.g` and `form.base` in every event file to 0.999 (18,000 values), rebuilt, and compared:
- **Embeds (13 for UFC 334):** byte-identical. The builder reads only the Form Figure (`fm["ra"/"rb"]`). Spot to watch reads `LABS["cardio"]` and CW, not Form distance.
- **Site, rendered:** these pages had 0 changed lines:
  - the Model page (sheet tracker, recommendation record, graded bets);
  - Home;
  - the UFC 334 and UFC 333 card pages.

  The only changes are on fight pages: "division base" in the Form numbers table, which is a display.
- **Static readers of the other moved fields:**
  - `model_compare/*` `form_gtd`: a log; no page reads it.
  - `research.json` `gtd`/`gtd_calib`: read only by the Labs "Form distance model" calibration table (`app.js:673`), which is research.

  Picks and recs come from the sheet: `pf["sheet"]`, `so["rec"]`, embeds `pf["gtd"]`.

## C. An assumption under the US-only median

**Assumption tested:** the US book set is stable across years.

| Year | Closes | Mean US books | DK | FD | BetMGM | BetRivers |
|---|---|---|---|---|---|---|
| 2023 | 497 | 4.55 | 99% | 86% | 79% | 96% |
| 2026 | 463 | 3.51 | 96% | 86% | 68% | 5% |

- **The assumption is false.** BetRivers drops out of the archive in 2026, and BetMGM thins. DK is near-always present. FD is missing on 14% of closes in both years. Single-book closes: 1.0% in 2023, 2.4% in 2026.
- **The effect is small.** Re-taking 2023 medians over only the 2026-style set (DK, FD, Caesars (William Hill), MGM) moves them by a median of 0.14 pts, p95 0.65, max 1.49. 9 of 492 closes move more than 1 pt. So 2023 and 2026 closes are comparable, within about 1 pt.

## D. Status

| Item | State |
|---|---|
| Verifier, v25 | 2,869/2,869 numbers; event odds and line history 0 mismatches; locks 31/0 changed; metrics 2,984/2,984 |
| Negatives (cut branch) | 30/30 |
| Call 1 | On `embeds-v5-r13-cut`; failed bar item 2; not on `embeds-v5` |
| Call 2 | Field confirmed for past bouts only; card flag added; flip count 16 |
| Call 3 | Confirmed; ships with merge |

**Remaining merge blockers:**
1. Sean: fix Gordon/Costa/Hasan and republish the sheet.
2. REHEARSAL PASS after that republish.
3. Kirk's call on the cut branch: ship, drop, or re-pre-register as E1 + E2 only.
4. Kirk's go.

**Kirk decides:**
- **Call 1, three options:**
  - (a) Ship as is. 9 bouts go opener-only, and 513 fight-day closes move back to earlier snapshots.
  - (b) Drop it.
  - (c) A new pre-registration with E1 + E2 only (your literal two estimates). It fixes the bouts with a BettingPros time and leaves the archive-only bouts on E1.
- **If any cut ships:** a dated corrections entry, since past closes move.
- **Embed line history:** whether it should take the same cut. It was out of the pre-registration's scope; no effect before UFC 334 starts.
- **Research:** whether the all-books research close should also use a cut. It is unchanged here.

Reproducibility: scripts, outputs and sha256 (first 12 characters) are listed in `hashes_r13.txt`. Key files: PREREG 5c6676024b9d, apply 13f85fbae92e / 75e3ad456274, checkA 3226ba5b62e0, perturbation 3d87c7d7e75e, checkC ae1be025420c / afd722504ff6, call 2 28deaf1a84c5.

thread done
