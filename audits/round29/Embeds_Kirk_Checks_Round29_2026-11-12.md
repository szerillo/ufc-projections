# Embeds and sheet: Kirk checks, round 29 (2026-11-12)

`embeds-v5` is at v41 (9823ffeb). The loader candidate is on branch `loader-guard` (f86316ab). Nothing is merged and nothing went to main. The sheet was read only (about 20:35Z) and not edited.

## Calls
1. **Fight 11 Form Line:** left as is. Logged as backlog item 11, naming the conflict: our file says 6'5", while UFCStats and UFC.com both say 6'6".
2. **Labs height rows:** stay held through 334.
3. **Fight 3:** stays held until the refresh and the two-source rule both pass.
4. **636px fight pages:** fixed before the merge. All four conditions are met:
   - CSS only: `form/style.css | 2 +-`, adding `.grid2>*,.grid3>*{min-width:0}` inside the 860px media query.
   - Verifier: `TOTAL: 2963/2963 numbers verified; 0 mismatches/assertion failures`. Holds 0, locks 32/0.
   - No data or number file touched.
   - At 390px, every page is 390 wide: all 13 fight pages (before: 636 to 850) plus card, sheet, fighter, compare, Labs and home. No page errors. Full-page screenshots of fights 1, 3 and 11 are in `audits/round29/`.

## A. Loader guard (v2.9 candidate, not installed)
- **Cause of the Nov 12 drop:** Refresh rebuilds the card from ufc.com. When a sheet row's bout is missing there, v2.8 clears the names. It also blanks every price and script-written column on that row, including the Calculator opener F.
- **v2.9 changes:**
  - It refuses to clear a row whose bout is still listed on BestFightOdds (any book, Polymarket included) or Novig. The row is kept exactly as it was, and the alert line starts with "!!! … REFUSED to clear".
  - When ufc.com lists fewer bouts than the last load did, that warning is the alert's first line.
  - A really cancelled bout comes off with UFC > Remove a cancelled bout. You name one fighter and confirm, and it applies to one bout only.
- **Plant tests:** run on the loader's own loadCard_, writeTab_ and writeCalculator_ against an in-memory sheet.

| Test | v2.8 | v2.9 |
|---|---|---|
| Control: prices move, 13 bouts | pass | pass |
| Nov 12 case: ufc.com drops Gordon–Costa, BFO still lists it | **cleared** (names, D, opener) | kept untouched, REFUSED warning, count drop as the first line, other rows refreshed |
| Only Novig still lists it | cleared | kept |
| Really cancelled, BFO still lists it | cleared | refused; cleared with the override; no repeat warning after |
| Cancelled, on no source | cleared, no count warning | cleared, count drop warned once |
| Override names one bout | n/a | Costa removed, another missing bout still held |

v2.9 passes 13/13. v2.8 passes 6/13, and the failures reproduce today's bug.

- **Today's restore is complete:** Feed has 13 rows. Gordon's hand inputs are intact (Tap 3, Junk 15, Tip 19, Markov 57, AP/AQ 70/20). Opener F (34.3%) equals the de-vigged BFO opener (+181/-215), so the re-read matches.

## B. Gordon, v2.7 vs v2.8
- **Live sheet as of 20:35Z:** still on v2.7. Prelims D is +420 Caesars, and Calculator AH reads "DOG +420 Caesars (+4 TRAP)", which is v2.7's text without "excluded from D/I".
- **The install is Kirk's job:** PUBLISH.md T1 to T5. Claude cannot confirm it will happen and does not edit the sheet.
- **Predicted effect:** live inputs run through each loader's own price code, then through `scripts/sheet_v47.py`. The before column reproduces the live row.

| | v2.7 (live) | v2.8 |
|---|---|---|
| D / I | +420 Caesars / -400 FanDuel | +310 FanDuel / -400 FanDuel |
| Listed dog / fav no-vig | 19.38% / 80.62% | 23.36% / 76.64% |
| True dog | 22.80% | 26.23% |
| Edges dog / fav | +3.57 / -2.80 | +1.84 / -6.23 |
| Rec | BET Melquizael Costa (80%+ rule, shop) | - |

- The TRAP price is what pushes the favorite over 80%.
- On the other 12 fights, B42 moves True % by at most 0.046 points, and no other rec changes.
- The actual readback follows after Kirk's T4.

## C. Untested assumption: a sheet export missing a bout stops go-live
No plant tested it. The plant was a fresh 12-fight export without Gordon vs Costa, run through friday_refresh step 2b extracted verbatim.
- **Before:** it blocks (exit 2), but **ALLOW_STALE=1 also waves the missing bout through** (exit 0). The stale-export override covered a different failure.
- **After:** a missing bout blocks even with ALLOW_STALE=1. Only `ALLOW_MISSING_BOUT=<last name>` passes it.
- The rehearsal runs friday_refresh under pipefail, so a block there stops the rehearsal.

## Kirk decides
1. Install loader v2.9 before 334, which breaks the v2.8 freeze (new hash 6864fa0d), or after?
2. Until then, is a manual rule acceptable? After any Refresh, check Feed has 13 rows before Publish. Step 2b now enforces this at merge time anyway.
