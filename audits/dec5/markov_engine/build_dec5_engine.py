# Dec 5 2026 (UFC FN Adesanya vs Magomedov, Markov card 11 of the k lock): stage the V4.1b engine file.
# Fills ufc_stats, kd_stats (with the Sherdog pre_ufc layer) and the record part of career_context from the
# dec5-precard inputs (C1, a48a4739) plus a Sherdog win-method pull (Nov 27). fights_raw (Oddsbreaker) and
# market_odds stay EMPTY until the Tue/Wed scrape; momentum is a 0.0 placeholder until the BFO L5 pull.
# Engine logic is copied byte for byte from the template. The file is NOT runnable until those inputs exist.
# Usage: python3 build_dec5_engine.py <template.py> <ufcstats_raw.txt> <sherdog.txt> <sherdog_wins.json> <out_sim.py> <out_manual.md>
import sys, re, json, datetime as dt
TPL, RAW, SH, WINS, OUT, MAN = sys.argv[1:7]
CARD = dt.date(2026, 12, 5)
pct = lambda s: round(float(s.rstrip('%')) / 100, 2)
raw = [l.rstrip('\n').split('|') for l in open(RAW) if l.strip()]
pre = {}
for l in open(SH):
    m = re.match(r'^"([^"]+)":\s*(\{.*?\})\s*#', l)
    if m: pre[m.group(1)] = json.loads(m.group(2))
wins = {k: v for k, v in json.load(open(WINS)).items() if not k.startswith('_')}
manual = []
# Manual inputs (judgment calls), each listed in the MD output
pre['Magomed Tuchalov'].update(pre_bouts=6, pre_wins=6, pre_finish_rate=1.0)
manual.append('Tuchalov pre_ufc 6-0, all finishes (C1 file had 5-0): Sherdog lists 6 pro bouts before the UFC win (Khakimzhonov, Hardcore MMA Aug 2023, was not counted); matches UFCStats 7-0.')
pre['Ivan Gnizditskiy'].update(pre_bouts=5, pre_wins=5, pre_finish_rate=1.0)
manual.append('Gnizditskiy pre_ufc 5-0 per UFCStats (Sherdog 7-0 adds a League of Boxing knuckle bout and a 2018 tournament bout). Fewer bouts = less prior weight, the conservative choice.')
manual.append('Osmanli pre_ufc kept at Sherdog 11-1; UFCStats shows 13-2 overall (2 wins Sherdog does not list). No third source scraped (Tapology is off limits).')
wins['Magomed Tuchalov'] = [7, 5, 1, 1]; wins['Ivan Gnizditskiy'] = [5, 4, 1, 0]
manual.append('career_context records: Sherdog win-method counts for all 28; Tuchalov and Gnizditskiy use the UFCStats records above. Mairon Santos (Sherdog 17 W vs UFCStats 18) and Hecher Sosa (14 vs 15) use Sherdog counts; both have 2+ UFC bouts so only career KO/sub shares move.')
us, kd, cc = [], [], []
for b, name, rec, box, dob, ht, reach, stance, n, mn, k, dec, fw, fl, sl, last, top in raw:
    s = box.split(','); g = lambda x: x.split('=')[1]
    n_, mins = int(g(n)), float(g(mn)); kl, ka = map(int, g(k).split('/')); d_ = int(g(dec))
    fwn, wn = map(int, g(fw).split('/')); fln, ln = map(int, g(fl).split('/')); sln = int(g(sl))
    age = round((CARD - dt.datetime.strptime(dob, '%b %d, %Y').date()).days / 365.25, 1)
    off_ko = top.startswith('top=Loss KO/TKO')
    us.append(f'    "{name}": {{"slpm": {float(s[0]):.2f}, "str_acc": {pct(s[1])}, "sapm": {float(s[2]):.2f}, "str_def": {pct(s[3])}, "td_avg": {float(s[4]):.2f}, "td_acc": {pct(s[5])}, "td_def": {pct(s[6])}, "sub_avg": {float(s[7]):.1f}}},  # bout {b}; {rec}; {n_} UFC/DWCS bouts')
    p = pre.get(name) if n_ <= 3 else None
    psl, pl = (p['pre_sub_losses'], p['pre_losses']) if p else (0, 0)
    slr = round((sln + psl + 1) / (ln + pl + 4), 3)
    pdict = ''
    if p:
        q = {k_: p[k_] for k_ in ('pre_bouts', 'pre_wins', 'pre_losses', 'pre_ko_losses', 'pre_sub_losses', 'pre_finish_rate', 'regional_5r_2plus')}
        pdict = ',\n        "pre_ufc": ' + json.dumps(q).replace('true', 'True').replace('false', 'False')
    if n_ == 0:
        kd.append(f'    "{name}": {{"off_ko_loss": False, "age": {age}, "gender": "M", "ufc_fights": 0, "sub_loss_rate": {slr}{pdict}}},  # UFC DEBUT: rate keys and finish_rate left out (division-mean fallback)')
    else:
        fr = '' if wn == 0 else f'"finish_rate": {fwn / wn:.3f}, '
        kd.append(f'    "{name}": {{"kd_per15": {kl / mins * 15:.2f}, "kd_abs_per15": {ka / mins * 15:.2f}, "career_dec_rate": {d_ / n_:.3f}, {fr}"been_finished_rate": {fln / ln if ln else 0.0:.3f}, '
                  f'"off_ko_loss": {off_ko}, "age": {age}, "gender": "M", "ufc_fights": {n_}, "sub_loss_rate": {slr}, "sub_att_per15": {min(float(s[7]), 3.0):.1f}{pdict}}},  # {n_} bouts, {mins} min, KD {kl}/{ka}, dec {d_}, finW {fwn}/{wn}, finL {fln}/{ln}, subL {sln}' + ('  THIN' if n_ <= 3 else ''))
    w = wins[name]
    cc.append(f'    "{name}": {{"momentum": 0.0, "career_ko_pct": {w[1]}/{w[0]}, "career_sub_pct": {w[2]}/{w[0]}, "career_wins": {w[0]}}},  # PENDING momentum from BFO L5 (Tue/Wed); record {rec}')
data = ('fights_raw = {\n    # PENDING Tue/Wed: Oddsbreaker matchup strings (~ separators), 14 bouts per data/official/2026-12-05.DRAFT.txt\n}\n\n'
        'ufc_stats = {\n' + '\n'.join(us) + '\n}\n\n'
        'kd_stats = {\n' + '\n'.join(kd) + '\n}\n\n'
        'market_odds = {\n    # PENDING Tue/Wed: 4-book median moneylines (FanDuel, Caesars, BetRivers, Unibet)\n}\n\n'
        'career_context = {\n' + '\n'.join(cc) + '\n}\n')
t = open(TPL).read()
a = t.index('fights_raw = {'); z = t.index('\n}\n', t.index('career_context = {')) + 3
open(OUT, 'w').write(t[:a] + data + t[z:])
open(MAN, 'w').write('# Dec 5 engine staging: manual inputs (judgment calls)\n\n' + '\n'.join('- ' + m for m in manual) + '\n')
print(len(us), 'ufc_stats;', len(kd), 'kd_stats;', sum(1 for x in kd if '"pre_ufc"' in x), 'with pre_ufc;', len(cc), 'career_context')
