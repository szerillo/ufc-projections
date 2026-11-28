# Dec 5 go-live branch (2026-11-28, branch dec5-golive, on main 14680204; DRAFT card until UFC.com confirms)

What is on it: dec5-spread-dryrun merged onto main (pre-card Markov inputs, BFO odds draft and D-code check, spread-lock dry run,
cards.yml entry fn_adesanya_magomedov, data/official/2026-12-05.DRAFT.txt). dec5-odds-feed-guard is left out: main already has
the newer, merged guard (14680204). One script fix: rehearse_go_live.sh now refuses with a plain message when the card has no
sheet export yet (it raised a Python traceback).

Rehearsal 2026-11-28 (scripts/rehearse_go_live.sh with CARD/SLUG/EVENT for Dec 5): REFUSED at the first step, as designed:
"no sheet export for fn_adesanya_magomedov on main yet". Nothing after that step can run before Sean publishes. The Friday
refresh dry run (same day) already showed steps 0, 1 and 1b green on the live feed, stopping at 2b for the same reason.
On this branch: odds guard tests 23/23, card guard PASS.

Friday order once Sean has published (Kirk):
1. UFC.com check, then `git mv data/official/2026-12-05.DRAFT.txt data/official/2026-12-05.txt` (the card guard needs that name).
2. Confirm first_fight_utc / main_event_utc in cards.yml against UFC.com.
3. Round-18 served-set check + re-pin, then BR=dec5-golive SLUG=fn_adesanya_magomedov scripts/merge_main.sh.
4. CARD=... SLUG=fn_adesanya_magomedov EVENT=form/data/events/2026-12-05-<card>.json scripts/rehearse_go_live.sh
5. Spread lock preflight and lock (audits/forward_scoring/README.md section 1), before the first bout.
