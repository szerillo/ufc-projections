# UFC Fight Night Prochazka vs Stirling go-live (Sat Nov 21, Doha)

Branch `fn-prochazka-stirling`. Until Sean publishes, every bout shows market prices only plus the Markov read (C4's V4.1b run).
Nothing reaches main without Kirk's go. Run everything from a checkout of szerillo/ufc-projections with the sharp-tracker
checkout at /tmp/st.

    CARD="UFC Fight Night: Proch"; SLUG=fn_prochazka_stirling
    EVENT=form/data/events/2026-11-21-ufc-fight-night-prochazka-vs-stirling.json
    MK=ufc-fight-night-prochazka-vs-stirling; NAME=UFC_FN_Prochazka_vs_Stirling

## A. Kirk, when C4 says "thread done": land the final Markov files
1. `git fetch origin && git checkout fn-prochazka-stirling && git pull --ff-only`
2. `bash scripts/markov_land.sh <folder with C4's final files> $NAME $SLUG $MK "UFC Fight Night: Prochazka vs. Stirling"`
   It must end in MARKOV LANDED. Compare the three sha256 lines it prints with C4's final run log.
3. `git add markov/${NAME}_* data/cards/$MK.json data/manifest.json embeds/$SLUG && git commit -m "markov: C4 final run" && git push origin fn-prochazka-stirling`
   ("nothing to commit" means C4's final files are byte-identical to the ones already wired.)

## B. Sheet (Friday by 12:00 pm ET)
4. Kirk's Markov watcher writes C4's sheet_inputs.csv into the sheet (AP/AQ in the UFC 334 format). Sean does not enter Markov numbers.
5. Sean: **UFC > Refresh prices** (stop on any `!!!` line), then **Site > Publish to site**, then says "published" with the time.
   projections.yml checks the export and promotes it on main.

## C. Kirk, after "published" (within 2 hours of the publish)
6. `git checkout fn-prochazka-stirling && git pull --ff-only`
7. `CARD="$CARD" SLUG=$SLUG EVENT=$EVENT ST=/tmp/st bash scripts/rehearse_go_live.sh` must end in REHEARSAL PASS.
   If it stops on "Listed prices not seen at a US-regulated book": `python3 scripts/listed_price_report.py --slug $SLUG --event $EVENT`, Sean types each "Best US now" price into the sheet, Publish again (no Refresh), redo step 7.
8. `git status --short` (only the refresh's files), then `git add -A && git commit -m "fn-prochazka-stirling: refresh on Sean's export" && git push origin fn-prochazka-stirling`
9. `BR=fn-prochazka-stirling SLUG=$SLUG bash scripts/merge_main.sh` must end in MERGE READY.
10. Kirk's go: `git push origin _merge:main`
11. `python3 scripts/post_merge_check.py --wait 600` must end in POST-MERGE CHECK PASS.
    **Rollback trigger:** any other ending, or a wrong number on the live page: `SLUG=$SLUG bash scripts/rollback_main.sh`, then on Kirk's go `git push origin _rollback:main`.

## D. Saturday morning (prelims 10:00 am ET, main card 1:00 pm ET)
12. Sean: Refresh prices, Publish, by about 8:30 am ET.
13. Kirk: `git checkout main && git pull --ff-only && bash scripts/friday_refresh.sh "$CARD" $SLUG $EVENT /tmp/st`
14. `SLUG=$SLUG EVENT=$EVENT bash scripts/saturday_check.sh` must end in SATURDAY CHECK PASS (it also confirms only the refresh's own files changed).
15. Kirk's go: `git add -A && git commit -m "fn-prochazka-stirling: Saturday refresh" && git push origin main`, then step 11.

## E. After the card is graded (weekly, every card)
16. Re-fit the Markov offset (sheet v4.8, see SHEET_MAP.md "B42"): once this card's rows are graded in Snapshots,
    type Calculator D42's value (4 decimals) into B42 as a plain number. Do it before the next card's first-walkout snapshot,
    never mid-card, so a whole card is graded under one offset. Log old and new value in SHEET_MAP.md's B42 history.

## Notes
- Nov 19 (Sean approved): Calculator B42 is now a FIXED offset 0.1086 (was the card-average formula 0.0872). Each fight is independent.
  Only Prochazka-Stirling's rec changed (now "lean Navajo Stirling"); Mar Fan and Mitchell stay BET; flags unchanged.
- merge_main.sh refuses if main moved with anything other than the odds bot or Sean's export since the served-set check
  (audits/MAIN_AT_CHECK.txt, re-pinned Nov 19 to 97522f68). If it refuses, re-run `python3 audits/fn_prochazka_stirling/served_set_check.py` and re-pin.
- Staging only, before the publish: `ALLOW_NO_EXPORT=1 bash scripts/friday_refresh.sh "$CARD" $SLUG $EVENT /tmp/st` refreshes the market-only pages. It never adds model numbers.
- Nov 19 (Kirk): fight 12 **John Mitchell vs Shoaib Yousaf is official** (Sean), the prelim opener. It is in card_overrides `add`
  (the odds feed does not carry it yet), so it is fight 1 and every other bout moved up one (main event = fight 12, files fight_01..fight_12).
  Split 5 main / 7 prelims; the event file now carries `n_main` and form/app.js reads it (12 bouts would otherwise guess 6 main).
  - Its embed shows the Markov read and "No odds feed price for this bout yet" until BettingPros lists it; the next refresh picks it up with no change.
  - Step 3 of friday_refresh (`check_price_freshness`) needs an archive price for it within 4 h; the archive had one at 04:41Z Nov 19.
  - Step 2b blocks go-live until Sean's export has the bout (Prelims row 8, entered Nov 19 01:40 ET).
  - Section A: land only C4's **relabelled** files (flags.json with `fight_12_status`). Landing the earlier provisional copies again drops
    fight 12 from the Markov card. The flags.json on the branch is a label-only relabel of C4's file (numbers unchanged), done on the branch
    because the relabelled copies were not in "C - UFC Markov/outputs/"; C4's own copy replaces it.
