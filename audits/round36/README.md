# Kirk round 36: Sean's hand-set method numbers (MM-1)

- MM1_PREREG.md: the rule, written before it was run (sha256 in SHA256SUMS).
- Diff vs the Nov 12 22:47Z export: method_inputs unchanged on 12 of 13 fights (Sanches ai 0.83 -> 0.85, which the formula
  uses). The changed numbers are typed constants in the method cells themselves: DEC on 9 fights (10 sides), DEC + KO on Hasan.
- report_0609Z_as_published.md: the 06:09Z export through the new check. Only the stale-prices error remains (Sean's step).
- report_0609Z_prices_fresh_sim.md: the same export with only prices_loaded set to 1 h before publish (what a Refresh does to
  that field): PASS, 286 values compared, 0 mismatched, 10 manual method sides listed with cell, typed value and formula value.
- test_manual_method_out.txt: MM-1 plants 7/7 (Nov 12 export passes with no manual method; a wrong DEC, a wrong typed DEC,
  SUB not 1 - DEC - KO, GTD off by 0.5 pts all fail; a consistent retype passes).
- test_manual_price_out.txt (8/8) and test_sheet_v47_out.txt: the existing self-tests, unchanged results.
