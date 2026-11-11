function snapshotSheet_(ss) {
  var sh = ss.getSheetByName('Snapshots');
  if (!sh) { sh = ss.insertSheet('Snapshots'); sh.getRange(1, 1, 1, SNAP_HDR.length).setValues([SNAP_HDR]).setFontWeight('bold'); sh.setFrozenRows(1); }
  if (sh.getMaxColumns() < SNAP_HDR.length) sh.insertColumnsAfter(sh.getMaxColumns(), SNAP_HDR.length - sh.getMaxColumns());
  sh.getRange(1, 1, 1, SNAP_HDR.length).setValues([SNAP_HDR]);   // keeps older sheets in step with new columns
  return sh;
}

// ---- v2.7 method-layer snapshot helpers
// tab row v (cols A..AQ, 0-based), calc row c, fight f (market), same = sheet dog is f.dog
function methodSnap_(v, c, f, same) {
  var n = function (x) { return typeof x === 'number' ? x : ''; };
  var inputs = [v[29], v[30], v[31], v[33], v[34], v[35]].map(n);
  var shares = [v[21], v[22], v[23], v[25], v[26], v[27]].map(n);
  var Q = c[16], model = ['', '', '', '', '', ''];
  if (typeof Q === 'number' && shares.every(function (x) { return typeof x === 'number'; })) model = [Q * shares[0], Q * shares[1], Q * shares[2], (1 - Q) * shares[3], (1 - Q) * shares[4], (1 - Q) * shares[5]].map(round4_);
  var mkt = ['', '', '', '', '', ''];
  if (f && f.props) { var D = same ? f.props.dog : f.props.fav, F = same ? f.props.fav : f.props.dog;
    var g = function (st) { return st && typeof st.prob === 'number' ? st.prob : null; };
    var raw = [g(D && D.dec), g(D && D.ko), g(D && D.sub), g(F && F.dec), g(F && F.ko), g(F && F.sub)];
    if (raw.every(function (x) { return x != null; })) { var t = raw.reduce(function (a, b) { return a + b; }, 0); if (t > 0) mkt = raw.map(function (x) { return round4_(x / t); }); } }
  return inputs.concat(shares).concat(model).concat(mkt).concat(['', '', '']);
}
function methodOutcome_(x, dogWon) {
  var m = String(x.method || '').toLowerCase(); if (!x.winner || /draw|no contest|overturn/.test(m)) return '';
  var how = /decision/.test(m) ? 'DEC' : /^\s*sub|submission \(/.test(m) && !/tko/.test(m) ? 'SUB' : /ko|tko|dq/.test(m) ? 'KO' : /sub/.test(m) ? 'SUB' : '';
  return how ? (dogWon ? 'dog' : 'fav') + how : '';
}

function snapshotCard() {
  var ss = SpreadsheetApp.getActive(); syncLayout_(ss);
  var ev = currentEvent_(); if (!ev) return; var pk = ev.pk;
  var feed = ss.getSheetByName('Feed'); var evName = feed.getRange('B1').getValue(), evDate = feed.getRange('D1').getValue();
  var card = buildCard_(ev);                       // fresh consensus = the close  (v2.1 fix: v2.0 passed the pk and threw)
  var norm = function (x) { return String(x || '').toLowerCase().replace(/[^a-z]/g, ''); };
  var lastOf = function (n) { var t = String(n || '').trim().split(/\s+/); return norm(t[t.length - 1]); };
  var findFight = function (dog, fav) {
    var i, f, a, b;
    for (i = 0; i < card.fights.length; i++) { f = card.fights[i]; a = norm(f.dog); b = norm(f.fav); if ((a === norm(dog) && b === norm(fav)) || (a === norm(fav) && b === norm(dog))) return f; }
    for (i = 0; i < card.fights.length; i++) { f = card.fights[i]; a = lastOf(f.dog); b = lastOf(f.fav); if ((a === lastOf(dog) && b === lastOf(fav)) || (a === lastOf(fav) && b === lastOf(dog))) return f; }
    for (i = 0; i < card.fights.length; i++) { f = card.fights[i]; if ((nameScore_(f.dog, dog) && nameScore_(f.fav, fav)) || (nameScore_(f.dog, fav) && nameScore_(f.fav, dog))) return f; }
    return null;
  };
  var NC = MAIN_ROWS[1] - MAIN_ROWS[0] + 1 + PRE_ROWS[1] - PRE_ROWS[0] + 1;
  var csh = ss.getSheetByName('Calculator'); var calc = csh.getRange(2, 1, NC, Math.min(35, csh.getMaxColumns())).getValues();
  calc = calc.map(function (r) { while (r.length < 35) r.push(''); return r; });
  var tabs = [['Main Card', MAIN_ROWS, 0], ['Prelims', PRE_ROWS, MAIN_ROWS[1] - MAIN_ROWS[0] + 1]];
  var rows = [], now = new Date();
  tabs.forEach(function (t) {
    var sh = ss.getSheetByName(t[0]); var n = t[1][1] - t[1][0] + 1;
    var v = sh.getRange(t[1][0], 1, n, 43).getValues();
    for (var r = 0; r < n; r++) {
      var c = calc[t[2] + r]; if (!c || !c[0]) continue;
      var dog = c[0], fav = c[1]; var f = findFight(dog, fav);
      var pClose = f ? ((norm(f.dog) === norm(dog) || lastOf(f.dog) === lastOf(dog) || (nameScore_(f.dog, dog) && !nameScore_(f.dog, fav))) ? f.pDog : (f.pDog == null ? null : 1 - f.pDog)) : null;
      var gtdClose = f && f.props.gtd ? f.props.gtd.prob : '';
      rows.push([pk, evDate, evName, t[0], t[1][0] + r, v[r][0], dog, fav, c[10], c[2], c[3], c[4], c[5], c[6], pClose == null ? '' : pClose,
        c[9], c[16], c[23], c[24], c[25], c[26], c[27], v[r][13], v[r][15], v[r][16], v[r][18], gtdClose,
        c[21], c[17], c[13], c[14], c[30], v[r][3], v[r][8], now,
        '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
        (typeof v[r][41] === 'number' && typeof v[r][42] === 'number' && typeof c[11] === 'number') ? round4_(c[11] * v[r][41] + (1 - c[11]) * v[r][42]) : '', '', '', '', typeof c[32] === 'number' ? c[32] : '', '']
        .concat(methodSnap_(v[r], c, f, f ? (pClose === f.pDog) : true)));
    }
  });
  var sh = snapshotSheet_(ss);
  // replace any earlier snapshot of the same card
  var last = sh.getLastRow();
  if (last > 1) { var pks = sh.getRange(2, 1, last - 1, 1).getValues(); for (var i = pks.length - 1; i >= 0; i--) if (String(pks[i][0]) === String(pk)) sh.deleteRow(i + 2); }
  last = sh.getLastRow();
  sh.getRange(last + 1, 1, rows.length, SNAP_HDR.length).setValues(rows);
  var np = propSnapWrite_(ss, card, pk, evName, evDate, now);
  SpreadsheetApp.getUi().alert('Snapshot saved: ' + rows.length + ' fights for ' + evName + ' (+ ' + np + ' PropSnap rows: every market x source). Re-run before the first walkout to capture the true close.');
}


function gradeCard() {
  var ss = SpreadsheetApp.getActive(), ui = SpreadsheetApp.getUi();
  var feed = ss.getSheetByName('Feed'); var dflt = feed ? String(feed.getRange('B2').getValue()) : '', dfltUrl = feed ? String(feed.getRange('B3').getValue()) : '';
  var r = ui.prompt('Grade which card?', 'ufc.com event URL (default: last loaded ' + (dfltUrl || 'none') + '):', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var url = (r.getResponseText() || dfltUrl).trim(); if (!url) return;
  var pk = dflt;   // snapshot rows are keyed by the card id stored at load time
  var evc = ufcEventCard_(url); var ev = { name: evc.name, date: evc.date };
  var norm = function (x) { return String(x || '').toLowerCase().replace(/[^a-z]/g, ''); };
  var res = evc.bouts.filter(function (b) { return b.winner; }).map(function (b) {
      var m = /(\d+):(\d+)/.exec(b.time || ''); var secs = ((b.round || 1) - 1) * 300 + (m ? (+m[1]) * 60 + (+m[2]) : 0);
      var lastOf0 = function (n) { var t = String(n || '').trim().split(/\s+/); return norm(t[t.length - 1]); };
      return { full1: b.red, full2: b.blue, n1: norm(b.red), n2: norm(b.blue), l1: lastOf0(b.red), l2: lastOf0(b.blue), winner: lastOf0(b.winner), method: b.method, dec: /decision/i.test(b.method || ''), round: b.round, time: b.time, secs: secs }; });
  if (!res.length) { ui.alert('No results yet for ' + url + ' (checked the ufc.com page and its live-stats feed' + (evc.fmid ? ', event ' + evc.fmid : ', no event id found on the page') + ').'); return; }
  // match a snapshot row to a result: full names first, then last names (sheet may say "Joshua Van" / "Patricio Pitbull")
  var lastOf = function (n) { var t = String(n || '').trim().split(/\s+/); return norm(t[t.length - 1]); };
  var findRes = function (dog, fav) {
    var i, x;
    for (i = 0; i < res.length; i++) { x = res[i]; if ((x.n1 === norm(dog) && x.n2 === norm(fav)) || (x.n1 === norm(fav) && x.n2 === norm(dog))) return x; }
    for (i = 0; i < res.length; i++) { x = res[i]; var ld = lastOf(dog), lf = lastOf(fav); var hit = function (l, a) { return l === a || a.indexOf(l) >= 0 || l.indexOf(a) >= 0; };
      if ((hit(ld, x.l1) && hit(lf, x.l2)) || (hit(ld, x.l2) && hit(lf, x.l1))) return x; }
    for (i = 0; i < res.length; i++) { x = res[i]; if (x.n1 === norm(dog) || x.n2 === norm(dog) || x.n1 === norm(fav) || x.n2 === norm(fav)) return x; }
    for (i = 0; i < res.length; i++) { x = res[i]; if ((nameScore_(x.full1, dog) && nameScore_(x.full2, fav)) || (nameScore_(x.full1, fav) && nameScore_(x.full2, dog))) return x; }
    return null;
  };

  // ---- Snapshots
  var sh = snapshotSheet_(ss); var last = sh.getLastRow(); var graded = 0, fights = {};
  if (last > 1) {
    var v = sh.getRange(2, 1, last - 1, SNAP_HDR.length).getValues();
    for (var i = 0; i < v.length; i++) {
      var row = v[i]; if (String(row[0]) !== String(pk)) continue;
      var x = findRes(row[6], row[7]); if (!x) continue;
      var dogIsF1 = x.n1 === norm(row[6]) || (x.n1 !== norm(row[7]) && (x.l1 === lastOf(row[6]) || x.l1.indexOf(lastOf(row[6])) >= 0 || lastOf(row[6]).indexOf(x.l1) >= 0 || (nameScore_(x.full1, row[6]) && !nameScore_(x.full1, row[7]))));
      var dogWon = x.winner === (dogIsF1 ? x.l1 : x.l2) ? 1 : 0;
      var gtd = x.dec ? 1 : 0, o15 = x.secs > 450 ? 1 : 0, o25 = x.secs > 750 ? 1 : 0, o45 = x.secs > 1350 ? 1 : 0;
      var br = function (p) { return typeof p === 'number' ? Math.round(Math.pow(p - dogWon, 2) * 10000) / 10000 : ''; };
      var rec = String(row[22] || ''), pl = '';
      if (/^BET|^lean/i.test(rec)) { var onDog = rec.toLowerCase().indexOf(String(row[6]).toLowerCase()) >= 0; var odds = onDog ? row[32] : row[33]; if (typeof odds === 'number') { var won = onDog ? dogWon : 1 - dogWon; pl = won ? Math.round(payout_(odds) * 100) / 100 : -1; } }
      var play = String(row[23] || ''), ppl = '';
      if (/^GTD/i.test(play) && typeof row[25] === 'number') ppl = gtd ? Math.round(payout_(toAmer_(row[25]) * 1) * 100) / 100 : -1;
      if (/^ITD/i.test(play) && typeof row[25] === 'number') ppl = !gtd ? Math.round(payout_(toAmer_(1 - row[25])) * 100) / 100 : -1;
      var outRow = [x.winner, x.method, x.round, x.time, x.secs, dogWon, gtd, o15, o25, o45, br(row[14]), br(row[16]), br(row[15]), pl, ppl, new Date()];
      sh.getRange(i + 2, 36, 1, outRow.length).setValues([outRow]); graded++;
      var bg = function (p) { return typeof p === 'number' ? Math.round(Math.pow(p - gtd, 2) * 10000) / 10000 : ''; };
      sh.getRange(i + 2, 53, 1, 3).setValues([[bg(row[26]), bg(row[24]), bg(row[51])]]);   // GTD Brier: close, Fight GTD model, Markov
      sh.getRange(i + 2, 57, 1, 1).setValue(br(row[55]));   // Brier of the exchange reference (v2.3) — compare with col 46 (close) after ~10 cards
      // v2.7 method grading: 6-outcome Brier (dog/fav x DEC/KO/SUB) for the model's joint probabilities vs the market's
      var mo = methodOutcome_(x, dogWon);
      if (mo && sh.getMaxColumns() >= 84) { var mB = function (off) { var ps = [], k, ok = true; for (k = 0; k < 6; k++) { var q = row[off + k]; if (typeof q !== 'number') { ok = false; break; } ps.push(q); } if (!ok) return ''; var idx = ['dogDEC', 'dogKO', 'dogSUB', 'favDEC', 'favKO', 'favSUB'].indexOf(mo), b = 0; for (k = 0; k < 6; k++) b += Math.pow(ps[k] - (k === idx ? 1 : 0), 2); return round4_(b); };
        sh.getRange(i + 2, 82, 1, 3).setValues([[mo, mB(69), mB(75)]]); }
      fights[norm(row[6])] = { dog: row[6], fav: row[7], pClose: row[14], gtdClose: row[26], o15: row[28], o25: row[29], o45: row[31], x: x, dogWon: dogWon };
      fights[norm(row[7])] = fights[norm(row[6])];
    }
  }

  // ---- Archive CLV table (row 4 header: Date, Event, Bet, Book, Odds Taken, Closing Odds, CLV, Result, P/L)
  var ar = ss.getSheetByName('Archive'), filled = 0;
  if (ar && ar.getLastRow() >= 5) {
    var av = ar.getRange(5, 1, ar.getLastRow() - 4, 9).getValues();
    for (var k = 0; k < av.length; k++) {
      var a = av[k]; if (!a[2] || a[7]) continue;                       // needs a Bet, skip already-graded
      var evMatch = norm(a[1]) && (norm(ev.name).indexOf(norm(a[1])) >= 0 || norm(a[1]).indexOf(norm(ev.name)) >= 0);
      if (!evMatch && !(a[0] instanceof Date && ev.date && Math.abs(a[0].getTime() - new Date(ev.date).getTime()) < 3 * 864e5)) continue;
      var bet = String(a[2]); var bl = bet.toLowerCase(); var fight = null, side = null;
      var bn = norm(bet);
      for (var key in fights) { var fg = fights[key]; if (bn.indexOf(norm(fg.dog)) >= 0) { fight = fg; side = 'dog'; break; } if (bn.indexOf(norm(fg.fav)) >= 0) { fight = fg; side = 'fav'; break; } }   // full name first
      if (!fight) for (var key2 in fights) { var fg2 = fights[key2]; var dl = String(fg2.dog).split(' ').pop().toLowerCase(), fl = String(fg2.fav).split(' ').pop().toLowerCase(); if (bl.indexOf(dl) >= 0) { fight = fg2; side = 'dog'; break; } if (bl.indexOf(fl) >= 0) { fight = fg2; side = 'fav'; break; } }
      if (!fight) continue;
      var taken = Number(a[4]); if (!validOdds_(taken)) continue;
      var pClose, won;
      if (/gtd|distance/i.test(bl)) { pClose = fight.gtdClose; won = fight.x.dec; }
      else if (/itd|inside/i.test(bl)) { pClose = typeof fight.gtdClose === 'number' ? 1 - fight.gtdClose : ''; won = !fight.x.dec; }
      else if (/(over|o)\s*4\.5/i.test(bl)) { pClose = fight.o45; won = fight.x.secs > 1350; }
      else if (/(under|u)\s*4\.5/i.test(bl)) { pClose = typeof fight.o45 === 'number' ? 1 - fight.o45 : ''; won = fight.x.secs <= 1350; }
      else if (/(over|o)\s*2\.5/i.test(bl)) { pClose = fight.o25; won = fight.x.secs > 750; }
      else if (/(under|u)\s*2\.5/i.test(bl)) { pClose = typeof fight.o25 === 'number' ? 1 - fight.o25 : ''; won = fight.x.secs <= 750; }
      else if (/(over|o)\s*1\.5/i.test(bl)) { pClose = fight.o15; won = fight.x.secs > 450; }
      else if (/(under|u)\s*1\.5/i.test(bl)) { pClose = typeof fight.o15 === 'number' ? 1 - fight.o15 : ''; won = fight.x.secs <= 450; }
      else { pClose = side === 'dog' ? fight.pClose : (typeof fight.pClose === 'number' ? 1 - fight.pClose : ''); won = side === 'dog' ? fight.dogWon === 1 : fight.dogWon === 0; }
      var closeOdds = typeof pClose === 'number' ? toAmer_(pClose) : '';
      var clv = typeof pClose === 'number' ? Math.round((pClose - imp_(taken)) * 1000) / 10 : '';
      ar.getRange(5 + k, 6, 1, 4).setValues([[closeOdds, clv === '' ? '' : clv + '%', won ? 'W' : 'L', won ? Math.round(payout_(taken) * 100) / 100 : -1]]); filled++;
    }
  }
  var pg = propSnapGrade_(ss, pk, fights);
  ui.alert(ev.name + ': ' + res.length + ' results found, ' + graded + ' snapshot rows graded, ' + pg + ' PropSnap rows graded, ' + filled + ' Archive bets filled.' + (graded ? '' : '\n(No snapshot for this pk — run "Snapshot card" before the next one.)'));
}



// ================================================================ PROPSNAP (v2.5) — long-format archive of every market x source at the close
// One row per (fight, market, source). Sources: books (de-vigged median of sportsbooks), exch (weighted exchange fair), and each
// exchange on its own (Novig / Polymarket / Kalshi, with $ volume for Novig). Graded by "Grade last card"; summarised by the
// Scorecard menu — that is the test of "are the exchanges sharper than the books" on your own fights, market by market.
var PROPSNAP_HDR = ['pk', 'date', 'event', 'tab', 'row', 'dog', 'fav', 'market', 'source', 'prob', 'odds', 'weight/vol', 'two-way', 'snapshot time', 'result', 'Brier', 'graded'];
function propSnapSheet_(ss) {
  var sh = ss.getSheetByName('PropSnap');
  if (!sh) { sh = ss.insertSheet('PropSnap'); sh.getRange(1, 1, 1, PROPSNAP_HDR.length).setValues([PROPSNAP_HDR]).setFontWeight('bold'); sh.setFrozenRows(1); }
  return sh;
}
function propSnapWrite_(ss, card, pk, evName, evDate, now) {
  var sh = propSnapSheet_(ss), rows = [];
  var tabOf = {}; [['Main Card', MAIN_ROWS], ['Prelims', PRE_ROWS]].forEach(function (t) { var th = ss.getSheetByName(t[0]); if (!th) return; var v = th.getRange(t[1][0], 2, t[1][1] - t[1][0] + 1, 2).getValues(); v.forEach(function (r, i) { if (r[0]) tabOf[nkey_(r[0]).key] = [t[0], t[1][0] + i]; }); });
  card.fights.forEach(function (f) {
    var loc = tabOf[nkey_(f.dog).key] || tabOf[nkey_(f.fav).key] || ['', ''];
    var push = function (market, source, p, odds, w, two) { if (typeof p !== 'number' || isNaN(p)) return; rows.push([pk, evDate, evName, loc[0], loc[1], f.dog, f.fav, market, source, round4_(p), odds == null ? '' : odds, w == null ? '' : w, two ? 'y' : 'n', now, '', '', '']); };
    // moneyline (dog side)
    push('ML dog', 'books', f.pDog, f.dogOdds, f.nBooks, true);
    var ex = (f.exchPairs || []).length ? wmedian_(f.exchPairs) : null; push('ML dog', 'exch', ex, ex == null ? '' : toAmer_(ex), (f.exchPairs || []).length, true);
    (f.exchPairs || []).forEach(function (x) { push('ML dog', x.book, x.v, toAmer_(x.v), x.w, true); });
    if (f.bestDog) push('ML dog', 'best-book', imp_(f.bestDog.odds), f.bestDog.odds, f.bestDog.book, false);
    // props
    var P = f.props || {}; var list = [['GTD', P.gtd], ['O1.5', P.o15], ['O2.5', P.o25], ['O4.5', P.o45]];
    ['dec', 'ko', 'sub', 'itd'].forEach(function (k) { list.push(['dog ' + k.toUpperCase(), P.dog && P.dog[k]]); list.push(['fav ' + k.toUpperCase(), P.fav && P.fav[k]]); });
    list.forEach(function (it) { var m = it[0], st = it[1]; if (!st) return;
      if (typeof st.bookProb === 'number') push(m, 'books', st.bookProb, toAmer_(st.bookProb), st.n, true);
      if (typeof st.exch === 'number') push(m, 'exch', st.exch, toAmer_(st.exch), st.exchSrc, true);
      (st.srcRows || []).forEach(function (r) { if (EXCHANGE_BOOKS[r.book]) push(m, r.book, r.p, r.odds, r.w, r.two); });
      if (st.best) push(m, 'best-book', imp_(st.best.odds), st.best.odds, st.best.book, false);
    });
  });
  // replace earlier rows for the same pk
  var last = sh.getLastRow();
  if (last > 1) { var pks = sh.getRange(2, 1, last - 1, 1).getValues(); for (var i = pks.length - 1; i >= 0; i--) if (String(pks[i][0]) === String(pk)) sh.deleteRow(i + 2); }
  last = sh.getLastRow();
  if (rows.length) sh.getRange(last + 1, 1, rows.length, PROPSNAP_HDR.length).setValues(rows);
  return rows.length;
}
// fights: map normalized name -> {dog, fav, x:{method, secs}, dogWon}
function propSnapGrade_(ss, pk, fights) {
  var sh = ss.getSheetByName('PropSnap'); if (!sh || sh.getLastRow() < 2) return 0;
  var norm = function (x) { return String(x || '').toLowerCase().replace(/[^a-z]/g, ''); };
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, PROPSNAP_HDR.length).getValues(), out = [], n = 0;
  for (var i = 0; i < v.length; i++) {
    var r = v[i]; if (String(r[0]) !== String(pk)) { out.push([r[14], r[15], r[16]]); continue; }
    var fg = fights[norm(r[5])] || fights[norm(r[6])]; if (!fg) { out.push([r[14], r[15], r[16]]); continue; }
    var x = fg.x, dec = !!x.dec, ko = /ko|tko/i.test(x.method || '') && !/sub/i.test(x.method || ''), sub = /sub/i.test(x.method || ''), dw = fg.dogWon === 1, fw = fg.dogWon === 0;
    var m = String(r[7]), y;
    if (m === 'ML dog') y = dw; else if (m === 'GTD') y = dec; else if (m === 'O1.5') y = x.secs > 450; else if (m === 'O2.5') y = x.secs > 750; else if (m === 'O4.5') y = x.secs > 1350;
    else { var side = /^dog/.test(m) ? dw : fw, how = m.split(' ')[1]; y = side && (how === 'DEC' ? dec : how === 'KO' ? ko : how === 'SUB' ? sub : !dec); }
    var res = y ? 1 : 0, p = Number(r[9]);
    out.push([res, isNaN(p) ? '' : round4_(Math.pow(p - res, 2)), new Date()]); n++;
  }
  sh.getRange(2, 15, out.length, 3).setValues(out);
  return n;
}
// Scorecard: mean Brier by market group x source over every graded PropSnap row (needs ~10 cards before it means anything)
function propScorecard() {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName('PropSnap'), ui = SpreadsheetApp.getUi();
  if (!sh || sh.getLastRow() < 2) { ui.alert('No PropSnap rows yet — run Snapshot then Grade on a card first.'); return; }
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, PROPSNAP_HDR.length).getValues(), agg = {};
  v.forEach(function (r) { if (r[14] === '' || r[15] === '') return; var grp = /^ML/.test(r[7]) ? 'ML' : /^(GTD|O\d)/.test(r[7]) ? 'duration' : 'method'; var key = grp + '|' + r[8]; agg[key] = agg[key] || { n: 0, b: 0, ll: 0 }; agg[key].n++; agg[key].b += Number(r[15]); var p = Math.min(0.999, Math.max(0.001, Number(r[9]))); agg[key].ll += -(r[14] ? Math.log(p) : Math.log(1 - p)); });
  var rows = [['group', 'source', 'n', 'mean Brier', 'mean log-loss']];
  Object.keys(agg).sort().forEach(function (k) { var a = agg[k], parts = k.split('|'); rows.push([parts[0], parts[1], a.n, Math.round(a.b / a.n * 10000) / 10000, Math.round(a.ll / a.n * 10000) / 10000]); });
  var out = ss.getSheetByName('Scorecard') || ss.insertSheet('Scorecard'); out.clear(); out.getRange(1, 1, rows.length, 5).setValues(rows); out.getRange(1, 1, 1, 5).setFontWeight('bold');
  out.getRange(rows.length + 2, 1).setValue('Lower is better. Compare "books" vs "exch" (and each exchange) within a group; "best-book" is the shopped price (vig included) and should score worse on Brier but is what you bet into. Re-run after each graded card.');
  ui.alert('Scorecard written: ' + (rows.length - 1) + ' group x source lines from ' + v.filter(function (r) { return r[15] !== ''; }).length + ' graded rows.');
}

/**
 * Sheet function: row number (1-based within the range) of the fighter in `range` that best matches `name`,
 * tolerant of accents, name order, nicknames and small spelling differences. Use like
 *   =INDEX(Uploader!F:F, FIGHTERROW(B2, Uploader!B:B))
 * @customfunction
 */
function FIGHTERROW(name, range) {
  var flat = (range || []).map(function (r) { return r[0]; });
  var best = -1, bs = 0;
  for (var i = 0; i < flat.length; i++) { if (!flat[i]) continue; var sc = nameScore_(name, flat[i]); if (sc > bs) { bs = sc; best = i; } }
  return best >= 0 ? best + 1 : '';
}
/** Sheet function: the matching spelling itself. =FIGHTERNAME(B2, EventPlayerIds!E:E) @customfunction */
function FIGHTERNAME(name, range) { var r = FIGHTERROW(name, range); return r ? range[r - 1][0] : ''; }