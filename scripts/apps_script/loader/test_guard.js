// Kirk round 28 A: plant tests for the refresh guard. Runs the loader's own loadCard_ / writeTab_ / writeCalculator_ on an
// in-memory spreadsheet; only the network (buildCard_) and the Feed/Edges writers are stubbed.
//   node test_guard.js <Code.gs>    -> one line per test, exit 1 on any FAIL
const fs = require("fs"); const file = process.argv[2] || __dirname + "/Code_v2.9_guard.gs"; const src = fs.readFileSync(file, 'utf8');
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
let SS, ALERTS, PROPS;
function fresh() { SS = {}; ['Main Card', 'Prelims', 'Calculator'].forEach(n => SS[n] = new Sheet(n)); ALERTS = []; PROPS = {}; }
global.SpreadsheetApp = { getActive: () => ({ getSheetByName: n => SS[n] || null, insertSheet: n => (SS[n] = new Sheet(n)) }),
  getUi: () => ({ alert: (a, b) => { ALERTS.push(b === undefined ? a : a + ': ' + b); return 'YES'; }, Button: { YES: 'YES', OK: 'OK' }, ButtonSet: {} }) };
global.PropertiesService = { getScriptProperties: () => ({ getProperty: () => null }), getDocumentProperties: () => ({ getProperty: k => PROPS[k] === undefined ? null : PROPS[k], setProperty: (k, v) => { PROPS[k] = v; } }) };
global.UrlFetchApp = {}; global.Utilities = { formatDate: () => '2026-11-14' }; global.Logger = { log() {} };
eval(src + `
syncLayout_ = function () {}; dkFeed_ = function () { return null; }; conformNames_ = function (f) { return f; };
writeFeed_ = function () {}; writeEdges_ = function () { return 0; }; ensureFairTable_ = function () {};
MAIN_ROWS = [2, 6]; PRE_ROWS = [2, 9];
global.__L = { loadCard_: loadCard_, setBuild: function (fn) { buildCard_ = fn; }, WARN: function () { return WARN; } };`);
const BOUTS = [['Josh Hokit', 'Ciryl Gane', 1], ['Amanda Nunes', 'Kayla Harrison', 1], ['Yousri Belgaroui', 'Caio Borralho', 1], ['Uros Medic', 'Kevin Holland', 1], ['Luis Gurule', 'Bilal Hasan', 1],
  ['Charles Radtke', 'Stephen Thompson', 0], ['Chris Duncan', 'Drew Dober', 0], ['Jim Miller', 'Terrance McKinney', 0], ['Jared Gordon', 'Melquizael Costa', 0], ['Cesar Almeida', 'Donte Johnson', 0],
  ['Bia Mesquita', 'Macy Chiasson', 0], ['Juan Diaz', 'Alatengheili', 0], ['Samuel Sanches', 'Evan Elder', 0]];
const P = { prob: null, medOdds: '' }, M = { dec: P, ko: P, sub: P, itd: P };
function fight([dog, fav, main], i, bump) { return { order: i + 1, main: !!main, tag: '155', baseTag: '155', dog, fav, pDog: 0.3, pDogOpen: 0.32, dogOdds: 233 + bump, favOdds: -233 - bump,
  bestDog: { odds: 250 + bump, book: 'FanDuel' }, bestFav: { odds: -220 - bump, book: 'DraftKings' }, props: { gtd: { prob: 0.5 }, o15: P, o25: P, o45: P, dog: M, fav: M },
  dogRec: { w: 5, fw: 3, l: 1, fl: 1 }, favRec: { w: 8, fw: 5, l: 2, fl: 1 }, weighNote: '', missDog: 0, missFav: 0, exchPairs: [], books: [], fiveR: i === 0 }; }
function card(boutsOnUfc, ext, bump) { return { pk: '334', name: 'UFC 334', date: '2026-11-14', url: 'u', bfo: 'b', ordered: false, ufcCount: boutsOnUfc.length,
  ext: ext.map(([a, b, s]) => ({ a, b, src: s })), fights: boutsOnUfc.map(b => fight(b, BOUTS.indexOf(b), bump)) }; }
const GC = BOUTS[8], ALL_EXT = BOUTS.map(([a, b]) => [a, b, 'BestFightOdds']);
const prelimRow = () => SS['Prelims'].getRange(2 + 3, 1, 1, 9).getValues()[0];    // Prelims row 5 = Gordon vs Costa
const calcRow = () => SS['Calculator'].getRange(2 + 5 + 3, 1, 1, 34).getValues()[0];
function run(c, opt) { __L.setBuild(() => JSON.parse(JSON.stringify(c))); __L.loadCard_({ pk: '334' }, Object.assign({ writeNames: false, forceOpen: false }, opt || {})); return ALERTS[ALERTS.length - 1] || ''; }
function setup() { fresh(); run(card(BOUTS, ALL_EXT, 0), { writeNames: true }); return { pre: JSON.stringify(prelimRow()), calc: JSON.stringify(calcRow()) }; }
const res = []; const ok = (name, cond, note) => res.push((cond ? 'PASS ' : 'FAIL ') + name + (note ? ' | ' + note : ''));
const minus = BOUTS.filter(b => b !== GC);
// 0 control: nothing changes, prices move 10 -> refresh writes the new price, no warning
{ const s = setup(); const a = run(card(BOUTS, ALL_EXT, 10)); ok('T0 control (13 on ufc.com, prices moved)', prelimRow()[3] === 260 && !/!!!/.test(a), 'D ' + prelimRow()[3]); }
// 1 the Nov 12 case: ufc.com mid-edit drops Gordon-Costa, BFO still lists it
{ const s = setup(); const a = run(card(minus, ALL_EXT, 10));
  const kept = JSON.stringify(prelimRow()) === s.pre && JSON.stringify(calcRow()) === s.calc;
  ok('T1 mid-edit drop, still on BFO: row kept untouched', kept, 'names ' + prelimRow()[1] + ' / ' + prelimRow()[2] + ', D ' + prelimRow()[3] + ', calc F ' + calcRow()[5]);
  ok('T1 refusal warned', /REFUSED to clear/.test(a) && /BestFightOdds/.test(a));
  ok('T1 count drop is the first line', /^!!! ufc\.com now lists 12 bouts for this card; the last load had 13/.test(a), a.split('\n')[0].slice(0, 90));
  ok('T1 other rows still refreshed', SS['Prelims'].getRange(2, 4).getValue() === 260); }
// 2 same, the only source still listing it is Novig
{ setup(); const a = run(card(minus, ALL_EXT.filter(e => e[0] !== GC[0]).concat([[GC[0], GC[1], 'Novig']]), 10));
  ok('T2 mid-edit drop, only Novig lists it: row kept', prelimRow()[1] === 'Jared Gordon' && /still listed on Novig/.test(a)); }
// 3 genuinely cancelled, BFO still lists it: refused without the override, cleared with it
{ setup(); const a = run(card(minus, ALL_EXT, 10));
  ok('T3 cancelled, still on BFO, no override: refused', prelimRow()[1] === 'Jared Gordon' && /REFUSED/.test(a));
  const a2 = run(card(minus, ALL_EXT, 10), { allowRemove: ['Costa'] });
  ok('T3 with the override (Remove a cancelled bout: Costa): cleared', prelimRow()[1] === '' && prelimRow()[2] === '' && !/REFUSED/.test(a2), 'alert: ' + a2.split('\n').filter(l => /Gordon/.test(l))[0]);
  const a3 = run(card(minus, ALL_EXT, 10));
  ok('T3 next refresh after the override: no count warning', !/!!!/.test(a3)); }
// 4 genuinely cancelled and gone from every source: cleared with the normal warning, the count drop warned once
{ setup(); const a = run(card(minus, ALL_EXT.filter(e => e[0] !== GC[0]), 10));
  ok('T4 cancelled, on no source: cleared', prelimRow()[1] === '' && /no longer on this tab/.test(a));
  ok('T4 count drop warned', /^!!! ufc\.com now lists 12/.test(a));
  const a2 = run(card(minus, ALL_EXT.filter(e => e[0] !== GC[0]), 10)); ok('T4 warned once, not every refresh', !/!!!/.test(a2)); }
// 5 the override names only one bout: another missing-but-listed bout stays held
{ setup(); const two = BOUTS.filter(b => b !== GC && b !== BOUTS[9]); const a = run(card(two, ALL_EXT, 10), { allowRemove: ['Costa'] });
  ok('T5 override is per bout (Costa removed, Almeida-Johnson still held)', prelimRow()[1] === '' && SS['Prelims'].getRange(6, 2).getValue() === 'Cesar Almeida' && /REFUSED/.test(a)); }
res.forEach(l => console.log(l)); const nf = res.filter(l => l.startsWith('FAIL')).length; console.log(file.split('/').pop() + ': ' + (res.length - nf) + '/' + res.length + ' pass'); process.exit(nf ? 1 : 0);
