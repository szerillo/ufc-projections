# Publish projections from the UFC Model sheet to the site

One action in the sheet publishes the ticked fights to the card page. Nothing is hand-edited in the HTML.

```
Sheet: Site > Publish to site
  -> data/pending/<slug>_projections.json   (GitHub contents API, Sean's token)
  -> Action "Projections check": scripts/verify_projections.py recomputes every fight with scripts/sheet_v47.py
       all numbers within 0.0001 pts, flag and rec identical -> copied to data/<slug>_projections.json
       anything off -> run fails, live file untouched
  -> <slug>_fight_form.html reads data/<slug>_projections.json at page load ("updated X ago")
       no file yet -> "Projections coming"
```

## One-time setup (Sean)

1. **Token.** GitHub > Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token.
   - Resource owner: szerillo. Repository access: **Only select repositories** > `ufc-projections`.
   - Repository permissions: **Contents: Read and write**. Leave everything else at No access.
   - Expiration: your choice (90 days is reasonable). Copy the token once; GitHub won't show it again.
2. **Store it in the sheet's script, not anywhere else.** In the UFC Model sheet: Extensions > Apps Script >
   Project Settings (gear) > Script Properties > Add script property: name `GITHUB_TOKEN`, value = the token. Save.
   Don't paste it in chat, a doc, a cell or a commit. If it ever leaks, revoke it on GitHub and make a new one.
   The value is not hidden: anyone with edit access to the sheet can open Apps Script > Project Settings and read it
   in plain text. Keep edit access to the sheet (and so the script) limited to you.
3. **Add the script.** In the Apps Script editor: Files `+` > Script > name it `publish_to_site`, paste the contents of
   `scripts/apps_script/publish_to_site.gs`, Save. It adds no `onOpen`, so the loader's UFC menu is untouched.
4. **Menu trigger.** Apps Script > Triggers (clock icon) > Add Trigger: function `publishMenu`, deployment Head,
   event source From spreadsheet, event type On open. Save and approve the permissions prompt
   (it asks for spreadsheet access and external requests, which is the GitHub upload). Reload the sheet: a **Site** menu appears.
5. **Publish column.** On Main Card and on Prelims, put the header `Publish` in **AR1** and turn AR2:AR11 into checkboxes
   (select the range > Insert > Checkbox). AR is the first free column after AQ. If you want a different column,
   change `publishCol` at the top of the script.

## Each card

1. Make sure the card is in `cards.yml` and its page exists (`python3 -I scripts/build_card_page.py ...`, see the script header).
2. Fill the sheet as usual. Tick **Publish** only on fights you've checked.
3. Site > **Preview publish (no upload)** shows exactly what would go out. Then Site > **Publish to site**, enter the slug
   (e.g. `ufc_334`; it's remembered), confirm.
4. GitHub > Actions > "Projections check": green = live within a couple of minutes; red = the summary lists every number that
   didn't match and the site kept the last good file. Fix the sheet and publish again.
5. Re-publish any time (price moves, new Markov run). Unticking a fight and re-publishing removes it from the page.

## Thursday install (Kirk, Nov 12, round 30): loader v2.9 + publish script, once, with readback and an abort line per step

Loader **v2.9** (sha256 starts `c8d938d7`) = v2.8 (`7200be8d`, TRAP prices never drive D/I) plus the refresh guard (round 29/30:
a refresh never clears a bout still priced on BestFightOdds/Novig; a source outage writes nothing; bout-count drop warning;
UFC > Remove a cancelled bout). Install v2.9 directly; do not install v2.8 first. Files are opened from fixed commits, so the
text cannot change under you. Before T1: Prelims, Jared Gordon row shows D = **+420** and Calculator AH "(+4 TRAP)" (v2.7).

| # | Do | Readback | Abort (stop, change nothing else, tell Claude) |
|---|---|---|---|
| T1 | Sheet > Extensions > Apps Script > gear (Project Settings) > Script Properties. If `BETTABLE_BOOKS` is listed, leave it. If not: Add script property, name `BETTABLE_BOOKS`, value `["DraftKings", "FanDuel", "BetMGM", "Caesars", "BetRivers", "HardRockBet", "Fanatics", "ESPNBet"]` (straight quotes) > Save script properties. | `BETTABLE_BOOKS` listed with that value. (v2.9's default is the same list, so this only pins it.) | Save shows an error, or the value has curly quotes: delete the property and stop. |
| T2 | New tab: open https://raw.githubusercontent.com/szerillo/ufc-projections/1968dcfc/scripts/apps_script/loader/Code_v2.9_guard.gs > Ctrl+A > Ctrl+C. Apps Script > Editor > `Code.gs` > click in the code > Ctrl+A > Ctrl+V > Ctrl+S. | No red error bar. Line 2 reads `* PATCH loader-guard (Kirk rounds 29-30, v2.9 on top of v2.8)`. The last line starts `function FIGHTERNAME(name, range)`. Claude then reads the editor (read only) and confirms sha256 `c8d938d7`. | Red error, a different line 2 or last line, or a different hash: paste `Code_v2.7_installed.gs` back (rollback below) and stop. |
| T3 | Only if Site > Preview publish does NOT already open with `Script build b47-out`: open https://raw.githubusercontent.com/szerillo/ufc-projections/fef6927b/scripts/apps_script/publish_to_site.gs > Ctrl+A > Ctrl+C > Apps Script > `publish_to_site` > Ctrl+A > Ctrl+V > Ctrl+S. | No red error; reload the sheet: menus **UFC** (now with "Remove a cancelled bout…") and **Site** both load. | A menu is missing or a red error: rollback T2 (and T3 if pasted), stop. |
| T4 | Sheet > UFC > **Refresh prices (keep openers)**. Read the whole alert before closing it. | No alert line starts with `!!!`. Feed lists 13 fights. Prelims, Jared Gordon row: D = **+310** (not +420); Calculator AC "… \| +310 FanDuel"; AH ends "TRAP, excluded from D/I"; Bet Rec (N) = **-**. Every other row has both names. | `!!! REFUSED, source unreachable` = nothing was written: wait 5 min, repeat T4 once, then stop. Any other `!!!` line, D still +420, or a row with blank names: stop (do not publish). |
| T5 | Site > **Preview publish** (no upload). | First line: `Script build b47-out · price row matches 13/13 · method inputs 13/13 · TRAP prices in D/I 0 · prices loaded ...` | Another build name, a count below 13/13, or `TRAP prices in D/I` 1 or more: stop; do not publish. |

After T5 Claude reads Gordon's row back (read only) and posts before/after.

| # | Do | Readback |
|---|---|---|
| T6 | Site > **Publish to site**, slug `ufc_334`, all 13 ticked (within 3 h of T4). This replaces the stale 01:18Z pending file (27 rejects). | Alert **Uploaded**; main's top commit "Publish ufc_334 projections from sheet (13 fights)". |
| T7 | Merge `publish-to-site` into main (Claude, on Kirk's go), within 3 h of T4. | Projections check runs on the merge push, green, "Values compared: 286, mismatched: 0"; bot commit "projections: verified ...". |
| T7b | Right after T7: Actions > Projections check > **Run workflow** (branch main). GitHub only shows this button once the workflow is on main, so it cannot be tested before the merge (Block 52); this is Friday step 4's fallback. | A run starts and is green with "Already live" (no new commit). |
| T8 | After Pages deploys (about 1 min): `python3 -I scripts/render_check.py https://szerillo.github.io/ufc-projections ufc_334` (Claude). | "416 shown values compared, 0 mismatched" (13 fights x 16 values x page and embed). |
| T8b | Merge branch `open-label` into main (Claude, on Kirk's go; label only: 3 labels on fight pages, no numbers). Then `python3 -I scripts/open_label_check.py https://szerillo.github.io/ufc-projections` after the Pages deploy. | "O1: 110 fight pages read, 97 show 2+ different open values, 0 without source labels". **Rollback:** `git revert -m 1 <merge>` (one commit; the page returns to the old labels). |
| T9 | Kirk: Site > **Publish to site** once more (any time after T8). First real test of a Sheet publish starting the check on its own (the Apps Script commits through the contents API; never exercised with the workflow on main). | A Projections check run starts within 2 min and is green. No run in 2 min: Friday's manual Run workflow becomes a required step, not a fallback. |

**Rollback (one step each).** Code.gs > replace its contents with, then Ctrl+S, then UFC > Refresh prices:
- guard misbehaves, TRAP rule fine: `scripts/apps_script/loader/Code_v2.8_patched.gs` (sha256 `7200be8d`, branch `loader-guard`);
- full revert to what ran before Thursday: `scripts/apps_script/loader/Code_v2.7_installed.gs` (sha256 `e5233b99`). Proof:
  Preview shows `TRAP prices in D/I 1` again while BFO's Caesars is still +420, and Gordon's D is +420.
The publish script needs no rollback: it works with any of the three loaders (it only reports the TRAP count).

## Friday script (UFC 334 go-live, in this order)

Already done (Nov 11): token, Script Property, `publishMenu` trigger and Publish checkboxes are set up (Kirk); the branch
merges into main with no conflicts; the merge was rehearsed twice (13 s from merge to verified file).
**The merge waits for Sean's go.** Fill in the time column as you go.

| # | Who | Do | Proof it worked | Time (ET) |
|---|---|---|---|---|
| 0 | Kirk | Apps Script > `publish_to_site` > replace its contents with `scripts/apps_script/publish_to_site.gs` from the branch (sha256 starts `de4c2be3`) > Save. (It exports the method inputs, the price-load stamp, each fight's Feed price row and the flagged outliers; without them the check goes red.) | Saves with no red error; Site > Preview publish opens with **Script build b47-out · price row matches 13/13 · method inputs 13/13 · TRAP prices in D/I 0 · prices loaded ...**. Another build name, a count below 13/13, or no such line = old file or partial paste: paste again. **TRAP prices in D/I 1** means loader v2.7 is still installed (Gordon +420 drives the rec): install loader v2.9 first (Thursday install T2). | |
| 1 | Kirk | UFC > **Refresh prices**. | Feed!F1 ("Loaded") shows the current time. | |
| 2 | Kirk | Site > **Publish to site**, slug `ufc_334`, every Main Card and Prelims fight ticked. Do steps 3-4 within 3 hours of step 1. | Alert says **Uploaded**; main's top commit is "Publish ufc_334 projections from sheet (13 fights)". | |
| 3 | Kirk, on Sean's go | https://github.com/szerillo/ufc-projections/compare/main...publish-to-site > Create pull request > **Merge pull request** > Confirm. | "Able to merge" before the click; main's top commit is the merge. | |
| 4 | automatic | **Projections check** starts by itself (the merge brings the workflow to main). | Actions: green within about 20 s; main gets "projections: verified from sheet at ...". Not started in 2 min: Actions > Projections check > Run workflow (main). | |
| 5 | automatic | Pages deploys the verified file. | About 1 minute (median 46 s, max 68 s). | |
| 6 | Claude, then Kirk | `python3 -I scripts/render_check.py https://szerillo.github.io/ufc-projections ufc_334` (every shown value on the page and all 13 embeds vs the verified file; red lists surface, bout, field, expected, shown). Then Kirk opens https://szerillo.github.io/ufc-projections/ufc_334_fight_form.html and one fight embed. | Status **green**: "Projections · 13 of 13 fights · updated X min ago · prices loaded X min ago", no amber text, every panel filled. Spot check one fight: dog True % = Calculator L, "Goes the distance" = column Q. | |
| 7 | Sean | Share the page (or not). | | |

**No-go** (don't share the page) if any of these happen: the merge shows a conflict; no green Projections check within
2 minutes even after one manual run; the check is red (the run summary names every number that didn't match; "prices
were loaded X h ago" means repeat steps 1-2, which re-runs the check by itself now that it's on main); the page status is
amber ("could not be read", "not on this card", "spelled differently", "over 12h old"); or the spot check disagrees with
the sheet. If a bad file already went live: **Roll back projections** (below) and the page returns to "Projections coming".

What the check covers now: every True %, edge, flag and rec, the method split (dec/KO/sub, both sides) and the fight GTD,
recomputed from the file's own inputs within 0.0001 pts, plus a price-load stamp no older than 3 hours at the time of the
check (pre-registered Nov 11), plus an opponent-match guard (pre-registered Nov 11, Block 46): each price must be the price on
the Feed row for that same bout, and the bout must exist in `data/<slug>_odds.json`. A bout that fails only that guard is
held back as **Line pending** (no numbers on the page) and the rest go live; any other failure keeps the whole file off (Block 47).
With loader v2.8 or v2.9 a TRAP price (4+ pts better than the exchange fair) never drives the price; the page says "Outlier excluded". The step 6 spot check stays as a second look, not as the only check.

## Saturday odds (the card-night loop)

GitHub throttles the schedule (the odds bot ran 3.5 to 10.9 h apart this week), so the card-night loop is started by hand.
Actions > **Pull UFC odds (card-night loop)** > Run workflow, defaults, branch main:

- **Sat 12:00 pm ET**: run it twice. The first runs about 5h40m; the second waits and starts when the first ends (~5:40 pm).
- **Sat 6:00 pm ET**: run it once more. It waits behind the second and covers ~11:20 pm to the end of the window
  (main event + 35 min, ~1:05 am ET Sun). A scheduled tick that queues in the meantime replaces a waiting run; that's fine.
- Inside the window the bot pulls hourly before the first bell and every 30 min during the card.
- What the page shows: "Live odds · BettingPros · updated X ago", green under 90 min old, amber after. If nothing runs,
  the page keeps the last pull and shows its age in amber; projections are unaffected (their own 12 h guard).
- Tested Nov 11 (run 43131039515, 2 min, 3 ticks): one pull of 13 UFC 334 fights and 9 for the next card, pushed to main
  and live on the site 45 s later. The loop always writes main, whichever branch starts it.

## Undo a bad publish (one step)

GitHub > Actions > **Roll back projections** > Run workflow (slug `ufc_334`). Or, from any browser: in the repo,
Add file > Create new file, name it `data/rollback/ufc_334.txt`, leave it empty, Commit. Either way the card page goes back
to the version from the publish before the latest one (or to "Projections coming" if there was none; dry runs from
before go-live never count), and the bad
pending file is deleted so it can't come back. Running it twice changes nothing more. Tested on the branch Nov 11:
13 s from the request to the restored file; the site then needs one Pages deploy (median 46 s, max 68 s over the last 20).

To undo a rollback, publish again from the sheet. Don't revert the rollback commit in git: that puts the request file back
and rolls back again.

## Tests for the card page

`python3 -I scripts/test_fighter_names.py` (name rule, Python and page copies) and `python3 -I scripts/test_card_guards.py`
(one corrupted record per loop; the rest of the page must render).

## What the file contains

Per ticked fight: names, the inputs the check needs (best dog/fav price, open %, Markov %, Markov shift B42, Tapology / Junkie /
tipster %, context code, manual adjust, women flag), the sheet's outputs (listed no-vig %, shifted Markov, Q, True % both sides,
edges at the price, drift, flag, Bet Rec text), method shares (V:X, Z:AB), Fight GTD (Q) and listed GTD (S), Markov decision
shares (AP, AQ). `include` at the top of the script leaves out the Bet Rec, the flag, method, GTD or Markov groups; anything
left out is not in the public file at all (the check then skips it). The inputs always go out because the check needs them.
Which of these are public is Sean's call.

## Limits

- The check mirrors the moneyline block (Calculator G/H/Q/L/W/AA, Main Card H/K/M/N) and, since Block 44, the method split
  (V:AB) and fight GTD (Q). Blank Markov, the 0.03/0.97 clamp and the X<=0 AVERAGE fallback were tested in a scratch copy
  of the sheet on Nov 11 (Block 46): the mirror matched Google's own recalculation within 5e-11.
- The opponent guard uses the Feed and the BettingPros odds file, not the DK DFS list (EventPlayerIds), which can be stale
  after a late replacement (UFC 334: it still pairs Juan Diaz with Adrian Yanez).
- The Markov shift B42 is taken from the sheet as an input because it averages every row, including fights not published.
- Rows: Main Card 2-6 and Prelims 2-9 (the rows with formulas). A fight placed on Main Card row 7 or Prelims rows 10-11 can't
  be published until those rows get formulas.
