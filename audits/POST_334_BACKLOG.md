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
6. **Labs angle bugs found in round 20 (fix with the research refresh, pre-registered):**
   - `form_model.angle_sides`: an angle where BOTH fighters qualify keeps only one side (dict overwrite). "Age 37 or older"
     drops 43 bets in the fresh build; check every symmetric angle.
   - Fighters who share a UFCStats name (Bruno Silva, Jean Silva, ...): the build takes the first namesake's DOB, stance and
     reach. 15 "Younger by 5+", 5 "Under 32 vs 36+" and 8 "Reach 4+" memberships depend on which namesake is used.
   - "Southpaw vs orthodox" is clean on both checks (the embed box on fight 10 uses it).
