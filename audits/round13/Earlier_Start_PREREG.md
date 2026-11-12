# Published close cut at the earlier start estimate: pre-registered 2026-11-12 (Kirk round 13, call 1), before the rule is run

Why: round 12 found an in-fight snapshot (Blanchfield vs Jasudavicius, 2026-10-18 01:55 UTC) counted as pre-start, because
the published close used only the archive's commence time on the bout's LAST snapshot (02:00), which was later than the
real start. BettingPros had 01:20.

What I looked at before writing this (inputs only, no rule outcome): the archive has 1 to 6 distinct commence times per
event (2,749 events with more than one; spread median 1.8 h, max 31 h). Only 13 published past odds blocks carry an
event-file start, and the repo's BettingPros odds files hold 225 bouts with a scheduled time.

Start estimates for a bout:
- E1, archive: the commence time on the bout's last archive snapshot (today's rule).
- E2, schedule: the BettingPros scheduled_utc for the bout, when the repo has it (event-file "start", or a bout in a
  data/*_odds.json file matched by both names and the event date).
- E3, archive earlier: the earliest commence time on any of the bout's archive snapshots that lies within 12 h before E1
  (a commence more than 12 h earlier is a reschedule, not a start estimate, and is ignored).
Cut = the earliest of the estimates on file. A snapshot is pre-start only if its time is strictly before the cut.

Scope: the PUBLISHED odds block only (current/closing line, chart series, per-book table). Unchanged:
- the opener (it is days earlier; reported if any opener falls after the cut);
- research, Form fits, the bias slope and every backtest (they keep the all-books close on E1; flagged to Kirk, not changed here).
If the cut leaves no snapshot with a US-regulated price, the bout shows the opener only, as the 5 no-US bouts do.

Pass bar (Kirk), all three:
1. Blanchfield vs Jasudavicius: the new published close is within 2.0 pts of its pre-fight median, defined independently
   of the US filter as the no-vig median of ALL listed books at the latest snapshot strictly before the cut.
2. No bout loses all its US prices: 0 bouts go from a v24 US close to no close. Any such bout is a FAIL on this item,
   reported by name; it publishes opener-only per the call; the rule is not changed.
3. A site-wide diff over every published odds block: counts (unchanged, close moved, close lost), median, p95 and max
   change in points, the 5 largest by name. Reported, not judged. The checker's independent event-odds recompute,
   updated to the same rule with its own code, must agree on UFC 334 with 0 mismatches.

Run once. No change to the 12 h window, the estimates or the strict inequality after seeing the result.
