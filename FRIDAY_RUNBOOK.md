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

## Notes
- merge_main.sh refuses if main moved with anything other than the odds bot or Sean's export since the served-set check
  (audits/MAIN_AT_CHECK.txt, re-pinned Nov 19 to 97522f68). If it refuses, re-run `python3 audits/fn_prochazka_stirling/served_set_check.py` and re-pin.
- Staging only, before the publish: `ALLOW_NO_EXPORT=1 bash scripts/friday_refresh.sh "$CARD" $SLUG $EVENT /tmp/st` refreshes the market-only pages. It never adds model numbers.
