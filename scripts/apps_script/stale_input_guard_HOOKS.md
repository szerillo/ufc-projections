# Stale-input guard: loader hooks (installed in the sheet's bound script, file Code.gs)

The guard code lives at the end of Code.gs (copy in stale_input_guard.gs). Three one-line hooks in the loader:

1. loadCard_, new-card branch: `clearCardInputs_(ss); cleared = true; guardNewCard_(ss);`
2. writeTab_, before the existing `if (!nameScore_(cur[q][0], fq.dog)) {`:
   `if ((cur[q][0] || cur[q][1]) && !((nameScore_(cur[q][0], fq.dog) && nameScore_(cur[q][1], fq.fav)) || (nameScore_(cur[q][0], fq.fav) && nameScore_(cur[q][1], fq.dog)))) guardBookingChange_(sh, rows[0] + q, cur[q][0] + ' vs ' + cur[q][1], fq.dog + ' vs ' + fq.fav);`
   (fires only when the bout changed; a favorite flip of the same two fighters does not reset the row)
3. onOpen menu, after "Load next UFC card": `.addItem('Confirm inputs on selected rows (stale-input guard)', 'guardConfirmRows')`

Sheet side (Sheets API, Nov 19 2026): Calculator AJ (stamp) and AK (STALE INPUTS flag, flip-tolerant),
Bet Rec N wrapped with `IF(LEN(Calculator!$AK{r})>0,"check inputs: "&Calculator!$AK{r}, <original>)` on
Main Card N2:N6 and Prelims N2:N9, warning-only protection on Main Card V2:AB7 and Prelims V2:AB11.
Markov watcher: writes through the API do not fire onEdit; it should write Calculator AJ = "dog|fav" with J/AP/AQ (blank is fine, means no flag).
