// Run on https://www.sherdog.com/. NAMES: fighters with <=3 UFC/DWCS bouts (pre_ufc) and anyone needing career KO/SUB %.
// Sherdog spellings differ (Bia Mesquita = Beatriz Mesquita); check the candidate list when two names match.
const NAMES = {'Kayla Harrison': 'Kayla Harrison', 'Bia Mesquita': 'Beatriz Mesquita'};
window.__H = {}; window.__slog = 'start';
(async () => { try {
  const P = s => new DOMParser().parseFromString(s, 'text/html'), sl = ms => new Promise(r => setTimeout(r, ms));
  const isUFC = e => /^UFC|Contender Series|DWCS|Ultimate Fighter/i.test(e);
  for (const [n, q] of Object.entries(NAMES)) {
    const sd = P(await (await fetch('/stats/fightfinder?SearchTxt=' + encodeURIComponent(q))).text()); await sl(400);
    const a = [...sd.querySelectorAll('table a[href*="/fighter/"]')][0]; if (!a) { window.__H[n] = 'not found'; continue; }
    const d = P(await (await fetch(a.getAttribute('href'))).text()); await sl(500);
    const t = [...d.querySelectorAll('table')].find(t => /Result/.test(t.textContent) && /Method/.test(t.textContent));
    const R = [...t.querySelectorAll('tr')].map(r => [...r.querySelectorAll('td')].map(x => x.textContent.replace(/\s+/g, ' ').trim())).filter(x => x.length >= 6 && /^(win|loss|draw|nc)/i.test(x[0]));
    const pre = R.filter(r => !isUFC(r[2])), W = pre.filter(r => /^win/i.test(r[0])), L = pre.filter(r => /^loss/i.test(r[0]));
    const AW = R.filter(r => /^win/i.test(r[0]));
    window.__H[n] = {sherdog_id: a.getAttribute('href').split('-').pop(), pre_bouts: pre.length, pre_wins: W.length, pre_losses: L.length,
      pre_ko_losses: L.filter(r => /KO/i.test(r[3])).length, pre_sub_losses: L.filter(r => /Submission/i.test(r[3])).length,
      pre_finish_rate: W.length ? +(W.filter(r => /KO|Submission/i.test(r[3])).length / W.length).toFixed(3) : 0,
      regional_5r_2plus: pre.filter(r => +r[4] >= 4).length >= 2,   // undercounts scheduled-5R bouts that ended early
      last_pre_ufc_promotion: pre[0] ? pre[0][2].slice(0, 40) : '',
      career_ko_pct: AW.length ? +(AW.filter(r => /KO/.test(r[3])).length / AW.length).toFixed(3) : 0,
      career_sub_pct: AW.length ? +(AW.filter(r => /Submission/.test(r[3])).length / AW.length).toFixed(3) : 0};
  }
  window.__slog = 'done';
} catch (e) { window.__slog = 'ERR ' + e; } })();
