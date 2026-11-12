# MMA Fight Form (site)

Live at the repo's GitHub Pages root: `index.html` + `form/app.js` + `form/style.css`, reading static JSON in `form/data/`.

## Rebuild the data

```
python3 scripts/build_form.py            # downloads sources into .form_cache/ then writes form/data/
python3 scripts/build_form.py --no-download   # reuse the cache
```

Sources joined by the build:

| What | Source |
|---|---|
| Results + round-by-round stats | UFCStats via `Greco1899/scrape_ufc_stats` (GPL-3.0), refreshed after each event |
| Line history 2022-2025 | The Odds API snapshots in `szerillo/sharp-tracker` → `data/oddsapi/compact/mma.jsonl.gz` |
| Line history 2026 + live | `data/oddsapi/mma/*.json.gz` and `data/mma/oddsapi_live.jsonl` in the same repo |
| Upcoming card + openers | BettingPros snapshots in this repo's `data/*_odds.json` (the existing odds cron) |
| Model projections | `FIGHTS` + `USER_PROJECTIONS_BY_FIGHT` inside each `ufc_*_fight_form.html` widget |

To put a new card on the front page: add it to `cards.yml` (as before), run `scripts/fetch_odds.py`, then rebuild.

## Pages (hash routes)

`#/` this week · `#/card/<slug>` · `#/fight/<slug>/<n>` · `#/fighter/<slug>` · `#/cards` · `#/fighters` · `#/model` · `#/about`

## Known limits

- Fighters are keyed by name. Two UFC fighters with the same name share a page (flagged on the page).
- UFC fights only; pre-UFC and regional fights are not in the past performances.
- 2026 odds history is fight-weekend snapshots plus the live feed, so "first seen" can be later than the true opener.
- The research closing line (Form fits, the bias slope k, Labs angles and backtests) is not cut at the bout start: it takes the last archive snapshot at or before the archive's commence time, which can include an in-fight price. Only the published close has hand fixes (`data/odds_close_fixes.json`, 2 bouts, Nov 12 2026).
- Film links are searches (YouTube, UFC Fight Pass), not direct links.

## v2 additions

- `scripts/form_model.py` (numpy only): Form Figure per performance, Form Line win model and distance model (both walk-forward by year), and the backtests written to `form/data/research.json`.
- New routes: `#/research`, `#/rankings`, `#/sheet/<slug>` (printable).
- Fair line = `sigmoid(k * logit(no-vig consensus))`, with `k` (about 1.2) fit on all fights with a closing line and stored in `index.json`.
- Upcoming cards overlay the current consensus from `data/<slug>_odds.json` in the browser, so the "Current" column follows the odds cron without a rebuild. Charts, fair-line inputs and the price board still need a rebuild.

## v3 additions

- Method model (`form_model.py`): P(KO / SUB / DEC | winner), walk-forward, shown as a method board of fair prices on card and fight pages. GTD on the site is the two decision chances added together.
- Past performances carry judges' scorecards (from the fighter's side) or the finish detail, and a round split (R1 vs R3+ strike differential) feeds the tape.
- Fighter pages have situational splits and a compare box; `#/compare/<slug>/<slug>` puts any two fighters side by side.

## v4: model sheet + Markov

- The build reads the UFC Model Google Sheet (link-readable) by tab gid: Snapshots (graded tracker), Calculator, Main Card, Prelims, PropSnap. Graded fights get every input, the flags and the closing prop market; `model.json` gets a tracker scoreboard.
- The browser also reads Main Card / Prelims / Calculator live for the upcoming card, so sheet edits show up on the site without a rebuild.
- Markov outputs: drop each `*_V41b_Output.md` into `markov/`; the build parses its ARCHIVE block (win % shrunk and raw, P(dec), expected minutes, round distribution).

## v5: Publish to site export + v4 single-fight embeds

- **Sean's projection = the sheet's "Publish to site" export.** `scripts/publish_source.py` attaches `data/<slug>_projections.json` (verified copy) or else `data/pending/<slug>_projections.json` to the upcoming event: win % (`sheet.true_dog/true_fav`), DEC / KO / SUB (`method`), GTD (`gtd`) and the sheet inputs. Only when there is no export for the card does the build keep its own sheet pull (or a widget's projections). Each fight carries `proj_src` (`publish` / `sheet` / `widget` / null) and the event carries `proj_source` (file, published_at, counts). `build_form.py` calls it; to refresh a committed event file without a full rebuild (no sheet ID needed):
  `python3 scripts/card_overrides.py --slug ufc_334 --event form/data/events/<event>.json --index form/data/index.json --check && python3 scripts/publish_source.py --slug ufc_334 --event form/data/events/<event>.json`
- **Fight numbers = bout order** (`card_overrides.apply_doc` rewrites `n` from `data/card_overrides.json` order: 1 = first early prelim, highest = main event; cancelled bouts dropped). `--check` fails if they differ.
- **v4 embeds**: `python3 scripts/build_fight_embeds.py --slug ufc_334` writes `embeds/<slug>/fight_NN.html` (one per bout, + `.registry.json` with the rule and source of every number, + `card.json`) and the card's roster block in `embed.html`. Rebuild after an odds refresh or a new publish; the embeds are static.
- **Checks** (all must pass before pushing):
  `python3 scripts/verify_fight_embeds.py --slug ufc_334 --negative` re-derives every number in every embed from the sources, plus row order, numbering, cancelled bouts, badge, export-sourced Sean cells; the negative run plants errors and must catch all of them.
  `python3 scripts/check_site_projections.py --slug ufc_334 --negative` renders the card, home, print and fight pages with `form/app.js` (`scripts/site_render.js`, needs node or bun) and asserts every displayed Sean number equals the export.
