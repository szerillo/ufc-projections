# Dry run: Friday Dec 4 spread-lock path on the DRAFT Dec 5 card (2026-11-27, branch dec5-spread-dryrun, not merged)

Tests the path, not prices. `python3 -I audits/dec5/spread_dryrun/dryrun_spread_lock.py --cache <UFCStats cache>` builds
SYNTHETIC inputs in /tmp/dec5_spread_dryrun (export with no-vig BFO draft medians as true_fav and a flat placeholder method split,
odds file, DRAFT event file with the unconfirmed 15:00Z / 21:00Z times, three TEST book rows at -110), then runs preflight,
lock and close in SPREAD_TRACK_TEST mode, table, grade on fake results, and the refusals. No number it prints is a price.

Result 2026-11-27: 10/10 checks pass.
- Preflight reads the inputs and says READY with two warnings: DRAFT card list, and the UFCStats cache is 14 days old
  (refresh before Friday; branch ufcstats-refresh-2026-11-27 has the method).
- Lock, table, close (14 bouts each) and grade all run on the Dec 5 names, including the -3.5 cover logic on a decision,
  a KO and a split decision, and the unit rule on -110 (to win 1u, so a loss is -1.10).
- Refused as designed: a staging export, a lock after the first bout, and a preflight after the first bout.

## Known gap found (not counted as a pass)
spread_track.py only allows test rows under /tmp/. A checkout that itself sits under /tmp (scratch trees, worktrees) is under
/tmp, so a test-mode lock aimed at analysis/spread_locks/2026-12-05.jsonl is ACCEPTED, and `grade` does not skip "test" rows.
- Mitigation now: spread_lock_preflight.py BLOCKS when the lock file holds any test row (checked in this dry run).
- Fix proposed, not applied (spread_track.py is locked): PROPOSED_spread_track_guard.diff.
- Runbook rule until then: never run SPREAD_TRACK_TEST=1 from an audit-locks checkout.
