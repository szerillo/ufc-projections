// Loader v2.9 refresh guard: plant tests (Kirk rounds 29-30). The loader's own buildCard_, loadCard_, writeTab_,
// writeCalculator_ and guard code run on an in-memory spreadsheet. Stubbed: the network (ufc.com event page, BFO event
// page, Novig trading page), athlete/opener pages (blank), the Feed/Edges writers and the fair-odds table layout.
//   node test_guard.js [Code.gs]    -> one line per test; exit 1 on any FAIL
const fs = require('fs'); const file = process.argv[2] || __dirname + '/Code_v2.9_guard.gs'; const src = fs.readFileSync(file, 'utf8');
function colNum(a) { let n = 0; for (const ch of a) n = n * 26 + ch.charCodeAt(0) - 64; return n; }
class Sheet { constructor(name) { this.name = name; this.d = {}; }
  getName() { return this.name; } getMaxColumns() { return 60; } insertColumnsAfter() {} clear() { this.d = {}; } getLastRow() { return 40; }
  getRange(r, c, nr, nc) { if (typeof r === 'string') { const m = /^([A-Z]+)(\d+)$/.exec(r); c = colNum(m[1]); r = +m[2]; } return new Rng(this, r, c, nr || 1, nc || 1); } }
class Rng { constructor(s, r, c, nr, nc) { Object.assign(this, { s, r, c, nr, nc }); }
  k(i, j) { return (this.r + i) + ',' + (this.c + j); }
  getValues() { const o = []; for (let i = 0; i < this.nr; i++) { const row = []; for (let j = 0; j < this.nc; j++) { const v = this.s.d[this.k(i, j)]; row.push(v === undefined ? '' : v); } o.push(row); } return o; }
  setValues(v) { for (let i = 0; i < this.nr; i++) for (let j = 0; j < this.nc; j++) this.s.d[this.k(i, j)] = v[i][j]; return this; }
  getValue() { return this.getValues()[0][0]; } setValue(v) { this.s.d[this.k(0, 0)] = v; return this; }
  clearContent() { for (let i = 0; i < this.nr; i++) for (let j = 0; j < this.nc; j++) delete this.s.d[this.k(i, j)]; return this; }
  getFormula() { return ''; } setNumberFormat() { return this; } setFontWeight() { return this; } activate() { return this; } }
let SS, ALERTS, PROPS, NET;
function fresh() { SS = {}; ['Main Card', 'Prelims', 'Calculator'].forEach(n => SS[n] = new Sheet(n)); ALERTS = []; PROPS = {}; }
global.SpreadsheetApp = { getActive: () => ({ getSheetByName: n => SS[n] || null, insertSheet: n => (SS[n] = new Sheet(n)), getSheets: () => Object.values(SS) }),
  getUi: () => ({ alert: (a, b) => { ALERTS.push(b === undefined ? a : a + ': ' + b); return 'YES'; }, Button: { YES: 'YES', OK: 'OK' }, ButtonSet: {} }) };
global.PropertiesService = { getScriptProperties: () => ({ getProperty: () => null }), getDocumentProperties: () => ({ getProperty: k => PROPS[k] === undefined ? null : PROPS[k], setProperty: (k, v) => { PROPS[k] = v; } }) };
const resp = (code, body) => ({ getResponseCode: () => code, getContentText: () => body });
global.UrlFetchApp = { fetch: (url, o) => {   // only Novig goes through here; ufc.com and BFO pages are stubbed below
  if (/trading\/UFC\/page/.test(url)) { if (NET.novig === 'down') throw new Error('Timeout: request took too long'); return resp(200, JSON.stringify({ cards: NET.novig.map(([h, a], i) => ({ type: 'game_event_card', eventId: 'e' + i, homeTeam: { name: h }, awayTeam: { name: a }, scoreboard: {} })) })); }
  return resp(200, '{"data":{"event":[]}}'); } };
global.Utilities = { formatDate: () => '2026-11-14' }; global.Logger = { log() {} };
eval(src + `
syncLayout_ = function () {}; dkFeed_ = function () { return null; }; conformNames_ = function (f) { return f; }; applyCardOrder_ = function () {};
writeFeed_ = function () {}; writeEdges_ = function () { return 0; }; ensureFairTable_ = function () {};
getAll_ = function (u) { return u.map(function () { return ''; }); };
ufcEventCard_ = function (url) { return { name: 'UFC 334: Gane vs. Hokit', date: '2026-11-14', url: url, fmid: '1', bouts: NET.ufc.map(function (b, i) { return { section: b[2] ? 'main' : 'prelims', order: i + 1, fmid: '', cls: 'Lightweight', weight: 155, women: false, title: false, red: b[0], blue: b[1], redUrl: 'r' + i, blueUrl: 'b' + i, winner: '' }; }) }; };
bfoEvent_ = function (path) { if (NET.bfo === 'down') throw new Error('HTTP 503 for https://www.bestfightodds.com' + path);
  return { books: ['FanDuel', 'Caesars'], path: path, fights: NET.bfo.map(function (p, i) { return { mu: String(i), f1: p[0], f2: p[1], slug1: 's' + i, slug2: 't' + i, ml: { FanDuel: [200 + NET.bump, -240 - NET.bump], Caesars: [190 + NET.bump, -230 - NET.bump] }, props: [] }; }) }; };
MAIN_ROWS = [2, 6]; PRE_ROWS = [2, 9];
global.__L = { loadCard_: loadCard_ };`);
const B = [['Josh Hokit', 'Ciryl Gane', 1], ['Amanda Nunes', 'Kayla Harrison', 1], ['Yousri Belgaroui', 'Caio Borralho', 1], ['Kevin Holland', 'Uros Medic', 1], ['Luis Gurule', 'Bilal Hasan', 1],
  ['Charles Radtke', 'Stephen Thompson', 0], ['Drew Dober', 'Chris Duncan', 0], ['Jim Miller', 'Terrance McKinney', 0], ['Jared Gordon', 'Melquizael Costa', 0], ['Cesar Almeida', 'Donte Johnson', 0],
  ['Macy Chiasson', 'Bia Mesquita', 0], ['Alatengheili', 'Juan Diaz', 0], ['Evan Elder', 'Samuel Sanches', 0]];
const GC = B[8], noGC = B.filter(b => b !== GC), URL = 'https://www.ufc.com/event/ufc-334';
const prelim = (r) => SS['Prelims'].getRange(r, 1, 1, 9).getValues()[0];
const snapAll = () => JSON.stringify([SS['Main Card'].d, SS['Prelims'].d, SS['Calculator'].d]);
function net(ufc, bfo, novig, bump) { NET = { ufc, bfo, novig, bump: bump || 0 }; }
function run(opt, bfoPath) { ALERTS.length = 0; __L.loadCard_({ pk: '4433', url: URL, bfo: bfoPath || '/events/ufc-334-gane-vs-hokit-4433' }, Object.assign({ writeNames: false, forceOpen: false }, opt || {})); return ALERTS.join('\n'); }
function setup(cards) { fresh(); net(cards || B, (cards || B).map(b => [b[0], b[1]]), (cards || B).map(b => [b[0], b[1]])); run({ writeNames: true }); }
const allPairs = (cards) => (cards || B).map(b => [b[0], b[1]]);
const res = []; const ok = (name, cond, note) => res.push((cond ? 'PASS ' : 'FAIL ') + name + (note ? ' | ' + String(note).slice(0, 150) : ''));
const GROW = 5;   // Prelims row 5 = Jared Gordon vs Melquizael Costa (as on the live sheet)
{ setup(); net(B, allPairs(), allPairs(), 10); const a = run(); ok('T0 control: 13 on ufc.com, prices moved, no warning', prelim(2)[3] === 210 && !/!!!/.test(a), 'D ' + prelim(2)[3]); }
{ setup(); const before = JSON.stringify(prelim(GROW)); net(noGC, allPairs(), allPairs(), 10); const a = run();
  ok('T1 Nov 12 case: dropped on ufc.com, BFO lists it -> row kept untouched', JSON.stringify(prelim(GROW)) === before && /REFUSED to clear/.test(a), prelim(GROW).slice(1, 4).join(' / '));
  ok('T1 count drop is the alert\'s first line', /^!!! ufc\.com now lists 12 bouts/.test(a), a.split('\n')[0]);
  ok('T1 the other 12 rows refreshed', prelim(2)[3] === 210); }
{ setup(); net(noGC, allPairs(noGC), allPairs(), 10); const a = run(); ok('T2 only Novig lists it -> kept', prelim(GROW)[1] === 'Jared Gordon' && /still listed on Novig/.test(a)); }
{ setup(); net(noGC, allPairs(), allPairs(), 10); const a = run(); ok('T3 cancelled, BFO still lists it, no override -> refused', prelim(GROW)[1] === 'Jared Gordon' && /REFUSED/.test(a));
  const a2 = run({ allowRemove: ['Costa'] }); ok('T3 override "Costa" -> removed', prelim(GROW)[1] === '' && /no longer on this tab/.test(a2), a2.split('\n').find(l => /Gordon/.test(l)));
  const a3 = run(); ok('T3 next refresh: no repeat warning', !/!!!/.test(a3)); }
{ setup(); net(noGC, allPairs(noGC), allPairs(noGC), 10); const a = run(); ok('T4 cancelled, on no source -> cleared, count drop warned', prelim(GROW)[1] === '' && /^!!! ufc\.com now lists 12/.test(a));
  ok('T4 warned once', !/!!!/.test(run())); }
{ setup(); const two = noGC.filter(b => b !== B[9]); net(two, allPairs(), allPairs(), 10); const a = run({ allowRemove: ['Costa'] });
  ok('T5 override is per bout (Gordon-Costa removed, Almeida-Johnson still held)', prelim(GROW)[1] === '' && prelim(GROW + 1)[1] === 'Cesar Almeida' && /REFUSED/.test(a)); }
// A: source failures
{ setup(); const s0 = snapAll(); net(noGC, 'down', allPairs(), 10); const a = run();
  ok('A1 BFO down (HTTP 503) + bout dropped -> REFUSED, nothing written', snapAll() === s0 && /REFUSED, source unreachable: BestFightOdds/.test(a), a.split('\n')[0]); }
{ setup(); const s0 = snapAll(); net(noGC, [], allPairs(), 10); const a = run();
  ok('A2 BFO returns an empty page -> REFUSED, nothing written', snapAll() === s0 && /REFUSED, source unreachable: BestFightOdds/.test(a)); }
{ setup(); const s0 = snapAll(); net(B, 'down', allPairs(), 10); const a = run();
  ok('A3 BFO down, nothing dropped -> still nothing written (no blank prices)', snapAll() === s0 && /REFUSED, source unreachable/.test(a)); }
{ setup(); const before = JSON.stringify(prelim(GROW)); net(noGC, allPairs(noGC), 'down', 10); const a = run();
  ok('A4 Novig down (timeout), BFO no longer lists it -> REFUSED, row kept', JSON.stringify(prelim(GROW)) === before && /unreachable source \(Novig/.test(a), a.split('\n').find(l => /Gordon/.test(l))); }
{ setup(); const before = JSON.stringify(prelim(GROW)); net(noGC, allPairs(noGC), [], 10); const a = run();
  ok('A5 Novig returns no events -> REFUSED, row kept', JSON.stringify(prelim(GROW)) === before && /unreachable source \(Novig/.test(a)); }
{ setup(); const s0 = snapAll(); net(noGC, 'down', 'down', 10); const a = run();
  ok('A6 both down -> REFUSED, nothing written', snapAll() === s0 && /REFUSED, source unreachable/.test(a)); }
// C: override names
{ setup(); net(noGC, allPairs(), allPairs(), 10); const a = run({ allowRemove: ['Costas'] });
  ok('C1 override with a wrong name ("Costas") -> nothing removed', prelim(GROW)[1] === 'Jared Gordon' && /matches 0 rows/.test(a), a.split('\n')[0]); }
{ const S = B.map(b => b === B[9] ? ['Cesar Costa', 'Donte Johnson', 0] : b); setup(S); const sGC = S.filter(b => b !== GC);
  net(sGC, allPairs(S), allPairs(S), 10); const a = run({ allowRemove: ['Costa'] });
  ok('C2 shared name ("Costa": Melquizael Costa and Cesar Costa) -> nothing removed', prelim(GROW)[1] === 'Jared Gordon' && prelim(GROW + 1)[1] === 'Cesar Costa' && /matches 2 rows/.test(a), a.split('\n')[0]);
  const a2 = run({ allowRemove: ['Melquizael Costa'] });
  ok('C3 same card, full name "Melquizael Costa" -> exactly that bout removed', prelim(GROW)[1] === '' && prelim(GROW + 1)[1] === 'Cesar Costa'); }
{ setup(); net(noGC, allPairs(), allPairs(), 10); const a = run({ allowRemove: ['Hokit'] });
  ok('C4 override names a bout still on ufc.com -> nothing removed, said so', prelim(GROW)[1] === 'Jared Gordon' && SS['Main Card'].getRange(2, 2).getValue() === 'Josh Hokit' && /still on ufc\.com/.test(a)); }
{ setup(); net(noGC, allPairs(), allPairs(), 10); const a = run({ allowRemove: ['ost'] });
  ok('C5 a fragment ("ost") matches no whole name -> nothing removed', prelim(GROW)[1] === 'Jared Gordon' && /matches 0 rows/.test(a)); }
// D: count memory
{ setup(); net(noGC, allPairs(), allPairs(), 10); const a = run({}, '/events/ufc-334-gane-vs-hokit-4499');
  ok('D1 BFO page id changes (BFO re-files the card as 4499) + count drop -> still warned', /^!!! ufc\.com now lists 12 bouts/.test(a), a.split('\n')[0]); }
{ setup(); const moved = [GC[0], GC[1]]; net(noGC, allPairs(noGC), allPairs(noGC).concat([moved]), 10); const a = run();
  ok('D2 bout moved to another card (Novig lists it under the other event) -> refused + count warned; override clears it',
    prelim(GROW)[1] === 'Jared Gordon' && /^!!! ufc\.com now lists 12/.test(a) && (run({ allowRemove: ['Gordon'] }), prelim(GROW)[1] === '')); }
{ setup(); const add = B.concat([['New Guy', 'Other Guy', 0]]); net(add.filter(b => b !== GC), allPairs(add), allPairs(add), 10); const a = run();
  ok('D3 one bout added and one dropped (count stays 13) -> count line silent, row-level refusal still fires', !/now lists/.test(a) && /REFUSED to clear/.test(a) && prelim(GROW)[1] === 'Jared Gordon'); }
res.forEach(l => console.log(l)); const nf = res.filter(l => l.startsWith('FAIL')).length; console.log(file.split('/').pop() + ': ' + (res.length - nf) + '/' + res.length + ' pass'); process.exit(nf ? 1 : 0);
