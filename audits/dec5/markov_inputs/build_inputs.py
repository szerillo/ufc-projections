"""Dec 5 2026 Markov inputs from UFCStats fighter pages (Chrome same-origin pull, Nov 27): ufc_stats and kd_stats blocks in
the V4.1b format (references/kd_scrape.md). Rates RAW; the engine applies K=5 regression. Pre-UFC (Sherdog) layer pending."""
import re, datetime as dt, sys
CARD = dt.date(2026, 12, 5); WOMEN = set()
pct = lambda s: round(float(s.rstrip("%")) / 100, 2)
L = [l.rstrip("\n").split("|") for l in open(sys.argv[1]) if l.strip()]
us, kd = [], []
for b, name, rec, box, dob, ht, reach, stance, n, mn, k, dec, fw, fl, sl, last, top in L:
    s = box.split(","); g = lambda x: int(x.split("=")[1]); n_, mins = g(n), float(mn.split("=")[1])
    kl, ka = map(int, k.split("=")[1].split("/")); d_ = g(dec); fwn, wn = map(int, fw.split("=")[1].split("/")); fln, ln = map(int, fl.split("=")[1].split("/")); sln = g(sl)
    age = round((CARD - dt.datetime.strptime(dob, "%b %d, %Y").date()).days / 365.25, 1)
    lastd = last.split("=")[1]; days = (CARD - dt.datetime.strptime(lastd.replace(".", ""), "%b %d, %Y").date()).days if lastd else None
    off_ko = top.startswith("top=Loss KO/TKO")
    us.append(f'"{name}": {{"slpm": {float(s[0]):.2f}, "str_acc": {pct(s[1])}, "sapm": {float(s[2]):.2f}, "str_def": {pct(s[3])}, "td_avg": {float(s[4]):.2f}, "td_acc": {pct(s[5])}, "td_def": {pct(s[6])}, "sub_avg": {float(s[7]):.1f}}}  # bout {b}; record {rec}; {n_} UFC/DWCS bouts; last {lastd or "none"}{f" ({days} days)" if days else ""}; {top[4:]}')
    if n_ == 0:
        kd.append(f'# "{name}": UFC debut, no UFC/DWCS bouts: leave out of kd_stats (division-mean fallback) and fill pre_ufc from Sherdog'); continue
    kd.append(f'"{name}": {{"kd_per15": {kl / mins * 15:.2f}, "kd_abs_per15": {ka / mins * 15:.2f}, "career_dec_rate": {d_ / n_:.3f}, "finish_rate": {fwn / wn if wn else 0:.3f}, '
              f'"been_finished_rate": {fln / ln if ln else 0.0:.3f}, "off_ko_loss": {str(off_ko).lower()}, "age": {age}, "gender": "M", "ufc_fights": {n_}, '
              f'"sub_loss_rate": {(sln + 1) / (ln + 4):.3f}, "sub_att_per15": {min(float(s[7]), 3.0):.1f}}}  # {n_} bouts, {mins} min, KD {kl}/{ka}, dec {d_}, finW {fwn}/{wn}, finL {fln}/{ln}'
              + ("  THIN SAMPLE (<=3 UFC bouts): needs Sherdog pre_ufc" if n_ <= 3 else "") + ("  ARTIFACT: under 1 UFC minute" if mins < 1 else ""))
open(sys.argv[2], "w").write("UFC FN Adesanya vs Magomedov (Dec 5 2026) - UFCStats career statistics, scraped 2026-11-27 via ufcstats.com event a1bf037613180253 (Sean's Chrome, same-origin fetch)\n"
                             "Format: \"Name\": {slpm, str_acc, sapm, str_def, td_avg, td_acc, td_def, sub_avg}  # bout; record; prior UFC/DWCS bouts; last fight\n\n" + "\n".join(us) + "\n")
open(sys.argv[3], "w").write("UFC FN Adesanya vs Magomedov (Dec 5 2026) - V4 kd_stats from UFCStats fight-by-fight logs (prior UFC/DWCS bouts only; scraped 2026-11-27).\n"
                             "kd_per15 / kd_abs_per15 per 15 min over prior bouts; rates RAW (engine applies K=5). sub_loss_rate = (UFC sub losses + 1)/(UFC losses + 4); "
                             "for the <=3 group add Sherdog pre-UFC losses before running. sub_att_per15 = UFCStats Sub. Avg. capped at 3.0. Ages at Dec 5 2026. All men.\n"
                             "off_ko_loss TRUE: Adesanya (Pyfer KO R2, Mar 28 2026), Cutelaba (Stirling KO, Jun 20 2026). Osmanli's last bout is a DQ loss (not KO).\n\n" + "\n".join(kd) + "\n")
print(len(us), "ufc_stats rows;", sum(1 for k in kd if not k.startswith("#")), "kd_stats rows")
