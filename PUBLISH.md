# Publish projections from the UFC Model sheet to the site

One action in the sheet publishes the ticked fights to the card page. Nothing is hand-edited in the HTML.

```
Sheet: Site > Publish to site
  -> data/pending/<slug>_projections.json   (GitHub contents API, Sean's token)
  -> Action "Projections check": scripts/verify_projections.py recomputes every fight with scripts/sheet_v47.py
       all numbers within 0.1 pts, flag and rec identical -> copied to data/<slug>_projections.json
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

## Go-live checklist (Friday morning, about 10 minutes, in order)

Already done on the branch (Nov 11): it merges into main with no conflicts; the dry-run projections are off the live path,
so after the merge the page says "Projections coming" until you publish; the name, crash and sheet-mirror tests pass.

| # | Min | Do | Proof it worked (check exactly this) |
|---|---|---|---|
| 1 | 1 | Open https://github.com/szerillo/ufc-projections/compare/main...publish-to-site > Create pull request > Merge pull request > Confirm. | Green "Able to merge" before you click. After: main's top commit is "Merge pull request ... publish-to-site". |
| 2 | 1 | Wait one minute, open https://szerillo.github.io/ufc-projections/ufc_334_fight_form.html | Page loads; the status line under the title says **Projections coming**. Actions tab lists **Projections check** and **Roll back projections**. |
| 3 | 2 | github.com > Settings > Developer settings > Fine-grained tokens > Generate. Repository access: Only select > `ufc-projections`. Permissions: Contents **Read and write**, nothing else. Copy it. | The token's page shows 1 repository and "Contents: Read and write" (GitHub adds "Metadata: Read" on its own; that's expected). |
| 4 | 1 | UFC Model sheet > Extensions > Apps Script > Project Settings > Script Properties > Add: `GITHUB_TOKEN` = the token > Save. Nowhere else. | `GITHUB_TOKEN` is listed with its value hidden. |
| 5 | 1 | Apps Script: Files + > Script > `publish_to_site` > paste `scripts/apps_script/publish_to_site.gs` > Save. Your call first: the `include` line at the top sets which sheet fields go public (rec, flag, method, markov, gtd; all on as shipped). | Saves with no red error; `publishMenu` is in the function dropdown. |
| 6 | 1 | Triggers (clock) > Add Trigger: `publishMenu`, From spreadsheet, On open > Save > approve the Google prompt. Reload the sheet. | A **Site** menu sits next to **UFC**. |
| 7 | 1 | Main Card and Prelims: `Publish` in AR1, AR2:AR11 > Insert > Checkbox. Tick one fight > Site > **Preview publish**. | The preview lists exactly that one fight. |
| 8 | 1 | UFC > Refresh prices. Tick every fight you've checked > Site > **Publish to site** > slug `ufc_334` > OK. | Alert says **Uploaded**. Within a minute Actions > Projections check is green and main has a commit "projections: verified from sheet at ...". This is the first real use of your token. |
| 9 | 1 | Reload the card page (step 2 link) and open one fight embed. | Status reads "Projections · N of 13 fights · updated X min ago" in green, no amber text. Pick one fight: the dog's True % equals Calculator column L for that fight's row. |

**No-go:** stop and don't share the page if any of these happen: step 1 shows a conflict; step 8's alert shows an error
(401, 403 or 404 means the token or its repository access is wrong: redo step 3); the Projections check is red twice
after a fresh publish; or step 9 shows amber ("could not be read", "not on this card", "over 12h old") or a True % that
doesn't match the sheet. If a bad file already went live, run **Roll back projections** (below) and the page returns to
"Projections coming". Nothing else on the site depends on this page.

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

- The check covers the moneyline block (sheet_v47 mirrors Calculator G/H/Q/L/W/AA and Main Card H/K/M/N). Method shares and
  GTD are passed through with sanity checks only (each in [0,1], shares sum to 1); there is no Python mirror of those formulas.
- The Markov shift B42 is taken from the sheet as an input because it averages every row, including fights not published.
- Rows: Main Card 2-6 and Prelims 2-9 (the rows with formulas). A fight placed on Main Card row 7 or Prelims rows 10-11 can't
  be published until those rows get formulas.
