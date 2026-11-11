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