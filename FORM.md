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
