# Round 34: Line-pending bouts in the embed build

Code: scripts/build_fight_embeds.py, scripts/verify_fight_embeds.py, scripts/saturday_check.sh (card.json allowed).

- control.py, control_out.txt: 0 pending, same inputs, old builder (origin/main 6d02728b) vs new. Registries and card.json byte-identical; HTML identical once the guard script and #sean-proj wrapper are removed.
- plants.sh, plants_out.txt: 1 pending, 3 pending, main event pending, control. Verifier 0 mismatches each, pending bouts named.
- guard_rt.py, guard_rt_out.txt: runtime guard at 390px. A later live file that holds a bout back hides that embed's numbers; other fights unchanged; unreachable file changes nothing.
- friday_out.txt: friday_refresh on a checkout of the branch with tonight's live export (22:47Z, 0 pending). TOTAL 2965/2965, 0 mismatches.
- sat_asis.txt: saturday_check as written stops at check 1 (checkout is the branch commit, not origin/main). Expected until the push.
- sat_branch.sh, sat_branch_out.txt: the same script with only check 1 changed (HEAD must be origin/main plus the branch commits) and the cd path. PASS.
- sat_plant.sh, sat_plant_out.txt: same, with a local fake-main commit holding fight 10 (Holland vs Medic) Line pending. PASS, 2901/2901.
- sat_neg_out.txt: an off-list file still refuses.
