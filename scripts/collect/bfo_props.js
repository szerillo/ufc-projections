// BestFightOdds props collector (run in Sean's Chrome, in a tab on bestfightodds.com).
// Same-origin fetch of one or more BFO event pages; reads the moneyline rows and the
// prop rows (tr.pr) that follow each matchup. No login, one page per call, 300 ms apart.
//
// Usage in javascript_tool:
//   window.__EVENTS = ['/events/ufc-334-4433', '/events/ufc-334-4370'];  // a card can span two IDs
//   <paste this file>        -> returns 'started'
//   window.__bfo_log         -> 'done N rows' when finished
//   window.__bfo_compact.slice(i, i+880) -> read back in ~880-char slices (tool output truncates near 1,000), save as {slug}_props.txt
//   (window.__bfo_out keeps every prop row if a method or round prop is needed later)
//
// Output: one line per row, ' ; ' separated cells (tilde-heavy returns get blocked):
//   M ; <bout key> ; <fighter> ; <book1 price> ; ... (moneyline)
//   P ; <bout key> ; <prop label> ; <book1 price> ; ...
// First line is H ; books ; <book names in column order>.
(async () => {
  window.__bfo_log = 'running';
  const lines = [];
  let books = null;
  const clean = s => s.replace(/&#189;/g, '.5').replace(/½/g, '.5').replace(/[▲▼]/g, '').trim();
  for (const ev of (window.__EVENTS || [])) {
    const html = await fetch(ev, { credentials: 'include' }).then(r => r.text());
    const doc = new DOMParser().parseFromString(html, 'text/html');
    for (const t of doc.querySelectorAll('table.odds-table')) {
      const hdr = [...t.querySelectorAll('thead th')].map(c => clean(c.textContent).replace(/\$.*$/, ''));
      if (hdr.length < 4) continue;               // the left-hand name-only table
      const bk = hdr.slice(1, -1);                 // drop leading blank and trailing 'Props'
      if (!books) { books = bk; lines.push('H ; books ; ' + bk.join(' ; ')); }
      let pair = [], key = '';
      for (const tr of t.querySelectorAll('tbody tr')) {
        const cells = [...tr.children].map(c => clean(c.textContent));
        if (!cells.length) continue;
        if (tr.classList.contains('pr')) {
          if (key) lines.push(['P', key, cells[0], ...cells.slice(1, 1 + bk.length)].join(' ; '));
          continue;
        }
        if (pair.length === 2) pair = [];
        pair.push(cells[0]);
        if (pair.length === 2) key = pair[0] + ' vs ' + pair[1];
        lines.push(['M', pair.length === 2 ? key : '(pending)', cells[0], ...cells.slice(1, 1 + bk.length)].join(' ; '));
      }
    }
    await new Promise(r => setTimeout(r, 300));
  }
  // first fighter's M line was written before its opponent was known; fix the key
  for (let i = 0; i + 1 < lines.length; i++)
    if (lines[i].startsWith('M ; (pending)')) {
      const k = lines[i + 1].split(' ; ')[1];
      lines[i] = lines[i].replace('(pending)', k);
    }
  window.__bfo_out = lines.join('\n');
  // compact read-back: moneylines plus the two-sided duration props only, prices as CODE+price
  const CODE = { Polymarket: 'PM', Kalshi: 'KA', FanDuel: 'FD', Caesars: 'CZ', BetRivers: 'BR',
                 BetWay: 'BW', Unibet: 'UB', BetMGM: 'MG', DraftKings: 'DK' };
  const ab = (books || []).map(b => CODE[b] || b.slice(0, 4));
  const KEEP = /^(Fight goes to decision|Fight doesn't go to decision|Over \d\.5 rounds|Under \d\.5 rounds)$/i;
  const SHORT = l => l.replace(/^Fight goes to decision$/i, 'GTD').replace(/^Fight doesn't go to decision$/i, 'ITD')
    .replace(/^Over (\d\.5) rounds$/i, 'O$1').replace(/^Under (\d\.5) rounds$/i, 'U$1');
  const out = []; let last = '';
  for (const l of lines) {
    const c = l.split(' ; ');
    if (c[0] === 'H') { out.push('H;' + ab.join(',')); continue; }
    if (c[0] === 'P' && !KEEP.test(c[2])) continue;
    if (c[1] !== last) { out.push('#' + c[1]); last = c[1]; }
    out.push([c[0], c[0] === 'P' ? SHORT(c[2]) : c[2], c.slice(3).map((v, i) => v ? ab[i] + v : '').filter(Boolean).join(',')].join(';'));
  }
  window.__bfo_compact = out.join('\n');   // same format as {slug}_props.txt; parse with scripts/bfo_props.py
  window.__bfo_log = 'done ' + lines.length + ' rows, compact ' + window.__bfo_compact.length + ' chars';
})();
'started';
