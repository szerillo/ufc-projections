// Fixture test for the loader's grading (gradeCard + propSnapGrade_), run against an in-memory sheet.
//   node test_grading_names.js <helpers.gs> <grading.gs>     exit 0 = every case passes, 1 = at least one fails
// The .gs files are the loader's own code (verbatim v2.7 excerpt, or the patched excerpt); only the sheet, the UI and the
// ufc.com fetch are mocked. Case 1 uses the live sheet's stored Santos probabilities, so a pass reproduces the Nov 11 hand edit.
'use strict';
const fs = require('fs'), vm = require('vm');
const [helpersPath, gradingPath] = process.argv.slice(2);

function makeSheet(rows) { // rows: 2D array incl. header row
  const g = rows.map(r => r.slice());
  const cell = (r, c) => { while (g.length < r) g.push([]); const row = g[r - 1]; while (row.length < c) row.push(''); return row; };
  return {
    data: g,
    getLastRow: () => g.length, getMaxColumns: () => Math.max(84, ...g.map(r => r.length)),
    insertColumnsAfter() {}, setFrozenRows() {},
    getRange(r, c, nr = 1, nc = 1) {
      if (typeof r === 'string') { const m = /^([A-Z]+)(\d+)$/.exec(r); c = m[1].charCodeAt(0) - 64; r = +m[2]; }
      return {
        getValues: () => Array.from({ length: nr }, (_, i) => Array.from({ length: nc }, (_, j) => { const row = g[r - 1 + i] || []; const v = row[c - 1 + j]; return v === undefined ? '' : v; })),
        getValue: () => { const row = g[r - 1] || []; const v = row[c - 1]; return v === undefined ? '' : v; },
        setValues(vals) { vals.forEach((vr, i) => vr.forEach((v, j) => { cell(r + i, c + j)[c + j - 1] = v; })); return this; },
        setValue(v) { cell(r, c)[c - 1] = v; return this; },
        setFontWeight() { return this; },
      };
    },
  };
}

function runCase(tc) {
  const snapHdr = Array.from({ length: 84 }, (_, i) => 'c' + i);
  const snapRow = Array(84).fill(''); Object.entries(tc.snap).forEach(([k, v]) => { snapRow[+k] = v; });
  const sheets = {
    Feed: makeSheet([['Event', 'x'], ['pk', tc.feedPk], ['ufc.com event', tc.url]]),
    Snapshots: makeSheet([snapHdr, snapRow]),
    PropSnap: makeSheet([['pk', 'date', 'event', 'tab', 'row', 'dog', 'fav', 'market', 'source', 'prob', 'odds', 'weight/vol', 'two-way', 'snapshot time', 'result', 'Brier', 'graded']].concat(tc.prop || [])),
  };
  const alerts = [];
  const ctx = {
    console, Math, Date, String, Number, JSON, Object, Array, RegExp, isNaN, parseInt,
    SNAP_HDR: snapHdr,
    SpreadsheetApp: {
      getActive: () => ({ getSheetByName: n => sheets[n] || null, insertSheet: n => (sheets[n] = makeSheet([])) }),
      getUi: () => ({
        ButtonSet: { OK_CANCEL: 1 }, Button: { OK: 'OK' },
        prompt: (title) => ({ getSelectedButton: () => 'OK', getResponseText: () => (/card id/i.test(title) ? tc.pickPk : tc.url) }),
        alert: (m) => alerts.push(String(m)),
      }),
    },
    ufcEventCard_: () => ({ name: tc.event, date: '2026-10-31', fmid: '1', bouts: tc.bouts }),
    payout_: o => (o > 0 ? o / 100 : 100 / -o), imp_: o => (o < 0 ? -o / (-o + 100) : 100 / (o + 100)),
    toAmer_: p => (p >= 0.5 ? Math.round(-100 * p / (1 - p)) : Math.round(100 * (1 - p) / p)),
    round4_: x => Math.round(x * 10000) / 10000, validOdds_: o => typeof o === 'number' && Math.abs(o) >= 100,
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(helpersPath, 'utf8') + '\n' + fs.readFileSync(gradingPath, 'utf8'), ctx);
  vm.runInContext('gradeCard()', ctx);
  const s = sheets.Snapshots.data[1], errs = [];
  for (const [k, want] of Object.entries(tc.expectSnap)) if (s[+k] !== want) errs.push(`Snapshots col ${+k + 1}: got ${JSON.stringify(s[+k])}, want ${JSON.stringify(want)}`);
  (tc.expectProp || []).forEach(([i, res, brier]) => { const r = sheets.PropSnap.data[i]; if (r[14] !== res || r[15] !== brier) errs.push(`PropSnap row ${i + 1} (${r[7]} ${r[8]}): got result ${r[14]} Brier ${r[15]}, want ${res} / ${brier}`); });
  return { errs, alerts };
}

// ---- cases. Snapshots columns (0-based): 0 pk, 6 dog, 7 fav, 14 close, 15 Markov J, 16 model Q, 22 rec, 40 dog won, 41 GTD,
//      45/46/47 Brier close/Q/J, 56 Brier exch, 55 exch fair. PropSnap: 14 result, 15 Brier.
const santosSnap = { 0: '4427', 6: 'Yana Santos', 7: 'Luana Santos', 14: 0.27060653188180406, 15: 0.46, 16: 0.26348275862068965, 22: '-', 55: 0.271160798994846 };
const santosProp = [ // as in the live sheet: PropSnap's name columns are swapped (dog = Luana) while the prices are Yana's
  ['4427', '', '', 'Main Card', 4, 'Luana Santos', 'Yana Santos', 'ML dog', 'books', 0.2706, 270, 4, 'y', '', '', '', ''],
  ['4427', '', '', 'Main Card', 4, 'Luana Santos', 'Yana Santos', 'dog DEC', 'books', 0.524, -110, 3, 'y', '', '', '', ''],
  ['4427', '', '', 'Main Card', 4, 'Luana Santos', 'Yana Santos', 'fav DEC', 'books', 0.524, -110, 3, 'y', '', '', '', ''],
];
const santosExpect = { 40: 0, 41: 1, 45: 0.0732, 46: 0.0694, 47: 0.2116, 56: 0.0735 };
const santosPropExpect = [[1, 0, 0.0732], [2, 0, 0.2746], [3, 1, 0.2266]];
const bout = (red, blue, winner, method, round, time, redUrl, blueUrl) => ({ red, blue, winner, method, round, time, redUrl, blueUrl });
const url = 'https://www.ufc.com/event/ufc-fight-night-october-31-2026';
const CASES = [
  { name: '1 same surname: Luana (red) def. Yana (blue); sheet dog Yana', feedPk: '4427', pickPk: '4427', url, event: 'UFC Fight Night: Moicano vs Nolan',
    snap: santosSnap, prop: santosProp, bouts: [bout('Luana Santos', 'Yana Santos', 'Luana Santos', 'Decision - Unanimous', 3, '5:00', '/athlete/luana-santos', '/athlete/yana-santos')],
    expectSnap: santosExpect, expectProp: santosPropExpect },
  { name: '2 same surname, corners swapped: Yana (red), Luana (blue) wins', feedPk: '4427', pickPk: '4427', url, event: 'x',
    snap: santosSnap, prop: santosProp, bouts: [bout('Yana Santos', 'Luana Santos', 'Luana Santos', 'Decision - Unanimous', 3, '5:00', '/athlete/yana-santos', '/athlete/luana-santos')],
    expectSnap: santosExpect, expectProp: santosPropExpect },
  { name: '3 same surname, ufc.com uses another name for the dog (Yana Kunitskaya)', feedPk: '4427', pickPk: '4427', url, event: 'x',
    snap: santosSnap, prop: santosProp, bouts: [bout('Luana Santos', 'Yana Kunitskaya', 'Luana Santos', 'Decision - Unanimous', 3, '5:00', '/athlete/luana-santos', '/athlete/yana-kunitskaya')],
    expectSnap: santosExpect, expectProp: santosPropExpect },
  { name: '4 regression: Pitbull (sheet) = Freire (ufc.com) KO win as the dog', feedPk: '9697', pickPk: '9697', url, event: 'x',
    snap: { 0: '9697', 6: 'Patricio Pitbull', 7: 'Doo Ho Choi', 15: 0.39, 16: 0.3127262678803641, 22: '-' },
    bouts: [bout('Patricio Freire', 'Dooho Choi', 'Patricio Freire', 'KO/TKO', 1, '3:28', '/athlete/patricio-freire', '/athlete/dooho-choi')],
    expectSnap: { 40: 1, 41: 0, 46: 0.4723, 47: 0.3721 } },
  { name: '5 regression: different surnames, split decision for the dog', feedPk: '4427', pickPk: '4427', url, event: 'x',
    snap: { 0: '4427', 6: 'Dakota Hope', 7: 'Francis Marshall', 14: 0.4, 15: 0.45, 16: 0.42, 22: '-' },
    bouts: [bout('Francis Marshall', 'Dakota Hope', 'Dakota Hope', 'Decision - Split', 3, '5:00', '/athlete/francis-marshall', '/athlete/dakota-hope')],
    expectSnap: { 40: 1, 41: 1, 45: 0.36, 46: 0.3364, 47: 0.3025 } },
  { name: '6 card picker: Feed!B2 holds the next card (4433), grade the Oct 31 card (4427)', feedPk: '4433', pickPk: '4427', url, event: 'x',
    snap: { 0: '4427', 6: 'Dakota Hope', 7: 'Francis Marshall', 14: 0.4, 15: 0.45, 16: 0.42, 22: '-' },
    bouts: [bout('Francis Marshall', 'Dakota Hope', 'Dakota Hope', 'Decision - Split', 3, '5:00', '/athlete/francis-marshall', '/athlete/dakota-hope')],
    expectSnap: { 40: 1 } },
];
let fail = 0;
for (const tc of CASES) {
  let r; try { r = runCase(tc); } catch (e) { r = { errs: ['threw: ' + e.message], alerts: [] }; }
  console.log((r.errs.length ? 'FAIL ' : 'PASS ') + tc.name); r.errs.forEach(e => console.log('     ' + e));
  if (r.alerts.length) console.log('     alert: ' + r.alerts[r.alerts.length - 1].replace(/\n/g, ' | ').slice(0, 220));
  fail += r.errs.length ? 1 : 0;
}
console.log(fail ? `${fail} of ${CASES.length} cases failed` : `all ${CASES.length} cases passed`);
process.exit(fail ? 1 : 0);
