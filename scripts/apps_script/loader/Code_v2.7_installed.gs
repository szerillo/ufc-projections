/**
 * UFC Model — card loader (Apps Script)  v2.7  Nov 5 2026 (Snapshots archive the method layer: your AD-AJ inputs, model shares, model vs market joint method probs, 6-way method Brier)
 * v2.6.1  Oct 28 2026 (warns when ufc.com shows <6 main for a Fight Night; accepts a tab named 'Card Order')
 * v2.6  Oct 28 2026 (CardOrder tab: Tapology paste sets bout order + main/prelim split; main-card resize; hand inputs follow the fight)
 * v2.5.5  Oct 22 2026 (NOVIG_PROXY relay option; Novig 403s Google-origin POSTs)
 * v2.5.4  Oct 22 2026 (Novig: graphql errors surfaced; numeric-string prices accepted; ML/total fallback from the trading page)
 * v2.5.3  Oct 22 2026 (UFC > Test Novig connection diagnostic)
 * v2.5.2  Oct 22 2026 (refresh re-orients dog/fav on rows that were never priced)
 * v2.5.1  Oct 22 2026 (BFO markup change: first fighter row now carries data-admin-matchup — regex loosened; this blanked every price on UFC 333)
 * v2.5  Oct 16 2026 (PropSnap tab: every market x source archived at the close, graded, Scorecard menu)
 * v2.4  Oct 16 2026 (Novig pulled directly: ML, GTD, O/U, method per fight; weight by $ traded)
 * v2.3.1  Oct 16 2026 (EXCH_PROP_W: exchange quotes blended into every prop number incl. the method table)
 * v2.3  Oct 16 2026 (exchange reference: Novig x2 / Polymarket / Kalshi -> Calculator AG, ML outliers AH, manual Novig AI; prop outliers in Feed; exch Brier in Snapshots)
 * v2.2.1  Oct 16 2026 (prop median taken in probability space — a +150/-170 pair no longer prints "-9")
 * v2.2  Oct 15 2026 (BFO split-card merge; rows keep ufc.com bout order)
 * v2.1  Oct 12 2026 (snapshot fix; results + weigh-ins from ufc.com live feed)
 * previously: v2.0  Oct 7 2026  — sources: ufc.com + BestFightOdds (fightodds.io API closed Oct 2026)
 *
 * Install once: Extensions ▸ Apps Script ▸ paste this whole file over Code.gs ▸ Save ▸ reload the sheet.
 * A "UFC" menu appears. "Load next UFC card" fills every market input the model needs. Sources (v2.0, Oct 2026):
 *   ufc.com        -> upcoming events, bout order / main-card vs prelims, weight class (women/5R tags), fighter records
 *                     (career W-L, KO/Sub wins, finish losses from UFC history), per-15 stats, and RESULTS for grading
 *   BestFightOdds  -> per-book moneylines + props (event page) and the OPENING line (fighter page)
 *   (fightodds.io's API went behind bot protection in Oct 2026 and is no longer used.)
 *
 *   Main Card / Prelims : A weight tag ("125-5", "w115"), B dog, C fav, D/I = BEST bettable price (vig included, so Edge = EV at your price),
 *                         S listed GTD, T listed ITD, N14:R27 MARKET method odds (DEC/KO/SUB/ITD, dog row then fav row)
 *                         next to YOUR fair-odds table in H14:L27 (formulas, never overwritten), edges in S14:V27
 *   Edges               : F Win Odds, H/J/L Dec/KO/SUB market odds filled by fighter name
 *   Calculator          : F dog OPEN % (median de-vigged opener → drives DRIFT + MOMENTUM), N O2.5 listed,
 *                         R O1.5 listed, X/Y fighter finish layer from career records (K=5 toward division rate),
 *                         AC/AD consensus no-vig line | best price + book (line-shopping), AE O4.5 listed (5R only)
 *   Feed                : raw dump (every book, open + current, every prop used) for the Archive / audits
 *
 * Snapshot card (run when the card starts) stamps every fight — market close, your Q/Markov/X/Y/flags/bet recs — into
 * the Snapshots tab. Grade last card pulls results from the ufc.com event page, scores every snapshot row (Brier close vs Q vs
 * Markov, rec P/L) and fills Closing Odds / CLV / Result / P-L in the Archive CLV table for any bet you logged there
 * (Bet text just needs a fighter's last name, plus GTD / ITD / over 2.5 / under 1.5 / over 4.5 for non-ML bets).
 *
 * Nothing model-side is touched: G/H/Q/AA formulas, Markov col J, Tap/Junk C/D, sharp blend E, K codes stay yours.
 * Re-run any time before the card to refresh prices; F (opener) is only written if it is blank, so the true
 * opener survives refreshes. "Force refresh openers" overwrites it.
 */


// Books excluded from consensus/open (exchanges & prediction markets: thin, junk openers). Edit freely.
var EXCLUDE_BOOKS = ['Polymarket', 'Kalshi', 'ProphetX', 'SXBet', '4casters', '4Cx', 'Novig', 'Sporttrade'];
// v2.3 — EXCHANGE REFERENCE. Exchanges / prediction markets are kept out of the book consensus (above) but form their own
// de-vigged reference line ("exch fair"); every bettable book is then compared to it to find OUTLIERS. Weights are
// relative (Novig counts double). Novig is not on BestFightOdds: paste its dog/fav moneyline into Calculator AI (e.g. "+118/-130")
// and it is folded into exch fair on the next refresh. Outlier classes follow Alpha Map 2h: 1–3 pts better than the reference
// = value (+4%), 4+ pts = stale/informed line, treat as a trap, not an edge.
var EXCHANGE_BOOKS = { 'Novig': 2, 'Polymarket': 1, 'Kalshi': 1 };
var OUTLIER_MIN = 0.01, OUTLIER_TRAP = 0.04;
// Weight of the exchange quote inside every PROP number the sheet reads (listed GTD/ITD, O1.5/O2.5/O4.5, the N14:R27 method
// table that the v4.5 KO:SUB anchor pulls toward). 0 = books only, 1 = exchange only when one quotes the market. The book-only
// number is kept in the Feed so the two can be graded against each other.
var EXCH_PROP_W = 0.5;
var NOVIG_ON = true;   // pull Novig markets directly (api.novig.us); set false to skip
// Novig's edge returns 403 to POSTs from Google's servers (GETs are fine), so the per-fight markets call needs a relay.
// Deploy novig_proxy_worker.js on Cloudflare Workers (free) and put its URL here; leave '' to fall back to ML + round total
// from the trading page (no GTD / method quotes from Novig in that mode).
function SP_(k, d) { var v = PropertiesService.getScriptProperties().getProperty(k); return v == null || v === '' ? d : v; }   // settings kept out of the code
var NOVIG_PROXY = SP_('NOVIG_PROXY', ''), NOVIG_PROXY_KEY = SP_('NOVIG_PROXY_KEY', '');   // Script Properties (Project Settings), not code
// Books you can actually bet — best price is searched only among these. Edit to your accounts.
var BETTABLE_BOOKS = JSON.parse(SP_('BETTABLE_BOOKS', '["DraftKings", "FanDuel", "BetMGM", "Caesars", "BetRivers", "HardRockBet", "Fanatics", "ESPNBet"]'));   // your accounts: Script Property BETTABLE_BOOKS (a JSON list)

var MAIN_TYPES = { ME: 1, CO: 1, MC: 1 };      // fightodds fightType codes that belong on the Main Card tab
var MAIN_ROWS = [2, 7];                        // Main Card fight rows (Calculator rows 2-7)
var PRE_ROWS = [2, 11];                        // Prelims fight rows (Calculator rows 8-17); change with UFC > Resize prelims
// Main-card size: numbered events (UFC 332) run 5 fights, Fight Nights run 6. fightodds sometimes tags one more as MC;
// anything beyond the cap goes to the top of the prelims.
function maxMain_(eventName) { return /^UFC\s*\d/.test(String(eventName || '').trim()) ? 5 : 6; }
var TABLE_ROW0 = 14;                           // method-odds table starts here on both tabs (H:L)

// The Calculator decides the layout: rows whose col A links to 'Main Card' are main-card rows, rows linking to
// Prelims are prelim rows. Called before anything that reads/writes by row so MAIN_ROWS follows the sheet.
function syncLayout_(ss) {
  var calc = ss.getSheetByName('Calculator'); if (!calc) return;
  var f = calc.getRange(2, 1, 40, 1).getFormulas(), firstPre = -1, lastLink = 1;
  for (var i = 0; i < f.length; i++) { var x = f[i][0] || ''; if (/Prelims!/.test(x) && firstPre < 0) firstPre = i + 2; if (/Prelims!|Main Card/.test(x)) lastLink = i + 2; }
  if (firstPre > 2) MAIN_ROWS = [2, firstPre - 1];
}

function onOpen() {
  SpreadsheetApp.getUi().createMenu('UFC')
    .addItem('Load next UFC card', 'loadNextCard')
    .addItem('Load card by ufc.com URL…', 'loadCardByPk')
    .addItem('Refresh prices (keep openers)', 'refreshPrices')
    .addItem('Force refresh openers too', 'refreshAll')
    .addSeparator()
    .addItem('Snapshot card → Snapshots (run at close)', 'snapshotCard')
    .addItem('Grade last card (results + CLV)', 'gradeCard')
    .addItem('Scorecard: exchanges vs books (PropSnap)', 'propScorecard')
    .addItem('Test Novig connection', 'testNovig')
    .addSeparator()
    .addItem('Repair fair-odds tables (H14:L27)', 'repairFairTables')
    .addItem('Conform fighter names to DK feed', 'conformNamesMenu')
    .addItem('Resize prelims rows (extend formulas)', 'resizePrelimsMenu')
    .addItem('Set main-card rows (5 / 6)…', 'setMainRowsMenu')
    .addItem('Paste bout order (Tapology) → CardOrder tab', 'cardOrderMenu')
    .addItem('Relink rows (after inserting/deleting rows)', 'relinkRowsMenu')
    .addToUi();
}

// ---------------------------------------------------------------- menu entry points
function loadNextCard() {
  var ev = pickUpcomingEvent_();
  if (!ev) return;
  loadCard_(ev, { writeNames: true, forceOpen: false });
}
function loadCardByPk() {
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('ufc.com event URL', 'e.g. https://www.ufc.com/event/ufc-333 (the BFO page is found automatically):', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  loadCard_({ url: r.getResponseText().trim() }, { writeNames: true, forceOpen: false });
}
function refreshPrices() {
  var ev = currentEvent_(); if (!ev) return;
  loadCard_(ev, { writeNames: false, forceOpen: false });
}
function refreshAll() {
  var ev = currentEvent_(); if (!ev) return;
  loadCard_(ev, { writeNames: false, forceOpen: true });
}
function currentPk_() { var ev = currentEvent_(); return ev ? ev.pk : null; }
function currentEvent_() {
  var feed = SpreadsheetApp.getActive().getSheetByName('Feed');
  var pk = feed ? feed.getRange('B2').getValue() : '', url = feed ? String(feed.getRange('B3').getValue()) : '', bfo = feed ? String(feed.getRange('D3').getValue()) : '';
  if (!url) { SpreadsheetApp.getUi().alert('No card loaded yet — use "Load next UFC card" first.'); return null; }
  return { pk: pk, url: url, bfo: bfo };
}

// ---------------------------------------------------------------- odds math
function imp_(o) { o = Number(o); return o < 0 ? -o / (-o + 100) : 100 / (o + 100); }
function toAmer_(p) { if (!(p > 0 && p < 1)) return ''; return p >= 0.5 ? Math.round(-100 * p / (1 - p)) : Math.round(100 * (1 - p) / p); }
function median_(a) { a = a.filter(function (x) { return typeof x === 'number' && !isNaN(x); }).sort(function (x, y) { return x - y; }); if (!a.length) return null; var m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; }
function validOdds_(o) { return typeof o === 'number' && Math.abs(o) >= 100 && Math.abs(o) < 20000; }
function fmtDate_(d) { return Utilities.formatDate(d, 'UTC', 'yyyy-MM-dd'); }
function payout_(o) { return o > 0 ? o / 100 : 100 / -o; }
function included_(book) { return EXCLUDE_BOOKS.indexOf(book) < 0; }
function bettable_(book) { return BETTABLE_BOOKS.indexOf(book) >= 0; }
function devig2_(a, b) { var pa = imp_(a), pb = imp_(b); return pa / (pa + pb); }
// weighted median of [{v, w}]
function wmedian_(pairs) {
  pairs = pairs.filter(function (p) { return typeof p.v === 'number' && !isNaN(p.v); }).sort(function (a, b) { return a.v - b.v; });
  if (!pairs.length) return null; var tot = 0, acc = 0, i; for (i = 0; i < pairs.length; i++) tot += pairs[i].w;
  for (i = 0; i < pairs.length; i++) { acc += pairs[i].w; if (acc >= tot / 2) return pairs[i].v; } return pairs[pairs.length - 1].v;
}
// Exchange reference for a two-way market: rows [{book, o1, o2}] -> {p (side-1 prob), pairs, src} or null
function exchFair_(rows) {
  var pr = []; rows.forEach(function (r) { var w = EXCHANGE_BOOKS[r.book]; if (!w) return; if (typeof r.w === 'number') w = r.w; if (validOdds_(r.o1) && validOdds_(r.o2)) pr.push({ v: devig2_(r.o1, r.o2), w: w, book: r.book }); });
  if (!pr.length) return null; return { p: wmedian_(pr), pairs: pr, src: pr.map(function (x) { return x.book; }).join('+') };
}
// Bettable-book prices that beat the reference: delta = ref prob − implied(book price), i.e. EV at that book in prob points
function outliers_(rows, ref) {
  var out = []; if (ref == null) return out;
  rows.forEach(function (r) {
    if (!bettable_(r.book)) return;
    if (validOdds_(r.o1)) { var d = ref - imp_(r.o1); if (d >= OUTLIER_MIN) out.push({ book: r.book, odds: r.o1, side: 1, delta: d }); }
    if (validOdds_(r.o2)) { var d2 = (1 - ref) - imp_(r.o2); if (d2 >= OUTLIER_MIN) out.push({ book: r.book, odds: r.o2, side: 2, delta: d2 }); }
  });
  return out.sort(function (a, b) { return b.delta - a.delta; });
}
function fmtOutl_(o, n1, n2) { return (o.side === 1 ? n1 : n2) + ' ' + fmtOdds_(o.odds) + ' ' + o.book + ' (' + (o.delta >= 0 ? '+' : '') + (Math.round(o.delta * 1000) / 10) + (o.delta >= OUTLIER_TRAP ? ' TRAP' : '') + ')'; }


// ---------------------------------------------------------------- fighter-name reconciliation
// The DK feed (EventPlayerIds col E/G) is the naming authority for Uploader/Edges lookups; fightodds spellings are
// conformed to it when the loader writes names ("Yasmine Jauregui" -> "Yazmin Jauregui", "Heili Alateng" -> "Alateng Heili").
var NAME_ALIASES = { 'patriciopitbull': 'patriciofreire', 'pitbull': 'freire', 'joshuavan': 'joshvan', 'ozzydiaz': 'osmandiaz' };   // add as they come up: normalized -> normalized
function nkey_(s) {
  s = String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\b(jr|sr|ii|iii)\b\.?/g, '').replace(/[^a-z ]/g, ' ').replace(/\s+/g, ' ').trim();
  var joined = s.replace(/ /g, ''); if (NAME_ALIASES[joined]) return { key: NAME_ALIASES[joined], toks: [NAME_ALIASES[joined]] };
  return { key: joined, toks: s.split(' ').filter(Boolean) };
}
function editDist_(a, b) { var m = [], i, j; for (i = 0; i <= a.length; i++) { m[i] = [i]; } for (j = 0; j <= b.length; j++) m[0][j] = j;
  for (i = 1; i <= a.length; i++) for (j = 1; j <= b.length; j++) m[i][j] = Math.min(m[i - 1][j] + 1, m[i][j - 1] + 1, m[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)); return m[a.length][b.length]; }
// 0 = no match, 3 = exact, 2 = same tokens any order / alias, 1 = same last token + similar first token
function nameScore_(a, b) {
  var A = nkey_(a), B = nkey_(b); if (!A.key || !B.key) return 0; if (A.key === B.key) return 3;
  var sa = A.toks.slice().sort().join(''), sb = B.toks.slice().sort().join(''); if (sa === sb) return 2;
  var la = A.toks[A.toks.length - 1], lb = B.toks[B.toks.length - 1];
  var lastHit = la === lb || A.toks.indexOf(lb) >= 0 || B.toks.indexOf(la) >= 0 || (la.length > 4 && lb.length > 4 && editDist_(la, lb) <= 1);
  if (!lastHit) return 0;
  if (A.toks.length === 1 || B.toks.length === 1) return 1;
  var fa = A.toks[0], fb = B.toks[0];
  return (fa === fb || editDist_(fa, fb) <= 2 || fa.slice(0, 3) === fb.slice(0, 3)) ? 1 : 0;
}
function bestName_(name, candidates) { var best = null, bs = 0; candidates.forEach(function (c) { var sc = nameScore_(name, c); if (sc > bs) { bs = sc; best = c; } }); return bs > 0 ? best : null; }
// DK feed: EventPlayerIds rows -> [{name, opp}]
function dkFeed_(ss) {
  var sh = ss.getSheetByName('EventPlayerIds'); if (!sh || sh.getLastRow() < 2) return [];
  var v = sh.getRange(2, 5, sh.getLastRow() - 1, 3).getValues();
  return v.filter(function (r) { return r[0]; }).map(function (r) { return { name: String(r[0]).trim(), opp: String(r[2] || '').trim() }; });
}
// Conform a fight's names to the DK feed; warn when DK pairs the fighter with someone else.
function conformNames_(f, dk) {
  if (!dk.length) return f;
  var names = dk.map(function (d) { return d.name; });
  var d = bestName_(f.dog, names), v = bestName_(f.fav, names);
  var g = {}; for (var k in f) g[k] = f[k];
  if (d) g.dog = d; if (v) g.fav = v;
  var row = dk.filter(function (x) { return x.name === (d || v); })[0];
  if (row && row.opp) { var other = d ? v : d; var oppHit = nameScore_(row.opp, d ? f.fav : f.dog) > 0; if (!oppHit) WARN.push('DK feed pairs ' + row.name + ' with ' + row.opp + '; fightodds has ' + f.dog + ' vs ' + f.fav + ' — check the booking.'); }
  if (!d) WARN.push('Not in DK feed: ' + f.dog); if (!v) WARN.push('Not in DK feed: ' + f.fav);
  return g;
}


// ================================================================ SOURCES (v2): ufc.com + BestFightOdds
// ufc.com: upcoming events, bout order/sections/weight classes, athlete records + stats, results after the card.
// BestFightOdds: per-book moneylines + props on the event page, opening line on the fighter page.
var UA_ = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9' };
function get_(url) { var r = UrlFetchApp.fetch(url, { muteHttpExceptions: true, followRedirects: true, headers: UA_ }); if (r.getResponseCode() !== 200) throw new Error('HTTP ' + r.getResponseCode() + ' for ' + url); return r.getContentText(); }
function getAll_(urls) { return UrlFetchApp.fetchAll(urls.map(function (u) { return { url: u, muteHttpExceptions: true, followRedirects: true, headers: UA_ }; })).map(function (r) { return r.getResponseCode() === 200 ? r.getContentText() : ''; }); }
function ent_(s) { return String(s || '').replace(/&#0?39;|&rsquo;|&#8217;/g, "'").replace(/&amp;/g, '&').replace(/&#189;|&frac12;/g, '½').replace(/&nbsp;/g, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); }

// ---- ufc.com
function ufcUpcoming_() {
  var h = get_('https://www.ufc.com/events'), out = [], seen = {};
  var re = /c-card-event--result__headline">\s*<a href="([^"]+)">([^<]+)<\/a>[\s\S]{0,400}?c-card-event--result__date[^>]*>\s*(?:<a[^>]*>)?\s*([^<]{6,60})</g, m;
  while ((m = re.exec(h))) { var url = m[1].indexOf('http') === 0 ? m[1] : 'https://www.ufc.com' + m[1]; if (seen[url]) continue; seen[url] = 1; out.push({ url: url, name: ent_(m[2]), when: ent_(m[3]) }); }
  // the list has upcoming first, then past; keep the ones whose date is today or later (within 60 days)
  var now = new Date(), keep = [];
  out.forEach(function (e) { var d = parseUfcDate_(e.when); if (d && d.getTime() > now.getTime() - 36e5 * 6 && d.getTime() < now.getTime() + 60 * 864e5) { e.date = fmtDate_(d); keep.push(e); } });
  return keep;
}
function parseUfcDate_(s) { var m = /([A-Z][a-z]{2}),\s*([A-Z][a-z]{2})\s+(\d{1,2})/.exec(s || ''); if (!m) return null; var mon = 'JanFebMarAprMayJunJulAugSepOctNovDec'.indexOf(m[2]) / 3; var now = new Date(); var y = now.getFullYear(); var d = new Date(y, mon, +m[3]); if (d.getTime() < now.getTime() - 120 * 864e5) d = new Date(y + 1, mon, +m[3]); if (d.getTime() > now.getTime() + 300 * 864e5) d = new Date(y - 1, mon, +m[3]); return d; }

function pickUpcomingEvent_() {
  var evs = ufcUpcoming_().filter(function (e) { return !/BJJ|Contender|Road to UFC/i.test(e.name + e.url); });
  if (!evs.length) { SpreadsheetApp.getUi().alert('No upcoming UFC event found on ufc.com/events.'); return null; }
  if (evs.length === 1) return evs[0];
  var ui = SpreadsheetApp.getUi();
  var msg = evs.slice(0, 6).map(function (n, i) { return (i + 1) + ') ' + n.date + '  ' + n.name; }).join('\n');
  var r = ui.prompt('Which card?', msg + '\n\nEnter a number (default 1):', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return null;
  var k = parseInt(r.getResponseText() || '1', 10) - 1;
  return evs[Math.max(0, Math.min(evs.length - 1, k))];
}

// Event page -> {name, date, bouts:[{section, order, cls, weight, women, title, red, blue, redUrl, blueUrl, winner, method, round, time}]}
function ufcEventCard_(url) {
  var h = get_(url);
  var name = ent_((h.match(/<title>([^<]+)<\/title>/) || ['', ''])[1]).replace(/\s*\|\s*UFC\s*$/, '');
  var when = ent_((h.match(/c-hero__headline-suffix[^>]*>\s*([^<]+)</) || h.match(/(Sat|Fri|Sun|Thu|Wed), [A-Z][a-z]{2} \d{1,2}/) || ['', ''])[1] || (h.match(/((Sat|Fri|Sun|Thu|Wed), [A-Z][a-z]{2} \d{1,2})/) || ['', ''])[1]);
  var d = parseUfcDate_(when); var date = d ? fmtDate_(d) : '';
  var secIdx = [['main', h.indexOf('id="main-card"')], ['prelims', h.indexOf('id="prelims-card"')], ['early', h.indexOf('id="early-prelims"')]].filter(function (x) { return x[1] >= 0; }).sort(function (a, b) { return a[1] - b[1]; });
  var parts = h.split('<div class="c-listing-fight" '), bouts = [], pos = 0, order = 0;
  for (var i = 1; i < parts.length; i++) {
    pos = h.indexOf('<div class="c-listing-fight" ', pos + 1);
    var b = parts[i]; var sec = 'main'; for (var k = 0; k < secIdx.length; k++) if (secIdx[k][1] < pos) sec = secIdx[k][0];
    var cls = ent_((b.match(/c-listing-fight__class-text">([^<]+)</) || ['', ''])[1]);
    var names = [], urls = [], re = /c-listing-fight__corner-name--(red|blue)">\s*<a href="([^"]+)">([\s\S]*?)<\/a>/g, m;
    while ((m = re.exec(b))) { urls.push(m[2]); names.push(ent_(m[3])); }
    if (names.length < 2) continue;
    var outcomes = [], re2 = /c-listing-fight__outcome--(win|loss|draw|no-contest)/g; while ((m = re2.exec(b))) outcomes.push(m[1]);
    var rt = function (c) { return ent_((b.match(new RegExp('c-listing-fight__result-text ' + c + '[^>]*>([^<]*)<')) || ['', ''])[1]); };
    var winner = outcomes[0] === 'win' ? names[0] : (outcomes[1] === 'win' ? names[1] : '');
    var lw = cls.toLowerCase(), weight = /straw/.test(lw) ? 115 : /flyweight/.test(lw) ? 125 : /bantam/.test(lw) ? 135 : /feather/.test(lw) ? 145 : /lightweight/.test(lw) ? 155 : /welter/.test(lw) ? 170 : /middle/.test(lw) ? 185 : /light heavy/.test(lw) ? 205 : /heavy/.test(lw) ? 265 : 'CW';
    order++;
    bouts.push({ section: sec, order: order, fmid: (b.match(/^data-fmid="(\d+)"/) || ['', ''])[1], cls: cls, weight: weight, women: /women/i.test(cls), title: /title/i.test(cls), red: names[0], blue: names[1], redUrl: urls[0], blueUrl: urls[1], winner: winner, method: rt('method'), round: parseInt(rt('round'), 10) || null, time: rt('time'), weighRed: null, weighBlue: null });
  }
  var evc = { name: name, date: date, url: url, fmid: (h.match(/"event_fmid":"(\d+)"/) || ['', ''])[1], bouts: bouts };
  ufcLiveEnrich_(evc);
  return evc;
}

// ufc.com's live-stats feed (the JSON the event page itself polls). Has official weigh-in weights for every fighter
// and the result (winner / method / round / time) the moment a fight is final — the static event HTML can lag results
// by days (CDN cache), which is what broke grading on Oct 10 2026.
function ufcLive_(fmid) {
  if (!fmid) return null;
  try {
    var r = UrlFetchApp.fetch('https://d29dxerjsp82wz.cloudfront.net/api/v3/event/live/' + fmid + '.json', { muteHttpExceptions: true, headers: UA_ });
    if (r.getResponseCode() !== 200) return null;
    var j = JSON.parse(r.getContentText()); return j && j.LiveEventDetail ? j.LiveEventDetail : null;
  } catch (e) { WARN.push('ufc.com live feed: ' + e.message); return null; }
}
function ufcLiveEnrich_(evc) {
  var live = ufcLive_(evc.fmid); if (!live || !live.FightCard) return;
  var byId = {}; live.FightCard.forEach(function (f) { byId[String(f.FightId)] = f; });
  evc.bouts.forEach(function (b) {
    var f = byId[b.fmid];
    if (!f) { for (var i = 0; i < live.FightCard.length; i++) { var x = live.FightCard[i], fs = x.Fighters || []; if (fs.length === 2 && ((nameScore_(fs[0].Name.FirstName + ' ' + fs[0].Name.LastName, b.red) && nameScore_(fs[1].Name.FirstName + ' ' + fs[1].Name.LastName, b.blue)) || (nameScore_(fs[1].Name.FirstName + ' ' + fs[1].Name.LastName, b.red) && nameScore_(fs[0].Name.FirstName + ' ' + fs[0].Name.LastName, b.blue)))) { f = x; break; } } }
    if (!f || !f.Fighters || f.Fighters.length !== 2) return;
    var fs = f.Fighters; var redIdx = (fs[0].Corner === 'Red' || nameScore_(fs[0].Name.FirstName + ' ' + fs[0].Name.LastName, b.red)) ? 0 : 1;
    var red = fs[redIdx], blue = fs[1 - redIdx];
    b.weighRed = typeof red.WeighIn === 'number' ? red.WeighIn : null; b.weighBlue = typeof blue.WeighIn === 'number' ? blue.WeighIn : null;
    if (f.Status === 'Final' && f.Result && f.Result.Method && !b.winner) {
      var ro = red.Outcome && red.Outcome.Outcome, bo = blue.Outcome && blue.Outcome.Outcome;
      b.winner = ro === 'Win' ? b.red : (bo === 'Win' ? b.blue : '');
      b.method = f.Result.Method; b.round = f.Result.EndingRound || b.round; b.time = f.Result.EndingTime || b.time;
      b.liveResult = true;
    }
  });
}
// Weigh-in overage vs the contracted limit (non-title: limit + 1 lb allowance; title: the limit). 'CW' and unknown -> null.
function missLbs_(weighIn, limit, title) {
  if (typeof weighIn !== 'number' || typeof limit !== 'number') return null;
  var over = weighIn - (title ? limit : limit + 1); return over > 0 ? Math.round(over * 100) / 100 : 0;
}

// Athlete page -> record + finish counts (career W/L + KO/Sub wins; finish losses from the UFC-history lines) + stat line
function ufcAthlete_(h) {
  var out = { w: 0, fw: 0, l: 0, fl: 0, stats: '' };
  if (!h) return out;
  var rec = /(\d+)-(\d+)-(\d+)\s*\(W-L-D\)/.exec(h); if (rec) { out.w = +rec[1]; out.l = +rec[2]; }
  var num = function (label) { var m = new RegExp('athlete-stats__stat-numb">\\s*(\\d+)\\s*<\\/p>\\s*<p class="athlete-stats__text athlete-stats__stat-text">\\s*' + label).exec(h); return m ? +m[1] : 0; };
  out.fw = num('Wins by Knockout') + num('Wins by Submission');
  var re = /<p>\s*<strong>[^<]*<\/strong>\s*\([^)]*\)\s*([^<]{10,300})<\/p>/g, m, fl = 0;
  while ((m = re.exec(h))) { var t = m[1].toLowerCase(); if (/\b(lost|was knocked out|was stopped|was submitted|was finished|tapped)\b/.test(t) && !/decision/.test(t)) fl++; }
  out.fl = Math.min(fl, out.l);
  var st = function (label) { var r = new RegExp('c-stat-compare__number">\\s*([\\d.]+)[\\s\\S]{0,300}?c-stat-compare__label">\\s*' + label).exec(h); return r ? r[1] : ''; };
  var kd = (h.match(/c-overlap__stats-value">\s*([\d.]+)\s*<[\s\S]{0,200}?Knockdown Avg/) || h.match(/([\d.]+)\s*<\/div>\s*<div[^>]*>\s*Knockdown Avg/) || ['', ''])[1];
  var avg = (h.match(/(\d{1,2}:\d{2})\s*<[\s\S]{0,200}?Average fight time/) || ['', ''])[1];
  out.stats = ['SLpM ' + st('Sig\\. Str\\. Landed'), 'SApM ' + st('Sig\\. Str\\. Absorbed'), 'TD15 ' + st('Takedown avg'), 'TDD ' + st('Takedown Defense') + '%', 'Sub15 ' + st('Submission avg'), 'KD15 ' + kd, 'avg ' + avg].join(' | ');
  return out;
}

// ---- BestFightOdds
function bfoCandidates_(dateStr) {
  var h = get_('https://www.bestfightodds.com/'), out = [], seen = {};
  var re = /<a href="(\/events\/[^"]+)"><h1>([^<]*?) Odds<\/h1><\/a><span class="table-header-date">([A-Z][a-z]+) (\d{1,2})[a-z]{2}<\/span>/g, m;
  while ((m = re.exec(h))) { if (seen[m[1]]) continue; seen[m[1]] = 1; if (!/^UFC/i.test(m[2]) || /BJJ/i.test(m[2])) continue; var mon = 'JanFebMarAprMayJunJulAugSepOctNovDec'.indexOf(m[3].slice(0, 3)) / 3; out.push({ path: m[1], name: m[2], month: mon, day: +m[4] }); }
  if (!dateStr) return out;
  var d = new Date(dateStr + 'T12:00:00Z');
  var near = out.filter(function (e) { var dd = new Date(Date.UTC(d.getUTCFullYear(), e.month, e.day)); return Math.abs(dd - d) <= 2 * 864e5; });
  near.forEach(function (e) { e.near = true; });
  return near.concat(out.filter(function (e) { return near.indexOf(e) < 0; }));
}
// Event page -> {books:[names], fights:[{mu, f1, f2, slug1, slug2, ml:{book:[o1,o2]}, props:[{name, odds:{book:o}}]}]}
function bfoEvent_(path) {
  var h = get_('https://www.bestfightodds.com' + path);
  var tables = h.split(/<table[^>]*class="odds-table[^"]*"[^>]*>/); var t = tables[tables.length - 1];
  var thead = (t.match(/<thead>[\s\S]*?<\/thead>/) || [''])[0], books = [], bm;
  var reB = /<th scope="col" data-b="(\d+)"[^>]*>\s*<a[^>]*>([^<]+)<\/a>/g; while ((bm = reB.exec(thead))) books.push(ent_(bm[2]));
  var body = t.slice(t.indexOf('<tbody>')); var rows = body.split('<tr'); rows.shift();
  var fights = [], cur = null, pending = null;
  rows.forEach(function (r) {
    var isPr = /^\s*class="pr"/.test(r); var th = (r.match(/<th scope="row"[^>]*>([\s\S]*?)<\/th>/) || ['', ''])[1];   // v2.5.1: first row of each pair now carries data-admin-matchup="…"
    var cells = []; var reC = /<td([^>]*)>([\s\S]*?)<\/td>/g, cm; while ((cm = reC.exec(r))) cells.push([cm[1], cm[2]]);
    var odds = {}; for (var c = 1; c < cells.length && c - 1 < books.length; c++) { var sp = /<span[^>]*>\s*([+-]\d+)\s*<\/span>/.exec(cells[c][1]); if (sp) odds[books[c - 1]] = +sp[1]; }
    if (!isPr) {
      var fm = /\/fighters\/([^"]+)"[^>]*>\s*<span[^>]*>([^<]+)</.exec(th); if (!fm) return;
      var name = ent_(fm[2]), slug = fm[1], mu = (r.match(/data-admin-matchup="(\d+)"/) || r.match(/matchups\/(\d+)/) || r.match(/data-li="\[\d+,\d,(\d+)\]/) || ['', ''])[1];
      if (!pending) { pending = { mu: mu, f1: name, slug1: slug, o1: odds }; }
      else { cur = { mu: pending.mu || mu, f1: pending.f1, f2: name, slug1: pending.slug1, slug2: slug, ml: {}, props: [] }; Object.keys(pending.o1).forEach(function (b) { cur.ml[b] = [pending.o1[b], null]; }); Object.keys(odds).forEach(function (b) { cur.ml[b] = cur.ml[b] || [null, null]; cur.ml[b][1] = odds[b]; }); fights.push(cur); pending = null; }
    } else if (cur) { cur.props.push({ name: ent_(th), odds: odds }); }
  });
  return { books: books, fights: fights, path: path };
}
// Fighter page -> opening odds for the given event path: [openF, openOpp] (American)
function bfoOpen_(h, eventPath) {
  if (!h) return null; var i = h.indexOf('href="' + eventPath + '"'); if (i < 0) return null;
  var seg = h.slice(i, i + 4000); var re = /oppcell"><a href="\/fighters\/[^"]+">([^<]+)<\/a><\/t[dh]><td class="moneyline"[^>]*><span[^>]*>([+-]\d+)<\/span>/g, m, out = [];
  while ((m = re.exec(seg)) && out.length < 2) out.push({ name: ent_(m[1]), open: +m[2] });
  return out.length === 2 ? out : null;
}


// ---- Novig (v2.4). Public, no login: the UFC trading page lists every event; the Hasura endpoint only accepts the app's own
// persisted query (any other query -> "query is not allowed"), so we replay it verbatim. "available" is the current ASK as a
// probability, so Yes/No asks sum to >1 (ML ~1.005, GTD ~1.06, method props ~1.12) — they are de-vigged like a book pair.
// volume = $ traded; seeded markets with volume 0 are "is_consensus" quotes (derived from books), so weight follows volume.
var NOVIG_QUERY = "query EventMarkets_Query($eventId: uuid, $marketVisibleWhere: market_bool_exp) @cached(ttl: 5) {\n  event(where: {id: {_eq: $eventId}}) {\n    ...MarketSelector_Frag\n    ...EventData_Frag\n    ...EventScoreboard_Frag\n    ...CustomEvent_Frag\n    id\n    description\n    type\n    league\n    scheduled_start\n    status\n    tournament_markets: markets {\n      type\n      __typename\n    }\n    game {\n      id\n      awayTeam {\n        id\n        name\n        symbol\n        primary_color\n        secondary_color\n        swish_id\n        optic_odds_id\n        __typename\n      }\n      homeTeam {\n        id\n        name\n        symbol\n        primary_color\n        secondary_color\n        swish_id\n        optic_odds_id\n        __typename\n      }\n      end_date\n      away_score\n      home_score\n      time_remaining\n      sport\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment MarketData_Frag on market {\n  id\n  type\n  strike\n  status\n  re_settled_at\n  competitor {\n    id\n    name\n    country\n    __typename\n  }\n  market_locks(\n    order_by: {created_at: desc}\n    where: {deleted_at: {_is_null: true}}\n  ) {\n    id\n    market_id\n    created_at\n    minute_duration\n    __typename\n  }\n  player {\n    id\n    full_name\n    __typename\n  }\n  __typename\n}\n\nfragment Outcome_Frag on outcome {\n  id\n  available\n  altAvailable\n  index\n  description\n  competitor {\n    id\n    symbol\n    __typename\n  }\n  __typename\n}\n\nfragment StrikePriceSelector_Frag on market {\n  id\n  description\n  eventId\n  strike\n  ...MarketData_Frag\n  outcomes {\n    id\n    index\n    description\n    ...Outcome_Frag\n    __typename\n  }\n  __typename\n}\n\nfragment TennisScoreboard_Frag on game {\n  events {\n    id\n    status\n    __typename\n  }\n  home_set_1\n  home_set_2\n  home_set_3\n  home_set_4\n  home_set_5\n  away_set_1\n  away_set_2\n  away_set_3\n  away_set_4\n  away_set_5\n  possession\n  home_game_score\n  away_game_score\n  homeTeam {\n    id\n    name\n    __typename\n  }\n  awayTeam {\n    id\n    name\n    __typename\n  }\n  __typename\n}\n\nfragment BaseEvent_Frag on event {\n  id\n  status\n  type\n  description\n  league\n  scheduled_start\n  event_locks(order_by: {created_at: desc}, where: {deleted_at: {_is_null: true}}) {\n    id\n    event_id\n    minute_duration\n    created_at\n    __typename\n  }\n  __typename\n}\n\nfragment MarketSelector_Frag on event {\n  id\n  type\n  league\n  markets(where: $marketVisibleWhere) {\n    is_consensus\n    id\n    strike\n    type\n    description\n    status\n    volume\n    market_detail {\n      question\n      __typename\n    }\n    ...MarketData_Frag\n    ...StrikePriceSelector_Frag\n    outcomes {\n      id\n      index\n      description\n      available\n      ...Outcome_Frag\n      __typename\n    }\n    market_locks(\n      order_by: {created_at: desc}\n      where: {deleted_at: {_is_null: true}}\n    ) {\n      id\n      market_id\n      minute_duration\n      created_at\n      __typename\n    }\n    player {\n      id\n      full_name\n      logo\n      jersey_number\n      player_competitors {\n        competitor {\n          id\n          name\n          short_name\n          symbol\n          swish_id\n          optic_odds_id\n          primary_color\n          secondary_color\n          country\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    competitor {\n      id\n      name\n      short_name\n      symbol\n      swish_id\n      optic_odds_id\n      primary_color\n      secondary_color\n      country\n      __typename\n    }\n    __typename\n  }\n  event_locks(order_by: {created_at: desc}, where: {deleted_at: {_is_null: true}}) {\n    id\n    event_id\n    minute_duration\n    created_at\n    __typename\n  }\n  __typename\n}\n\nfragment EventData_Frag on event {\n  id\n  type\n  status\n  scheduled_start\n  league\n  game {\n    id\n    league\n    sport\n    scheduled_start\n    period\n    time_remaining\n    home_score\n    away_score\n    awayTeam {\n      id\n      name\n      symbol\n      short_name\n      mascot\n      primary_color\n      secondary_color\n      swish_id\n      optic_odds_id\n      wins\n      losses\n      draws\n      country\n      __typename\n    }\n    homeTeam {\n      id\n      name\n      symbol\n      short_name\n      mascot\n      primary_color\n      secondary_color\n      swish_id\n      optic_odds_id\n      wins\n      losses\n      draws\n      country\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment EventScoreboard_Frag on event {\n  id\n  type\n  status\n  description\n  league\n  scheduled_start\n  game {\n    id\n    ...TennisScoreboard_Frag\n    status\n    home_score\n    away_score\n    period\n    time_remaining\n    down\n    distance\n    yardLine\n    yardline_territory\n    league\n    sport\n    homeTeam {\n      id\n      name\n      short_name\n      mascot\n      symbol\n      primary_color\n      secondary_color\n      wins\n      losses\n      draws\n      swish_id\n      optic_odds_id\n      ranking\n      country\n      __typename\n    }\n    awayTeam {\n      id\n      name\n      short_name\n      mascot\n      symbol\n      primary_color\n      secondary_color\n      wins\n      losses\n      draws\n      swish_id\n      optic_odds_id\n      ranking\n      country\n      __typename\n    }\n    __typename\n  }\n  parent_event {\n    id\n    description\n    __typename\n  }\n  scoreboard_markets: markets(where: {type: {_eq: \"MONEY\"}}, limit: 1) {\n    id\n    type\n    outcomes {\n      id\n      index\n      status\n      __typename\n    }\n    __typename\n  }\n  custom_markets: markets(where: {type: {_eq: \"CUSTOM\"}}, limit: 1) {\n    id\n    type\n    __typename\n  }\n  __typename\n}\n\nfragment CustomEvent_Frag on event {\n  ...BaseEvent_Frag\n  custom_event_markets_aggregate: markets_aggregate(\n    where: {type: {_eq: \"CUSTOM\"}, status: {_eq: \"OPEN\"}}\n  ) {\n    aggregate {\n      count\n      __typename\n    }\n    __typename\n  }\n  custom_event_volume_aggregate: markets_aggregate(\n    where: {type: {_eq: \"CUSTOM\"}, status: {_eq: \"OPEN\"}}\n  ) {\n    aggregate {\n      sum {\n        volume\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  custom_event_markets: markets(\n    where: {type: {_eq: \"CUSTOM\"}, status: {_eq: \"OPEN\"}}\n    order_by: {volume: desc}\n  ) {\n    ...MarketData_Frag\n    description\n    volume\n    market_detail {\n      question\n      __typename\n    }\n    outcomes {\n      ...Outcome_Frag\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n";
var NOVIG_WHERE = {"_and":[{"status":{"_eq":"OPEN"}},{"_or":[{"is_consensus":{"_eq":true}},{"outcomes":{"available":{"_is_null":false}}}]},{"_and":[{"_not":{"market_locks":{"_and":[{"deleted_at":{"_is_null":true}}]}}},{"event":{"_not":{"event_locks":{"_and":[{"deleted_at":{"_is_null":true}}]}}}}]}]};
function novigWeight_(vol) { vol = Number(vol) || 0; return vol >= 1000 ? (EXCHANGE_BOOKS.Novig || 2) : vol >= 100 ? 1 : 0.5; }
function novigEvents_() {
  try {
    var h = get_('https://api.novig.us/nbx/v1/trading/UFC/page?displayUnseededMarkets=false'); var j = JSON.parse(h), out = [];
    (function walk(o) { if (!o || typeof o !== 'object') return; if (Array.isArray(o)) { o.forEach(walk); return; }
      if (o.type === 'game_event_card' && o.eventId && o.homeTeam && o.awayTeam) {
        var sb = o.scoreboard || {}, hm = sb.homeTeam && sb.homeTeam.moneyline, am = sb.awayTeam && sb.awayTeam.moneyline, tot = null;
        (o.columns || []).forEach(function (c) { if (/total/i.test(c.title || '') && c.outcomes && c.outcomes.length === 2) { var ov = null, un = null, strike = null; c.outcomes.forEach(function (x) { var mm = /^([OU])\s*([\d.]+)/i.exec(x.displayLabel || ''); if (!mm) return; strike = mm[2]; if (/^o/i.test(mm[1])) ov = Number(x.available); else un = Number(x.available); }); if (strike && ov != null) tot = { strike: strike, over: ov, under: un }; } });
        out.push({ id: o.eventId, home: o.homeTeam.name, away: o.awayTeam.name, start: o.scheduledStart, mlHome: hm ? Number(hm.available) : null, mlAway: am ? Number(am.available) : null, total: tot });
      }
      Object.keys(o).forEach(function (k) { walk(o[k]); }); })(j);
    return out;
  } catch (e) { WARN.push('Novig events: ' + e.message); return []; }
}
function novigMarkets_(eventId) {
  try {
    var hdr = {}; for (var k in UA_) hdr[k] = UA_[k]; if (NOVIG_PROXY && NOVIG_PROXY_KEY) hdr['x-proxy-key'] = NOVIG_PROXY_KEY;
    var r = UrlFetchApp.fetch(NOVIG_PROXY || 'https://api.novig.us/v1/graphql', { method: 'post', contentType: 'application/json', muteHttpExceptions: true, headers: hdr,
      payload: JSON.stringify({ operationName: 'EventMarkets_Query', variables: { eventId: eventId, marketVisibleWhere: NOVIG_WHERE }, query: NOVIG_QUERY }) });
    if (r.getResponseCode() !== 200) { var msg = 'Novig graphql: HTTP ' + r.getResponseCode() + (r.getResponseCode() === 403 && !NOVIG_PROXY ? ' (Novig blocks POSTs from Google servers — set NOVIG_PROXY; using trading-page ML/total instead)' : ' ' + r.getContentText().slice(0, 100).replace(/\s+/g, ' ')); if (WARN.indexOf(msg) < 0) WARN.push(msg); return null; }
    var j = JSON.parse(r.getContentText()); if (j.errors) WARN.push('Novig graphql: ' + JSON.stringify(j.errors).slice(0, 160)); var ev = j.data && j.data.event && j.data.event[0]; if (!ev) return null;
    return ev.markets || [];
  } catch (e) { WARN.push('Novig markets: ' + e.message); return null; }
}
// Fold a Novig event's markets into the BFO-shaped structures: ml {Novig:[oRed,oBlue]} and prop rows (yes row + no row, odds.Novig)
function novigFold_(mk, red, blue, ml, props) {
  var A = function (p) { p = Number(p); return (p > 0 && p < 1) ? toAmer_(p) : null; };
  var yn = function (m) { var y = null, n = null; (m.outcomes || []).forEach(function (o) { if (/^yes$/i.test(o.description)) y = A(o.available); else if (/^no$/i.test(o.description)) n = A(o.available); }); return [y, n]; };
  var addProp = function (yesName, noName, y, n, w, match) {
    if (y == null) return;
    var i = -1; for (var k = 0; k < props.length; k++) if (match ? match(props[k].name) : props[k].name === yesName) { i = k; break; }
    if (i < 0) { props.push({ name: yesName, odds: {} }); props.push({ name: noName, odds: {} }); i = props.length - 2; }
    props[i].odds.Novig = y; props[i].w = w; if (n != null && props[i + 1]) props[i + 1].odds.Novig = n;
  };
  var who = function (m) { var nm = m.competitor && m.competitor.name; if (!nm) return null; return nameScore_(nm, red) ? red : (nameScore_(nm, blue) ? blue : null); };
  var found = 0;
  (mk || []).forEach(function (m) {
    var w = novigWeight_(m.volume), p = yn(m);
    if (m.type === 'MONEY') { var oR = null, oB = null; (m.outcomes || []).forEach(function (o) { var nm = (o.competitor && o.competitor.symbol) || o.description; if (nameScore_(nm, red) || (red.indexOf(String(nm).split(' ').pop()) >= 0)) oR = A(o.available); else if (nameScore_(nm, blue) || (blue.indexOf(String(nm).split(' ').pop()) >= 0)) oB = A(o.available); });
      if (oR != null && oB != null) { ml.Novig = [oR, oB]; ml.NovigW = w; found++; } }
    else if (m.type === 'GO_THE_DISTANCE') { addProp('Fight goes to decision', 'Fight does not go to decision', p[0], p[1], w, function (t) { return /^Fight goes to decision/i.test(t); }); found++; }
    else if (m.type === 'TOTAL' && m.strike) { var o = null, u = null; (m.outcomes || []).forEach(function (x) { if (/^over/i.test(x.description)) o = A(x.available); else if (/^under/i.test(x.description)) u = A(x.available); }); var half = String(m.strike).replace(/\.5$/, '½').replace(/\.0+$/, ''); addProp('Over ' + half + ' rounds', 'Under ' + half + ' rounds', o, u, w, function (t) { return new RegExp('^Over ' + half + ' rounds', 'i').test(t); }); found++; }
    else if (/^VICTORY_BY_/.test(m.type)) { var f = who(m); if (!f) return; var how = m.type === 'VICTORY_BY_DECISION' ? 'decision' : m.type === 'VICTORY_BY_SUBMISSION' ? 'submission' : 'TKO/KO';
      var ln = f.split(' ').pop(), re = how === 'decision' ? /wins by decision/i : how === 'submission' ? /wins by submission/i : /wins by (TKO|KO)/i;
      addProp(f + ' wins by ' + how, f + ' does not win by ' + how, p[0], p[1], w, function (t) { return re.test(t) && (nameScore_(t.split(' wins')[0], f) > 0 || t.indexOf(ln + ' wins') === 0); }); found++; }
  });
  return found;
}

// Diagnostic: shows exactly where the Novig pull succeeds or fails (HTTP codes, event count, name matching vs the loaded card)
function testNovig() {
  var ui = SpreadsheetApp.getUi(), out = [], code = '?', nEv = 0, evs = [];
  try { var r = UrlFetchApp.fetch('https://api.novig.us/nbx/v1/trading/UFC/page?displayUnseededMarkets=false', { muteHttpExceptions: true, headers: UA_ }); code = r.getResponseCode(); out.push('1) trading page: HTTP ' + code + ', ' + r.getContentText().length + ' chars' + (code !== 200 ? ' — body: ' + r.getContentText().slice(0, 200) : '')); } catch (e) { out.push('1) trading page threw: ' + e.message); }
  WARN.length = 0; evs = novigEvents_(); nEv = evs.length; out.push('2) events parsed: ' + nEv + (WARN.length ? ' (' + WARN.join('; ') + ')' : '') + (nEv ? ' — first: ' + evs[0].home + ' vs ' + evs[0].away : ''));
  if (nEv) {
    try { var r2 = UrlFetchApp.fetch('https://api.novig.us/v1/graphql', { method: 'post', contentType: 'application/json', muteHttpExceptions: true, headers: UA_, payload: JSON.stringify({ operationName: 'EventMarkets_Query', variables: { eventId: evs[0].id, marketVisibleWhere: NOVIG_WHERE }, query: NOVIG_QUERY }) });
      var txt = r2.getContentText(); out.push('3) graphql: HTTP ' + r2.getResponseCode() + ' — ' + txt.slice(0, 160).replace(/\s+/g, ' '));
      var mk = novigMarkets_(evs[0].id); out.push('4) markets for that event: ' + (mk ? mk.length + ' (' + mk.map(function (m) { return m.type; }).join(', ') + ')' : 'null'));
    } catch (e) { out.push('3) graphql threw: ' + e.message); }
    // name matching against the loaded card
    var ss = SpreadsheetApp.getActive(), hits = [], miss = [];
    [['Main Card', MAIN_ROWS], ['Prelims', PRE_ROWS]].forEach(function (t) { var sh = ss.getSheetByName(t[0]); if (!sh) return; var v = sh.getRange(t[1][0], 2, t[1][1] - t[1][0] + 1, 2).getValues();
      v.forEach(function (row) { if (!row[0]) return; var ok = evs.some(function (e) { return (nameScore_(e.home, row[0]) && nameScore_(e.away, row[1])) || (nameScore_(e.home, row[1]) && nameScore_(e.away, row[0])); }); (ok ? hits : miss).push(row[0] + ' v ' + row[1]); }); });
    out.push('5) card rows matched to a Novig event: ' + hits.length + ' / ' + (hits.length + miss.length) + (miss.length ? '\n   unmatched: ' + miss.join('; ') : ''));
  }
  ui.alert('Novig test\n\n' + out.join('\n'));
}

// ================================================================ v2.6 — CARD ORDER, MAIN-CARD SIZE, INPUTS FOLLOW THE FIGHT
// ufc.com sometimes lists a fight in the wrong section/order until fight week (Oct 31 2026: Reese–Gall shown as a prelim,
// Tapology + the broadcast have it on a 6-fight main card). Paste Tapology's card (copy the page or just the Fight Card
// section) anywhere in a tab named CardOrder; the loader finds each ufc.com bout in that text and takes its position,
// its section label (Main Event / Co-Main / Main Card / Prelim) and "5 x 5" rounds. A paste from an older card simply
// doesn't match (< 70% of bouts) and is ignored.
function normTxt_(s) { return ' ' + String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim() + ' '; }
function cardOrderMenu() {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName('CardOrder') || ss.insertSheet('CardOrder');
  sh.clear(); ss.setActiveSheet(sh); sh.getRange('A1').activate();
  SpreadsheetApp.getUi().alert('CardOrder tab is ready (cleared). Copy the Fight Card from the Tapology event page and paste it at A1 — any format is fine, ' +
    'the loader only looks for the fighters\' names and the "Main Event / Co-Main / Main Card / Prelim" labels. Then run "Load next UFC card".\n\nTo go back to ufc.com order, clear the tab.');
}
function applyCardOrder_(evc) {
  var ssx = SpreadsheetApp.getActive(), sh = ssx.getSheetByName('CardOrder');
  if (!sh) ssx.getSheets().forEach(function (t) { if (!sh && /^card\s*order$/i.test(t.getName().trim())) sh = t; });
  if (!sh || sh.getLastRow() < 1) {
    var nm = evc.bouts.filter(function (b) { return b.section === 'main'; }).length;
    if (!/^UFC\s*\d/.test(evc.name) && nm < 6) WARN.push('ufc.com lists only ' + nm + ' main-card fights for this Fight Night. If Tapology shows 6, run UFC ▸ Paste bout order (Tapology), paste the card at A1, and load again.');
    return 0;
  }
  var raw = sh.getRange(1, 1, sh.getLastRow(), Math.max(1, sh.getLastColumn())).getDisplayValues().map(function (r) { return r.join(' '); }).join(' ');
  var T = normTxt_(raw); if (T.length < 40) return 0;
  var occ = function (name) {            // positions of a fighter in the text: full name, else last name as a whole word
    var out = [], n = normTxt_(name), ln = ' ' + n.trim().split(' ').pop() + ' ', i;
    [n, ln].forEach(function (needle) { if (out.length || needle.trim().length < 3) return; i = T.indexOf(needle); while (i >= 0) { out.push(i); i = T.indexOf(needle, i + 1); } });
    return out;
  };
  var cands = evc.bouts.map(function (b) {
    var A = occ(b.red), B = occ(b.blue), pairs = [];
    A.forEach(function (a) { B.forEach(function (c) { if (Math.abs(a - c) < 700) pairs.push({ pos: Math.min(a, c), mid: (a + c) / 2, d: Math.abs(a - c) }); }); });
    return pairs;
  });
  // pass 1: tightest pair; pass 2: among close pairs, the one nearest the card's median (headlines / weigh-in lists mention names too)
  var p1 = cands.map(function (ps) { return ps.length ? ps.slice().sort(function (x, y) { return x.d - y.d; })[0] : null; });
  var mids = p1.filter(Boolean).map(function (p) { return p.mid; }).sort(function (a, b) { return a - b; });
  if (mids.length < Math.max(3, Math.ceil(evc.bouts.length * 0.7))) { if (mids.length >= 3) WARN.push('CardOrder tab matched only ' + mids.length + ' of ' + evc.bouts.length + ' bouts — ignored (stale paste?). Using ufc.com order.'); return 0; }
  var med = mids[mids.length >> 1];
  var pick = cands.map(function (ps) { return ps.length ? ps.slice().sort(function (x, y) { return Math.abs(x.mid - med) - Math.abs(y.mid - med); })[0] : null; });
  var LABELS = [[' main event ', 'main'], [' co main ', 'main'], [' main card ', 'main'], [' early prelim', 'prelims'], [' prelim', 'prelims']];
  var near = function (mid, re) { var best = null; LABELS.forEach(function (L) { var i = T.indexOf(L[0]); while (i >= 0) { var d = Math.abs(i - mid); if (d < 450 && (!best || d < best.d)) best = { d: d, sec: L[1], lab: L[0] }; i = T.indexOf(L[0], i + 1); } }); return best; };
  var matched = 0, mainN = 0;
  evc.bouts.forEach(function (b, k) {
    var p = pick[k]; if (!p) { b._pos = 1e9 + k; return; }
    matched++; b._pos = p.pos;
    var lab = near(p.mid); if (lab) { b.section = lab.sec; if (lab.sec === 'main') mainN++; }
    var w0 = Math.max(0, p.mid - 250), win = T.slice(w0, p.mid + 250), re = /\s([35]) x 5\s/g, mm, bestR = null;
    while ((mm = re.exec(win))) { var dd = Math.abs(w0 + mm.index - p.mid); if (!bestR || dd < bestR.d) bestR = { d: dd, n: +mm[1] }; }
    if (bestR) b.rounds = bestR.n;
  });
  evc.bouts.sort(function (a, b) { return a._pos - b._pos; });
  evc.bouts.forEach(function (b, i) { b.order = i + 1; delete b._pos; });
  evc.ordered = true;
  WARN.push('Bout order + main/prelim split taken from the CardOrder tab (Tapology paste): ' + matched + ' of ' + evc.bouts.length + ' bouts matched, ' + mainN + ' on the main card.');
  return matched;
}

// Main-card row count. Grows/shrinks Main Card + Calculator (+ Upload) formulas, moves the prelim block, re-links every row.
function setMainRowsMenu() {
  var ss = SpreadsheetApp.getActive(), ui = SpreadsheetApp.getUi(); syncLayout_(ss);
  var r = ui.prompt('Main-card rows', 'Currently ' + (MAIN_ROWS[1] - MAIN_ROWS[0] + 1) + '. Enter 5 (numbered events) or 6 (Fight Nights):', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return; var n = parseInt(r.getResponseText(), 10); if (!(n >= 3 && n <= 7)) return;
  setMainRows_(ss, n, false);
  ui.alert('Main card is now ' + n + ' rows (Calculator 2-' + (1 + n) + '; prelims Calculator ' + (2 + n) + '-' + (1 + n + PRE_ROWS[1] - PRE_ROWS[0] + 1) + '). Run "Load next UFC card" to re-place the fights — hand inputs follow their fights.');
}
function fillFormulas_(sh, tRow, rowsList, skipCols) {
  var ncol = sh.getLastColumn(), tf = sh.getRange(tRow, 1, 1, ncol).getFormulas()[0], changed = [];
  rowsList.forEach(function (rr) { var ef = sh.getRange(rr, 1, 1, ncol).getFormulas()[0], ev = sh.getRange(rr, 1, 1, ncol).getValues()[0], did = false;
    for (var c = 0; c < ncol; c++) { if (!tf[c] || ef[c] || skipCols.indexOf(c + 1) >= 0) continue; if (typeof ev[c] === 'string' && ev[c].length > 25) continue; sh.getRange(tRow, c + 1).copyTo(sh.getRange(rr, c + 1)); did = true; }
    if (did) changed.push(rr); });
  return changed;
}
function setMainRows_(ss, n, silent) {
  var mc = ss.getSheetByName('Main Card'), calc = ss.getSheetByName('Calculator'), up = ss.getSheetByName('Upload');
  var nPre = PRE_ROWS[1] - PRE_ROWS[0] + 1, calcLast = 1 + n + nPre, old = MAIN_ROWS[1] - MAIN_ROWS[0] + 1;
  var snap0 = snapshotInputs_(ss);                 // prelim inputs live on Calculator rows that are about to move
  // Calculator notes block sits under the fight rows — make room if needed
  for (var probe = 2 + Math.min(old, n) + 1; probe <= calcLast; probe++) { var pa = calc.getRange(probe, 1).getFormula(), pv = calc.getRange(probe, 1, 1, 3).getValues()[0].join(''); if (!pa && pv.length > 25) { calc.insertRowsBefore(probe, calcLast - probe + 1); break; } }
  var mrows = []; for (var r = 3; r <= 1 + n; r++) mrows.push(r);
  fillFormulas_(mc, 2, mrows, []);
  var crows = []; for (var c = 3; c <= calcLast; c++) crows.push(c);
  var newCalc = fillFormulas_(calc, 2, crows, [26]);
  if (up) fillFormulas_(up, 2, crows, []);
  newCalc.forEach(function (rr) { ['C', 'D', 'E', 'F', 'J', 'K', 'M', 'N', 'R', 'X', 'Y', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI'].forEach(function (col) { var rg = calc.getRange(col + rr); if (!rg.getFormula()) rg.clearContent(); }); });
  if (n < old) for (var k = 2 + n; k <= 1 + old; k++) ['B', 'C', 'D', 'I', 'S', 'T'].forEach(function (col) { var rg = mc.getRange(col + k); if (!rg.getFormula()) rg.clearContent(); });
  for (var zr = 3; zr <= calcLast + 2; zr++) { var zc = calc.getRange(zr, 26); if (!zc.getFormula() && zc.getValue() !== '') zc.clearContent(); }
  var zf = calc.getRange(2, 26).getFormula(); if (zf) calc.getRange(2, 26).setFormula(zf.replace(/\$?A2:\$?A\d+/g, '$A2:$A' + calcLast).replace(/L2:L\d+/g, 'L2:L' + calcLast).replace(/X2:X\d+/g, 'X2:X' + calcLast).replace(/Y2:Y\d+/g, 'Y2:Y' + calcLast));
  MAIN_ROWS = [2, 1 + n];
  relink_(ss, true);
  ensureFairTable_(mc, n, true);
  ensureFairTable_(ss.getSheetByName('Prelims'), nPre, true);
  var asFights = function (sh, rows) { return sh.getRange(rows[0], 2, rows[1] - rows[0] + 1, 2).getValues().map(function (r) { return String(r[0] || '').trim() ? { dog: r[0], fav: r[1] } : null; }); };
  restoreInputs_(ss, snap0, asFights(mc, MAIN_ROWS), asFights(ss.getSheetByName('Prelims'), PRE_ROWS));
}

// Hand inputs + opener keyed by fight. Calculator: C D E (public/sharp %), F (opener), J (Markov), K (code), M (manual),
// AI (Novig paste). Tab: AD-AF your dog proj, AH-AJ your fav proj, AP-AQ Markov DEC. A flipped fight is re-oriented.
var CALC_IN = [3, 4, 5, 6, 10, 11, 13, 35], TAB_IN = [30, 31, 32, 34, 35, 36, 42, 43];
function snapshotInputs_(ss) {
  var calc = ss.getSheetByName('Calculator'), out = [], nMain = MAIN_ROWS[1] - MAIN_ROWS[0] + 1;
  [['Main Card', MAIN_ROWS, 0], ['Prelims', PRE_ROWS, nMain]].forEach(function (t) {
    var sh = ss.getSheetByName(t[0]); if (!sh) return; var n = t[1][1] - t[1][0] + 1;
    var nm = sh.getRange(t[1][0], 2, n, 2).getValues(), tv = sh.getRange(t[1][0], 1, n, 43).getValues(), tf = sh.getRange(t[1][0], 1, n, 43).getFormulas();
    var cv = calc.getRange(2 + t[2], 1, n, 35).getValues(), cf = calc.getRange(2 + t[2], 1, n, 35).getFormulas();
    for (var i = 0; i < n; i++) { if (!String(nm[i][0] || '').trim()) continue;
      var e = { dog: nm[i][0], fav: nm[i][1], calc: {}, tab: {} };
      CALC_IN.forEach(function (c) { if (!cf[i][c - 1] && cv[i][c - 1] !== '') e.calc[c] = cv[i][c - 1]; });
      TAB_IN.forEach(function (c) { if (!tf[i][c - 1] && tv[i][c - 1] !== '') e.tab[c] = tv[i][c - 1]; });
      out.push(e); }
  });
  return out;
}
function restoreInputs_(ss, snap, mainRows, preRows) {
  var calc = ss.getSheetByName('Calculator'), nMain = MAIN_ROWS[1] - MAIN_ROWS[0] + 1, moved = 0;
  clearCardInputs_(ss);
  var cl = 1 + nMain + PRE_ROWS[1] - PRE_ROWS[0] + 1; var fr = calc.getRange(2, 6, cl - 1, 1), ff = fr.getFormulas(); fr.setValues(ff.map(function (x) { return [x[0] || '']; }));
  var flipP = function (v) { return (typeof v === 'number' && v >= 0 && v <= 1) ? 1 - v : v; };
  var flipCalc = { 3: flipP, 4: flipP, 5: flipP, 6: flipP, 10: flipP, 11: function (v) { return v === 'G' ? 'GF' : v === 'GF' ? 'G' : v === 'D' ? '' : (typeof v === 'number' ? -v : v); }, 13: function (v) { return typeof v === 'number' ? -v : v; }, 35: function (v) { var m = /([+-]?\d+)\s*\/\s*([+-]?\d+)/.exec(String(v)); return m ? m[2] + '/' + m[1] : v; } };
  var swapTab = { 30: 34, 31: 35, 32: 36, 34: 30, 35: 31, 36: 32, 42: 43, 43: 42 };
  var place = function (f, tabName, tabRow, calcRow) {
    if (!f) return; var e = null, flip = false;
    for (var i = 0; i < snap.length && !e; i++) { var s = snap[i];
      if (nameScore_(s.dog, f.dog) && nameScore_(s.fav, f.fav)) e = s; else if (nameScore_(s.dog, f.fav) && nameScore_(s.fav, f.dog)) { e = s; flip = true; } }
    if (!e) return; moved++;
    var tab = ss.getSheetByName(tabName);
    Object.keys(e.calc).forEach(function (c) { var v = flip && flipCalc[c] ? flipCalc[c](e.calc[c]) : e.calc[c]; var rg = calc.getRange(calcRow, +c); if (!rg.getFormula()) rg.setValue(v); });
    Object.keys(e.tab).forEach(function (c) { var tc = flip ? swapTab[c] : +c; var rg = tab.getRange(tabRow, tc); if (!rg.getFormula()) rg.setValue(e.tab[c]); });
  };
  mainRows.forEach(function (f, i) { place(f, 'Main Card', MAIN_ROWS[0] + i, 2 + i); });
  preRows.forEach(function (f, j) { place(f, 'Prelims', PRE_ROWS[0] + j, 2 + nMain + j); });
  return moved;
}

// ---- build the card (same shape the writers expect)
function buildCard_(ev) {
  var evc = ufcEventCard_(ev.url);
  applyCardOrder_(evc);                             // v2.6: Tapology paste in the CardOrder tab overrides ufc.com order / main-card split
  // BFO sometimes splits one card into two pages (UFC Edmonton Oct 17 + Oct 18 2026: prelims on one, main card on the
  // other, because the main card starts after midnight UTC). Every candidate page within ±2 days that matches at least
  // one bout is merged; the Feed stores all paths comma-separated.
  var cands;
  if (ev.bfo) cands = String(ev.bfo).split(',').map(function (p) { return { path: p.trim() }; }).filter(function (p) { return p.path; });
  else { var all = bfoCandidates_(evc.date); var near = all.filter(function (e) { return e.near; }); cands = near.length ? near : all.slice(0, 3); }
  var best = { books: [], fights: [], path: '' }, paths = [], bookSeen = {};
  for (var ci = 0; ci < cands.length; ci++) {
    try { var be = bfoEvent_(cands[ci].path); var hits = 0;
      evc.bouts.forEach(function (b) { be.fights.forEach(function (f) { if ((nameScore_(b.red, f.f1) && nameScore_(b.blue, f.f2)) || (nameScore_(b.red, f.f2) && nameScore_(b.blue, f.f1))) hits++; }); });
      if (!hits) continue;
      paths.push(cands[ci].path);
      be.fights.forEach(function (f) { f.path = cands[ci].path; best.fights.push(f); });
      be.books.forEach(function (bk) { if (!bookSeen[bk]) { bookSeen[bk] = 1; best.books.push(bk); } });
    } catch (e) { WARN.push('BFO ' + cands[ci].path + ': ' + e.message); }
  }
  best.path = paths.join(',');
  if (!paths.length) WARN.push('No BestFightOdds page matched this card — prices blank.');
  else if (paths.length > 1) WARN.push('BestFightOdds has this card on ' + paths.length + ' pages (' + paths.join(', ') + ') — merged.');
  // athlete pages (records + stats) and BFO fighter pages (openers), fetched in bulk
  var athUrls = []; evc.bouts.forEach(function (b) { athUrls.push(b.redUrl, b.blueUrl); });
  var athHtml = getAll_(athUrls); var athMap = {}; athUrls.forEach(function (u, i) { athMap[u] = ufcAthlete_(athHtml[i]); });
  var openUrls = best.fights.map(function (f) { return 'https://www.bestfightodds.com/fighters/' + f.slug1; });
  var openHtml = openUrls.length ? getAll_(openUrls) : [];
  var out = { ordered: !!evc.ordered, name: evc.name, date: evc.date, pk: paths.length ? (paths[0].match(/-(\d+)$/) || ['', evc.url])[1] : evc.url, url: evc.url, bfo: best.path, fights: [] };
  var mainCount = 0;
  var nvEvents = NOVIG_ON ? novigEvents_() : [], nvHit = 0;
  evc.bouts.forEach(function (b, idx) {
    var f = null, fi = -1; for (var i = 0; i < best.fights.length; i++) { var x = best.fights[i]; if ((nameScore_(b.red, x.f1) && nameScore_(b.blue, x.f2)) || (nameScore_(b.red, x.f2) && nameScore_(b.blue, x.f1))) { f = x; fi = i; break; } }
    // Novig (v2.4): find the event by the two names, pull its markets, fold them in as book "Novig" (weight by volume)
    var nv = null; for (var ni = 0; ni < nvEvents.length; ni++) { var e = nvEvents[ni]; if ((nameScore_(e.home, b.red) && nameScore_(e.away, b.blue)) || (nameScore_(e.home, b.blue) && nameScore_(e.away, b.red))) { nv = e; break; } }
    if (nv) {
      var mk = novigMarkets_(nv.id);
      if (!mk || !mk.length) {   // graphql blocked/empty -> synthesize MONEY + TOTAL from the trading page card itself
        mk = [];
        if (nv.mlHome > 0 && nv.mlAway > 0) mk.push({ type: 'MONEY', volume: 1000, outcomes: [{ description: nv.home, available: nv.mlHome, competitor: { symbol: nv.home } }, { description: nv.away, available: nv.mlAway, competitor: { symbol: nv.away } }] });
        if (nv.total) mk.push({ type: 'TOTAL', strike: nv.total.strike, volume: 1000, outcomes: [{ description: 'Over ' + nv.total.strike, available: nv.total.over }, { description: 'Under ' + nv.total.strike, available: nv.total.under }] });
        if (mk.length) { var fb = 'Novig: ML + round total only (from the trading page) — GTD/method quotes need NOVIG_PROXY.'; if (WARN.indexOf(fb) < 0) WARN.push(fb); }
      }
      if (mk && mk.length) { if (!f) f = { f1: b.red, f2: b.blue, mu: '', path: '', ml: {}, props: [], novigOnly: true }; if (novigFold_(mk, f.f1, f.f2, f.ml, f.props)) nvHit++; }
    }
    var redIs1 = f ? !!nameScore_(b.red, f.f1) : true;
    var books = [];
    if (f) Object.keys(f.ml).forEach(function (bk) { var o = f.ml[bk]; if (!Array.isArray(o) || !validOdds_(o[0]) || !validOdds_(o[1])) return; books.push({ book: bk, o1: redIs1 ? o[0] : o[1], o2: redIs1 ? o[1] : o[0], op1: null, op2: null, w: bk === 'Novig' ? f.ml.NovigW : undefined }); });
    var open = f ? bfoOpen_(openHtml[fi], f.path) : null;
    var openRed = null, openBlue = null;
    if (open) { var oa = open[0], ob = open[1]; if (nameScore_(oa.name, b.red)) { openRed = oa.open; openBlue = ob.open; } else if (nameScore_(ob.name, b.red)) { openRed = ob.open; openBlue = oa.open; } }
    var inc = books.filter(function (x) { return included_(x.book); });
    var p1 = median_(inc.map(function (x) { return devig2_(x.o1, x.o2); })); if (p1 == null) p1 = median_(books.map(function (x) { return devig2_(x.o1, x.o2); }));
    var p1open = (validOdds_(openRed) && validOdds_(openBlue)) ? devig2_(openRed, openBlue) : null;
    var dogIs1 = p1 != null ? p1 < 0.5 : false;
    var dogName = dogIs1 ? b.red : b.blue, favName = dogIs1 ? b.blue : b.red;
    var pDog = p1 == null ? null : (dogIs1 ? p1 : 1 - p1), pDogOpen = p1open == null ? null : (dogIs1 ? p1open : 1 - p1open);
    var bestPrice = function (side1) { var bb = null; books.filter(function (x) { return bettable_(x.book); }).forEach(function (x) { var o = side1 ? x.o1 : x.o2; if (!bb || payout_(o) > payout_(bb.odds)) bb = { odds: o, book: x.book }; }); return bb; };
    // props: pair consecutive rows (yes/no)
    var pr = f ? f.props : [];
    function propStat(pred) {
      var idxs = []; for (var i = 0; i < pr.length; i++) if (pred(pr[i].name)) idxs.push(i);
      if (!idxs.length) return null; var yes = pr[idxs[0]], no = pr[idxs[0] + 1] || { odds: {} };
      var rows = []; Object.keys(yes.odds).forEach(function (bk) { if (validOdds_(yes.odds[bk])) rows.push({ book: bk, o1: yes.odds[bk], o2: validOdds_(no.odds[bk]) ? no.odds[bk] : null, w: bk === 'Novig' ? yes.w : undefined }); });
      if (!rows.length) return null;
      var incl = rows.filter(function (r) { return included_(r.book); }); if (!incl.length) incl = rows;
      var two = incl.filter(function (r) { return r.o2 != null; });
      var prob = two.length ? median_(two.map(function (r) { return devig2_(r.o1, r.o2); })) : median_(incl.map(function (r) { return imp_(r.o1); }));
      var bb = null; rows.filter(function (r) { return bettable_(r.book); }).forEach(function (r) { if (!bb || payout_(r.o1) > payout_(bb.odds)) bb = { odds: r.o1, book: r.book }; });
      var ex = exchFair_(rows);                                   // exchange reference for this prop (yes-side prob), if any exchange quotes both sides
      var exYes = ex ? ex.p : (function () { var e1 = rows.filter(function (r) { return EXCHANGE_BOOKS[r.book]; }); return e1.length ? median_(e1.map(function (r) { return imp_(r.o1); })) : null; })();
      var bookProb = prob;                                        // books-only (kept for the Feed / grading)
      if (exYes != null && EXCH_PROP_W > 0) prob = EXCH_PROP_W * exYes + (1 - EXCH_PROP_W) * bookProb;   // v2.3.1: exchange-blended
      return { prob: prob, bookProb: bookProb, probOpen: null, medOdds: toAmer_(prob), n: incl.length, best: bb,
        exch: exYes, exchSrc: ex ? ex.src : (exYes != null ? 'yes-only' : ''),
        srcRows: rows.map(function (r) { return { book: r.book, p: r.o2 != null ? devig2_(r.o1, r.o2) : imp_(r.o1), odds: r.o1, w: r.w, two: r.o2 != null }; }), outl: exYes != null ? outliers_(rows.map(function (r) { return { book: r.book, o1: r.o1, o2: r.o2 == null ? 0 : r.o2 }; }), exYes).filter(function (o) { return o.side === 1; }) : [] };
    }
    var lastTok = function (n) { var t = String(n).trim().split(/\s+/); return t[t.length - 1]; };
    var who = function (n) { var ln = lastTok(n); return function (txt) { return nameScore_(txt.split(' wins')[0], n) > 0 || txt.indexOf(ln + ' wins') === 0; }; };
    var props = {
      gtd: propStat(function (t) { return /^Fight goes to decision/i.test(t); }),
      o15: propStat(function (t) { return /^Over 1½ rounds/i.test(t); }), o25: propStat(function (t) { return /^Over 2½ rounds/i.test(t); }), o45: propStat(function (t) { return /^Over 4½ rounds/i.test(t); })
    };
    var meth = function (n) { var w = who(n); return { dec: propStat(function (t) { return w(t) && /wins by decision/i.test(t); }), ko: propStat(function (t) { return w(t) && /wins by (TKO|KO)/i.test(t); }), sub: propStat(function (t) { return w(t) && /wins by submission/i.test(t); }), itd: propStat(function (t) { return w(t) && /wins inside distance/i.test(t); }) }; };
    props.dog = meth(dogName); props.fav = meth(favName);
    var redRec = athMap[b.redUrl] || { w: 0, fw: 0, l: 0, fl: 0, stats: '' }, blueRec = athMap[b.blueUrl] || { w: 0, fw: 0, l: 0, fl: 0, stats: '' };
    var fiveR = b.title || b.rounds === 5 || (b.section === 'main' && idx === 0);
    var tag = (b.women ? 'w' : '') + b.weight + (fiveR ? '-5' : '');
    var isMain = b.section === 'main'; if (isMain) mainCount++;
    // weigh-ins (ufc.com live feed): overage in lb for each side, oriented dog/fav
    var missRed = missLbs_(b.weighRed, b.weight, b.title), missBlue = missLbs_(b.weighBlue, b.weight, b.title);
    var missDog = dogIs1 ? missRed : missBlue, missFav = dogIs1 ? missBlue : missRed;
    var wNote = ''; if (missDog > 0) wNote += 'DOG ' + lastTok(dogName) + ' +' + missDog + ' lb'; if (missFav > 0) wNote += (wNote ? ' | ' : '') + 'FAV ' + lastTok(favName) + ' +' + missFav + ' lb';
    if (!wNote && (b.weighRed != null || b.weighBlue != null)) wNote = 'made weight';
    // exchange reference (ML): dog-oriented prob pairs; outliers computed later in writeCalculator_ (manual Novig may be added there)
    var exML = exchFair_(books);
    var exchPairs = exML ? exML.pairs.map(function (x) { return { v: dogIs1 ? x.v : 1 - x.v, w: x.w, book: x.book }; }) : [];
    out.fights.push({
      order: b.order, type: isMain ? (idx === 0 ? 'ME' : 'MC') : 'PL', main: isMain, fiveR: fiveR, slug: f ? f.mu : '', tag: tag, baseTag: (b.women ? 'w' : '') + b.weight, women: b.women, dogIs1: dogIs1 ? true : false,
      missDog: missDog, missFav: missFav, weighNote: wNote, exchPairs: exchPairs,
      dog: dogName, fav: favName, pDog: pDog, pDogOpen: pDogOpen, nBooks: inc.length,
      dogOdds: toAmer_(pDog), favOdds: toAmer_(pDog == null ? null : 1 - pDog),
      bestDog: bestPrice(dogIs1), bestFav: bestPrice(!dogIs1),
      dogRec: dogIs1 ? redRec : blueRec, favRec: dogIs1 ? blueRec : redRec, dogStats: (dogIs1 ? redRec : blueRec).stats, favStats: (dogIs1 ? blueRec : redRec).stats,
      props: props, books: books.map(function (x) { return { book: x.book, o1: dogIs1 ? x.o1 : x.o2, o2: dogIs1 ? x.o2 : x.o1, op1: dogIs1 ? openRed : openBlue, op2: dogIs1 ? openBlue : openRed }; })
    });
    // books[] is oriented dog/fav here, so dogIs1 must read true for the Feed printer
    out.fights[out.fights.length - 1].dogIs1 = true;
  });
  if (NOVIG_ON) WARN.push(nvHit ? 'Novig: ' + nvHit + ' of ' + evc.bouts.length + ' fights priced (ML / GTD / O-U / method, weight by $ traded).' : 'Novig: no markets matched this card.');
  return out;
}

// ---------------------------------------------------------------- write to the sheet
function loadCard_(ev, opt) {
  var ss = SpreadsheetApp.getActive(); syncLayout_(ss);
  WARN.length = 0;
  var card = buildCard_(ev); var pk = card.pk;
  // New card (different event pk than the one on the sheet): wipe last card's hand inputs and take fresh openers.
  var feed = ss.getSheetByName('Feed'); var prevPk = feed ? String(feed.getRange('B2').getValue()) : '';
  var cleared = false;
  if (opt.writeNames && prevPk && prevPk !== String(pk)) {
    var ui = SpreadsheetApp.getUi();
    var ok = ui.alert('New card', 'Loading ' + card.name + '. Clear last card\'s hand inputs (Markov, Tap/Junk/Tip, K codes, manual adj, your proj DEC/KO/SUB, Markov DEC) and take fresh openers?\n\nSnapshot + grade the old card first if you haven\'t.', ui.ButtonSet.YES_NO);
    if (ok === ui.Button.YES) { clearCardInputs_(ss); cleared = true; }
    opt.forceOpen = true;                              // last card's openers never carry over
  }
  var warn = [];
  var dk = dkFeed_(ss); card.fights = card.fights.map(function (f) { return conformNames_(f, dk); });
  // v2.2: rows follow ufc.com bout order (main event first) even when a fight has no price yet — the old "priced
  // fights first" sort put a prelim-level fight in the main-event row whenever BFO was missing lines.
  var mainAll = card.fights.filter(function (f) { return f.main; }).sort(function (a, b) { return a.order - b.order; });
  var MAX_MAIN = card.ordered ? 99 : maxMain_(card.name);   // a CardOrder paste is authoritative on the main-card split
  var demoted = mainAll.slice(MAX_MAIN); demoted.forEach(function (f) { f.main = false; });
  var main = mainAll.slice(0, MAX_MAIN);
  var pre = card.fights.filter(function (f) { return !f.main; }).sort(function (a, b) { return a.order - b.order; });
  if (demoted.length) warn.push('fightodds tagged ' + demoted.length + ' extra main-card fight(s) (cap ' + MAX_MAIN + ' for this event type); moved to prelims: ' + demoted.map(function (f) { return f.dog + ' vs ' + f.fav; }).join(', '));
  // v2.6: the sheet's main-card row count follows the card (Fight Nights 6, numbered events 5) — offer to resize
  var snap = (opt.writeNames && !cleared && prevPk === String(pk)) ? snapshotInputs_(ss) : null;   // same card re-loaded: keep inputs with their fights
  if (opt.writeNames && main.length > MAIN_ROWS[1] - MAIN_ROWS[0] + 1) {
    var ui2 = SpreadsheetApp.getUi();
    if (ui2.alert('Main card size', card.name + ' has ' + main.length + ' main-card fights; the sheet has ' + (MAIN_ROWS[1] - MAIN_ROWS[0] + 1) + ' main-card rows. Resize the Main Card / Calculator layout to ' + main.length + ' now?', ui2.ButtonSet.YES_NO) === ui2.Button.YES) {
      setMainRows_(ss, main.length, true); warn.push('Layout resized: ' + main.length + ' main-card rows (Calculator 2-' + (1 + main.length) + '), prelims follow.');
    }
  }
  if (main.length > MAIN_ROWS[1] - MAIN_ROWS[0] + 1) warn.push('Main card has ' + main.length + ' fights; only ' + (MAIN_ROWS[1] - MAIN_ROWS[0] + 1) + ' rows fit — last ones dropped.');
  if (pre.length > PRE_ROWS[1] - PRE_ROWS[0] + 1) warn.push('Prelims has ' + pre.length + ' fights; only ' + (PRE_ROWS[1] - PRE_ROWS[0] + 1) + ' rows fit — early prelims dropped (lowest on the card).');
  main = main.slice(0, MAIN_ROWS[1] - MAIN_ROWS[0] + 1);
  pre = pre.slice(0, PRE_ROWS[1] - PRE_ROWS[0] + 1);

  var mainRows = writeTab_(ss.getSheetByName('Main Card'), main, MAIN_ROWS, opt);
  var preRows = writeTab_(ss.getSheetByName('Prelims'), pre, PRE_ROWS, opt);
  // v2.6: hand inputs follow the FIGHT, not the row — a reorder/resize must not leave Markov/Tap/openers on the wrong bout
  if (snap) { var moved = restoreInputs_(ss, snap, mainRows, preRows); if (moved) warn.push('Hand inputs + openers re-attached to their fights after the reorder (' + moved + ' fights).'); }
  writeCalculator_(ss, mainRows.concat(preRows), opt);
  writeFeed_(ss, card);
  var edgesHit = writeEdges_(ss, card);
  var noOdds = card.fights.filter(function (f) { return f.pDog == null; }).map(function (f) { return f.dog + ' vs ' + f.fav; });
  var msg = card.name + ' (' + card.date + ') loaded: ' + main.length + ' main / ' + pre.length + ' prelim fights.' + (edgesHit ? ' Edges tab: ' + edgesHit + ' fighters priced.' : '');
  if (noOdds.length) msg += '\n\nNo moneyline posted yet for: ' + noOdds.join('; ') + ' (names written, prices blank — refresh later).';
  if (warn.length || WARN.length) msg += '\n\n' + warn.concat(WARN).join('\n');
  SpreadsheetApp.getUi().alert(msg);
}

// Returns the fight (or null) sitting in each row, so the Calculator rows line up with the tab rows.
// With writeNames=false the fights are matched to the names already on the tab (row order is yours);
// unmatched fights go into empty rows.
function placeFights_(sh, fights, rows, opt) {
  var nRows = rows[1] - rows[0] + 1, slots = [];
  for (var r = 0; r < nRows; r++) slots.push(null);
  if (opt.writeNames) { fights.forEach(function (f, i) { if (i < nRows) slots[i] = f; }); return slots; }
  var names = sh.getRange(rows[0], 2, nRows, 2).getValues(), priced = sh.getRange(rows[0], 4, nRows, 1).getValues();
  var norm = function (s) { return String(s || '').toLowerCase().replace(/[^a-z]/g, ''); };
  var left = [];
  fights.forEach(function (f) {
    var hit = -1;
    for (var r = 0; r < nRows; r++) { var b = names[r][0], c = names[r][1]; if (!norm(b) && !norm(c)) continue; if (nameScore_(b, f.dog) || nameScore_(b, f.fav) || nameScore_(c, f.dog) || nameScore_(c, f.fav)) { hit = r; break; } }
    if (hit >= 0 && !slots[hit]) {
      // keep the sheet's dog/fav orientation if the market has flipped since the names were written
      // keep the sheet's orientation only if that row was priced when the names were written (v2.5.2: a load that found no
      // prices wrote an arbitrary dog/fav, so a refresh must be allowed to re-orient it)
      if (nameScore_(names[hit][0], f.fav) && !nameScore_(names[hit][0], f.dog)) {
        if (String(priced[hit][0] || '').trim() !== '') { f = flipFight_(f); WARN.push(sh.getName() + ' row ' + (rows[0] + hit) + ': market now favors ' + f.dog + ' — orientation kept, reload names to re-orient.'); }
        else WARN.push(sh.getName() + ' row ' + (rows[0] + hit) + ': re-oriented — ' + f.dog + ' is the dog, ' + f.fav + ' the favorite (row had no price before). Check any Markov/Tap/Junk you typed on this row: col J etc. are the DOG\'s numbers.');
      }
      slots[hit] = f;
    } else left.push(f);
  });
  for (var r2 = 0; r2 < nRows && left.length; r2++) { if (!slots[r2] && !norm(names[r2][0]) && !norm(names[r2][1])) slots[r2] = left.shift(); }
  return slots;
}
var WARN = [];
function flipFight_(f) {
  var g = {}; for (var k in f) g[k] = f[k];
  g.dog = f.fav; g.fav = f.dog; g.dogIs1 = !f.dogIs1;
  g.pDog = f.pDog == null ? null : 1 - f.pDog; g.pDogOpen = f.pDogOpen == null ? null : 1 - f.pDogOpen;
  g.dogOdds = f.favOdds; g.favOdds = f.dogOdds; g.bestDog = f.bestFav; g.bestFav = f.bestDog;
  g.dogRec = f.favRec; g.favRec = f.dogRec; g.missDog = f.missFav; g.missFav = f.missDog;
  g.exchPairs = (f.exchPairs || []).map(function (x) { return { v: 1 - x.v, w: x.w, book: x.book }; });
  g.weighNote = String(f.weighNote || '').replace(/\bDOG\b/g, '\u0000').replace(/\bFAV\b/g, 'DOG').replace(/\u0000/g, 'FAV');
  g.props = {}; for (var k2 in f.props) g.props[k2] = f.props[k2]; g.props.dog = f.props.fav; g.props.fav = f.props.dog;
  return g;
}

function writeTab_(sh, fights, rows, opt) {
  var nRows = rows[1] - rows[0] + 1;
  var slots = placeFights_(sh, fights, rows, opt);
  if (!opt.writeNames) {   // booking changes: the row matched on one fighter, the other differs -> rewrite that cell
    var cur = sh.getRange(rows[0], 2, nRows, 2).getValues();
    for (var q = 0; q < nRows; q++) { var fq = slots[q];
      if (!fq) { if (String(cur[q][0] || '').trim() || String(cur[q][1] || '').trim()) { WARN.push(sh.getName() + ' row ' + (rows[0] + q) + ': ' + cur[q][0] + ' vs ' + cur[q][1] + ' is no longer on this tab (moved or cancelled) — names cleared.'); sh.getRange(rows[0] + q, 1, 1, 3).clearContent(); } continue; }
      if (!nameScore_(cur[q][0], fq.dog)) { WARN.push(sh.getName() + ' row ' + (rows[0] + q) + ': ' + cur[q][0] + ' -> ' + fq.dog + ' (booking/spelling change)'); sh.getRange(rows[0] + q, 2).setValue(fq.dog); }
      else if (String(cur[q][0]) !== fq.dog) sh.getRange(rows[0] + q, 2).setValue(fq.dog);
      if (!nameScore_(cur[q][1], fq.fav)) { WARN.push(sh.getName() + ' row ' + (rows[0] + q) + ': ' + cur[q][1] + ' -> ' + fq.fav + ' (booking/spelling change)'); sh.getRange(rows[0] + q, 3).setValue(fq.fav); }
      else if (String(cur[q][1]) !== fq.fav) sh.getRange(rows[0] + q, 3).setValue(fq.fav);
    }
  }
  var A = [], D = [], I = [], S = [], T = [], tbl = [];
  for (var r = 0; r < nRows; r++) {
    var f = slots[r];
    if (!f) { A.push(['', '', '']); D.push(['']); I.push(['']); S.push(['']); T.push(['']); tbl.push(['', '', '', '', ''], ['', '', '', '', '']); continue; }
    A.push([f.tag, f.dog, f.fav]);
    // D/I = best price you can actually bet (so List % and Edge are EV at YOUR price, vig included);
    // falls back to the no-vig consensus only when no bettable book has a line.
    D.push([f.bestDog ? f.bestDog.odds : f.dogOdds]); I.push([f.bestFav ? f.bestFav.odds : f.favOdds]);
    var g = f.props.gtd; S.push([g && g.prob != null ? g.prob : '']); T.push([g && g.prob != null ? 1 - g.prob : '']);
    var mo = function (s) { return s && s.medOdds ? s.medOdds : ''; };
    tbl.push([f.dog, mo(f.props.dog.dec), mo(f.props.dog.ko), mo(f.props.dog.sub), mo(f.props.dog.itd)]);
    tbl.push([f.fav, mo(f.props.fav.dec), mo(f.props.fav.ko), mo(f.props.fav.sub), mo(f.props.fav.itd)]);
  }
  if (opt.writeNames) sh.getRange(rows[0], 1, nRows, 3).setValues(A);
  sh.getRange(rows[0], 4, nRows, 1).setValues(D);
  sh.getRange(rows[0], 9, nRows, 1).setValues(I);
  sh.getRange(rows[0], 19, nRows, 1).setValues(S).setNumberFormat('0%');
  sh.getRange(rows[0], 20, nRows, 1).setValues(T).setNumberFormat('0%');
  ensureFairTable_(sh, nRows, false);
  sh.getRange(TABLE_ROW0, 14, nRows * 2, 5).setValues(tbl);                       // N:R = MARKET consensus odds
  sh.getRange(TABLE_ROW0, 15, nRows * 2, 4).setNumberFormat('+0;-0');
  return slots;
}

// H14:L27 = YOUR fair odds (formulas: name, True% x method share -> American), N14:R27 = market consensus (script),
// S14:V27 = fair prob - market implied prob (edge, + = you like it more than the market).
function ensureFairTable_(sh, nRows, force) {
  var n = nRows * 2, r0 = TABLE_ROW0;
  if (!force && sh.getRange(r0, 8).getFormula()) return;   // already formulas: leave the user's version alone
  var fr = '(2+INT((ROW()-' + r0 + ')/2))', dog = 'ISEVEN(ROW()-' + r0 + ')';
  var pick = function (dc, fc) { return 'IF(' + dog + ',INDEX($' + dc + ':$' + dc + ',' + fr + '),INDEX($' + fc + ':$' + fc + ',' + fr + '))'; };
  var winp = pick('F', 'K');
  var fair = function (shareExpr) { return '=IFERROR(LET(w,' + winp + ',s,' + shareExpr + ',p,IF(OR(w>1,s>1),w*s/10000,w*s),IF(OR(p<=0,p>=1),"",IF(p>=0.5,-ROUND(100*p/(1-p),0),ROUND(100*(1-p)/p,0)))),"")'; };
  var rows = [];
  for (var i = 0; i < n; i++) rows.push([
    '=IFERROR(' + pick('B', 'C') + ',"")',
    fair(pick('V', 'Z')), fair(pick('W', 'AA')), fair(pick('X', 'AB')),
    fair('(' + pick('W', 'AA') + '+' + pick('X', 'AB') + ')')
  ]);
  sh.getRange(r0, 8, n, 5).setFormulas(rows);
  sh.getRange(r0, 9, n, 4).setNumberFormat('+0;-0');
  var edge = [], imp = function (c) { return 'IF(' + c + '<0,-' + c + '/(100-' + c + '),100/(100+' + c + '))'; };
  for (var k = 0; k < n; k++) { var r = r0 + k, e = []; ['I', 'J', 'K', 'L'].forEach(function (c, idx) { var m = String.fromCharCode(79 + idx) + r; e.push('=IF(OR(' + c + r + '="",' + m + '=""),"",' + imp(c + r) + '-' + imp(m) + ')'); }); edge.push(e); }
  sh.getRange(r0, 19, n, 4).setFormulas(edge).setNumberFormat('+0.0%;-0.0%');
  sh.getRange(r0 - 1, 8, 1, 15).setValues([['Fighter', 'FAIR DEC', 'FAIR KO', 'FAIR SUB', 'FAIR ITD', '', 'Fighter (mkt)', 'MKT DEC', 'MKT KO', 'MKT SUB', 'MKT ITD', 'edge DEC', 'edge KO', 'edge SUB', 'edge ITD']]).setFontWeight('bold');
}

// Hand-entered columns only; any cell holding a formula is left alone.
function inputRanges_() { var pl = PRE_ROWS[1], cl = MAIN_ROWS[1] - MAIN_ROWS[0] + 1 + PRE_ROWS[1] - PRE_ROWS[0] + 2; return { 'Calculator': ['C2:E' + cl, 'J2:K' + cl, 'M2:M' + cl, 'AI2:AI' + cl], 'Main Card': ['AD2:AF7', 'AH2:AJ7', 'AP2:AQ7'], 'Prelims': ['AD2:AF' + pl, 'AH2:AJ' + pl, 'AP2:AQ' + pl] }; }
function clearCardInputs_(ss) {
  var IR = inputRanges_();
  Object.keys(IR).forEach(function (name) {
    var sh = ss.getSheetByName(name); if (!sh) return;
    IR[name].forEach(function (a1) {
      var rg = sh.getRange(a1), f = rg.getFormulas(), v = rg.getValues();
      for (var i = 0; i < v.length; i++) for (var j = 0; j < v[i].length; j++) if (!f[i][j]) v[i][j] = ''; else v[i][j] = f[i][j];
      rg.setValues(v);
    });
  });
}

// Rewrite Main Card / Prelims fighter names in the DK feed's spelling (EventPlayerIds) so Uploader/Edges lookups match.
function conformNamesMenu() {
  var ss = SpreadsheetApp.getActive(), dk = dkFeed_(ss), names = dk.map(function (d) { return d.name; }), changed = [], missing = [];
  if (!names.length) { SpreadsheetApp.getUi().alert('EventPlayerIds is empty — paste the DK feed first.'); return; }
  [['Main Card', MAIN_ROWS], ['Prelims', PRE_ROWS]].forEach(function (t) {
    var sh = ss.getSheetByName(t[0]), n = t[1][1] - t[1][0] + 1, v = sh.getRange(t[1][0], 2, n, 2).getValues();
    for (var r = 0; r < n; r++) for (var c = 0; c < 2; c++) { var cur = String(v[r][c] || '').trim(); if (!cur) continue;
      var hit = bestName_(cur, names); if (!hit) { missing.push(cur); continue; }
      if (hit !== cur) { sh.getRange(t[1][0] + r, 2 + c).setValue(hit); changed.push(cur + ' -> ' + hit); } }
  });
  SpreadsheetApp.getUi().alert((changed.length ? 'Renamed:\n' + changed.join('\n') : 'No spelling differences found.') + (missing.length ? '\n\nNot in DK feed (left as is): ' + missing.join(', ') : ''));
}

// Extend Prelims / Calculator / Upload formulas to cover PRE_ROWS (set PRE_ROWS at the top first), rebuild fair tables.
function resizePrelimsMenu() {
  var ss = SpreadsheetApp.getActive(); syncLayout_(ss); var nPre = PRE_ROWS[1] - PRE_ROWS[0] + 1, nMain = MAIN_ROWS[1] - MAIN_ROWS[0] + 1;
  var pre = ss.getSheetByName('Prelims'), calc = ss.getSheetByName('Calculator'), up = ss.getSheetByName('Upload');
  var tmpl = 2;                                                      // Prelims template row (formulas reference Calculator row tmpl+6)
  var lastCol = pre.getLastColumn();
  // Cell-by-cell: every column where the template holds a formula is copied (relative refs shift) into any target
  // cell that lacks one. Hand-input / loader columns (no formula in the template) are never touched. Returns rows changed.
  var fillFormulas = function (sh, tRow, rowsList, skipCols) {
    var ncol = sh.getLastColumn(), tf = sh.getRange(tRow, 1, 1, ncol).getFormulas()[0], changed = [];
    rowsList.forEach(function (rr) { var ef = sh.getRange(rr, 1, 1, ncol).getFormulas()[0], ev = sh.getRange(rr, 1, 1, ncol).getValues()[0], did = false;
      for (var c = 0; c < ncol; c++) { if (!tf[c] || ef[c] || skipCols.indexOf(c + 1) >= 0) continue;
        if (typeof ev[c] === 'string' && ev[c].length > 25) continue;        // looks like a note, not a stale value — leave it
        sh.getRange(tRow, c + 1).copyTo(sh.getRange(rr, c + 1)); did = true; }
      if (did) changed.push(rr); });
    return changed;
  };
  // Calculator: the notes block sits right under the fight rows — insert blank rows if the fight rows would run into it
  var calcLast0 = 1 + nMain + nPre;
  for (var probe = 1 + nMain + 2; probe <= calcLast0; probe++) {
    var pa = calc.getRange(probe, 1).getFormula(), pv = calc.getRange(probe, 1, 1, 3).getValues()[0].join('');
    if (!pa && pv.length > 25) { calc.insertRowsBefore(probe, calcLast0 - probe + 1); break; }
  }
  var preRows = []; for (var r = tmpl + 1; r <= PRE_ROWS[1]; r++) preRows.push(r);
  var newPre = fillFormulas(pre, tmpl, preRows, []);
  var calcLast = 1 + nMain + nPre, ctmpl = 1 + nMain + 1;             // Calculator: first prelim row is the template
  var calcRows = []; for (var cr = ctmpl + 1; cr <= calcLast; cr++) calcRows.push(cr);
  var newCalc = fillFormulas(calc, ctmpl, calcRows, [26]);           // col Z is an ARRAYFORMULA spill — never copy into it
  // Z: clear any static values sitting in the spill range, then re-point the array to the new last row
  for (var zr = 3; zr <= calcLast + 2; zr++) { var zc = calc.getRange(zr, 26); if (!zc.getFormula() && zc.getValue() !== '') zc.clearContent(); }
  var zf = calc.getRange(2, 26).getFormula(); if (zf) calc.getRange(2, 26).setFormula(zf.replace(/\$?A2:\$?A\d+/g, '$A2:$A' + calcLast).replace(/L2:L\d+/g, 'L2:L' + calcLast).replace(/X2:X\d+/g, 'X2:X' + calcLast).replace(/Y2:Y\d+/g, 'Y2:Y' + calcLast));
  if (up) fillFormulas(up, ctmpl, calcRows, []);
  // copied hand-input values in the NEW rows are junk: clear non-formula cells there (existing rows untouched)
  var wipe = function (sh, rowsList, a1cols) { rowsList.forEach(function (rr) { a1cols.forEach(function (c) { var rg = sh.getRange(c + rr); if (!rg.getFormula()) rg.clearContent(); }); }); };
  wipe(pre, newPre, ['A', 'B', 'C', 'D', 'I', 'S', 'T', 'AD', 'AE', 'AF', 'AH', 'AI', 'AJ', 'AP', 'AQ']);
  wipe(calc, newCalc, ['C', 'D', 'E', 'F', 'J', 'K', 'M', 'N', 'R', 'X', 'Y', 'AC', 'AD', 'AE']);
  calcRows.forEach(function (rr) { ['C', 'D', 'E', 'J', 'K', 'M'].forEach(function (c) { var rg = calc.getRange(c + rr); var v = rg.getValue(); if (!rg.getFormula() && typeof v === 'string' && v.charAt(0) === '#') rg.clearContent(); }); });
  ensureFairTable_(pre, nPre, true);
  ensureFairTable_(ss.getSheetByName('Main Card'), nMain, true);
  relinkRowsMenu();
  SpreadsheetApp.getUi().alert('Prelims sized for ' + nPre + ' fights (rows ' + PRE_ROWS[0] + '-' + PRE_ROWS[1] + '; Calculator rows ' + ctmpl + '-' + calcLast + '). New rows: Prelims ' + (newPre.join(',') || 'none') + ', Calculator ' + (newCalc.join(',') || 'none') + '. Now run Refresh prices.');
}

// Row links drift when someone inserts/deletes a row on a tab (cross-sheet refs don't shift). This rewrites every
// cross-sheet row reference so that Main Card row r <-> Calculator row r, Prelims row r <-> Calculator row r+(main rows), Upload row r <-> Calculator row r.
function relinkRowsMenu() { var ss = SpreadsheetApp.getActive(); syncLayout_(ss); relink_(ss, false); }
function relink_(ss, silent) {
  var nMain = MAIN_ROWS[1] - MAIN_ROWS[0] + 1, off = nMain;   // Prelims r -> Calculator r+off
  var calcLast = 1 + nMain + (PRE_ROWS[1] - PRE_ROWS[0] + 1);
  var fixRow = function (sh, r, sheetRe, targetRow) {   // rewrite row numbers in refs matching sheetRe within row r
    var ncol = sh.getLastColumn(), f = sh.getRange(r, 1, 1, ncol).getFormulas()[0], out = [], changed = false;
    for (var c = 0; c < ncol; c++) { var x = f[c]; if (x) { var y = x.replace(sheetRe, function (m, pre, col, dol, row) { return (+row >= 2 && +row <= 40) ? pre + col + dol + targetRow : m; }); if (y !== x) changed = true; out.push(y); } else out.push(null); }
    if (changed) for (var k = 0; k < ncol; k++) if (out[k] !== null && out[k] !== f[k]) sh.getRange(r, k + 1).setFormula(out[k]);
    return changed;
  };
  var CALC = /(Calculator!\$?)([A-Z]{1,2})(\$?)(\d+)/g, MAINC = /('Main Card'!\$?)([A-Z]{1,2})(\$?)(\d+)/g, PRE = /(Prelims!\$?)([A-Z]{1,2})(\$?)(\d+)/g;
  var n = 0, mc = ss.getSheetByName('Main Card'), pr = ss.getSheetByName('Prelims'), calc = ss.getSheetByName('Calculator'), up = ss.getSheetByName('Upload');
  for (var r = MAIN_ROWS[0]; r <= MAIN_ROWS[1]; r++) if (fixRow(mc, r, CALC, r)) n++;
  for (var r2 = PRE_ROWS[0]; r2 <= PRE_ROWS[1]; r2++) if (fixRow(pr, r2, CALC, r2 + off)) n++;
  for (var cr = 2; cr <= calcLast; cr++) {
    var isMain = cr <= 1 + nMain, tr = isMain ? cr : cr - off;
    // A/B/G are the structural links: set them outright so the sheet name is right too
    var tab = isMain ? "'Main Card'" : 'Prelims';
    calc.getRange(cr, 1).setFormula('=' + tab + '!B' + tr); calc.getRange(cr, 2).setFormula('=' + tab + '!C' + tr);
    calc.getRange(cr, 7).setFormula('=IFERROR(' + tab + '!E' + tr + '/(' + tab + '!E' + tr + '+' + tab + '!J' + tr + '),"")');
    if (fixRow(calc, cr, isMain ? MAINC : PRE, tr)) n++;
    // a prelim row still pointing at 'Main Card' (or vice versa) in other columns: swap the sheet name
    var ncol = calc.getLastColumn(), f = calc.getRange(cr, 1, 1, ncol).getFormulas()[0];
    for (var c = 0; c < ncol; c++) { if (!f[c]) continue; var y = isMain ? f[c].replace(/Prelims!/g, "'Main Card'!") : f[c].replace(/'Main Card'!/g, 'Prelims!'); if (y !== f[c]) { calc.getRange(cr, c + 1).setFormula(y.replace(isMain ? MAINC : PRE, function (m, pre, col, dol, row) { return pre + col + dol + tr; })); n++; } }
  }
  if (up) for (var ur = 2; ur <= calcLast; ur++) if (fixRow(up, ur, CALC, ur)) n++;
  if (!silent) SpreadsheetApp.getUi().alert('Relinked: ' + n + ' row(s) had drifted references. Main Card rows ' + MAIN_ROWS[0] + '-' + MAIN_ROWS[1] + ' <-> Calculator 2-' + (1 + nMain) + '; Prelims ' + PRE_ROWS[0] + '-' + PRE_ROWS[1] + ' <-> Calculator ' + (2 + nMain) + '-' + calcLast + '.');
}

function repairFairTables() {
  var ss = SpreadsheetApp.getActive(); syncLayout_(ss);
  ensureFairTable_(ss.getSheetByName('Main Card'), MAIN_ROWS[1] - MAIN_ROWS[0] + 1, true);
  ensureFairTable_(ss.getSheetByName('Prelims'), PRE_ROWS[1] - PRE_ROWS[0] + 1, true);
  SpreadsheetApp.getUi().alert('Fair-odds tables (H14:L27) re-installed on Main Card and Prelims; market odds live in N14:R27, edges in S14:V27.');
}

// Edges tab: A = fighter (from Uploader), F = Win Odds, H/J/L = Dec/KO/SUB odds — market inputs, filled by name.
function writeEdges_(ss, card) {
  var sh = ss.getSheetByName('Edges'); if (!sh || sh.getLastRow() < 2) return 0;
  var names = sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues();
  var norm = function (x) { return String(x || '').toLowerCase().replace(/[^a-z]/g, ''); };
  var byName = {};
  card.fights.forEach(function (f) {
    var mo = function (s) { return s && s.medOdds ? s.medOdds : ''; };
    byName[norm(f.dog)] = { ml: f.bestDog ? f.bestDog.odds : f.dogOdds, dec: mo(f.props.dog.dec), ko: mo(f.props.dog.ko), sub: mo(f.props.dog.sub) };
    byName[norm(f.fav)] = { ml: f.bestFav ? f.bestFav.odds : f.favOdds, dec: mo(f.props.fav.dec), ko: mo(f.props.fav.ko), sub: mo(f.props.fav.sub) };
  });
  var hits = 0;
  var keys = Object.keys(byName), origNames = {};
  card.fights.forEach(function (f) { origNames[norm(f.dog)] = f.dog; origNames[norm(f.fav)] = f.fav; });
  names.forEach(function (row, i) {
    var m = byName[norm(row[0])];
    if (!m) { var hit = bestName_(row[0], keys.map(function (k) { return origNames[k]; })); if (hit) m = byName[norm(hit)]; }
    if (!m) return;
    sh.getRange(i + 2, 6).setValue(m.ml); sh.getRange(i + 2, 8).setValue(m.dec); sh.getRange(i + 2, 10).setValue(m.ko); sh.getRange(i + 2, 12).setValue(m.sub); hits++;
  });
  return hits;
}

function writeCalculator_(ss, fights, opt) {
  var sh = ss.getSheetByName('Calculator');
  var base = baselineFinishRates_(ss);
  ensureHeader_(sh, 29, 'DOG: consensus no-vig | best (book)');   // AC
  ensureHeader_(sh, 30, 'FAV: consensus no-vig | best (book)');   // AD
  ensureHeader_(sh, 31, 'O4.5 listed (5R)');        // AE
  ensureHeader_(sh, 32, 'WEIGH-IN (miss)');         // AF
  ensureHeader_(sh, 33, 'EXCH fair dog % (Novig x2 / Polymarket / Kalshi)');   // AG
  ensureHeader_(sh, 34, 'ML OUTLIERS vs exch (bettable books; 1-3 pts = value, 4+ = TRAP)');   // AH
  ensureHeader_(sh, 35, 'Novig dog/fav ML (paste, e.g. +118/-130)');   // AI — manual, never overwritten
  var F = [], N = [], R = [], X = [], Y = [], AC = [], AD = [], AE = [], AF = [], AG = [], AH = [];
  var NC = MAIN_ROWS[1] - MAIN_ROWS[0] + 1 + PRE_ROWS[1] - PRE_ROWS[0] + 1;   // Calculator rows 2..(1+NC)
  var curF = sh.getRange(2, 6, NC, 1).getValues(), curK = sh.getRange(2, 11, NC, 1).getValues(), curNovig = sh.getRange(2, 35, NC, 1).getValues();
  for (var r = 0; r < NC; r++) {
    var f = fights[r];
    if (!f) { F.push(['']); N.push(['']); R.push(['']); X.push(['']); Y.push(['']); AC.push(['']); AD.push(['']); AE.push(['']); AF.push(['']); AG.push(['']); AH.push(['']); continue; }
    // Weigh-in rule (Alpha Map 2k): a FAVORITE who misses by >= 1.5 lb gets -0.03 on Q via K (only if K is blank — your D/G/GF codes win).
    // Misses <= 1 lb are noise and ignored; dog misses are already priced. Shown in AF either way.
    var afTxt = f.weighNote || '';
    if (f.missFav >= 1.5) {
      var k = curK[r][0];
      if (k === '' || k == null) { sh.getRange(2 + r, 11).setValue(-0.03); afTxt += ' -> K -0.03 (fav missed)'; }
      else if (k === -0.03) afTxt += ' -> K -0.03 (fav missed)';
      else { afTxt += ' -> K already set (' + k + '), rule not applied'; WARN.push('Calculator row ' + (2 + r) + ': ' + f.fav + ' missed by ' + f.missFav + ' lb but K = ' + k + '; -0.03 not applied.'); }
    }
    if (f.missDog >= 1.5 || f.missFav >= 1.5) WARN.push('Weight miss: ' + f.weighNote);
    AF.push([afTxt]);
    // exchange reference + outliers (v2.3). Manual Novig in AI ("+118/-130", dog/fav) replaces any Novig quote from BFO.
    var pairs = (f.exchPairs || []).slice();
    var nv = /([+-]?\d{3,5})\s*\/\s*([+-]?\d{3,5})/.exec(String(curNovig[r][0] || ''));
    if (nv && validOdds_(+nv[1]) && validOdds_(+nv[2])) { pairs = pairs.filter(function (x) { return x.book !== 'Novig'; }); pairs.push({ v: devig2_(+nv[1], +nv[2]), w: EXCHANGE_BOOKS.Novig || 2, book: 'Novig' }); }
    var exDog = pairs.length ? wmedian_(pairs) : null;
    f.exchDog = exDog;
    AG.push([exDog == null ? '' : exDog]);
    if (exDog == null) AH.push(['']);
    else {
      var ol = outliers_(f.books, exDog), dogs = ol.filter(function (o) { return o.side === 1; }).slice(0, 2), favs = ol.filter(function (o) { return o.side === 2; }).slice(0, 2);
      var src = pairs.map(function (x) { return x.book; }).join('+');
      AH.push([(dogs.length || favs.length) ? (dogs.map(function (o) { return fmtOutl_(o, 'DOG', 'FAV'); }).concat(favs.map(function (o) { return fmtOutl_(o, 'DOG', 'FAV'); })).join(' | ') + '  [' + src + ']') : 'none vs ' + src]);
      if (ol.length && ol[0].delta >= OUTLIER_TRAP) WARN.push('Outlier TRAP (4+ pts off exchange fair): ' + (ol[0].side === 1 ? f.dog : f.fav) + ' ' + fmtOdds_(ol[0].odds) + ' at ' + ol[0].book);
    }
    var keepOpen = !opt.forceOpen && curF[r][0] !== '' && curF[r][0] != null;
    F.push([keepOpen ? curF[r][0] : (f.pDogOpen != null ? f.pDogOpen : (f.pDog != null ? f.pDog : ''))]);   // no BFO opener -> first price seen
    N.push([f.props.o25 && f.props.o25.prob != null ? f.props.o25.prob : '']);
    R.push([f.props.o15 && f.props.o15.prob != null ? f.props.o15.prob : '']);
    var div = base[f.tag] != null ? base[f.tag] : (base[f.baseTag] != null ? base[f.baseTag] : 0.54);
    var fin = function (rec) { return (rec.fw + 5 * div) / (rec.w + 5); };
    var dur = function (rec) { return (rec.fl + 5 * div) / (rec.l + 5); };
    X.push([round4_((fin(f.dogRec) + dur(f.favRec)) / 2)]);
    Y.push([round4_((fin(f.favRec) + dur(f.dogRec)) / 2)]);
    AC.push([f.pDog == null ? '' : fmtOdds_(f.dogOdds) + (f.bestDog ? ' | ' + fmtOdds_(f.bestDog.odds) + ' ' + f.bestDog.book : ' | no bettable book')]);
    AD.push([f.pDog == null ? '' : fmtOdds_(f.favOdds) + (f.bestFav ? ' | ' + fmtOdds_(f.bestFav.odds) + ' ' + f.bestFav.book : ' | no bettable book')]);
    AE.push([f.fiveR && f.props.o45 && f.props.o45.prob != null ? f.props.o45.prob : '']);
  }
  sh.getRange(2, 6, NC, 1).setValues(F).setNumberFormat('0.0%');
  sh.getRange(2, 14, NC, 1).setValues(N).setNumberFormat('0.0%');
  sh.getRange(2, 18, NC, 1).setValues(R).setNumberFormat('0.000');
  sh.getRange(2, 24, NC, 1).setValues(X).setNumberFormat('0.0%');
  sh.getRange(2, 25, NC, 1).setValues(Y).setNumberFormat('0.0%');
  sh.getRange(2, 29, NC, 1).setValues(AC);
  sh.getRange(2, 30, NC, 1).setValues(AD);
  sh.getRange(2, 31, NC, 1).setValues(AE).setNumberFormat('0.0%');
  sh.getRange(2, 32, NC, 1).setValues(AF);
  sh.getRange(2, 33, NC, 1).setValues(AG).setNumberFormat('0.0%');
  sh.getRange(2, 34, NC, 1).setValues(AH);
}

function ensureHeader_(sh, col, text) {
  if (sh.getMaxColumns() < col) sh.insertColumnsAfter(sh.getMaxColumns(), col - sh.getMaxColumns());
  var c = sh.getRange(1, col); if (c.getValue() !== text) c.setValue(text).setFontWeight('bold');
}

// Baselines: col A weight key ("125", "w115", "185-5"), col D decision %. Finish rate = 1 − decision.
function baselineFinishRates_(ss) {
  var out = {}; var sh = ss.getSheetByName('Baselines'); if (!sh) return out;
  var v = sh.getRange(1, 1, sh.getLastRow(), 4).getValues();
  v.forEach(function (row) { var k = String(row[0]).trim(), d = row[3]; if (k && typeof d === 'number' && d > 0 && d < 1) out[k] = 1 - d; });
  return out;
}

function writeFeed_(ss, card) {
  var sh = ss.getSheetByName('Feed') || ss.insertSheet('Feed');
  sh.clear();
  var hdr = [['Event', card.name, 'Date', card.date, 'Loaded', new Date()], ['pk', card.pk, '', '', 'Books excluded', EXCLUDE_BOOKS.join(', ')], ['ufc.com event', card.url, 'BFO page', card.bfo, '', '']];
  sh.getRange(1, 1, 3, 6).setValues(hdr);
  var rows = [['order', 'type', 'tag', 'dog', 'fav', 'dog % (median devig)', 'dog % OPEN', 'drift', 'n books', 'dog consensus', 'fav consensus', 'best dog', 'best fav',
    'GTD % (exch-blended)', 'GTD % books only', 'O1.5 %', 'O2.5 %', 'O4.5 %', 'dog DEC', 'dog KO', 'dog SUB', 'dog ITD', 'fav DEC', 'fav KO', 'fav SUB', 'fav ITD',
    'dog rec W/finW/L/finL', 'fav rec W/finW/L/finL', 'all books (book:dog/fav open→now)', 'dog stats (SLpM/SApM/TD15/TDD/Sub15/KD15/avg min)', 'fav stats', 'weigh-in', 'exch fair dog %', 'prop outliers vs exchange (GTD / O-U / method; yes-side)']];
  var p = function (s) { return s && s.prob != null ? s.prob : ''; }; var mo = function (s) { return s && s.medOdds ? s.medOdds : ''; };
  card.fights.forEach(function (f) {
    rows.push([f.order, f.type, f.tag, f.dog, f.fav, f.pDog, f.pDogOpen, (f.pDog != null && f.pDogOpen != null) ? f.pDog - f.pDogOpen : '', f.nBooks, f.dogOdds, f.favOdds,
      f.bestDog ? fmtOdds_(f.bestDog.odds) + ' ' + f.bestDog.book : '', f.bestFav ? fmtOdds_(f.bestFav.odds) + ' ' + f.bestFav.book : '',
      p(f.props.gtd), f.props.gtd && f.props.gtd.bookProb != null ? f.props.gtd.bookProb : '', p(f.props.o15), p(f.props.o25), p(f.props.o45),
      mo(f.props.dog.dec), mo(f.props.dog.ko), mo(f.props.dog.sub), mo(f.props.dog.itd), mo(f.props.fav.dec), mo(f.props.fav.ko), mo(f.props.fav.sub), mo(f.props.fav.itd),
      f.dogRec.w + '/' + f.dogRec.fw + '/' + f.dogRec.l + '/' + f.dogRec.fl, f.favRec.w + '/' + f.favRec.fw + '/' + f.favRec.l + '/' + f.favRec.fl,
      f.books.map(function (b) { var d = f.dogIs1 ? [b.op1, b.op2, b.o1, b.o2] : [b.op2, b.op1, b.o2, b.o1]; return b.book + ':' + fmtOdds_(d[0]) + '/' + fmtOdds_(d[1]) + '→' + fmtOdds_(d[2]) + '/' + fmtOdds_(d[3]); }).join('  '),
      f.dogStats || '', f.favStats || '', f.weighNote || '', f.exchDog == null ? '' : f.exchDog, propOutl_(f)]);
  });
  sh.getRange(5, 1, rows.length, rows[0].length).setValues(rows);
  sh.getRange(6, 6, rows.length - 1, 3).setNumberFormat('0.0%');
  sh.getRange(6, 14, rows.length - 1, 5).setNumberFormat('0.0%');
  sh.setFrozenRows(5);
}

// Feed text: every prop where an exchange quotes the market and a bettable book beats it by >= OUTLIER_MIN
function propOutl_(f) {
  var items = [], P = f.props || {};
  var lab = { gtd: 'GTD', o15: 'O1.5', o25: 'O2.5', o45: 'O4.5' };
  Object.keys(lab).forEach(function (k) { var s = P[k]; if (s && s.outl && s.outl.length) items.push(lab[k] + ': ' + s.outl.slice(0, 2).map(function (o) { return fmtOdds_(o.odds) + ' ' + o.book + ' (+' + (Math.round(o.delta * 1000) / 10) + (o.delta >= OUTLIER_TRAP ? ' TRAP' : '') + ')'; }).join(', ') + ' vs exch ' + Math.round(s.exch * 1000) / 10 + '%'); });
  [['dog', f.dog], ['fav', f.fav]].forEach(function (side) { var m = P[side[0]] || {}; ['dec', 'ko', 'sub', 'itd'].forEach(function (k) { var s = m[k]; if (s && s.outl && s.outl.length) items.push(side[1].split(' ').pop() + ' ' + k.toUpperCase() + ': ' + s.outl.slice(0, 2).map(function (o) { return fmtOdds_(o.odds) + ' ' + o.book + ' (+' + (Math.round(o.delta * 1000) / 10) + (o.delta >= OUTLIER_TRAP ? ' TRAP' : '') + ')'; }).join(', ') + ' vs exch ' + Math.round(s.exch * 1000) / 10 + '%'); }); });
  return items.join('  ||  ');
}
function fmtOdds_(o) { if (o === '' || o == null || isNaN(o)) return ''; return (o > 0 ? '+' : '') + Math.round(o); }
function round4_(x) { return Math.round(x * 10000) / 10000; }


// ================================================================ SNAPSHOT + GRADE
var SNAP_HDR = ['pk', 'date', 'event', 'tab', 'row', 'tag', 'dog', 'fav', 'K code', 'Tap C', 'Junk D', 'Tip E', 'dog open F', 'dog listed G (sheet)', 'dog CLOSE (consensus)',
  'Markov J', 'model Q', 'Fin|DogWin X', 'Fin|FavWin Y', 'GTD fighter Z', 'flag AA', 'momentum AB', 'bet rec', 'GTD/ITD play', 'Fight GTD model', 'GTD listed', 'GTD close',
  'O/U play', 'O1.5 listed', 'O2.5 listed', 'O2.5 model', 'O4.5 listed', 'dog price (D)', 'fav price (I)', 'snapshot time',
  'winner', 'method', 'round', 'time', 'secs', 'dog won', 'GTD', 'over 1.5', 'over 2.5', 'over 4.5', 'Brier close', 'Brier model Q', 'Brier Markov J', 'rec ML P/L (u)', 'GTD/ITD play P/L (u)', 'graded', 'Markov P(dec)', 'Brier GTD close', 'Brier GTD model', 'Brier GTD Markov', 'exch fair dog (AG)', 'Brier exch fair',
  // v2.7 — method layer: your Tapology/projection inputs, the model's method shares, model vs market joint probabilities, graded
  'in dog DEC (AD)', 'in dog KO (AE)', 'in dog SUB (AF)', 'in fav DEC (AH)', 'in fav KO (AI)', 'in fav SUB (AJ)',
  'model dog DEC (V)', 'model dog KO (W)', 'model dog SUB (X)', 'model fav DEC (Z)', 'model fav KO (AA)', 'model fav SUB (AB)',
  'P model dogDEC', 'P model dogKO', 'P model dogSUB', 'P model favDEC', 'P model favKO', 'P model favSUB',
  'P mkt dogDEC', 'P mkt dogKO', 'P mkt dogSUB', 'P mkt favDEC', 'P mkt favKO', 'P mkt favSUB',
  'method outcome', 'Brier method model', 'Brier method mkt'];

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