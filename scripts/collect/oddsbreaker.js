// Run on https://natelatshaw.shinyapps.io/UFC_Matchup_Comparisons/ after ~10 s load. PANE = the event tab's href without '#'.
const PANE = [...document.querySelectorAll('a[data-toggle="tab"]')].find(a => /UFC 334/.test(a.textContent)).getAttribute('href').slice(1);
document.querySelector('a[href="#' + PANE + '"]').click();
const F = ['UFC Record', 'Total Fight Minutes', 'Age', 'Height', 'Reach', 'Stance', 'Win % (#)', 'Knockout % of Wins (#)', 'Submission % of Wins (#)',
  'Knockout % of Losses (#)', 'Submission % of Losses (#)', '% of Time Spent at Distance (# of Minutes)', '% of Time Spent in Clinch/on Ground (# of Minutes)',
  'Control Rate of Clinch/Ground Time', 'Significant Strikes Landed per Minute at Distance', 'Significant Strikes Absorbed per Minute at Distance',
  'Differential: Landed - Absorbed', 'Takedown Accuracy', 'Attempted per 5 Minutes at Distance', 'Takedown Defense', 'Faced per 5 Minutes at Distance',
  'Success Rate', 'Attempted per 5 Control Minutes', 'Defense Rate', 'Faced per 5 Controlled Minutes'];
window.__ext = () => { const d = {}; document.getElementById(PANE).querySelectorAll('table tr').forEach(r => { const c = r.querySelectorAll('th, td'); if (c.length >= 3) d[c[0].textContent.trim()] = [c[1].textContent.trim(), c[2].textContent.trim()]; });
  return [0, 1].map(i => F.map(k => d[k] ? d[k][i] : '--').join(' ; ')); };
window.__sig = () => { const t = document.getElementById(PANE).querySelector('table'); return t ? t.innerText.slice(0, 300) : ''; };
window.__store = {}; window.__olog = 'start';
(async () => { await new Promise(r => setTimeout(r, 5000)); const sel = document.getElementById(PANE).querySelector('select');
  window.__store[0] = [sel.options[0].text, ...window.__ext()];
  for (let n = 1; n < sel.options.length; n++) {              // change-poll: never read a stale table
    const before = window.__sig(); sel.value = sel.options[n].value; $(sel).trigger('change');
    for (let w = 0; w < 24000; w += 2000) { await new Promise(r => setTimeout(r, 2000)); if (window.__sig() !== before && window.__sig().length > 100) break; }
    await new Promise(r => setTimeout(r, 1500)); window.__store[n] = [sel.options[n].text, ...window.__ext()]; window.__olog = 'done ' + n; }
  window.__olog = 'ALL'; })();
// check: no two consecutive stores identical; read back 3 matchups per call. Missing matchups -> SYN rows (rule in inputs_to_blocks.py)
