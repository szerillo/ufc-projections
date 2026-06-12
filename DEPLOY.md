# UFC Freedom 250 — Push to Production

Everything is wired and verified. Here's the deploy walkthrough.

## What ships

| File | Path in your repo | What it does |
|---|---|---|
| `ufc_freedom_250_fight_form.html` | repo root | The widget. Self-contained, fetches live odds at boot. |
| `embed.html` | repo root | Embed code generator (like your MLB tracker) |
| `scripts/fetch_odds.py` | `scripts/` | Single-shot BettingPros ingest |
| `scripts/odds_tick.py` | `scripts/` | Cron controller. Decides whether to actually pull. |
| `.github/workflows/odds.yml` | `.github/workflows/` | GitHub Action. Cron `*/30`, commits if odds change. |
| `cards.yml` | repo root | Active card schedule (just Freedom 250 for now) |
| `data/freedom_250_odds.json` | `data/` | Fresh snapshot pulled just now |

## One-time setup

1. **Drop the six files into your `ufc-projections` repo** preserving paths.

2. **Push to main.** That alone is enough to make the widget viewable at:
   `https://szerillo.github.io/ufc-projections/ufc_freedom_250_fight_form.html`
   The widget will load the snapshot of `data/freedom_250_odds.json` on every page view.

3. **Verify the Action is running.** Go to Actions tab, click "Pull UFC odds". You should see either a green run (committed fresh odds) or a "skipped" run (we're outside the fetch window). Either way means the workflow is alive. If you want to test, click "Run workflow" manually — that bypasses the cadence controller.

4. **The API key works without configuration.** The ingest script uses the BettingPros public bundle key as default. If you ever want to override (e.g. they rotate it), set repo secret `BETTINGPROS_API_KEY`.

## Cadence schedule

Workflow ticks every 30 min. Tick controller decides whether to actually pull based on time-to-first-fight:

| Time to first fight | Actual pull interval |
|---|---|
| > 48h out | every 12h |
| 24-48h | every 6h |
| 6-24h | every 2h |
| 0-6h | every 1h |
| Inside the card | every 30 min |
| 30 min past main event | stop |

Per-fight: a fight is frozen once its scheduled bell - 5 min is reached. The widget shows the last good odds for any fight that's already in progress.

## Adding new cards

Append to `cards.yml`:

```yaml
- name: "UFC 305"
  slug: "ufc_305"
  first_fight_utc: "2026-07-12T22:00:00"
  main_event_utc:  "2026-07-13T03:30:00"
```

Then create a matching `ufc_305_fight_form.html` (copy the Freedom 250 widget, update the `FIGHTS` array and `USER_PROJECTIONS_BY_FIGHT`). The cron job will start pulling data for it on the next tick.

## What's wired into the widget right now

**Header status badge** — pulses green when live odds loaded successfully, turns red ("Live odds unavailable") when fetch fails. Includes "Updated X ago" timestamp.

**Per-fight panel** (Fight Form tab):
- Title row with FIGHT N / MAIN EVENT or CARD / Title belt (LW Title, Interim HW Title) / weight class
- Headline + ML line + Implied % + book Hold
- Tale of the Tape (collapsible, vertical 3-col layout, with STR DIFF and CONTROL edge rows showing arrow direction)
- Projections section (collapsible) with:
  - Moneyline: projected odds and %, listed odds + book name + raw implied %, edge
  - Fight Length: projected GTD / ITD, live YES / NO odds
  - Method of Victory: projected odds, projected %, live odds line in green when available
- Analysis section (collapsible) with PHYSICAL / STR DIFF / WRESTLING / CONTROL-GRAPPLING / PATHS / MODEL / BET REC rows

**Global Moneylines tab** — favorites/underdogs toggle, raw implied %, edge pills

**Global Props tab** — fight length + method of victory tables with live odds

**Methodology** — collapsible at the bottom, your concise text

## Sanity check before the link goes public

I'd recommend manually doing this after deploy:

1. Open the widget URL on your phone (forces mobile rendering)
2. Confirm status badge is green and shows recent timestamp
3. Tap through 2-3 fight tabs, confirm Tale of the Tape, Projections, and Analysis all render
4. Switch to Moneylines tab, confirm Listed odds match what BettingPros is showing
5. Switch to Props tab, confirm Method of Victory has the green "live" lines under most cells

If everything passes, ship the link.

## Known limitations

- **Live odds are headline-book.** Default order: DraftKings → FanDuel → BetMGM → Caesars → consensus. If you want to surface a different book or show multiple books side-by-side, edit `PREFERRED_BOOK_ORDER` in the HTML.
- **Recent form section was removed.** Career W/L by method and recent fight log used to live in the fighter pop-outs. Those came from hand-keyed data with reliability issues, so they're stripped. Add back when you have a verified data feed.
- **Only seven fights.** Mid-card cancellations after the snapshot won't propagate. You'd need to manually edit the FIGHTS array if a fight drops.

## Embed builder

`embed.html` is a standalone builder modeled on your MLB tracker. Once deployed it lives at:

```
https://szerillo.github.io/ufc-projections/embed.html
```

Pick a card + view + fight number, get back a copy-paste iframe snippet plus a live preview.

**URL schema the widget supports:**

| Param | Effect |
|---|---|
| `?embed=full` | Full widget with all three view tabs (Fight Form / Moneylines / Props). Header brand hidden, byline hidden. |
| `?embed=fight&n=N` | Only the Nth fight panel. View tabs and fight scroller hidden. Sized small. |
| `?embed=moneylines` | Just the Moneylines table (favorites/underdogs toggle stays). |
| `?embed=props` | Just the Props tables (fight length + method of victory). |

**Auto-resize.** The widget posts `{type: "ufc-iframe-height", height: N}` via `postMessage` on every body resize. If the parent page listens for that event and updates the iframe's height attribute, the embed will auto-fit. The MLB-style `data-autoresize="true"` attribute is what most CMS embed wrappers look for to enable this behavior — the embed builder adds it by default.

**Example iframe (matches your MLB tracker pattern):**

```html
<iframe style="border:none;width:100%;min-height:600px;"
        src="https://szerillo.github.io/ufc-projections/ufc_freedom_250_fight_form.html?embed=fight&n=1"
        width="100%" height="1500" frameborder="0" scrolling="auto"
        data-autoresize="true"
        title="UFC Freedom 250 Fight Form"></iframe>
```

## When you're ready to update analysis

The notes block (Analysis section) is a flat array in the HTML. Search for `notes: [` and you'll find each fight's array. Edit text, push, done. No build step.

If you want to swap in entirely new projections, edit `USER_PROJECTIONS_BY_FIGHT` near the top of the script tag. The model values overwrite everything downstream (per-fight panel, moneylines tab, method odds, ITD).
