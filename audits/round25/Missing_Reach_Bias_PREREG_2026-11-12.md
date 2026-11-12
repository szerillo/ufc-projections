# Missing reach and the Form Line: pre-registration (Kirk round 25 B)
Written before any number below was computed.
Question: when one fighter's reach is missing, the Form model reads the reach as equal. Is Form then biased for or against
the fighter whose reach is missing?
Data: every graded UFC win (no draws, no NC) with a walk-forward Form Line (form.p in the event files of the branch build,
the published model), all years the files carry. Reach presence from each fighter's file (bio.reach).
Groups: (L) both reaches listed; (M1) exactly one missing; (M2) both missing.
Primary test (M1 only, the only group where "equal" can favor one side): residual r = won - Form p for the fighter whose reach
is missing; report mean r with a 95% CI (normal, per-bout).
Bar (fixed now): bias is flagged only if |mean r| >= 0.03 AND the 95% CI excludes 0. Otherwise: no evidence of bias.
Secondary (descriptive, no bar): calibration in 4 Form bands (50-60, 60-70, 70-80, 80+ for the Form favorite) and Brier score,
group L vs M1 vs M2.
Run once. No other cut, no reweighting, no change to the model from this check before UFC 334.
