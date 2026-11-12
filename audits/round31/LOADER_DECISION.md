# Round 31 (code freeze): loader status at the freeze

v2.9 (`c8d938d7`, branch loader-guard 1968dcfc) is finished as far as proven; no further patches.
- Diff from v2.8: 60 insertions, 8 deletions; price/TRAP code byte-identical (audits/round30/loader_checks.txt).
- Plants: 25/25 on v2.9, 5/25 on v2.8 (audits/round30/A_C_D_guard_tests_v29.txt). A (outages) 6/6 REFUSE, C 5/5, D 3/3.
- Not proven: the guard has run only in the node harness, never in real Apps Script.

Safer Friday install: **v2.9.**
- Its price code is v2.8's byte for byte, so Gordon's D and rec are the same as v2.8's.
- It closes the two failures that can blank the sheet during a live refresh: today's ufc.com mid-edit clear, and a BFO outage
  blanking every price (v2.8 does both).
- If v2.9's new code misbehaves, the failure is a refusal or an extra alert line, never a wrong price. A bad refusal blocks the
  publish (Sean's step 3), which is the safe direction.
- Rollback is one paste: v2.8 (`7200be8d`).
