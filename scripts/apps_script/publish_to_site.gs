/**
 * UFC Model sheet -> site publisher ("Publish to site").
 *
 * Paste this file into the sheet's Apps Script project as a NEW file (publish_to_site.gs).
 * It does not touch the loader and defines no onOpen(), so the loader's UFC menu is unchanged.
 * The "Site" menu comes from an installable On-open trigger on publishMenu (see PUBLISH.md).
 *
 * What it does, only when Sean runs it:
 *   1. Reads every fight row on Main Card and Prelims whose Publish checkbox (PUBLISH_COL) is ticked.
 *   2. Builds data/pending/<slug>_projections.json: inputs, the sheet's own outputs, method shares, GTD.
 *   3. Shows a preview and asks for confirmation.
 *   4. Writes the file to szerillo/ufc-projections through the GitHub contents API.
 * A GitHub Action then recomputes every number with scripts/sheet_v47.py and only promotes the file
 * to data/<slug>_projections.json (what the site reads) if all of them match within 0.1 pts.
 *
 * The GitHub token lives in Script Properties under GITHUB_TOKEN. This script never logs or shows it.
 * Read-only on the sheet: it reads values and writes nothing back.
 */

var PUB = {
  owner: 'szerillo',
  repo: 'ufc-projections',
  branch: 'main',                 // dry runs used branch 'publish-to-site'
  publishCol: 'AR',               // checkbox column on Main Card and Prelims (first free column after AQ)
  tabs: [                         // fight rows that carry bet-rec / GTD / method formulas, and their Calculator row
    { name: 'Main Card', first: 2, last: 6, calcOffset: 0 },
    { name: 'Prelims',   first: 2, last: 9, calcOffset: 6 }
  ],
  // [Sean decides] which sheet fields are public. Set any to false to leave it out of the file.
  // The inputs block always goes out: the GitHub check needs it to recompute every number.
  include: { rec: true, flag: true, method: true, markov: true, gtd: true }
};

// No trailing underscore: Apps Script hides private (_) functions from the trigger list.
function publishMenu() {
  SpreadsheetApp.getUi().createMenu('Site')
    .addItem('Publish to site', 'publishToSite')
    .addItem('Preview publish (no upload)', 'previewPublish')
    .addToUi();
}

function previewPublish() { publish_(false); }
function publishToSite()  { publish_(true); }

function publish_(upload) {
  var ui = SpreadsheetApp.getUi();
  var props = PropertiesService.getScriptProperties();
  var slugDefault = props.getProperty('CARD_SLUG') || '';
  var resp = ui.prompt('Publish to site', 'Card slug as in cards.yml (e.g. ufc_334):', ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;
  var slug = (resp.getResponseText() || slugDefault).trim();
  if (!/^[a-z0-9_]+$/.test(slug)) { ui.alert('Slug must be lowercase letters, digits and underscores, like ufc_334.'); return; }
  props.setProperty('CARD_SLUG', slug);

  var doc = buildDoc_(slug);
  var outside = OUTSIDE_.length ? '\n\nNOT exported, below the formula rows (the site shows "Projections coming" for these):\n' + OUTSIDE_.join('\n') +
      '\nMove the bout into a formula row, or copy the row formulas down, then publish again.' : '';
  if (outside && !doc.fights.length) { ui.alert('Nothing was exported.' + outside); return; }
  if (!doc.fights.length) { ui.alert('No fights have the Publish box (column ' + PUB.publishCol + ') ticked. Nothing was exported.'); return; }
  var bad = doc.fights.filter(function (f) { return !isFinite(f.inputs.dog_odds) || !isFinite(f.inputs.fav_odds); });
  if (bad.length) { ui.alert('These ticked fights have no odds in D / I, fix them first:\n' + bad.map(function (f) { return f.dog + ' vs ' + f.fav; }).join('\n')); return; }

  var lines = doc.fights.map(function (f) {
    return f.fav + ' vs ' + f.dog + ': dog true ' + pct_(f.sheet.true_dog) + ', listed ' + pct_(f.sheet.listed) +
      (PUB.include.rec ? ', rec ' + f.sheet.rec : '');
  });
  var msg = doc.fights.length + ' fight(s) to data/pending/' + slug + '_projections.json on ' + PUB.branch + ':\n\n' + lines.join('\n') + outside;
  if (!upload) { ui.alert('Preview (nothing uploaded)', msg, ui.ButtonSet.OK); return; }
  if (ui.alert('Publish to site?', msg + '\n\nThe site updates only after the check passes (about 2 minutes).', ui.ButtonSet.OK_CANCEL) !== ui.Button.OK) return;

  var token = props.getProperty('GITHUB_TOKEN');
  if (!token) { ui.alert('No GITHUB_TOKEN in Script Properties. See PUBLISH.md step 2. Nothing was uploaded.'); return; }
  var res = putFile_(token, 'data/pending/' + slug + '_projections.json', JSON.stringify(doc, null, 1) + '\n',
                     'Publish ' + slug + ' projections from sheet (' + doc.fights.length + ' fights)');
  ui.alert(res.ok ? 'Uploaded. Check: github.com/' + PUB.owner + '/' + PUB.repo + '/actions (Projections check).'
                  : 'Upload failed: ' + res.msg + '\nNothing changed on the site.');
}

var OUTSIDE_ = [];   // filled by buildDoc_: bouts sitting below the formula rows (never exported)

function buildDoc_(slug) {
  OUTSIDE_ = [];
  var ss = SpreadsheetApp.getActive();
  var calc = ss.getSheetByName('Calculator');
  var C = calc.getRange('A1:AA20').getValues();             // C[row-1][col-1]
  var shift = num_(calc.getRange('B42').getValue());
  var fights = [];
  PUB.tabs.forEach(function (t) {
    var sh = ss.getSheetByName(t.name);
    var M = sh.getRange('A1:AQ12').getValues();
    var LT = sh.getRange('P14:Q35').getValues();             // market KO / SUB prices: dog row 14+2k, fav row 15+2k (W / AA formulas)
    var P = sh.getRange(PUB.publishCol + '1:' + PUB.publishCol + '12').getValues();
    for (var r = t.first; r <= t.last; r++) {
      if (P[r - 1][0] !== true) continue;                     // only ticked fights
      var m = M[r - 1], cr = r + t.calcOffset, c = C[cr - 1];
      var dog = String(m[1] || '').trim(), fav = String(m[2] || '').trim();
      if (!dog || !fav) continue;
      if (String(c[0]).trim() !== dog) throw new Error(t.name + ' row ' + r + ' (' + dog + ') does not line up with Calculator row ' + cr + ' (' + c[0] + ')');
      var f = {
        publish: true, tab: t.name, row: r, calc_row: cr, tag: String(m[0] || ''), dog: dog, fav: fav,
        inputs: {
          dog_odds: num_(m[3]), fav_odds: num_(m[8]), open_dog: num_(c[5]), markov: num_(c[9]), shift: shift,
          tap: num_(c[2]), junk: num_(c[3]), tip: num_(c[4]), ctx: c[10] === '' ? null : c[10],
          manual: num_(c[12]), women: num_(c[8]) === 1
        },
        sheet: {
          listed: num_(c[6]), markov_shifted: num_(c[7]), q: num_(c[16]), true_dog: num_(c[11]), true_fav: num_(m[10]),
          dog_edge: num_(m[7]), fav_edge: num_(m[12]), drift: num_(c[22]), flag: String(c[26] || ''), rec: String(m[13] || '-')
        }
      };
      if (PUB.include.method) f.method = { dog: { dec: num_(m[21]), ko: num_(m[22]), sub: num_(m[23]) },
                                           fav: { dec: num_(m[25]), ko: num_(m[26]), sub: num_(m[27]) } };
      if (PUB.include.gtd) { f.gtd = num_(m[16]); f.gtd_listed = num_(m[18]); }
      if (PUB.include.markov) f.markov_dec = { dog: num_(m[41]), fav: num_(m[42]) };
      if (PUB.include.method || PUB.include.gtd) {             // what the check needs to recompute V:AB and Q (Block 44)
        var k = 2 * (r - 2);
        f.method_inputs = { ap: num_(m[41]), aq: num_(m[42]), ad: num_(m[29]), ae: num_(m[30]), ah: num_(m[33]), ai: num_(m[34]),
                            al: num_(m[37]), am: num_(m[38]), an: num_(m[39]), s: num_(m[18]), cx: num_(c[23]), cy: num_(c[24]),
                            ko_dog: num_(LT[k][0]), sub_dog: num_(LT[k][1]), ko_fav: num_(LT[k + 1][0]), sub_fav: num_(LT[k + 1][1]) };
      }
      if (!PUB.include.rec) delete f.sheet.rec;     // left out of the file entirely; the check then skips it
      if (!PUB.include.flag) delete f.sheet.flag;
      fights.push(f);
    }
    // Rows below t.last have no bet-rec / GTD formulas (Main Card row 7, Prelims rows 10-11 as of 2026-11-11),
    // so they are never exported. Note any bout or ticked box there so the menu can say so (audit block 35).
    for (var r2 = t.last + 1; r2 <= 12; r2++) {
      var d2 = String(M[r2 - 1][1] || '').trim(), f2 = String(M[r2 - 1][2] || '').trim();
      if (d2 || f2 || P[r2 - 1][0] === true) OUTSIDE_.push(t.name + ' row ' + r2 + ': ' + (d2 || '?') + ' vs ' + (f2 || '?') + (P[r2 - 1][0] === true ? ' (ticked)' : ''));
    }
  });
  var loaded = ss.getSheetByName('Feed').getRange('F1').getValue();   // "Loaded": set by Load next card and Refresh prices
  return {
    schema: 1, slug: slug, event: String(ss.getSheetByName('Feed').getRange('B1').getValue() || ''),
    published_at: new Date().toISOString(), source: 'UFC Model sheet, rules v4.7, Publish to site',
    prices_loaded: loaded instanceof Date ? loaded.toISOString() : null,
    params: { shift: shift, b43: num_(calc.getRange('B43').getValue()), b44: num_(calc.getRange('B44').getValue()),
              b45: num_(calc.getRange('B45').getValue()), b41: num_(calc.getRange('B41').getValue()) },
    fights: fights
  };
}

function putFile_(token, path, text, message) {
  var url = 'https://api.github.com/repos/' + PUB.owner + '/' + PUB.repo + '/contents/' + path;
  var headers = { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' };
  var sha = null;
  var get = UrlFetchApp.fetch(url + '?ref=' + PUB.branch, { headers: headers, muteHttpExceptions: true });
  if (get.getResponseCode() === 200) sha = JSON.parse(get.getContentText()).sha;
  else if (get.getResponseCode() !== 404) return { ok: false, msg: 'GitHub read returned ' + get.getResponseCode() };
  var body = { message: message, content: Utilities.base64Encode(text, Utilities.Charset.UTF_8), branch: PUB.branch };
  if (sha) body.sha = sha;
  var put = UrlFetchApp.fetch(url, { method: 'put', headers: headers, contentType: 'application/json',
                                     payload: JSON.stringify(body), muteHttpExceptions: true });
  var code = put.getResponseCode();
  if (code === 200 || code === 201) return { ok: true };
  return { ok: false, msg: 'GitHub write returned ' + code + (code === 401 || code === 403 ? ' (token missing, expired or without Contents write on this repo)' : '') };
}

function num_(x) {
  if (x === '' || x === null || x === undefined) return null;
  if (typeof x === 'number') return x;
  var s = String(x).replace(/[%,\s]/g, '');
  if (s === '' || isNaN(Number(s))) return null;
  return String(x).indexOf('%') >= 0 ? Number(s) / 100 : Number(s);
}

function pct_(x) { return x === null ? '-' : (100 * x).toFixed(1) + '%'; }
