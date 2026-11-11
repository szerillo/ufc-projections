# Fight-week input pulls (no scratchpad)

Each collector runs in a NEW tab of Sean's Chrome (same-origin fetch, 250-500 ms between
requests, one page family at a time, no logins). Each stores results on `window` and is read
back in slices of about 1,500 characters (the tool output limit). The formatter
`../inputs_to_blocks.py` turns the read-back lines into the Markov folder's source files:

    inputs/<slug>/<slug>_ufcstats.txt   ufc_stats block   (ufcstats.js)
    inputs/<slug>/<slug>_kdstats.txt    kd_stats block    (ufcstats.js, KD recipe computed in-page)
    inputs/<slug>/<slug>_sherdog.txt    pre_ufc priors    (sherdog.js, fighters with <=3 UFC/DWCS bouts)
    inputs/<slug>/<slug>_oddsbreaker.txt fights_raw       (oddsbreaker.js, change-polled)
    inputs/<slug>/<slug>_careerctx.txt  career_context   (sherdog.js career KO/SUB %; momentum, layoff, prospect by hand)

Then `python3 scripts/markov_blocks.py` splices the blocks into the engine (PYTHONHASHSEED=0).

UFC 334 rebuild (2026-11-11): fresh pulls reproduced card 9 to within 2 points on 11 of 13
bouts (every column). Two 3+ gaps, both input drift from career_context: Harrison-Nunes P(dec)
-3.2 closes to -1.1 once career KO/SUB % is filled; Johnson-Almeida raw win -3.3 needs the hand
momentum/prospect terms (+0.03 prospect closes it to -1.7). Momentum has no written formula yet.
