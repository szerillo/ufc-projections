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

## Pass bar (fixed now)
- A field is replaced only if the live page has a value and our file differs (blank or different).
- A live value that differs from a non-blank file value (e.g. Yousri Belgaroui 6'5" -> 6'6") is applied only if a second
  source agrees: UFC.com athlete page for height/reach (exact match, no rounding: 67 vs 67.50 is a disagreement), and for stance
  no second source exists, so stance changes from non-blank values are NOT applied (blank -> value is applied, UFCStats only).
- Blank -> value for height/reach: UFCStats alone (the field was missing, not contested). Kirk may require UFC.com here too.
- Every changed number on any page (Form Lines, angles, tale of the tape, Labs) is listed by a diff of two full builds (before /
  after), as in round 23; any change not traced to a refreshed field reverts the whole refresh.
- Labs research numbers move with the refresh; they ship with the research refresh (backlog item 2), with one corrections entry.

## What is not done
No guessing, no third source, no rounding, no change to past graded records.
