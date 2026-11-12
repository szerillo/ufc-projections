Kirk round 33 (MP-1, manual price). Evidence:
- MP1_plants.txt: scripts/test_manual_price.py, 8/8 (tonight's two typed prices accepted; -105, +200, -147 outside window, a non-US book only, archive unreachable, 3 days later: all line_pending; Feed price control).
- MP1_vs_gate.txt: MP-1 vs the go-live Listed gate (build_line_history.listed_check) on the full archive, 12 prices: 12/12 agree.
- MP1_tonights_export.txt: tonight's real export (21:41:39Z) through the fixed check: PASS, 0 line pending, 2 manual prices.
- post_merge_retry_plant.txt: _audit 503 once then 404 -> PASS; 503 twice -> FAIL.
Found, not fixed (Kirk decides): a line_pending fight in the live file breaks the embed rebuild on main (fight 1 drops 17 numbers,
verifier 23 failures; saturday_check would refuse, so the last pushed embeds stay). Main right now: embeds were built from the
13-fight pending export and still show Sean's numbers for the 2 pending fights, while the card page shows "Line pending".
