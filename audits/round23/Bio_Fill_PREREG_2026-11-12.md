# Bio fill for 3 UFC 334 fighters: pre-registration (Kirk round 22, call 2)

Written before reading any UFC.com athlete page for these fighters and before any build with new values.

## Scope (exactly 5 fields)
| Fighter | Field | UFCStats live value (read 2026-11-12, fighter-details by ID) |
|---|---|---|
| Bilal Hasan (5182316da3c1d891) | reach | 70" |
| Bilal Hasan | stance | Switch |
| Bia Mesquita (eff9074bc066f0f2) | reach | 67" |
| Juan Diaz (74939a16c7b56f33) | reach | 69" |
| Juan Diaz | stance | Orthodox |

Nothing else: no other fighter, no other field (height stays as the source has it), Sanches untouched.

## Rule
1. A field is filled only if UFC.com's athlete page shows the same value. Reach: UFC.com "Reach" in inches, must equal
   UFCStats exactly. Stance: UFC.com must show a stance that equals UFCStats.
2. UFC.com missing the field, or a different value: the field stays blank and the pages show "not listed". No guess, no
   third source, no rounding.
3. How the value enters: the source CSV row for that fighter (UFCStats tott) gets ONLY the filled fields, in a scratch
   copy. A full scratch build with the patch is diffed against the same scratch build without it. Every changed value is
   listed and traced to a filled field (reach edge on the tale of the tape, reach arrows, angle membership such as
   reach4, Form model inputs and anything they move). Only traced changes are copied to the branch files.
4. Any changed value that cannot be traced to a filled field: revert the whole fill and ship blanks as "not listed".
5. Display: on embeds and site pages a missing reach or stance reads "not listed" (applies to every blank, not only these 3).
