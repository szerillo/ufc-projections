# UFC Fight Night Prochazka vs Stirling runbook (Sat Nov 21, Doha)

Built Wed Nov 18 night on branch `fn-prochazka-stirling`. Every bout shows **market prices only** until Sean publishes this
card from the sheet: a "No model projection published" note, market and best US moneyline (DK, FD, MGM, CZR), line move,
fight length and method market prices. No model numbers are invented. Card pages show "Projection pending" per bout.

Card variables used below:

    CARD="UFC Fight Night: Proch"; SLUG=fn_prochazka_stirling
    EVENT=form/data/events/2026-11-21-ufc-fight-night-prochazka-vs-stirling.json

## 0. Kirk, once: get the staging build on main
1. `git fetch origin && git checkout main && git pull --ff-only`
2. `git merge --no-ff origin/fn-prochazka-stirling -m "Merge fn-prochazka-stirling (market-only staging)"`
   If the only conflict is `data/fn_prochazka_stirling_odds.json` (the odds bot kept writing it): `git checkout --ours data/fn_prochazka_stirling_odds.json && git add data/fn_prochazka_stirling_odds.json && git commit --no-edit`, then run the staging refresh at the bottom before pushing so the embeds match main's odds.
3. Kirk's go: `git push origin main`, then `python3 scripts/post_merge_check.py --wait 600` must end in POST-MERGE CHECK PASS.

## Sean, by Friday 12:00 pm ET
4. In the sheet: **UFC > Load next UFC card** (Prochazka vs Stirling, 11 bouts, 6 main card / 5 prelims), then **UFC > Refresh prices**. Stop on any `!!!` line.
5. Fill the weekly inputs as usual (Markov win % and decision shares if a Markov run exists; context codes; Tapology / Junkie if collected). Check the 6th main-card row has its bet-rec, GTD and method formulas (known gap for a 6-fight main card).
6. **Site > Publish to site**, then tell Claude or Kirk "published" with the time.

## Claude, then Kirk (after each "published")
7. `bash scripts/friday_refresh.sh "$CARD" $SLUG $EVENT /tmp/st` (no ALLOW_NO_EXPORT: with an export present it builds the model cells; without one it stops with GO-LIVE BLOCKED).
8. `SLUG=$SLUG EVENT=$EVENT bash scripts/saturday_check.sh` must end in SATURDAY CHECK PASS.
9. `python3 -I scripts/render_check.py http://localhost:8000 $SLUG` against a local `python3 -m http.server 8000` (it compares the page with the promoted projections file, so it cannot run before the publish).
10. Kirk's go: commit the refresh and push to main, then `python3 scripts/post_merge_check.py --wait 600`. **Rollback trigger:** any other ending, or a wrong number on the live page: `bash scripts/rollback_main.sh`, push on Kirk's go.

## Saturday morning (Doha card: prelims 10:00 am ET, main card 1:00 pm ET)
11. Sean: Refresh prices, Publish by about 8:30 am ET. Then steps 7 to 10 so the embeds carry the final odds before the prelims. The export must be under 24 hours old for step 7.

## Staging only (no export yet)
`ALLOW_NO_EXPORT=1 bash scripts/friday_refresh.sh "$CARD" $SLUG $EVENT /tmp/st` rebuilds the market-only previews with fresh odds. It never adds model numbers.

Nothing reaches main without Kirk's go.
