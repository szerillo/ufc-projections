# UFC Model sheet map

Where the moving parts of the "UFC Model" Google Sheet live and what reads them. The sheet ID is private: never write it here, in commits or on pages.

## Tabs
| Tab | What it holds |
|---|---|
| Main Card / Prelims | One row per fight: prices, List %, True %, edges, Bet Rec (N), Markov decision shares (AP/AQ) |
| Calculator | Model math, rows 2-6 main card, 8-17 prelims; parameters in B41:B45 |
| Snapshots | Archived rows per card at first walkout, graded after the card (N = dog listed, P = Markov J, AY = graded, AO = dog won) |
| Betting Card | Sheet recs laid out for the card |

## Calculator chain (per fight row r)
- G = listed dog % (de-vigged from the tab prices)
- J = Markov dog win % (watcher-entered)
- H = `MAX(0.02, MIN(0.98, J - $B$42))`, or G when J is blank
- Q = G + 0.15*(H - G) - 0.04*women + context code - B43*max public excess - B44*min public excess, clamped
- L = Q + Manual Adjust M, shown as True % on the tabs
- Edges: dog = True - implied at dog price; fav = True - implied at fav price. Bet Rec rules v4.7 (first match wins).

## Parameters
| Cell | Value | Meaning |
|---|---|---|
| B41 | 0.5 | Method split market anchor |
| **B42** | **0.1086** | **MARKOV_SHIFT, fixed offset (v4.8)** |
| B43 | 0.15 | PUBLIC_FADE_MAX |
| B44 | 0.075 | PUBLIC_FADE_MIN |
| B45 | 0.15 | MARKOV_GTD_WT |

## B42: fixed Markov offset (v4.8, Nov 19 2026, Sean approved)
- **What:** Markov runs high on dogs. B42 is subtracted from every fight's Markov J before blending. It is a plain number, so no fight's inputs can move another fight.
- **Fit:** average of (Markov J - listed G) over every graded Snapshots row. D42 holds the live refit:
  `=IFERROR(AVERAGE(FILTER(Snapshots!P2:P1000-Snapshots!N2:N1000,Snapshots!P2:P1000<>"",Snapshots!N2:N1000<>"",Snapshots!AY2:AY1000<>"")),0)`
  Nothing reads D42; it is display only. C42 and E42 carry the in-sheet labels.
- **Re-fit: after each graded card.** When the card's Snapshots rows are graded, type D42's value (4 decimals) into B42 as a number. Do it before the next card's first-walkout snapshot, never mid-card. Never paste a formula into B42 (that would bring back cross-fight links).
- **Why not monthly:** one card adds 10-14 rows to about 114; the value moves a few hundredths of a point per card, and refitting at the grading step keeps one offset per card.
- **Sanity band:** if the refit moves B42 by more than 0.02 in one card, check Snapshots for a bad row (blank N, wrong J) before applying.
- **Replaced:** v4.6 formula `=IFERROR(AVERAGE(FILTER(J2:J17-G2:G17,J2:J17<>"",G2:G17<>"")),0)` (card-wide average; one fight's inputs moved every fight).

### B42 history
| Date | Value | Rows | Note |
|---|---|---|---|
| 2026-11-09 | formula (card avg) | n/a | v4.6 added |
| 2026-11-19 | 0.1086 | 114 graded | v4.8 fixed offset, FN Prochazka vs Stirling is the first card under it |

## Readers of B42 (no change needed for a constant)
- `scripts/apps_script/publish_to_site.gs` line ~93: exports `shift` per fight and in `params`.
- `scripts/verify_projections.py`: checks params shift equals each fight's inputs shift.
- `scripts/sheet_v47.py`: recomputes H as `markov - shift`.
- `scripts/publish_source.py`, `scripts/build_form.py` (`par`, reads Calculator row 42 col B).

## Backups
- Before the v4.8 change (Nov 19 2026): Drive copy "UFC Model BACKUP before B42 fixed offset 2026-11-19" and an xlsx export of the same name.
