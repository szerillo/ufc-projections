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
