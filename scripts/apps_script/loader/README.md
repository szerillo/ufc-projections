# Loader (UFC Model sheet, Apps Script): source, grading fix, test

Nothing here is installed in the sheet. Install date moved to **Thursday Nov 12** (Kirk, with the publish script; Block 48),
so the TRAP exclusion applies to UFC 334. Steps, readback and rollback: PUBLISH.md, "Thursday install".

## Files
- `Code_v2.7_installed.gs`: the loader as installed, read from the script editor Nov 11 (installed file sha256
  `3a1fcc2989ec78d1`, 124,707 chars, 1,340 lines). Two settings were moved out of the code before upload (below);
  nothing else differs.
- `Code_v2.8_patched.gs`: the same file with lines 1092-1340 replaced by `patched_grading.gs` (the grading fix), plus (Block 47)
  TRAP outlier prices excluded from D/I: a book 4+ pts better than the exchange fair never becomes the best price; the next
  best bettable book is used, or the consensus if none is left. Calculator AH marks it "TRAP, excluded from D/I".
  Test: `node scripts/apps_script/loader/test_out_trap.js` (Gordon, UFC 334: D +300 FanDuel, Caesars +420 excluded).
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
- L1189 `findRes`: one exact name no longer grades a bout on its own; the other corner must share a name token with the
  other sheet fighter. v2.7 graded Melissa Amaya vs Valesca Machado (Sept 26) against Amaya vs Tina Black (Machado was
  replaced), including a +0.49u win for the "BET Valesca Machado" rec. A replaced bout is now left ungraded.
- L1304 `propSnapGrade_`: grades on the Snapshots side and lists PropSnap rows whose name labels are swapped.

## Test
    node test_grading_names.js v2.7_name_helpers_L170-189.gs v2.7_grading_L1092-1340.gs   # 4 of 7 fail
    node test_grading_names.js v2.7_name_helpers_L170-189.gs patched_grading.gs            # 7 of 7 pass
The same holds on the full files (helpers = lines 171-190, grading = line 1093 to the end of each file).

## Install (Thursday Nov 12; about 10 minutes; steps 1-2 here, readback and rollback in PUBLISH.md)
1. Script Properties: add `BETTABLE_BOOKS` with the list from line 65 of the installed Code.gs. Proof: listed.
2. Replace Code.gs with `Code_v2.8_patched.gs`, Save. Proof: no red error; the UFC menu still loads after a reload.
3. (Sunday, after grading UFC 334, not Thursday) Live same-surname check: UFC > Grade last card, URL of the Oct 31 card, card id 4427 (Yana vs Luana Santos).
   Proof: the alert counts the card's rows, and a Snapshots/PropSnap export diffed against one taken just before shows
   no changed values except the "graded" timestamps (Snapshots AY, PropSnap Q): those rows were hand-corrected Nov 11
   to what the fix computes. Anything else changing: restore the previous Code.gs from version history.

## v2.9 candidate: refresh guard (Kirk round 29 A, Nov 12). NOT installed; v2.8 is the frozen Thursday install.
`Code_v2.9_guard.gs` = v2.8 plus: a Refresh never clears a row whose bout is missing from ufc.com but still listed on
BestFightOdds (any book, Polymarket included) or Novig; the row is kept exactly as it was and the alert says REFUSED. A drop in
the ufc.com bout count against the last load is the alert's first line. A really cancelled bout that a price source still lists
is removed with UFC > Remove a cancelled bout (last name, confirmed; one bout only). TRAP logic unchanged from v2.8.
Tests: `node test_guard.js` (13/13 on v2.9); `node test_guard.js Code_v2.8_patched.gs` shows the Nov 12 bug (6/13).
Install = replace Code.gs (as T2) with this file; rollback = paste Code_v2.8_patched.gs back.
