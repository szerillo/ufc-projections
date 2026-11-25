# Official UFC.com card lists (card guard G3)

One file per card, named by the event date: `YYYY-MM-DD.txt`. One bout per line, `Fighter A vs Fighter B`, copied from
the UFC.com event page (main card and prelims). Lines starting with `#` are comments. Accents, case and corner order do
not matter. `scripts/guard_card_status.py --require-official` (friday_refresh step 0 and merge_main) fails any upcoming
card without this file or with a bout missing from it. Update it when UFC.com changes the card.
