# MM-1: Sean's hand-set method numbers (pre-registered 2026-11-14 ~06:40Z, before running)

Kirk round 36. Sean confirmed (Nov 14 ~1:30 am ET) that he typed his own method numbers on several fights and that the
sheet is correct. Rule, written before running it once on the 06:09Z export:

1. The method split is checked exactly as before (Block 44: sheet_v47.method_gtd from the fight's own method_inputs,
   tolerance 0.0001, every cell compared). Nothing is loosened or skipped.
2. If a side does not match, the check tries, in this order and only these: pin that side's DEC to the exported value;
   then pin DEC and KO. Pinned = taken as Sean's typed value. Every cell that is not pinned (KO when only DEC is pinned,
   SUB always, the fight GTD = L x DEC_dog + (1 - L) x DEC_fav) must still match the tab formula, recomputed from the
   pinned values, within 0.0001.
3. A side that matches with no pin is not manual. A side that matches with neither pin set fails as before.
4. Accepted pins are written to the live file as "manual_method": fight, side, which share was pinned (DEC, KO), Sean's value and the formula value it replaced, label
   "manual method". The report lists them.
5. Plants: the 11/12 export (no typed values) still passes with no manual_method; a single DEC changed without its
   KO / SUB / GTD following must fail; a typed DEC + KO whose SUB does not equal 1 - DEC - KO must fail.

Amendment before the first commit (2026-11-14 ~07:05Z): the cell addresses are left out of the live file and the report,
because the public scan treats sheet cell references as sheet internals. They are reported to Kirk privately.
