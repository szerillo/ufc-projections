# r36 rebased onto origin/main e9ade8ca (Kirk, Nov 14)

Code commits only (footnotes + manual-price tag off, plant anchor); r36's refresh commit (older odds) left behind.
The live export is 32.5 h old, so friday_refresh blocks go-live (24 h rule). This is a rehearsal with ALLOW_STALE=1;
its outputs are NOT committed. The real refresh runs after Sean's publish (FRIDAY_RUNBOOK steps 6 and 7).

- friday_out.txt: embeds 2803/2803, card tables 1112 numbers, 0 failures; no manual tag, no footnote lines.
- sat_r36b.sh / sat_out.txt: saturday_check (check 1 = origin/main + branch): PASS. Listed gate notes Gane -180 and Juan Diaz -333 (stale export prices; Sean's Refresh fixes).
- neg.txt: negative suite 37/37.
