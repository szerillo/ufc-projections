# After UFC 334 (Nov 14 2026): open items, in priority order

Rewritten at the code freeze (Kirk, Nov 12). Nothing here is done before the card except the merge itself, the Saturday check or a
real bug. Every rule or threshold change is pre-registered first and run once. Evidence for each item is in the round folders
named.

1. **Grade UFC 334.**
   Next: Sunday or Monday, run Grade last card in the sheet (Snapshots and PropSnap), then `python3 -I scripts/check_rounds.py --post`.
   Record Markov window card 9 of 10.
   Re-judge, without changing them, the 4 h price-staleness threshold (round 11: "set on UFC 334 data") and the thin-market display.
2. **Loader v2.9 in its first live week.**
   - Installed Thursday if Kirk ran T1-T5; otherwise v2.7 or v2.8 is live.
   - Next: log every `!!!` alert line from Friday and Saturday (REFUSED rows, source-unreachable refusals, bout-count drops) and whether each was right.
   - Only the node harness has exercised the guard (25 plants), never real Apps Script; first real refusals get read by hand.
   - Evidence: audits/round30.
3. **BFO's stale Caesars column.**
   - BFO showed Gordon +420 / Costa -625 for 40+ hours. Caesars' own US feed was +300 to +310 all week (audits/round30/B_caesars_420.txt).
   - The TRAP rule caught it, but only because an exchange fair existed.
   - Next: pre-register a stale-book check (a book's price unchanged for N hours while the consensus moves, or disagreeing with that book's own feed), and decide what D uses when it fires.
4. **Fighter bio refresh** (prereg: audits/round27/Bio_Refresh_PREREG_post334.md, two-source rule from round 28 B). Next: run it as pre-registered.
   - Fetch UFCStats and UFC.com by fighter ID.
   - Build twice and diff every page number.
   - Any change that can't be traced to a refreshed field reverts the whole refresh.

   The refresh releases or keeps the round 28 holds (fight 3 Form Line, Belgaroui height, Labs height rows 3 in / 4 in): run `scripts/form_holds.py` after every rebuild until each hold is released by name.
   It also carries:
   - **Fight 11 Form Line correction:** Borralho 40.2% to about 40.0%, with Belgaroui's height conflict (6'5" ours vs 6'6" UFCStats and UFC.com) named on the corrections page.
   - **Shared-name fix:** bios keyed by fighter ID (see item 5).
5. **Labs angle bugs** (round 20 found, round 21 measured; live on main with "under review" marks from form/data/labs_review.json).
   - Both-sides overwrite in `form_model.angle_sides`: 8 angles.
   - Shared UFCStats names (Bruno Silva, Jean Silva, Mike Davis, Anthony Romero, Victor Valenzuela) take the wrong bio row in 23 of 30 bouts.
   - Together, 111 shown numbers in 12 angles move; no ROI sign changes.
   - Next: pre-register the fix (key bios and histories by fighter ID, count every qualifying side), ship it with item 6, remove the marks.
6. **Research refresh** (`form/data/research.json`, 2,388 to 2,420 fights).
   - The debut box moves from 233 / 49.8% / -11.9% to 234 / 49.6% / -12.3%.
   - Next: full build, rebuild `data/embeds/debut_angle_stats.json`, one corrections entry.
   - Run with items 5 and 7.
7. **TUF sensitivity for the debut angle** (round 19). Next: pre-register, then run debut_vs_vet with TUF tournament bouts counted both ways. Report it alongside item 6; the embed box doesn't change before that.
8. **Publish export: strip sheet coordinates and raw inputs** (round 18). The publish script unfreezes after 334.
   Next:
   - Pre-register the field list to drop (`tab`, `row`, `calc_row`, `tap`, `junk`, `tip`, `markov`, `shift`, `open_dog`, `ctx`, `manual`).
   - Check every consumer: `publish_source.py`, `build_fight_embeds.py`, verifier rules `pub_ml` / `pubp`, and the projections check.
   - Run the public scan on the new export.
9. **Missing reach vs newness** (rounds 25-26: -17.3 pts flagged, not separable). Next: pre-register a test that:
   - dates reach at fight time from archived UFCStats pages;
   - matches on UFC fight count;
   - drops the shared-name rows.
   No public claim about direction until it's run; the site keeps "Reach not listed; Form treats it as equal."
10. **Mesquita / Diaz reach and the half-inch rule** (round 24 call 2).
    - UFCStats 67 / 69 vs UFC.com 67.50 / 69.50: "not listed" on 334.
    - Next: pre-register whether a half-inch difference counts as agreement. This decides whether fight 3's Form Line can come back after item 4.
11. **Stance second source (southpaw box)** (rounds 21-22).
    - The southpaw box is off for 334 (`STANCE_2ND = {}`). UFC.com has no stance field, so stance never passes a two-source rule.
    - Next: pre-register a second stance source (no Tapology scraping, no reading stance off fight film by eye) or retire the box.
12. **Drift box** (round 25 A: pulled; the reference set used all books, "now" used US books only).
    Next: pre-register one book set for both ends, most likely rebuilding the reference from US-regulated books at open and close. Then decide whether it returns.
13. **TRAP cutoff is post hoc** (Block 48: the 4.0-point exclusion rule was set after seeing Gordon).
    Next: after 10 more cards, report every TRAP flag with the book's own feed price (item 3) and the close. Keep or change the cutoff only on a pre-registered bar.
14. **Merge-guard record.** After the merge, record the new main SHA in `audits/MAIN_AT_CHECK.txt` on purpose (round 18 served-set check on the real merge result).
15. **publish-to-site branch.** It carries PUBLISH.md (v2.9 install, T6-T9).
    Next: merge it into main on Kirk's go per PUBLISH.md T7 when the projections path goes live, or fold PUBLISH.md into main after 334.
