# UFC 334 runbook (frozen Nov 12; sheet loader v2.9)

## Kirk, Thursday: sheet loader v2.9 (full table: PUBLISH.md "Thursday install", branch publish-to-site)
- T1 Apps Script > Project Settings > Script Properties: `BETTABLE_BOOKS` present, or add it with the list in PUBLISH.md. Abort: a save error or curly quotes: delete it, stop.
- T2 Paste `Code_v2.9_guard.gs` from the pinned link over all of Code.gs, Ctrl+S. Line 2 reads "PATCH loader-guard (Kirk rounds 29-30, v2.9"; Claude confirms sha256 `c8d938d7`. Abort: red error, a different line 2 or hash: paste `Code_v2.7_installed.gs` back, stop.
- T3 Only if Site > Preview publish is not already "Script build b47-out": paste the publish script (`de4c2be3`). The UFC and Site menus load. Abort: a menu is missing: roll back, stop.
- T4 UFC > Refresh prices (keep openers). No alert line starts with `!!!`; Feed has 13 fights; Gordon D +310; AH ends "TRAP, excluded from D/I"; rec "-". Abort: "!!! REFUSED, source unreachable": wait 5 min, retry once; any other `!!!` line, D still +420, or a row with blank names: stop, don't publish.
- T5 Site > Preview publish: "b47-out · price row matches 13/13 · method inputs 13/13 · TRAP prices in D/I 0". Abort: anything else: stop, don't publish.
- Then Claude reads Gordon's row back. Rollback: paste `Code_v2.8_patched.gs` (keeps the TRAP rule) or `Code_v2.7_installed.gs`, then Refresh prices.

## Sean, Friday
1. Fri, when ready: in the repo run `python3 scripts/listed_price_report.py --slug ufc_334 --event form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json` (about 5 s).
2. For each row ending "NO: paste a current US-regulated price", type that row's "Best US now" price into the fighter's Listed cell in the UFC Model sheet.
3. In the sheet: menu **UFC > Refresh prices**, wait for it to finish, then menu **Site > Publish to site** and wait for the "published" message. If the Refresh alert has any line starting with `!!!`, do not publish; tell Claude.
4. Tell Claude "published" with the time.
5. Limits: the rehearsal refuses by itself if your export is over 2 hours old; if Claude tells you it did, redo steps 1 to 3. The refresh blocks 24 hours after your last publish (the current export, published Wed 8:18 pm ET, blocks from Thu 8:18 pm ET, so nothing refreshes Friday until you publish).

## Claude, then Kirk, Friday (after Sean's "published")
6. `bash scripts/rehearse_go_live.sh` must end in REHEARSAL PASS. It refuses by itself on an export over 2 h old, a bout missing from the export, a moved main, or any failed check.
7. Commit the refresh on `embeds-v5` and push the branch.
8. `bash scripts/merge_main.sh` must end in MERGE READY. A new odds key needs Kirk's approval; an odds copy that can't be shown newer price by price refuses.
9. Kirk's go: `git push origin _merge:main`. If the push is rejected, rerun step 8.
10. `python3 scripts/post_merge_check.py --wait 600` must end in POST-MERGE CHECK PASS. **Rollback trigger:** any other ending, or a wrong number on the live page: `bash scripts/rollback_main.sh`, push on Kirk's go.

## Saturday
11. Sean, after 12:00 pm ET: steps 1 to 4 once. That moves the 24-hour block past the main event.
12. Claude, in a main checkout: `bash scripts/friday_refresh.sh "UFC 334: Gane vs. Hokit" ufc_334 form/data/events/2026-11-14-ufc-334-gane-vs-hokit.json /tmp/st`, then `bash scripts/saturday_check.sh` must end in SATURDAY CHECK PASS.
13. Kirk's go: push the Saturday refresh, then `python3 scripts/post_merge_check.py --wait 600` again (same rollback trigger).

Nothing reaches main without Kirk's go.
