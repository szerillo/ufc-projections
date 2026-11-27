# Forward scoring and the Friday spread lock (prepared 2026-11-27, branch forward-scoring-prep, not merged)

Nothing here bets, writes the sheet or publishes. Bars live on audit-locks and are not restated or changed here:
PREREG_model_review_2026-11-24.md (T1, T2), PREREG_T4_women_refit.md (T4), PREREG_spreads_v1.md (spreads).

## 1. Friday Dec 4: spread-tracker lock for Dec 5 (approved by Sean: track vs books; Sean judges edges; no auto-bet)
Order on Friday, after Sean publishes the card to the site:
1. Refresh the UFCStats cache (Greco1899 CSVs; newest event must be Nov 21 or later; branch ufcstats-refresh-2026-11-27 has the method).
2. Copy books_2026-12-05.TEMPLATE.json to books.json and fill each posted spread from a NY-legal book page
   (DraftKings first): line, signed American price, seen_at UTC. Delete rows with no spread posted. US-regulated books only.
3. Preflight (read-only, exit 0 = ready):
   `python3 -I audits/forward_scoring/spread_lock_preflight.py --slug fn_adesanya_magomedov --date 2026-12-05 --books books.json --cache .form_cache --card-list data/official/2026-12-05.txt --allowlist <audit-locks>/analysis/PUBLIC_OK.txt`
4. Run the lock commands it prints, add the sha256 line to analysis/MANIFEST.txt, push audit-locks before the first bout.
5. Saturday: `--stage close` before each bout; grade after results with `spread_track.py grade`.

Blockers as of Nov 27 (preflight output): no published export yet (Sean), no odds file because the cards.yml entry for
fn_adesanya_magomedov is only on branch dec5-precard (needs the merge to main so the odds bot pulls it), and no site event
file for Dec 5 yet (site build). analysis/spread_locks/2026-12-05.jsonl is already allowlisted.
Watch: first bout time is unconfirmed (cards.yml says 15:00Z); with 14 bouts an earlier early-prelim start would move the lock deadline.

## 2. Forward scoring for T1, T2, T4 (from the Dec 5 card on)
Per card, after results: add a row to cards_forward.json (lock = the T0 walkout CSV on audit-locks analysis/snap_locks/<date>.csv,
lock_commit_utc = its audit-locks commit time, first_bout_utc from the event file), then
`python3 -I audits/forward_scoring/forward_score.py verify --lock <csv> --event <event.json> --commit-time <utc>` and
`python3 -I audits/forward_scoring/forward_score.py score --cards cards_forward.json --close <audit-locks>/analysis/model_review_2026-11-24/close.json --out report.md`.

How the bars are applied (no bar changed):
- **Results** come from the site event file (UFCStats), never from the lock CSV. Draws and NC are excluded. A card counts only if
  its lock was committed before its first bout and it is dated 2026-12-05 or later.
- **T1:** (a) log loss and Brier of power vs multiplicative de-vig of the snapshot's best prices D/I; (b) is the frozen registered
  result (n=158, diff -0.00147, MET); (c) pools forward 70%+ favorites with the rebuilt (b) rows (rebuild reproduces n=158 exactly).
  Verdict only after 10 counted cards.
- **T2:** Q with vs without 0.15*(H-G). "Without" = the sheet mirror (scripts/sheet_v47.py) with Markov blank, so H = G; where the
  mirror does not reproduce the stored Q within 0.15 pt (manual adjust, context code), the stored Q minus the term is used and the
  row is counted in the report. Units: BET recs only, 1u by the unit rule at listed best prices. Verdict after 10 counted cards.
- **T4:** walk-forward per card: fit on the 2022-2026 archive power close plus earlier forward cards; fitted size per card; A = Q as
  stored, B = Q with -fitted size, C = no term (reference). Interim lines only until 30 women's bouts or 20 cards.

- **T3 shadow (registered outcome: keep the veto + shadow log; no bar):** every forward dog with an open, risk 1u at the
  walkout best dog price. Three lines: dogs the sheet vetoed ("no dog bet (drifting)"), dogs drifting 3+ points by the T3
  definition (open dog % minus the snapshot's consensus close, or listed G if blank), and all other dogs.
- **T6 shadow (Sean's decision; no pass or fail):** every 80%+ listed favorite at its walkout best price under A = to-win 1u and
  B = risk capped at 2u, each for all 80%+ favorites and for the v4.9 BET subset (-500 or longer), with the worst single loss.
- **Tests:** `python3 -I audits/forward_scoring/test_forward_score.py` (synthetic 3-bout card, 11 checks).

## Dry run (2026-11-27, fixture, not a score)
The Nov 7 card's Snapshots rows were turned into a lock-format CSV (results columns removed) and run through `verify` and `score`
with `"test": true`. Checks: the result join matched all 14 bouts and agreed with the sheet's own "dog won" grading 14 of 14
(including the Seok Hyun Ko / Seokhyeon Ko and Jose Henrique Souza / Jose Souza spellings); the (b) rebuild gave n=158 and
diff -0.00147, the registered numbers. The fixture holds private sheet values, so it is not committed and no fixture numbers are
quoted here. The spread tracker lock ran in SPREAD_TRACK_TEST mode on the Nov 21 card into /tmp with the refreshed cache.
