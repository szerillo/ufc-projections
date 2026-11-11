// Run on any https://www.bestfightodds.com page. URLS: [[name, '/fighters/...'], ...] from the event page.
// L5 closing odds per fighter (excludes this card). Feeds career_context momentum, which has NO written formula yet:
// keep this file as the record and set momentum by hand until a rule is written and tested.
window.__fh = async (name, path, excludeRe) => {
  const doc = new DOMParser().parseFromString(await (await fetch(path)).text(), 'text/html'), rows = doc.querySelectorAll('table tr'), out = [];
  for (let r = 0; r < rows.length && out.length < 5; r++) { const c = rows[r].querySelectorAll('th,td'); if (c.length < 5) continue;
    if (!c[0].innerText.toLowerCase().includes(name.split(' ').pop().toLowerCase())) continue;
    const oc = rows[r + 1] ? rows[r + 1].querySelectorAll('th,td') : [], date = oc.length ? oc[oc.length - 1].innerText.trim() : '';
    if (excludeRe.test(date)) continue; out.push((oc[0] ? oc[0].innerText.trim() : '') + ' (' + date + '): ' + c[2].innerText.trim() + ' to ' + c[4].innerText.trim()); }
  return name + ': ' + (out.join(' | ') || '(none)'); };
