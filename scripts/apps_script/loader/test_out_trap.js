// Block 47: OUT-2 on Gordon's BFO books (Feed 02:19Z), using the loader's own helpers and the patched bestPrice lines.
const fs = require('fs'); const src = fs.readFileSync(process.argv[2] || __dirname + "/Code_v2.8_patched.gs", 'utf8');
global.SpreadsheetApp = {}; global.PropertiesService = { getScriptProperties: () => ({ getProperty: () => null }) }; global.UrlFetchApp = {}; global.Utilities = {}; global.Logger = { log() {} };
eval(src);
const books = [['Polymarket', 295, -361], ['Kalshi', 285, -400], ['FanDuel', 300, -380], ['Caesars', 420, -625], ['BetRivers', 275, -350], ['BetWay', 280, -385], ['Novig', 317, -344]]
  .map(([book, o1, o2]) => ({ book, o1, o2 }));
const body = src.split('\n'); const i = body.findIndex(l => l.includes('var exRef = exchFair_(books);'));
eval(body.slice(i, i + 4).join('\n'));            // exRef + patched bestPrice, verbatim from the file
const d = bestPrice(true), f = bestPrice(false);
console.log('exch fair dog', exRef.p.toFixed(4), '(', exRef.src, ') | D', d.odds, d.book, '| I', f.odds, f.book);
console.log(d.odds === 300 && d.book === 'FanDuel' && f.odds === -350 && f.book === 'BetRivers' ? 'PASS OUT-2 Gordon: D +300 FanDuel (Caesars +420 excluded), I -350 BetRivers' : 'FAIL');
const allTrap = books.map(b => b.book === 'Caesars' ? b : { ...b, o1: 1000 });  // every bettable dog price a TRAP
const keep = books; books.length = 0; allTrap.forEach(b => books.push(b));
const d2 = bestPrice(true); console.log(d2 === null || d2 === undefined ? 'PASS OUT-2 all books TRAP -> null (loader falls back to consensus)' : 'FAIL all-TRAP: ' + JSON.stringify(d2));
