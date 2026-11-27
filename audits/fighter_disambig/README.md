# Same-name fighter split (2026-11-27, branch fighter-disambig, not merged)

## The bug
build_form.py keys fighters by display name. Nine names are shared by two UFCStats fighters. Two things went wrong:
- **One file for two people:** Bruno Silva (flyweight, on the Dec 5 card) and Bruno Silva (middleweight) were one fighter file
  with 23 bouts and one Elo.
- **Wrong bio:** the bio came from the FIRST UFCStats row with that name, even when that person never had a UFC bout.
  Live examples on main: Jean Silva (featherweight, b. 1996) shows DOB 1977-10-08, so his site age is about 20 years too old;
  Mike Davis, Michael McDonald, Anthony Romero and Victor Valenzuela also show the other person's bio.
  The T0 snapshot ages (snapshot_t0.gs) read these fighter files, so any of these fighters would get a wrong age column.

## The fix
- `data/fighter_disambig.json`: for each of the 52 UFC bouts involving a shared name, the fighter-details id of the
  same-named fighter, read from each fight page on ufcstats.com (Chrome same-origin fetch). Only Bruno Silva has two people
  with UFC bouts; the other names have one fighter with bouts plus a same-named record without any.
- `labels` renames the non-primary fighter: "Bruno Silva (MW)" (slug bruno-silva-mw). The Dec 5 flyweight keeps "Bruno Silva".
- load_ufcstats renames that fighter per bout (stats already attached) and builds each shared-name bio from the right id.
- Test: scripts/test_fighter_disambig.py, 8/8 pass. Other tests (sheet_v47, fighter_names, guard_card_status) still pass.

## Build comparison (same cache, no sheet ID, scratch tree; logs in this folder)
- Odds matched: unchanged (2507 of 2587 since 2022). Bruno Silva's 15 bouts with odds split 7 (FLW) and 8 (MW).
- Fighters written: 2786 vs 2785 (the new Bruno Silva (MW) file).
- Form Line log loss on 2470 fights: 0.6398 on the branch vs 0.6417 with main's code (a side effect of the split; not a model change).

## To ship
Needs the next full build_form.py run with the sheet ID (Sean's step), after this branch is merged. Until then the live files
keep the merged Bruno Silva and the wrong bios above.
