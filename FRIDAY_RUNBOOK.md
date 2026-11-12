# UFC 334 runbook (Kirk round 32: built Thursday night; Friday is a re-publish)

Thursday night (done or in progress): loader v2.9 + publish script installed (T1-T5 passed), 13 fights published, branch
go-live-334 = embeds-v5 + publish-to-site, merged into main on Kirk's go. Friday and Saturday only re-publish and re-check.

## Sean, Friday (and Saturday after 12:00 pm ET)
1. In the sheet: menu **UFC > Refresh prices** and wait for it to finish. If the alert has any line starting with `!!!`, stop and tell Claude. Then menu **Site > Publish to site** and wait for the "published" message.
2. In the repo run `python3 scripts/listed_price_report.py --slug ufc_334 --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json` (about 5 s). It reads the export you just published.
3. For each row ending "NO: paste a current US-regulated price", type that row's "Best US now" price straight into the fighter's price cell on Main Card or Prelims (column D for the underdog, column I for the favorite). Do NOT run Refresh after this: Refresh rewrites D and I.
4. Menu **Site > Publish to site** again (no Refresh), then tell Claude "published" with the time.
5. Limits: the checks refuse by themselves if your export is over 2 hours old; if Claude tells you so, redo steps 1 to 4. The embed refresh blocks 24 hours after your last publish.

## Claude, then Kirk (after each "published")
6. In a main checkout: `bash scripts/friday_refresh.sh "UFC 334: Gane vs. Hokit" ufc_334 form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json /tmp/st`, then `bash scripts/saturday_check.sh` must end in SATURDAY CHECK PASS (this is the rehearsal once the merge is on main: checkout on origin/main, only the refresh's own files changed, scan clean, verifier 0 mismatches).
7. Kirk's go: push the refreshed embeds to main.
8. `python3 scripts/post_merge_check.py --wait 600` must end in POST-MERGE CHECK PASS. **Rollback trigger:** any other ending, or a wrong number on the live page: `bash scripts/rollback_main.sh`, push on Kirk's go.

## If the merge is NOT on main by Friday
Use go-live-334 instead: `bash scripts/rehearse_go_live.sh` (REHEARSAL PASS), commit the refresh on go-live-334, `bash scripts/merge_main.sh` (MERGE READY), Kirk's go `git push origin _merge:main`, then step 8.

Nothing reaches main without Kirk's go.
