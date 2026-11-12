# Friday runbook (Sean's steps only)
1. Fri, when ready: in the repo run `python3 scripts/listed_price_report.py --slug ufc_334 --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json` (about 5 s).
2. For each row ending "NO: paste a current US-regulated price", type that row's "Best US now" price into the fighter's Listed cell in the UFC Model sheet.
3. In the sheet: menu **UFC > Refresh prices**, wait for it to finish, then menu **Site > Publish to site** and wait for the "published" message.
4. Tell Claude "published" with the time.
5. Limits: the rehearsal refuses by itself if your export is over 2 hours old; if Claude tells you it did, redo steps 1 to 3. The refresh blocks 24 hours after your last publish (the current export, published Wed 8:18 pm ET, blocks from Thu 8:18 pm ET, so nothing refreshes Friday until you publish).
6. Sat, after 12:00 pm ET: repeat steps 1 to 4 once. That moves the 24-hour block past the main event.
7. Everything else (rehearsal, merge, checks, rollback) is Claude's, and nothing reaches main without Kirk's go.
