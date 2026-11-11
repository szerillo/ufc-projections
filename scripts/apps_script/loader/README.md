# Branch loader-patch: grading fix for the sheet's Apps Script loader (v2.7)

Status: the patch and its test exist as a LOCAL commit only. The loader source is not pushed to this public
repository; whether to publish it (or move it to a private repo) is Sean's call. Nothing here is installed in the sheet.

What the patch changes (loader v2.7, Code.gs line numbers):
- L1173 `gradeCard`: asks for the card id (Snapshots column A) instead of always grading Feed!B2.
- L1179: keeps the winner's corner (red/blue), full name and athlete URLs next to the last names.
- L1200-1201: the sheet dog's corner comes from full names, then (same surname) the first name or athlete URL slug;
  dogWon comes from the winner's corner. The old code compared last names only, so Yana vs Luana Santos was
  always graded as a Yana win.
- L1304 `propSnapGrade_`: keeps grading on the Snapshots side (the prices define the dog) and lists rows whose
  PropSnap name labels are swapped, instead of silently using them.

## Files (local commit)
- `v2.7_name_helpers_L170-189.gs`, `v2.7_grading_L1092-1340.gs`: verbatim excerpts of the installed Code.gs, read
  2026-11-11 from the script editor (read only). sha256 matches the hash computed inside the editor page:
  L170-189 `46fc1a991b19d807…` (1,868 chars), L1092-1340 `a1f020e5f43ef18e…` (21,899 chars); full file 124,707 chars `3a1fcc2989ec78d1…`.
- `patched_grading.gs`: the L1092-1340 excerpt with the patch.
- `test_grading_names.js`: runs the loader's own gradeCard + propSnapGrade_ on an in-memory sheet.
  `node test_grading_names.js v2.7_name_helpers_L170-189.gs v2.7_grading_L1092-1340.gs` -> 3 of 6 fail (exit 1)
  `node test_grading_names.js v2.7_name_helpers_L170-189.gs patched_grading.gs` -> 6 of 6 pass (exit 0)
