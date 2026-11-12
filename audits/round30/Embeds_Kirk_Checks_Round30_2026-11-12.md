# Sheet loader v2.9 and Kirk checks, round 30 (2026-11-12)

Nothing went to main, and the sheet was only read, never edited.
- Loader v2.9 is on branch `loader-guard` at 1968dcfc, file sha256 `c8d938d7df26…`.
- The install steps are on branch `publish-to-site` at d94b7e05 (PUBLISH.md, Thursday install).
- Evidence is in `audits/round30/` on `embeds-v5`.

## Call 1: v2.9 = v2.8 + the guard, nothing else
- **Diff:** `Code_v2.8_patched.gs => Code_v2.9_guard.gs | 68 +++++++++++++++++++---` (60 insertions, 8 deletions). The full diff is in the appendix and in `loader_v28_to_v29.diff`.
- **Price and TRAP code is byte-identical.** The check (`price_identity.py`, sha256 of each piece) covers:
  - functions: imp_, toAmer_, median_, validOdds_, payout_, included_, bettable_, devig2_, wmedian_, exchFair_, outliers_, fmtOutl_;
  - the price constants;
  - the buildCard_ best-price (D/I) block and the consensus/props block;
  - writeTab_'s D/I/S/T writers;
  - writeCalculator_ (identical once the held-row lines are taken out).
- **Block 47 TRAP test:** passes on v2.9 (`test_out_trap.js`: D +300 FanDuel with Caesars +420 excluded; all-TRAP falls back to consensus).
- **The 13 round-29 plants, now 25 with A, C and D:** v2.9 passes 25/25 and v2.8 passes 5/25.
- **Correction:** round 29's v2.9 (6864fa0d) passed only 14/25. It cleared a row when Novig was down, matched override names as fragments, and keyed the count memory on the BFO page id. All three are fixed in c8d938d7.
- **Re-pinned:** PUBLISH.md now installs v2.9 once (T2 opens the file at commit 1968dcfc). Rollback goes to v2.8 (keeps the TRAP rule) or v2.7 (full revert).
- **Rehearsal:** `rehearse_go_live.sh` reads the sheet export, not the loader. It refuses today ("export on main is the old one"). Its real run against a v2.9-produced export happens after T4/T5 and Sean's publish.

## Call 2: T1-T5 (PUBLISH.md, Thursday install)
The full table is on branch `publish-to-site`. In short:
- **T1:** set the BETTABLE_BOOKS property, or leave it if it's already there.
- **T2:** paste v2.9 from the fixed-commit raw link; check line 2; Claude confirms the hash.
- **T3:** paste the publish script only if Preview isn't already build b47-out.
- **T4:** Refresh prices. Expect no `!!!` line, 13 fights, Gordon D +310, AH "TRAP, excluded from D/I", rec "-".
- **T5:** Preview publish. Expect `b47-out · 13/13 · 13/13 · TRAP prices in D/I 0`.

Every step has an abort line.

## A. Source failures
| Plant | v2.8 | v2.9 |
|---|---|---|
| BFO HTTP 503, bout dropped | row cleared | **REFUSED, source unreachable**; nothing written |
| BFO empty page | row cleared | same refusal, nothing written |
| BFO down, nothing dropped | **every D blanked** (all rows "") | nothing written |
| Novig timeout, BFO no longer lists the bout | row cleared | REFUSED ("unreachable source (Novig)"), row kept |
| Novig returns no events | row cleared | same, row kept |
| Both down | row cleared | nothing written |

An outage now reads as "unknown", never as "not listed". v2.8 also blanked every price on a BFO outage when no other quote existed (`a3_v28.js`).

## B. Caesars +420 is not a real price
- **BFO read at 20:52:54Z:** Gordon +420 / Costa -625 in BFO's Caesars column.
- **Caesars' own US quote** (williamhill_us in the sharp-tracker odds archive), across 579 snapshots from Nov 5 to Nov 12, never showed +420:
  - Nov 5: +310
  - Nov 6: +300
  - Nov 12 18:10Z: +310
  - last read, 20:32:46Z: +310 / -400
- **Conclusion:** BFO's line is stale or bad. The TRAP rule removed a bad quote, not a real best price. D = +310 is the true best US price (FanDuel, and Caesars too by its own feed), and the rec ("-") is the same from either book.
- **Wording:** "Outlier excluded" stays correct. No corrections entry is needed, because the v2.7 "BET Costa" rec was never published.
- **Limit:** Caesars' own site is blocked in this Chrome, so it was not checked directly.

## C. Override names
| Plant | v2.9 |
|---|---|
| Wrong name "Costas" | nothing removed: "matches 0 rows" |
| Shared name "Costa" (Melquizael Costa and a planted Cesar Costa) | nothing removed: "matches 2 rows (shared name)" |
| Same card, full name "Melquizael Costa" | exactly that bout removed |
| Bout still on ufc.com ("Hokit") | nothing removed: "still on ufc.com" |
| Fragment "ost" | nothing removed |

## D. Count-drop alert
- **Assumption tested:** "the bout count compares the same card".
  - Round 29 keyed it on the BFO page id. That id changes when BFO re-files or splits a card, and it falls back to the ufc.com URL when BFO is down. Either way the alert went silent: plant D1 (BFO re-files the card as 4499) failed under round 29's file.
  - Fixed by keying on the ufc.com event URL, which is what the refresh itself reads. D1 now warns.
- **Also tested:**
  - D2: a bout moved to another card, still on Novig → refused plus a count warning; the override clears it.
  - D3: one bout added and one dropped (count stays 13) → the count line is silent by design, but the row-level refusal still fires. The count line is a second signal, not the guard.

## Kirk decides
- Run T1-T5 when ready; Claude reads Gordon back after T5.

## Appendix: full diff v2.8 -> v2.9
```diff
diff --git a/scripts/apps_script/loader/Code_v2.8_patched.gs b/scripts/apps_script/loader/Code_v2.9_guard.gs
index 230e93a0..181e6cb1 100644
--- a/scripts/apps_script/loader/Code_v2.8_patched.gs
+++ b/scripts/apps_script/loader/Code_v2.9_guard.gs
@@ -1,4 +1,10 @@
 /**
+ * PATCH loader-guard (Kirk rounds 29-30, v2.9 on top of v2.8): a refresh never clears a row whose bout is missing from
+ *   ufc.com but still listed on BestFightOdds (any book, Polymarket included) or Novig; it keeps the row as it was and warns.
+ *   A drop in the ufc.com bout count against the last load is the first line of the alert. Removing a really cancelled bout
+ *   that a price source still lists takes UFC > Remove a cancelled bout (named, confirmed; the name must match exactly one row on the card).
+ *   A source that fails or returns nothing is never read as "not listed": BestFightOdds unreachable = the whole refresh
+ *   writes nothing; Novig unreachable = no row is cleared. The bout-count memory is keyed on the ufc.com event URL.
  * PATCH loader-patch Block 47: TRAP outlier prices excluded from D/I (best price); AH marks them 'excluded from D/I'.
  * UFC Model — card loader (Apps Script)  v2.7  Nov 5 2026 (Snapshots archive the method layer: your AD-AJ inputs, model shares, model vs market joint method probs, 6-way method Brier)
  * v2.6.1  Oct 28 2026 (warns when ufc.com shows <6 main for a Fight Night; accepts a tab named 'Card Order')
@@ -89,6 +95,7 @@ function onOpen() {
     .addItem('Load card by ufc.com URL…', 'loadCardByPk')
     .addItem('Refresh prices (keep openers)', 'refreshPrices')
     .addItem('Force refresh openers too', 'refreshAll')
+    .addItem('Remove a cancelled bout…', 'removeCancelledMenu')
     .addSeparator()
     .addItem('Snapshot card → Snapshots (run at close)', 'snapshotCard')
     .addItem('Grade last card (results + CLV)', 'gradeCard')
@@ -120,6 +127,34 @@ function refreshPrices() {
   var ev = currentEvent_(); if (!ev) return;
   loadCard_(ev, { writeNames: false, forceOpen: false });
 }
+function removeCancelledMenu() {   // loader-guard: the deliberate override for a cancelled bout a price source still lists
+  var ev = currentEvent_(); if (!ev) return; var ui = SpreadsheetApp.getUi();
+  var r = ui.prompt('Remove a cancelled bout', 'Last name of either fighter in the cancelled bout (exactly one bout):', ui.ButtonSet.OK_CANCEL);
+  if (r.getSelectedButton() !== ui.Button.OK || !String(r.getResponseText()).trim()) return;
+  if (ui.alert('Remove a cancelled bout', 'Clear the row for the bout with "' + r.getResponseText().trim() + '" if ufc.com no longer lists it? Hand inputs on that row are cleared too.', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
+  loadCard_(ev, { writeNames: false, forceOpen: false, allowRemove: [r.getResponseText().trim()] });
+}
+var HELD_ROW_ = { held: true }, NOVIG_DOWN_ = false;   // loader-guard: a row kept exactly as it was (bout missing from ufc.com, still priced elsewhere)
+function extSource_(card, n1, n2) {   // which price sources still list this pair ('' = none)
+  var src = [];
+  ((card && card.ext) || []).forEach(function (e) { if (((nameScore_(n1, e.a) && nameScore_(n2, e.b)) || (nameScore_(n1, e.b) && nameScore_(n2, e.a))) && src.indexOf(e.src) < 0) src.push(e.src); });
+  return src.join(', ');
+}
+function resolveRemove_(ss, opt) {   // the override names ONE bout: the name must match exactly one row (whole words) on Main Card + Prelims
+  opt.removeRow = null; if (!opt.allowRemove || !opt.allowRemove.length) return;
+  var k = normTxt_(opt.allowRemove[0]), hits = [];
+  [['Main Card', MAIN_ROWS], ['Prelims', PRE_ROWS]].forEach(function (t) { var sh = ss.getSheetByName(t[0]); if (!sh) return; var v = sh.getRange(t[1][0], 2, t[1][1] - t[1][0] + 1, 2).getValues();
+    v.forEach(function (r, i) { if (k.trim() && (normTxt_(r[0]).indexOf(k) >= 0 || normTxt_(r[1]).indexOf(k) >= 0)) hits.push(t[0] + '#' + (t[1][0] + i)); }); });
+  if (hits.length === 1) opt.removeRow = hits[0];
+  else WARN.unshift('!!! Remove a cancelled bout: "' + opt.allowRemove[0] + '" matches ' + hits.length + ' rows on this card (' + (hits.length ? 'shared name: ' + hits.join(', ') : 'no fighter by that name') + '). Nothing was removed; use the fighter\'s full name.');
+}
+function allowedRemove_(opt, sh, row) { return !!opt.removeRow && opt.removeRow === sh.getName() + '#' + row; }
+function countGuard_(card, opt) {   // loud warning when ufc.com lists fewer bouts than at the last load of this card
+  var P = PropertiesService.getDocumentProperties(), key = 'UFC_BOUTS_' + String(card.url).replace(/[^A-Za-z0-9]+/g, '_'),   // keyed on the ufc.com event URL: the BFO page id (pk) changes when BFO splits a card or is down
+      prev = Number(P.getProperty(key) || 0), n = card.ufcCount;
+  var msg = (prev && n < prev) ? '!!! ufc.com now lists ' + n + ' bouts for this card; the last load had ' + prev + '. ufc.com may be mid-edit: check every row below before publishing.' : '';
+  return { msg: msg, save: function (refused) { if (!refused || opt.allowRemove) P.setProperty(key, String(n)); } };
+}
 function refreshAll() {
   var ev = currentEvent_(); if (!ev) return;
   loadCard_(ev, { writeNames: false, forceOpen: true });
@@ -379,7 +414,7 @@ function novigEvents_() {
       }
       Object.keys(o).forEach(function (k) { walk(o[k]); }); })(j);
     return out;
-  } catch (e) { WARN.push('Novig events: ' + e.message); return []; }
+  } catch (e) { WARN.push('Novig events: ' + e.message); NOVIG_DOWN_ = true; return []; }
 }
 function novigMarkets_(eventId) {
   try {
@@ -578,7 +613,7 @@ function buildCard_(ev) {
   var cands;
   if (ev.bfo) cands = String(ev.bfo).split(',').map(function (p) { return { path: p.trim() }; }).filter(function (p) { return p.path; });
   else { var all = bfoCandidates_(evc.date); var near = all.filter(function (e) { return e.near; }); cands = near.length ? near : all.slice(0, 3); }
-  var best = { books: [], fights: [], path: '' }, paths = [], bookSeen = {};
+  var best = { books: [], fights: [], path: '' }, paths = [], bookSeen = {}, bfoErr_ = 0;   // loader-guard: bfoErr_
   for (var ci = 0; ci < cands.length; ci++) {
     try { var be = bfoEvent_(cands[ci].path); var hits = 0;
       evc.bouts.forEach(function (b) { be.fights.forEach(function (f) { if ((nameScore_(b.red, f.f1) && nameScore_(b.blue, f.f2)) || (nameScore_(b.red, f.f2) && nameScore_(b.blue, f.f1))) hits++; }); });
@@ -586,7 +621,7 @@ function buildCard_(ev) {
       paths.push(cands[ci].path);
       be.fights.forEach(function (f) { f.path = cands[ci].path; best.fights.push(f); });
       be.books.forEach(function (bk) { if (!bookSeen[bk]) { bookSeen[bk] = 1; best.books.push(bk); } });
-    } catch (e) { WARN.push('BFO ' + cands[ci].path + ': ' + e.message); }
+    } catch (e) { WARN.push('BFO ' + cands[ci].path + ': ' + e.message); bfoErr_++; }
   }
   best.path = paths.join(',');
   if (!paths.length) WARN.push('No BestFightOdds page matched this card — prices blank.');
@@ -596,9 +631,14 @@ function buildCard_(ev) {
   var athHtml = getAll_(athUrls); var athMap = {}; athUrls.forEach(function (u, i) { athMap[u] = ufcAthlete_(athHtml[i]); });
   var openUrls = best.fights.map(function (f) { return 'https://www.bestfightodds.com/fighters/' + f.slug1; });
   var openHtml = openUrls.length ? getAll_(openUrls) : [];
-  var out = { ordered: !!evc.ordered, name: evc.name, date: evc.date, pk: paths.length ? (paths[0].match(/-(\d+)$/) || ['', evc.url])[1] : evc.url, url: evc.url, bfo: best.path, fights: [] };
+  var ext = best.fights.map(function (x) { return { a: x.f1, b: x.f2, src: 'BestFightOdds' + (x.ml && x.ml.Polymarket ? ' (Polymarket too)' : '') }; });   // loader-guard
+  var out = { ufcCount: evc.bouts.length, ext: ext, ordered: !!evc.ordered, name: evc.name, date: evc.date, pk: paths.length ? (paths[0].match(/-(\d+)$/) || ['', evc.url])[1] : evc.url, url: evc.url, bfo: best.path, fights: [] };
   var mainCount = 0;
-  var nvEvents = NOVIG_ON ? novigEvents_() : [], nvHit = 0;
+  NOVIG_DOWN_ = false; var nvEvents = NOVIG_ON ? novigEvents_() : [], nvHit = 0;
+  nvEvents.forEach(function (e) { out.ext.push({ a: e.home, b: e.away, src: 'Novig' }); });   // loader-guard
+  out.srcDown = [];   // loader-guard: a source that failed or came back empty is unknown, never 'not listed'
+  if (bfoErr_ || !paths.length) out.srcDown.push('BestFightOdds');
+  if (NOVIG_ON && (NOVIG_DOWN_ || !nvEvents.length)) out.srcDown.push('Novig');
   evc.bouts.forEach(function (b, idx) {
     var f = null, fi = -1; for (var i = 0; i < best.fights.length; i++) { var x = best.fights[i]; if ((nameScore_(b.red, x.f1) && nameScore_(b.blue, x.f2)) || (nameScore_(b.red, x.f2) && nameScore_(b.blue, x.f1))) { f = x; fi = i; break; } }
     // Novig (v2.4): find the event by the two names, pull its markets, fold them in as book "Novig" (weight by volume)
@@ -690,7 +730,9 @@ function buildCard_(ev) {
 function loadCard_(ev, opt) {
   var ss = SpreadsheetApp.getActive(); syncLayout_(ss);
   WARN.length = 0;
-  var card = buildCard_(ev); var pk = card.pk;
+  var card = buildCard_(ev); var pk = card.pk; opt.card = card; opt.refused = 0;   // loader-guard
+  if (!opt.writeNames && card.srcDown.indexOf('BestFightOdds') >= 0) { SpreadsheetApp.getUi().alert('!!! REFUSED, source unreachable: BestFightOdds failed or returned no page for this card. Nothing was written; every row and price is as it was. Refresh again in a few minutes.' + (WARN.length ? '\n\n' + WARN.join('\n') : '')); return; }
+  var cg = countGuard_(card, opt); resolveRemove_(ss, opt);
   // New card (different event pk than the one on the sheet): wipe last card's hand inputs and take fresh openers.
   var feed = ss.getSheetByName('Feed'); var prevPk = feed ? String(feed.getRange('B2').getValue()) : '';
   var cleared = false;
@@ -731,7 +773,9 @@ function loadCard_(ev, opt) {
   writeFeed_(ss, card);
   var edgesHit = writeEdges_(ss, card);
   var noOdds = card.fights.filter(function (f) { return f.pDog == null; }).map(function (f) { return f.dog + ' vs ' + f.fav; });
-  var msg = card.name + ' (' + card.date + ') loaded: ' + main.length + ' main / ' + pre.length + ' prelim fights.' + (edgesHit ? ' Edges tab: ' + edgesHit + ' fighters priced.' : '');
+  if (opt.removeRow && !opt.removed) WARN.unshift('!!! Remove a cancelled bout: ' + opt.removeRow.replace('#', ' row ') + ' is still on ufc.com. Nothing was removed.');
+  cg.save(opt.refused);
+  var msg = (cg.msg ? cg.msg + '\n\n' : '') + card.name + ' (' + card.date + ') loaded: ' + main.length + ' main / ' + pre.length + ' prelim fights.' + (edgesHit ? ' Edges tab: ' + edgesHit + ' fighters priced.' : '');
   if (noOdds.length) msg += '\n\nNo moneyline posted yet for: ' + noOdds.join('; ') + ' (names written, prices blank — refresh later).';
   if (warn.length || WARN.length) msg += '\n\n' + warn.concat(WARN).join('\n');
   SpreadsheetApp.getUi().alert(msg);
@@ -783,7 +827,11 @@ function writeTab_(sh, fights, rows, opt) {
   if (!opt.writeNames) {   // booking changes: the row matched on one fighter, the other differs -> rewrite that cell
     var cur = sh.getRange(rows[0], 2, nRows, 2).getValues();
     for (var q = 0; q < nRows; q++) { var fq = slots[q];
-      if (!fq) { if (String(cur[q][0] || '').trim() || String(cur[q][1] || '').trim()) { WARN.push(sh.getName() + ' row ' + (rows[0] + q) + ': ' + cur[q][0] + ' vs ' + cur[q][1] + ' is no longer on this tab (moved or cancelled) — names cleared.'); sh.getRange(rows[0] + q, 1, 1, 3).clearContent(); } continue; }
+      if (!fq) { var src_ = (String(cur[q][0] || '').trim() || String(cur[q][1] || '').trim()) ? extSource_(opt.card, cur[q][0], cur[q][1]) : '';
+        if (!src_ && (String(cur[q][0] || '').trim() || String(cur[q][1] || '').trim()) && opt.card && opt.card.srcDown.length) src_ = 'an unreachable source (' + opt.card.srcDown.join(', ') + ': failed or empty, so not known)';
+        if (allowedRemove_(opt, sh, rows[0] + q)) opt.removed = true;
+        if (src_ && !allowedRemove_(opt, sh, rows[0] + q)) { WARN.unshift('!!! ' + sh.getName() + ' row ' + (rows[0] + q) + ': ' + cur[q][0] + ' vs ' + cur[q][1] + ' is missing from ufc.com but still listed on ' + src_ + '. REFUSED to clear it: row kept exactly as it was, its prices were NOT refreshed. If the bout is really off, use UFC > Remove a cancelled bout.'); slots[q] = HELD_ROW_; opt.refused = (opt.refused || 0) + 1; continue; }
+        if (String(cur[q][0] || '').trim() || String(cur[q][1] || '').trim()) { WARN.push(sh.getName() + ' row ' + (rows[0] + q) + ': ' + cur[q][0] + ' vs ' + cur[q][1] + ' is no longer on this tab (moved or cancelled) — names cleared.'); sh.getRange(rows[0] + q, 1, 1, 3).clearContent(); } continue; }
       if (!nameScore_(cur[q][0], fq.dog)) { WARN.push(sh.getName() + ' row ' + (rows[0] + q) + ': ' + cur[q][0] + ' -> ' + fq.dog + ' (booking/spelling change)'); sh.getRange(rows[0] + q, 2).setValue(fq.dog); }
       else if (String(cur[q][0]) !== fq.dog) sh.getRange(rows[0] + q, 2).setValue(fq.dog);
       if (!nameScore_(cur[q][1], fq.fav)) { WARN.push(sh.getName() + ' row ' + (rows[0] + q) + ': ' + cur[q][1] + ' -> ' + fq.fav + ' (booking/spelling change)'); sh.getRange(rows[0] + q, 3).setValue(fq.fav); }
@@ -791,8 +839,10 @@ function writeTab_(sh, fights, rows, opt) {
     }
   }
   var A = [], D = [], I = [], S = [], T = [], tbl = [];
+  var keep = slots.indexOf(HELD_ROW_) >= 0 ? { D: sh.getRange(rows[0], 4, nRows, 1).getValues(), I: sh.getRange(rows[0], 9, nRows, 1).getValues(), S: sh.getRange(rows[0], 19, nRows, 1).getValues(), T: sh.getRange(rows[0], 20, nRows, 1).getValues(), tbl: sh.getRange(TABLE_ROW0, 14, nRows * 2, 5).getValues() } : null;   // loader-guard
   for (var r = 0; r < nRows; r++) {
     var f = slots[r];
+    if (f === HELD_ROW_) { A.push(['', '', '']); D.push(keep.D[r]); I.push(keep.I[r]); S.push(keep.S[r]); T.push(keep.T[r]); tbl.push(keep.tbl[2 * r], keep.tbl[2 * r + 1]); continue; }
     if (!f) { A.push(['', '', '']); D.push(['']); I.push(['']); S.push(['']); T.push(['']); tbl.push(['', '', '', '', ''], ['', '', '', '', '']); continue; }
     A.push([f.tag, f.dog, f.fav]);
     // D/I = best price you can actually bet (so List % and Edge are EV at YOUR price, vig included);
@@ -981,8 +1031,10 @@ function writeCalculator_(ss, fights, opt) {
   var F = [], N = [], R = [], X = [], Y = [], AC = [], AD = [], AE = [], AF = [], AG = [], AH = [];
   var NC = MAIN_ROWS[1] - MAIN_ROWS[0] + 1 + PRE_ROWS[1] - PRE_ROWS[0] + 1;   // Calculator rows 2..(1+NC)
   var curF = sh.getRange(2, 6, NC, 1).getValues(), curK = sh.getRange(2, 11, NC, 1).getValues(), curNovig = sh.getRange(2, 35, NC, 1).getValues();
+  var held = fights.indexOf(HELD_ROW_) >= 0 ? sh.getRange(2, 1, NC, 34).getValues() : null;   // loader-guard: a held row keeps every script-written cell
   for (var r = 0; r < NC; r++) {
     var f = fights[r];
+    if (f === HELD_ROW_) { var hv = held[r]; F.push([hv[5]]); N.push([hv[13]]); R.push([hv[17]]); X.push([hv[23]]); Y.push([hv[24]]); AC.push([hv[28]]); AD.push([hv[29]]); AE.push([hv[30]]); AF.push([hv[31]]); AG.push([hv[32]]); AH.push([hv[33]]); continue; }
     if (!f) { F.push(['']); N.push(['']); R.push(['']); X.push(['']); Y.push(['']); AC.push(['']); AD.push(['']); AE.push(['']); AF.push(['']); AG.push(['']); AH.push(['']); continue; }
     // Weigh-in rule (Alpha Map 2k): a FAVORITE who misses by >= 1.5 lb gets -0.03 on Q via K (only if K is blank — your D/G/GF codes win).
     // Misses <= 1 lb are noise and ignored; dog misses are already priced. Shown in AF either way.
```
