/**
 * Stale-input guard (fix B, approved by Sean Nov 19 2026).
 *
 * Problem it fixes: hand inputs (Markov, Tap/Junk/Tip, K codes, manual adjust, method inputs, typed DEC overrides in V/Z)
 * live on a ROW, not on a fight. When a new card loads or a bout is rebooked onto a row, the old inputs stayed and were
 * used for the new fight.
 *
 * What it does:
 *  - Calculator AJ = the bout ("dog|fav") the row's hand inputs were entered for. Written by onEdit when Sean edits an
 *    input, by the loader when it resets a row, and by the menu item "Confirm inputs on selected rows".
 *    (Writes through the Sheets API, e.g. the Markov watcher, do not fire onEdit; the watcher writes AJ itself.)
 *  - Calculator AK = "STALE INPUTS (entered for X vs Y)" when AJ is set, differs from the row's current fight, and the row
 *    still has hand inputs. Main Card / Prelims Bet Rec (N) shows "check inputs: ..." on that row instead of a rec.
 *  - Loader, new card (after "Clear last card's hand inputs" = Yes): restore the model formulas in V, W, X, Z, AA, AB on
 *    every card row (typed overrides are replaced by the formula) and blank every stamp.
 *  - Loader, booking change on a row (one fighter replaced): clear that row's hand inputs, restore its V..AB formulas,
 *    blank its stamp, and say so in the load message.
 * Formula restore uses the most common formula (R1C1) in that column among the tab's card rows, so a typed number on one
 * row never becomes the template.
 */
var GUARD = {
  STAMP_COL: 36, FLAG_COL: 37,                 // Calculator AJ, AK
  CALC_INPUT_COLS: [3, 4, 5, 10, 11, 13, 35],  // Calculator C D E J K M AI
  TAB_INPUT_COLS: [30, 31, 32, 34, 35, 36, 42, 43],  // Main Card / Prelims AD AE AF AH AI AJ AP AQ
  TAB_FORMULA_COLS: [22, 23, 24, 26, 27, 28],  // V W X Z AA AB
  TABS: ['Main Card', 'Prelims']
};
var GUARD_NEWCARD_DONE = false;  // set by guardNewCard_ for the rest of this load, so rows are not reset twice

// Calculator row <-> [tab, tab row], read from the Calculator column A formulas (each points at a fighter cell on a tab)
function guardMap_(ss) {
  var calc = ss.getSheetByName('Calculator'), f = calc.getRange(2, 1, 16, 1).getFormulas(), m = { calc: {}, tab: {} };
  for (var i = 0; i < f.length; i++) {
    var x = /^=\s*'?(Main Card|Prelims)'?!\$?B\$?(\d+)\s*$/.exec(String(f[i][0]));
    if (!x) continue;
    m.calc[2 + i] = [x[1], Number(x[2])];
    m.tab[x[1] + '#' + x[2]] = 2 + i;
  }
  return m;
}

function guardPair_(calc, r) {
  var v = calc.getRange(r, 1, 1, 2).getDisplayValues()[0], a = String(v[0]).trim(), b = String(v[1]).trim();
  return a && b ? a + '|' + b : '';
}

function guardStamp_(ss, calcRow) {
  var calc = ss.getSheetByName('Calculator');
  calc.getRange(calcRow, GUARD.STAMP_COL).setValue(guardPair_(calc, calcRow));
}

// Simple trigger: Sean edits an input cell -> stamp that fight's Calculator row with the fight now on it.
function onEdit(e) {
  try {
    if (!e || !e.range) return;
    var sh = e.range.getSheet(), name = sh.getName();
    if (name !== 'Calculator' && GUARD.TABS.indexOf(name) < 0) return;
    var c0 = e.range.getColumn(), c1 = e.range.getLastColumn(), r0 = e.range.getRow(), r1 = e.range.getLastRow();
    var cols = name === 'Calculator' ? GUARD.CALC_INPUT_COLS : GUARD.TAB_INPUT_COLS.concat(GUARD.TAB_FORMULA_COLS);
    if (!cols.some(function (c) { return c >= c0 && c <= c1; })) return;
    var ss = e.source || SpreadsheetApp.getActive(), m = guardMap_(ss);
    for (var r = r0; r <= r1; r++) {
      var cr = name === 'Calculator' ? (m.calc[r] ? r : 0) : (m.tab[name + '#' + r] || 0);
      if (cr) guardStamp_(ss, cr);
    }
  } catch (err) { /* never block an edit */ }
}

// Menu: Sean has checked the flagged row's inputs belong to the fight now on it.
function guardConfirmRows() {
  var ss = SpreadsheetApp.getActive(), rg = ss.getActiveRange(), sh = rg.getSheet(), name = sh.getName(), m = guardMap_(ss), n = 0;
  for (var r = rg.getRow(); r <= rg.getLastRow(); r++) {
    var cr = name === 'Calculator' ? (m.calc[r] ? r : 0) : (m.tab[name + '#' + r] || 0);
    if (cr) { guardStamp_(ss, cr); n++; }
  }
  ss.toast(n ? n + ' row(s) confirmed: inputs now belong to the fight on the row.' : 'Select a fight row on Calculator, Main Card or Prelims first.', 'Stale-input guard', 6);
}

// Most common formula (R1C1) per V..AB column among a tab's card rows: the template used to restore a row.
function guardCanon_(ss) {
  var out = {}, m = guardMap_(ss);
  GUARD.TABS.forEach(function (t) {
    var sh = ss.getSheetByName(t), rows = Object.keys(m.tab).filter(function (k) { return k.indexOf(t + '#') === 0; })
      .map(function (k) { return Number(k.split('#')[1]); });
    if (!sh || !rows.length) return;
    var r0 = Math.min.apply(null, rows), r1 = Math.max.apply(null, rows);
    out[t] = { rows: [r0, r1] };
    GUARD.TAB_FORMULA_COLS.forEach(function (c) {
      var f = sh.getRange(r0, c, r1 - r0 + 1, 1).getFormulasR1C1(), n = {}, best = '', bn = 0;
      f.forEach(function (x) { if (x[0]) { n[x[0]] = (n[x[0]] || 0) + 1; if (n[x[0]] > bn) { bn = n[x[0]]; best = x[0]; } } });
      out[t][c] = best;
    });
  });
  return out;
}

function guardRestoreFormulas_(sh, row, canonTab) {
  var done = 0;
  GUARD.TAB_FORMULA_COLS.forEach(function (c) {
    var g = sh.getRange(row, c);
    if (!g.getFormula() && canonTab && canonTab[c]) { g.setFormulaR1C1(canonTab[c]); done++; }
  });
  return done;
}

// One row: clear hand inputs (typed values only, formulas kept), restore V..AB formulas, blank the stamp.
function guardResetRow_(ss, calcRow, canon) {
  var m = guardMap_(ss), t = m.calc[calcRow], calc = ss.getSheetByName('Calculator');
  GUARD.CALC_INPUT_COLS.forEach(function (c) { var g = calc.getRange(calcRow, c); if (!g.getFormula()) g.clearContent(); });
  if (t) {
    var sh = ss.getSheetByName(t[0]);
    GUARD.TAB_INPUT_COLS.forEach(function (c) { var g = sh.getRange(t[1], c); if (!g.getFormula()) g.clearContent(); });
    guardRestoreFormulas_(sh, t[1], canon[t[0]]);
  }
  calc.getRange(calcRow, GUARD.STAMP_COL).setValue('');
}

// Loader hook: new card, after clearCardInputs_ (the "Clear last card's hand inputs" = Yes branch).
function guardNewCard_(ss) {
  try {
    GUARD_NEWCARD_DONE = true;
    var canon = guardCanon_(ss), m = guardMap_(ss), restored = 0;
    Object.keys(m.calc).forEach(function (cr) {
      var t = m.calc[cr], sh = ss.getSheetByName(t[0]);
      restored += guardRestoreFormulas_(sh, t[1], canon[t[0]]);
      ss.getSheetByName('Calculator').getRange(Number(cr), GUARD.STAMP_COL).setValue('');
    });
    if (typeof WARN !== 'undefined' && restored) WARN.push('Stale-input guard: ' + restored + ' typed method override(s) in V/W/X/Z/AA/AB replaced by the model formula for the new card.');
  } catch (err) { if (typeof WARN !== 'undefined') WARN.push('!!! Stale-input guard (new card) failed: ' + err); }
}

// Loader hook: a booking change on a row (writeTab_ found a different fighter on that row).
function guardBookingChange_(sh, tabRow, oldPair, newPair) {
  try {
    if (GUARD_NEWCARD_DONE) return;  // new card: inputs already wiped and formulas restored
    var ss = SpreadsheetApp.getActive(), m = guardMap_(ss), cr = m.tab[sh.getName() + '#' + tabRow];
    if (!cr) return;
    guardResetRow_(ss, cr, guardCanon_(ss));
    if (typeof WARN !== 'undefined') WARN.push(sh.getName() + ' row ' + tabRow + ': hand inputs cleared for ' + oldPair + ' -> ' + newPair + ' (stale-input guard). Re-enter Markov, Tap/Junk/Tip, codes, manual adjust and method inputs for the new bout.');
  } catch (err) { if (typeof WARN !== 'undefined') WARN.push('!!! Stale-input guard (booking change) failed: ' + err); }
}
