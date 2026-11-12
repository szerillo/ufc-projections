# Fighter bio refresh from UFCStats pages: pre-registration (Kirk round 27 call 1). Runs AFTER UFC 334; nothing pulled yet.

## Why
Our fighter bios come from a third-party scrape (Greco1899/scrape_ufc_stats, ufc_fighter_tott.csv). It does not refresh a
fighter's row once written: live UFCStats has values where the file is blank (round 26 Wayback: 20 fighter-dates had a reach
before the fight; round 27: on the 334 card, 4 fighters blank in height, 3 in reach, 3 in stance, and 1 changed height).

## Fields (only these)
height, reach, stance, date of birth. Weight class and records are not bio fields here (records come from fight results).

## Source and matching
- Each fighter's own UFCStats fighter-details page, fetched by UFCStats fighter ID (never by name), politely (1 request / 300 ms),
  same-origin in a browser tab, for every fighter with a UFC fight since 2015 plus every fighter on an upcoming card.
- Shared names: the ID decides; the shared-name bug (round 21) is fixed in the same build by keying bios by ID.

## Pass bar (revised Kirk round 28 B, before anything is pulled; supersedes the round 27 text)
ONE rule for every change, blank or not: a field takes a new value only if UFCStats (fighter-details by ID) and the UFC.com
athlete page show the same value. Exact match, no rounding (67 vs 67.50 disagree; 5'6" = 66.00 agrees).
- Height, reach: both sources must agree. Otherwise the field keeps what it has today (a blank stays blank and reads
  "not listed"; a value that a later check shows to be contested is held, as round 28 held Belgaroui's height).
- Stance: UFC.com shows no stance, so no stance changes in this refresh (blank stays "not listed").
- DOB: UFC.com shows age, not a date; age must be consistent with the UFCStats DOB on the read date, else no change.
- Why one rule: round 23's fill already used two sources on these same fighters and rejected Mesquita and Diaz reach on a
  half inch; round 28 call 1 pulled fight 3's Form Line because UFCStats-only values are unverified. Filling blanks from
  UFCStats alone would publish exactly the values that call called unverified. The cost is known and visible: some fields
  stay "not listed". Known now (round 23 reads): Mesquita reach 67 vs 67.50 and height 5'4" vs 66.00, Diaz reach 69 vs 69.50
  and height 5'8" vs 68.50 all fail, so they stay blank; Hasan height 5'7" vs 67.00 passes.
- Release of round 28 holds: fight 3's Form Line returns only from a build whose inputs all pass this rule; with Mesquita's
  height and reach still failing, it stays held and Kirk decides between keeping the hold and showing it with "not listed".
- Every changed number on any page (Form Lines, angles, tale of the tape, Labs) is listed by a diff of two full builds (before /
  after), as in round 23; any change not traced to a refreshed field reverts the whole refresh.
- Labs research numbers move with the refresh; they ship with the research refresh (backlog item 2), with one corrections entry.

## What is not done
No guessing, no third source, no rounding, no change to past graded records.
