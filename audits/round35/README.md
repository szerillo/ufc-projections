# Kirk round 35: the approved design as the embed design for all 13 UFC 334 fights

origin/main 81590403 already carried the approved design (card-tables-v4). This round adds the export's manual-price label on MP-1 listed prices (it was in the export but not rendered) and checks everything on the live export.

- friday_out.txt: friday_refresh on the live export (published 2026-11-12T22:47Z): embeds 2803/2803, card tables 1112 numbers, 0 failures.
- sat_r35.sh / sat_out.txt: saturday_check with check 1 = origin/main + 1 branch commit: PASS.
- render_out.txt: render_check on a local build (http://localhost:8806, ufc_334): 416 shown values, 0 mismatched, 0 page errors. It reads the card page and its embed surface.
- neg.txt: negative suite 37/37 (35 + 2 manual-label plants).
- plants.sh / plants_out.txt: round 34 Line-pending plants (1, 3, main event, 0 pending) on the new design, plus card tables per plant: all pass, pending bouts named.
- r35_fight13_* / r35_fight01_*: Gane vs Hokit and Elder vs Sanches, projection and stats, 390 px and desktop.
