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
4. **Menu trigger.** Apps Script > Triggers (clock icon) > Add Trigger: function `publishMenu_`, deployment Head,
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
