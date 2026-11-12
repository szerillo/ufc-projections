# Embeds: Kirk checks, round 28 (2026-11-12)

Branch `embeds-v5` at v40 (ad416766). Nothing merged, nothing pushed to main, the sheet is untouched.
Evidence: `audits/round28/` (sha256 in SHA256SUMS.txt).

## Call 1: fight 3 Form Line pulled
- **Data:** the event file now has `form.p` set to null for fight 3, with `form.held` = "Form Line held: fighter data incomplete". The Form Line angle built from it (fl5, Chiasson) is removed. The held value is kept only in `audits/round28/hold_values.json`.
- **What the pages show:**
  - Card table: "held‡", with the footnote "‡ Fight 3: Form Line held: fighter data incomplete."
  - Fight page: the Form Line row reads "held", with the fact line beside it and under the table.
  - Sheet: the summary line shows the fact line.
  - The fight 3 reach note is not shown, since there is no Form Line left for it to annotate.
- **Diff:** `call1_page_diff.txt` covers the card, fight 3, fight 11, sheet, Belgaroui's page, compare and Labs size. On fight 3, only the Form Line row and the "Form Line 5+ pts" angle row changed.
- **What else reads p:**
  - Tape: no. Form Figures (ra/rb) are a different model.
  - Angles: only fl5.
  - Card summary: Form column and sheet line only.
  - Method board: uses the fair market %, not p.
  - GTD (g) and the method split (ms): do not read p or bio height/reach.
  - Embeds: fight_03 has no Form Line row (registry checked).
  - OG text: the site has no OG tags.
- **390px:**
  - Card, embed and Labs pages: 390 wide.
  - Fight pages: 636 wide on v39 as well. This is a pre-existing two-column tape layout, not caused by this change; fight 3 went from 850 to 636.
- **Verifier:** `TOTAL: 2963/2963 numbers verified; 0 mismatches/assertion failures` (one fewer row: Belgaroui's height). Holds: 0 failures. Locks: 32 files, re-blessed with the reason. Scan: 760 files, 0 hits.

## Call 2: fights 2, 9, 11 left as is.

## A. Sanches DOB, Belgaroui height
- **Sanches:** round 27 compared fighter files, and Sanches has none. What Form, the pages and the embed actually read is his UFCStats bio row: 5'10", 74", Orthodox, Jan 28 2003, which equals live. Nothing on fight 1 moves.
  - Correction to round 27's bio counts against the real Form input: height 4, reach 2, stance 2, DOB 0.
- **Belgaroui:** our file says 6'5". Live UFCStats says 6'6", and UFC.com says 78.00 (also 6'6"). Two sources agree with each other, not with us.
  - Numbers that move:
    - (a) His height on the fight 11 tape (site and embed), compare page, sheet and fighter page.
    - (b) Labs "Height advantage": one fight moves from the 3 in bucket to the 4 in bucket (3 in ROI +0.8% to +0.4%; 4 in ROI -1.6% to -1.0%, from a same-code scratch build).
  - Both (a) and (b) are now HELD, with the fact lines "held · sources differ" and "Held: one fighter's height differs between sources".
  - (c) Fight 11's Form Line (40.2% to 40.0%) is left as is per call 2. Flagged below.

## B. One rule
For every change, blanks included, UFCStats and UFC.com must agree exactly. Stance never changes, because there is no second source.
- **Why:** round 23 already applied two sources to these fighters, and call 1 calls UFCStats-only values unverified.
- **Known cost, from the round 23 UFC.com reads:**
  - Mesquita: reach and height both fail.
  - Diaz: reach and height both fail.
  - Hasan: height passes.
- So fight 3's Form Line stays held after the refresh unless Kirk chooses to show it as "not listed".
- The prereg was updated before anything was pulled (sha e1787ed4…). Backlog item 10 now matches it.

## C. Records, bout by bout
Compared by fight-details ID across all 26 fighters:
- Ours only: 0.
- UFCStats only: 19 bouts, 16 DWCS and 3 Strikeforce, across 15 fighters.
- Every fighter's record gap equals the W/L of those rows exactly. Unexplained: 0.

## D. Leftover plants
Before this round the verifier had no hold rule at all; this round adds one. Five new plants:

| Plant | Result |
|---|---|
| Rebuild writes p back and drops the flag | Caught: 11 hold failures (data, event file, card, fight page, sheet) |
| Copy in embed JSON (card.json) | Caught |
| Copy in OG description | **Missed on first run**; fixed (percent copies next to "Form" in any file); now caught |
| Belgaroui height back on the fight 11 embed | Caught |
| Labs held row gets a number back | Caught |

Negative suite: 35/35.

## Kirk decides
1. Fight 11 Form Line reads Belgaroui's contested height (move 0.19 pts). Call 2 left it as is; A's rule would hold it. Keep or hold?
2. The Labs height rows 3 in / 4 in are held for a one-fight move. Keep the hold, or release it as immaterial?
3. After the refresh, fight 3 (Mesquita still failing two sources): keep it held, or show it with "not listed"?
4. Fight pages are 636px wide at 390 (pre-existing). Fix after 334?
