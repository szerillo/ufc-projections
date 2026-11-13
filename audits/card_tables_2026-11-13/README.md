# Card pages in the fight-preview format (Sean, 2026-11-13)

- plants_out.txt: verify_card_tables.py plants. A: one changed number fails. B: a fight dropped from props fails. C: fight 10 Line pending, embeds and card pages rebuilt, passes with Line pending rows (the 26 line-history/event-odds mismatches in that scratch run come from rebuilding without a refresh, archive newer than main's line history; every fight verifies). D: a number shown for the pending fight fails.
- friday_out.txt: friday_refresh on a checkout of d125baff (origin/main 2e60cbdc + this commit), tonight's live export. Embeds 2965/2965, card tables 208 rows / 1646 numbers, 0 failures.
- sat_branch.sh, sat_out.txt: saturday_check with only check 1 changed (HEAD = origin/main + 1 commit). PASS.
- before_after_ufc334.png: the embed tool's Moneylines preset before (generic card list) and the three new pages.
