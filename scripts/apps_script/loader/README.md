# Loader (UFC Model sheet, Apps Script): source, grading fix, test

Nothing here is installed in the sheet. Install date: **Sunday Nov 15** (after UFC 334), unless 334 needs it first.

## Files
- `Code_v2.7_installed.gs`: the loader as installed, read from the script editor Nov 11 (installed file sha256
  `3a1fcc2989ec78d1`, 124,707 chars, 1,340 lines). Two settings were moved out of the code before upload (below);
  nothing else differs.
- `Code_v2.8_patched.gs`: the same file with lines 1092-1340 replaced by `patched_grading.gs` (the grading fix).
- `v2.7_name_helpers_L170-189.gs`, `v2.7_grading_L1092-1340.gs`: the excerpts the test runs; `patched_grading.gs` is the fix.
- `test_grading_names.js`: runs the loader's own gradeCard + propSnapGrade_ on an in-memory sheet.

## Settings now in Script Properties (Project Settings > Script Properties), not in code
| Property | What | If unset |
|---|---|---|
| `BETTABLE_BOOKS` | JSON list of the books you can bet (your accounts). Copy the list from line 65 of the installed Code.gs before replacing it. | DraftKings, FanDuel, BetMGM, Caesars, BetRivers, HardRockBet, Fanatics, ESPNBet |
| `NOVIG_PROXY`, `NOVIG_PROXY_KEY` | URL and key of a Novig proxy worker, if you deploy one | empty, same as today |

Read through `SP_(name, default)` (one added line). Never paste these values into the code, a doc or chat.

## What the fix changes (v2.7 line numbers)
- L1173 `gradeCard`: asks for the card id (Snapshots column A) instead of always grading Feed!B2.
- L1179: keeps each corner's full name and athlete URL next to the last name.
- L1200-1201: the sheet dog's corner comes from full names, then (same surname) first name or URL slug; dogWon comes
  from the winner's corner. The old code compared last names, so Yana vs Luana Santos was always a Yana win.
- L1304 `propSnapGrade_`: grades on the Snapshots side and lists PropSnap rows whose name labels are swapped.

## Test
    node test_grading_names.js v2.7_name_helpers_L170-189.gs v2.7_grading_L1092-1340.gs   # 3 of 6 fail
    node test_grading_names.js v2.7_name_helpers_L170-189.gs patched_grading.gs            # 6 of 6 pass
The same holds on the full files (helpers = lines 171-190, grading = line 1093 to the end of each file).

## Sunday install (about 10 minutes)
1. Script Properties: add `BETTABLE_BOOKS` with the list from line 65 of the installed Code.gs. Proof: listed.
2. Replace Code.gs with `Code_v2.8_patched.gs`, Save. Proof: no red error; the UFC menu still loads after a reload.
3. Live same-surname check: UFC > Grade last card, URL of the Oct 31 card, card id 4427 (Yana vs Luana Santos).
   Proof: the alert counts the card's rows, and a Snapshots/PropSnap export diffed against one taken just before shows
   **zero changed values** (those rows were hand-corrected Nov 11 to what the fix computes). Anything else: restore the
   previous Code.gs from version history.
