# After UFC 334 (Nov 14 2026): first items, in order

Logged 2026-11-12 (Kirk round 18). Nothing here is done before the card; the publish script is frozen until then.

1. **Publish export: remove sheet coordinates and raw inputs.** `data/pending/<slug>_projections.json` is public once on main.
   It carries sheet coordinates per fight (`tab`, `row`, `calc_row`) and raw sheet inputs (`tap`, `junk`, `tip`, `markov`,
   `shift`, `open_dog`, `ctx`, `manual`). Change the publish script (frozen at de4c2be3 until after 334) to drop them, then
   check every consumer (`publish_source.py`, `build_fight_embeds.py`, `verify_fight_embeds.py` rules `pub_ml`, `pubp`)
   still has what it needs. Pre-register the field list and run the public scan on the new export.
2. **Refresh `form/data/research.json`** from a full build. It was built on 2,388 fights; the current code gives 2,420 (the
   round 7 matcher fix). Every Labs number moves; the embed debut box moves from 233 / 49.8% / -11.9% to 234 / 49.6% / -12.3%
   (the added bout: 2025-02-08 Rongzhu vs Kody Steele). Rebuild `data/embeds/debut_angle_stats.json` with it.
3. **`scripts/check_rounds.py --post`** for the first real post-card five-round comparison (UFC 334's pre-fight version is
   committed).
4. **TUF sensitivity for the debut angle** (Kirk round 19). Pre-register, then run the debut_vs_vet angle with TUF tournament
   bouts counted both ways (as prior UFC fights, as now; and not counted). Report both with the research.json refresh in
   item 2. The embed box does not change before that.
5. **Merge guard.** If main moved before the merge, `scripts/main_guard.py` refuses; redo the round-18 served-set check on the
   real merge result and record the new main SHA in `audits/MAIN_AT_CHECK.txt` on purpose.
6. **Labs angle bugs (round 20 found, round 21 measured; fix with the research refresh in item 2, pre-registered).** Live on main
   now; Labs and the fight-page angle rows carry an "under review" mark from `form/data/labs_review.json` until the rebuild.
   - `form_model.angle_sides`: when BOTH fighters qualify only side b is kept (dict overwrite). 8 angles: off_big_fig (+148
     bets on the published set), off_bad_fig (+113), age37 (+43), moving_up (+24), power_vs_chin (+9), moving_down (+7),
     wrestler_weak_tdd (+6), wrestler_strong_tdd (+2). Also drops one side's chip on upcoming fight pages (334: fights 13, 12).
   - Shared UFCStats names (Bruno Silva, Jean Silva, Mike Davis, Anthony Romero, Victor Valenzuela): `load_ufcstats` takes the
     FIRST tott row; wrong in 23 of 30 bouts since 2022 (fight-page IDs in `audits/round21/ns_ids.txt`). 36 memberships change
     in younger5, vs_36, reach4, age37 and southpaw (southpaw +2: Romero 2026-10-03, Levy 2024-03-16). The same row feeds the
     Form model's age/reach/stance features, so those fighters' Form Lines move too; fight histories are also merged by name
     (fighter pages already show the shared-name banner).
   - Together: 111 displayed Labs numbers in 12 of 46 angles change; no angle's ROI at the close changes sign
     (`audits/round21/labs_fix_effect.txt`). Fix: key bios and histories by UFCStats fighter ID, count every qualifying side.
7. **Bio values where UFCStats and UFC.com disagree (Kirk round 24 call 2).** Bia Mesquita reach (UFCStats 67", UFC.com 67.50)
   and Juan Diaz reach (69" vs 69.50) stay "not listed" for UFC 334: Bio_Fill_PREREG said the two must agree, and no rounding
   tolerance is added after the fact. Hasan and Diaz stance stay "not listed" (UFC.com has no stance field). After 334,
   pre-register a rule for half-inch differences and for a second stance source before using either. Note: a missing reach
   zeroes the Form model's reach term (read as equal reach), in training and prediction alike (audits/round24/B_missing_reach.txt).
8. **Drift box (Kirk round 25 A): pulled before shipping.** The Labs drift reference (1,733 fights) is all books at open and at
   close; the box's "now" used US-regulated books only. Same book set for Gane: -7.3 pts and 157/1,733 = 9.1% (box showed -7.1
   and 166 = 9.6%). To bring it back, pre-register ONE book set for both sides: either rebuild the reference set from US-regulated
   books at open and close, or show an all-books "now" on the box (which breaks the US-only current-line rule, so likely the former).
