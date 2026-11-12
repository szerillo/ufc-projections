// Kirk round 28 B: Gordon's D/I under v2.7 and v2.8 from the live Feed books (read 2026-11-12 ~20:35Z), loader's own code.
const fs = require('fs'); const run = (file) => { const src = fs.readFileSync(file, 'utf8');
  global.SpreadsheetApp = {}; global.PropertiesService = { getScriptProperties: () => ({ getProperty: () => null }), getDocumentProperties: () => ({}) }; global.UrlFetchApp = {}; global.Utilities = {}; global.Logger = { log() {} };
  const books = [['Polymarket', 295, -361], ['Kalshi', 285, -400], ['FanDuel', 310, -400], ['Caesars', 420, -625], ['BetRivers', 300, -400], ['BetWay', 280, -385], ['Novig', 326, -344]].map(([book, o1, o2]) => ({ book, o1, o2 }));
  return eval(src + `;(function(){ var books = ${JSON.stringify(books)}; var body = ${JSON.stringify(src)}.split('\\n'); var i = body.findIndex(function (l) { return l.indexOf('var bestPrice = function (side1)') >= 0; });
    var exRef = exchFair_(books); eval(body.slice(i, i + 3).join('\\n')); var d = bestPrice(true), f = bestPrice(false); return { ex: exRef.p, D: d.odds + ' ' + d.book, I: f.odds + ' ' + f.book }; })()`); };
console.log('v2.7', JSON.stringify(run('/tmp/lscan/scripts/apps_script/loader/Code_v2.7_installed.gs')));
console.log('v2.8', JSON.stringify(run('/tmp/r28/Code28.gs')));
console.log('v2.9', JSON.stringify(run('/tmp/r28/lg/Code_v2.9_guard.gs')));
