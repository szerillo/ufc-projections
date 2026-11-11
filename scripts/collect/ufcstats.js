// Run on http://ufcstats.com/statistics/events/upcoming (or completed). Set EVENT to the card name.
const EVENT = /UFC 334/i, EVDATE = new Date('2026-11-14');
window.__U = {f: {}}; window.__log = 'start';
(async () => { try {
  const P = s => new DOMParser().parseFromString(s, 'text/html'), sl = ms => new Promise(r => setTimeout(r, ms));
  const ev = [...document.querySelectorAll('a')].find(a => EVENT.test(a.textContent));
  const ed = P(await (await fetch(ev.href)).text());
  const links = [...new Set([...ed.querySelectorAll('a[href*="fighter-details"]')].map(a => a.href))];
  for (const [i, h] of links.entries()) {
    const d = P(await (await fetch(h)).text());
    const name = d.querySelector('.b-content__title-highlight').textContent.trim();
    const box = {}; d.querySelectorAll('li.b-list__box-list-item').forEach(li => { const m = li.textContent.replace(/\s+/g, ' ').trim().match(/^([^:]+):\s*(.*)$/); if (m) box[m[1].trim()] = m[2].trim(); });
    const rows = [...d.querySelectorAll('tr.b-fight-details__table-row')].filter(r => r.querySelectorAll('td').length >= 10).map(r => {
      const td = r.querySelectorAll('td'), two = k => [...td[k].querySelectorAll('p')].map(p => p.textContent.trim()), evp = two(6);
      return {wl: td[0].textContent.trim().toLowerCase(), opp: two(1)[1] || '', kd: two(2), event: evp[0] || '', date: evp[1] || '',
              method: two(7).join(' ').replace(/\s+/g, ' ').trim(), rnd: td[8].textContent.trim(), time: td[9].textContent.trim()}; });
    window.__U.f[name] = {rec: (d.querySelector('.b-content__title-record') || {}).textContent.replace(/\s+/g, ' ').replace('Record: ', '').trim(), box, rows};
    window.__log = 'fighter ' + (i + 1) + '/' + links.length; await sl(300);
  }
  // KD recipe (ufcstats_kd_recipe.md), prior UFC/DWCS bouts only; DWCS counts on the UFC side
  const pct = s => s ? parseFloat(s) / 100 : 0, num = s => s ? parseFloat(s) : 0;
  const mins = r => { const [m, s] = r.time.split(':').map(Number); return (parseInt(r.rnd) - 1) * 5 + m + s / 60; };
  window.__lines = Object.entries(window.__U.f).map(([n, f]) => {
    const b = f.box, R = f.rows.filter(r => ['win', 'loss', 'draw', 'nc'].includes(r.wl));
    const tot = R.reduce((a, r) => a + mins(r), 0), kdf = R.reduce((a, r) => a + (+r.kd[0] || 0), 0), kda = R.reduce((a, r) => a + (+r.kd[1] || 0), 0);
    const W = R.filter(r => r.wl === 'win'), L = R.filter(r => r.wl === 'loss'), fin = r => /KO|SUB/.test(r.method);
    const dob = b.DOB && b.DOB !== '--' ? new Date(b.DOB) : null, age = dob ? Math.round((EVDATE - dob) / 3.15576e10 * 10) / 10 : '';
    const us = [num(b.SLpM), pct(b['Str. Acc.']), num(b.SApM), pct(b['Str. Def']), num(b['TD Avg.']), pct(b['TD Acc.']), pct(b['TD Def.']), num(b['Sub. Avg.'])];
    const kd = [tot ? +(kdf / tot * 15).toFixed(2) : 0, tot ? +(kda / tot * 15).toFixed(2) : 0, R.length ? +(R.filter(r => /DEC/.test(r.method)).length / R.length).toFixed(3) : 0,
      W.length ? +(W.filter(fin).length / W.length).toFixed(3) : '', L.length ? +(L.filter(fin).length / L.length).toFixed(3) : 0,
      R[0] && R[0].wl === 'loss' && /KO/.test(R[0].method) ? 1 : 0, age, R.length,
      +((L.filter(r => /SUB/.test(r.method)).length + 1) / (L.length + 4)).toFixed(3), Math.min(3, num(b['Sub. Avg.']))];
    return [n, us.join(','), kd.join(','), f.rec, `${R.length} bouts ${tot.toFixed(1)} min KD ${kdf}/${kda} finW ${W.filter(fin).length}/${W.length} finL ${L.filter(fin).length}/${L.length}`].join('|'); });
  window.__log = 'done ' + links.length;
} catch (e) { window.__log = 'ERR ' + e; } })();
// read back: window.__lines.slice(0,6).join('\n'), then 6..12, ...
