# RESULTS: B42 holdout on card 10 (scored 2026-11-27 after PREREG commits 2b0056f1 / fbde820e)

Script score_holdout.py (sha256 0406967a08ba3cfb...), output score_holdout_out.txt (3b6c23a2e35c8564...), input export
sha256 bee567ba756bffa9... (private, not committed).

- **Integrity:** the export reproduces the Nov 19 backtest exactly on cards 2-9 (101 fights, S0 Brier 0.2158, A 0.2162).
- **Card 10 (12 graded fights), primary:** Brier A minus S0 = -0.00055, 95% CI -0.00185 to +0.00086.
  **Registered reading: A holds.** A (0.2143) edged the old card average (0.2148) on this card; both beat the other options,
  and Markov off was worst here (0.2215).
- **Pooled walk-forward cards 2-10 (113 fights, reported only):** S0 0.2157, A 0.2160. Same picture as Nov 19: the fixed offset
  costs nothing measurable, and the gaps sit far inside the noise.
- **Recs on card 10:** every option makes the same two BETs (Dom Mar Fan W, John Mitchell W), so the shift choice moved no bet.
- **Shift values:** S0's card average was 0.0886; the Nov 19 code's walk-forward offset from cards 1-9 is 0.1062 (all prior
  rows with J and G); the live sheet used 0.1086 (graded rows only). Sensitivity, not registered: A at 0.1086 gives Brier 0.2142,
  so the reading does not depend on which offset is used.
- **Power, as registered:** 12 fights are a sign check, not a confirmation. Follow-up per the PREREG: no change; note in SHEET_MAP.
