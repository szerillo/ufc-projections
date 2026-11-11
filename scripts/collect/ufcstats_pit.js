// UFCStats point-in-time collector for backtests (run in a tab on http://ufcstats.com/).
// For each past event, counts only bouts dated BEFORE the event, so nothing after the card
// (including the graded bout) leaks in. DWCS rows count on the UFC side, like ufcstats.js.
//
//   window.__EV = [['UFC 332: Silva vs. Wang', '2026-10-03'], ...];   // exact UFCStats names
//   <paste>  -> 'started';  poll window.__log;  read window.__pit.slice(i, i+880)
//
// One line per fighter:
//   name|date|n,min,kd_l,kd_a,dec_rate,fin_rate,been_fin,off_ko,age,sub_loss|W-L-D|koW,subW,koL,subL
(async () => { try {
  window.__log = 'start'; const out = [];
  const P = s => new DOMParser().parseFromString(s, 'text/html'), sl = ms => new Promise(r => setTimeout(r, ms));
  const list = P(await (await fetch('/statistics/events/completed?page=all')).text());
  const evA = [...list.querySelectorAll('a[href*="event-details"]')];
  for (const [ename, edate] of window.__EV) {
    const a = evA.find(x => x.textContent.trim().toLowerCase() === ename.toLowerCase());
    if (!a) { out.push('#MISSING ' + ename); continue; }
    const cut = new Date(edate + 'T00:00:00Z');
    const ed = P(await (await fetch(a.href)).text());
    const links = [...new Set([...ed.querySelectorAll('a[href*="fighter-details"]')].map(x => x.href))];
    for (const [i, h] of links.entries()) {
      const d = P(await (await fetch(h)).text());
      const name = d.querySelector('.b-content__title-highlight').textContent.trim();
      const box = {}; d.querySelectorAll('li.b-list__box-list-item').forEach(li => { const m = li.textContent.replace(/\s+/g, ' ').trim().match(/^([^:]+):\s*(.*)$/); if (m) box[m[1].trim()] = m[2].trim(); });
      const rows = [...d.querySelectorAll('tr.b-fight-details__table-row')].filter(r => r.querySelectorAll('td').length >= 10).map(r => {
        const td = r.querySelectorAll('td'), two = k => [...td[k].querySelectorAll('p')].map(p => p.textContent.trim()), evp = two(6);
        return { wl: td[0].textContent.trim().toLowerCase(), kd: two(2), date: new Date(evp[1] + ' UTC'),
                 method: two(7).join(' ').replace(/\s+/g, ' ').trim(), rnd: td[8].textContent.trim(), time: td[9].textContent.trim() }; });
      const R = rows.filter(r => ['win', 'loss', 'draw', 'nc'].includes(r.wl) && r.date < cut);   // newest first on the page
      const mins = r => { const [m, s] = r.time.split(':').map(Number); return (parseInt(r.rnd) - 1) * 5 + m + s / 60; };
      const tot = R.reduce((x, r) => x + mins(r), 0), kl = R.reduce((x, r) => x + (+r.kd[0] || 0), 0), ka = R.reduce((x, r) => x + (+r.kd[1] || 0), 0);
      const W = R.filter(r => r.wl === 'win'), L = R.filter(r => r.wl === 'loss'), D = R.filter(r => r.wl === 'draw');
      const ko = r => /KO/.test(r.method), sub = r => /SUB/.test(r.method), fin = r => ko(r) || sub(r);
      const dob = box.DOB && box.DOB !== '--' ? new Date(box.DOB + ' UTC') : null;
      const v = [R.length, tot.toFixed(1), kl, ka,
        R.length ? (R.filter(r => /DEC/.test(r.method)).length / R.length).toFixed(3) : '0',
        W.length ? (W.filter(fin).length / W.length).toFixed(3) : '',
        L.length ? (L.filter(fin).length / L.length).toFixed(3) : '0',
        R[0] && R[0].wl === 'loss' && ko(R[0]) ? 1 : 0,
        dob ? ((cut - dob) / 3.15576e10).toFixed(1) : '',
        ((L.filter(sub).length + 1) / (L.length + 4)).toFixed(3)];
      out.push([name, edate, v.join(','), `${W.length}-${L.length}-${D.length}`,
        [W.filter(ko).length, W.filter(sub).length, L.filter(ko).length, L.filter(sub).length].join(',')].join('|'));
      window.__log = ename + ' ' + (i + 1) + '/' + links.length; await sl(300);
    }
  }
  window.__pit = out.join('\n'); window.__log = 'done ' + out.length + ' lines, ' + window.__pit.length + ' chars';
} catch (e) { window.__log = 'ERR ' + e; } })();
'started';
