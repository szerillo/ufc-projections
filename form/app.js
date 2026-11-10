/* MMA Fight Form — single-page reader for form/data/*.json (built by scripts/build_form.py) */
(function () {
"use strict";
const DATA = "form/data/";
const $app = document.getElementById("app");
const cache = {};
const getJSON = (p) => cache[p] || (cache[p] = fetch(DATA + p).then(r => { if (!r.ok) throw new Error(p + " " + r.status); return r.json(); }));
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const ml = (v) => v == null ? "—" : (v > 0 ? "+" + v : "" + v);
const pct = (p, d = 1) => p == null ? "—" : (p * 100).toFixed(d) + "%";
const p2ml = (p) => { if (p == null || p <= 0 || p >= 1) return null; return p >= 0.5 ? -Math.round(100 * p / (1 - p)) : Math.round(100 * (1 - p) / p); };
const ml2p = (m) => m == null ? null : (m > 0 ? 100 / (m + 100) : -m / (-m + 100));
const fdate = (iso) => { const d = new Date(iso + (iso.length <= 10 ? "T12:00:00Z" : "")); return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }); };
const sdate = (iso) => { const d = new Date(iso + "T12:00:00Z"); return d.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "2-digit", timeZone: "UTC" }); };
const mmss = (s) => s == null ? "—" : Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
const signed = (v, d = 1) => v == null ? "—" : (v > 0 ? "+" : "") + v.toFixed(d);
const cls = (v) => v == null ? "" : v > 0 ? "pos" : v < 0 ? "neg" : "";
const yt = (a, b) => "https://www.youtube.com/results?search_query=" + encodeURIComponent(a + " vs " + b + " UFC full fight");
const fp = (a, b) => "https://ufcfightpass.com/search?q=" + encodeURIComponent(a + " " + b);
const logit = (p) => Math.log(p / (1 - p)), sig = (z) => 1 / (1 + Math.exp(-z));
const fair = (p) => p == null ? null : sig((window.__k || 1.2) * logit(Math.min(Math.max(p, 0.001), 0.999)));
const ml2dec = (m) => m == null ? null : (m > 0 ? 1 + m / 100 : 1 + 100 / -m);
const last = (n) => (n || "").split(" ").slice(-1)[0];
function bestPrice(od, side) { let b = null; for (const [k, x] of Object.entries((od && od.books) || {})) { const m = x[side === "a" ? "ma" : "mb"]; if (m == null) continue; if (!b || ml2dec(m) > ml2dec(b.ml)) b = { ml: m, book: k }; } return b; }
function methodRows(f) { // -> {a:{dec,ko,sub,itd,win}, b:{...}, gtd} using fair market win % when there is one, else the Form Line
  const fm = f.form; if (!fm || !fm.ms) return null;
  const o = oddsCells(f); const pa = o.pa != null ? fair(o.pa) : fm.p; if (pa == null) return null;
  const mk = (p, m) => ({ win: p, ko: p * m[0], sub: p * m[1], dec: p * m[2], itd: p * (m[0] + m[1]) });
  const a = mk(pa, fm.ms.a), b = mk(1 - pa, fm.ms.b);
  return { a, b, gtd: a.dec + b.dec, src: o.pa != null ? "fair market win %" : "Form Line win %" };
}
function methodBoard(ev) {
  const rows = [];
  for (const f of ev.fights) { const M = methodRows(f); if (!M) continue;
    for (const s_ of ["a", "b"]) rows.push(`<tr class="click" data-href="#/fight/${ev.slug}/${f.n}"><td class="c dim">${f.n}</td><td class="l b">${esc(f[s_].name)}</td><td>${(M[s_].win * 100).toFixed(0)}%</td>` + ["dec", "ko", "sub", "itd"].map(k => `<td>${ml(p2ml(M[s_][k]))} <span class="dim">${(M[s_][k] * 100).toFixed(0)}%</span></td>`).join("") + (s_ === "a" ? `<td rowspan="2" class="b" style="border-left:1px solid var(--hair)">${(M.gtd * 100).toFixed(0)}% <span class="dim">${ml(p2ml(M.gtd))}</span></td>` : "") + `</tr>`); }
  if (!rows.length) return "";
  return `<h3>Method board · Form fair prices</h3><div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Fighter</th><th>Win</th><th>By decision</th><th>By KO/TKO</th><th>By sub</th><th>Inside distance</th><th>Fight GTD</th></tr></thead><tbody>${rows.join("")}</tbody></table></div><div class="note">Win % is the bias-adjusted market line; the method split comes from the Form method model (each fighter's finishing history, the opponent's loss history and the division's base rates). No vig included. GTD is the two decision chances added together.</div>`;
}
const bookName = (b) => (window.__books || {})[b] || b;
const flink = (f) => f.slug ? `<a href="#/fighter/${f.slug}">${esc(f.name)}</a>` : esc(f.name);
const shortMethod = (m) => (m || "").replace("Decision - ", "").replace("Unanimous", "UD").replace("Split", "SD").replace("Majority", "MD").replace("Submission", "SUB").replace("TKO - Doctor's Stoppage", "TKO (Dr)").replace("Overturned", "OVT").replace("Could Not Continue", "CNC");

/* ---------- aggregates from past-performance lines ---------- */
function agg(lines) {
  const a = { n: 0, w: 0, l: 0, d: 0, nc: 0, secs: 0, sl: 0, sa: 0, osl: 0, osa: 0, kd: 0, okd: 0, tl: 0, ta: 0, otl: 0, ota: 0, ctrl: 0, octrl: 0, sub: 0, fin: 0, ko: 0, subw: 0, dec: 0, kol: 0, subl: 0, decl: 0 };
  for (const x of lines) {
    a.n++;
    if (x.r === "W") { a.w++; if (/KO/.test(x.m)) a.ko++; else if (/Sub/i.test(x.m)) a.subw++; else if (/Dec/i.test(x.m)) a.dec++; }
    else if (x.r === "L") { a.l++; if (/KO/.test(x.m)) a.kol++; else if (/Sub/i.test(x.m)) a.subl++; else if (/Dec/i.test(x.m)) a.decl++; }
    else if (x.r === "D") a.d++; else a.nc++;
    if (x.s && x.secs) {
      const s = x.s; a.secs += x.secs; a.sl += s[0]; a.sa += s[1]; a.osl += s[2]; a.osa += s[3]; a.kd += s[4]; a.okd += s[5];
      a.tl += s[6]; a.ta += s[7]; a.otl += s[8]; a.ota += s[9]; a.ctrl += s[10]; a.octrl += s[11]; a.sub += s[12];
    }
  }
  let r1 = 0, r1o = 0, r1s = 0, lt = 0, lto = 0, lts = 0;
  for (const x of lines) if (x.rs) { r1 += x.rs[0]; r1o += x.rs[1]; r1s += x.rs[2]; lt += x.rs[3]; lto += x.rs[4]; lts += x.rs[5]; }
  a.r1diff = r1s >= 300 ? (r1 - r1o) / (r1s / 60) : null; a.latediff = lts >= 300 ? (lt - lto) / (lts / 60) : null; a.latemin = lts / 60;
  const min = a.secs / 60;
  a.min = min;
  a.slpm = min ? a.sl / min : null; a.sapm = min ? a.osl / min : null; a.diff = min ? (a.sl - a.osl) / min : null;
  a.acc = a.sa ? a.sl / a.sa : null; a.def = a.osa ? 1 - a.osl / a.osa : null;
  a.td15 = min ? a.tl / min * 15 : null; a.tdacc = a.ta ? a.tl / a.ta : null; a.tdd = a.ota ? 1 - a.otl / a.ota : null;
  a.ctrlp = a.secs ? a.ctrl / a.secs : null; a.octrlp = a.secs ? a.octrl / a.secs : null;
  a.kd15 = min ? a.kd / min * 15 : null; a.okd15 = min ? a.okd / min * 15 : null; a.sub15 = min ? a.sub / min * 15 : null;
  a.avg = a.n ? a.secs / Math.max(1, lines.filter(x => x.secs).length) : null;
  a.rec = `${a.w}-${a.l}-${a.d}` + (a.nc ? ` (${a.nc} NC)` : "");
  return a;
}
function streak(lines) { let s = 0, t = null; for (const x of lines) { if (x.r !== "W" && x.r !== "L") break; if (t == null) t = x.r; if (x.r !== t) break; s++; } return t ? t + s : "—"; }
function ageAt(dob, iso) { if (!dob) return null; return (new Date(iso) - new Date(dob)) / (365.25 * 864e5); }
function daysBetween(a, b) { return Math.round((new Date(a) - new Date(b)) / 864e5); }

/* ---------- past-performance table ---------- */
function ppTable(lines, opts = {}) {
  if (!lines.length) return `<div class="box note">No prior UFC fights on record.</div>`;
  const rows = lines.slice(0, opts.limit || lines.length).map((x, i) => {
    const prev = lines[i + 1];
    const lay = prev ? daysBetween(x.d, prev.d) : null;
    const s = x.s, od = x.od || {};
    const min = x.secs ? x.secs / 60 : null;
    const diff = s && min ? (s[0] - s[2]) / min : null;
    const mv = od.po != null && od.pc != null ? (od.pc - od.po) * 100 : (od.mo != null && od.mc != null ? (ml2p(od.mc) - ml2p(od.mo)) * 100 : null);
    return `<tr>
      <td class="l"><a href="#/fight/${x.es}/${x.n}" title="${esc(x.e)}">${sdate(x.d)}</a></td>
      <td class="opp">${x.os ? `<a href="#/fighter/${x.os}">${esc(x.o)}</a>` : esc(x.o)} <small>${x.oe || ""}</small></td>
      <td class="c ${x.r}">${x.r}</td>
      <td class="b" title="Form Figure for this performance">${x.fg == null ? "—" : Math.round(x.fg)}</td>
      <td class="mth">${esc(shortMethod(x.m))}${x.ti ? " 🏆" : ""}${x.dt ? ` <small class="dim">${esc(x.dt)}</small>` : ""}</td>
      <td>${x.rd || "—"}${x.sc ? "/" + x.sc : ""} ${esc(x.t || "")}</td>
      <td class="l dim">${esc((x.wc || "").replace("Women's ", "W ").replace("weight", "").replace("Light Heavy", "LHW").replace("Catch ", "CW"))}</td>
      <td class="b">${ml(od.mc)}</td>
      <td class="${cls(mv)}" title="open ${ml(od.mo)} → close ${ml(od.mc)}">${mv == null ? "—" : signed(mv)}</td>
      <td>${s ? s[0] + "-" + s[1] : "—"}</td>
      <td class="dim">${s ? s[2] + "-" + s[3] : "—"}</td>
      <td class="${cls(diff)}">${diff == null ? "—" : signed(diff, 2)}</td>
      <td>${s ? s[4] + "-" + s[5] : "—"}</td>
      <td>${s ? s[6] + "/" + s[7] : "—"}</td>
      <td class="dim">${s ? s[8] + "/" + s[9] : "—"}</td>
      <td>${s ? mmss(s[10]) : "—"}</td>
      <td class="dim">${s ? mmss(s[11]) : "—"}</td>
      <td class="dim">${lay == null ? "debut" : lay + "d"}</td>
      <td class="c"><a href="${yt(opts.name || "", x.o)}" target="_blank" rel="noopener" title="Search film">▶</a> <a href="${esc(x.u)}" target="_blank" rel="noopener" title="UFCStats fight detail">§</a></td>
    </tr>`;
  }).join("");
  return `<div class="tw"><table class="pp"><thead><tr>
    <th class="l">Date</th><th class="l">Opponent <span style="font-weight:400">Elo</span></th><th class="c">Res</th><th title="Form Figure: result + in-fight dominance, adjusted for opponent. 50 = average UFC performance">Fig</th><th class="l">Method</th><th>Rd Time</th><th class="l">Wt</th>
    <th title="Closing moneyline (consensus)">Close</th><th title="Open→close move in implied win %, vig removed">Move</th>
    <th title="Sig. strikes landed-attempted">SS</th><th title="Opponent sig. strikes">Opp SS</th><th title="Sig. strike differential per minute">±/min</th>
    <th title="Knockdowns for-against">KD</th><th title="Takedowns landed/attempted">TD</th><th title="Opponent takedowns">Opp TD</th>
    <th title="Control time">Ctrl</th><th title="Opponent control time">Opp</th><th title="Days since previous UFC fight">Layoff</th><th class="c">Film</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

/* ---------- line chart ---------- */
function lineChart(od, aName, bName) {
  const S = (od && od.series) || [];
  if (S.length < 2) return `<div class="note">Not enough snapshots for a chart${S.length ? " (1 snapshot)" : ""}.</div>`;
  const W = 760, H = 230, L = 46, R = 58, T = 12, B = 26;
  const t0 = Date.parse(S[0][0] + "Z"), t1 = Date.parse(S[S.length - 1][0] + "Z");
  let lo = 1, hi = 0;
  for (const r of S) for (const v of [r[1], r[2], r[3], r[4]]) if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  const pad = Math.max(0.02, (hi - lo) * 0.15); lo = Math.max(0.01, lo - pad); hi = Math.min(0.99, hi + pad);
  const x = (t) => L + (W - L - R) * ((Date.parse(t + "Z") - t0) / Math.max(1, t1 - t0));
  const y = (p) => T + (H - T - B) * (1 - (p - lo) / (hi - lo));
  const path = (i) => { let d = "", pen = false; for (const r of S) { if (r[i] == null) { continue; } d += (pen ? "L" : "M") + x(r[0]).toFixed(1) + " " + y(r[i]).toFixed(1); pen = true; } return d; };
  let grid = "";
  for (let k = 0; k <= 4; k++) { const p = lo + (hi - lo) * k / 4; const yy = y(p).toFixed(1);
    grid += `<line x1="${L}" x2="${W - R}" y1="${yy}" y2="${yy}" stroke="#cfc6ae" stroke-width="1"/><text x="${L - 6}" y="${+yy + 4}" text-anchor="end" font-size="10" font-family="monospace" fill="#4a4438">${(p * 100).toFixed(0)}%</text><text x="${W - R + 6}" y="${+yy + 4}" font-size="10" font-family="monospace" fill="#4a4438">${ml(p2ml(p))}</text>`; }
  const ticks = [0, 0.5, 1].map(f => { const t = new Date(t0 + (t1 - t0) * f); return `<text x="${(L + (W - L - R) * f).toFixed(1)}" y="${H - 8}" text-anchor="${f === 0 ? "start" : f === 1 ? "end" : "middle"}" font-size="10" font-family="monospace" fill="#4a4438">${t.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" })}</text>`; }).join("");
  const last = S[S.length - 1];
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Line history">
    ${grid}${ticks}
    <path d="${path(3)}" fill="none" stroke="#14663a" stroke-width="1" opacity=".75"/>
    <path d="${path(4)}" fill="none" stroke="#1d3f77" stroke-width="1" opacity=".75"/>
    <path d="${path(2)}" fill="none" stroke="#a81c1c" stroke-width="1.4" stroke-dasharray="4 3"/>
    <path d="${path(1)}" fill="none" stroke="#17140f" stroke-width="2.2"/>
    <circle cx="${x(S[0][0]).toFixed(1)}" cy="${y(S[0][1]).toFixed(1)}" r="3.5" fill="#17140f"/>
    <circle cx="${x(last[0]).toFixed(1)}" cy="${y(last[1]).toFixed(1)}" r="3.5" fill="#17140f"/>
  </svg>
  <div class="legend"><span><i style="border-color:#17140f"></i>Consensus (no-vig) — ${esc(aName)} win %</span><span><i style="border-color:#a81c1c;border-top-style:dashed"></i>Pinnacle</span><span><i style="border-color:#14663a"></i>DraftKings</span><span><i style="border-color:#1d3f77"></i>FanDuel</span><span>right axis = ${esc(aName)} fair moneyline</span></div>`;
}

/* ---------- shared bits ---------- */
function oddsCells(f) {
  const od = f.odds, bp = f.bp;
  if (f.live) { const L = f.live, pa = ml2p(L.ma), pb = ml2p(L.mb), p = pa / (pa + pb);
    const po = od ? od.open.p : (bp && bp.a.open != null && bp.b.open != null ? ml2p(bp.a.open) / (ml2p(bp.a.open) + ml2p(bp.b.open)) : null);
    return { open: od ? `${ml(od.open.ma)} / ${ml(od.open.mb)}` : (bp ? `${ml(bp.a.open)} / ${ml(bp.b.open)}` : "—"), close: `<b>${ml(L.ma)}</b> / <b>${ml(L.mb)}</b>`, mv: po == null ? null : (p - po) * 100, pa: p }; }
  if (od) { const mv = (od.close.p - od.open.p) * 100;
    return { open: `${ml(od.open.ma)} / ${ml(od.open.mb)}`, close: `<b>${ml(od.close.ma)}</b> / <b>${ml(od.close.mb)}</b>`, mv, pa: od.close.p }; }
  if (bp && bp.a && bp.b && bp.a.cons != null) {
    const pa = ml2p(bp.a.cons), pb = ml2p(bp.b.cons), p = pa / (pa + pb);
    const po = bp.a.open != null && bp.b.open != null ? ml2p(bp.a.open) / (ml2p(bp.a.open) + ml2p(bp.b.open)) : null;
    return { open: `${ml(bp.a.open)} / ${ml(bp.b.open)}`, close: `<b>${ml(bp.a.cons)}</b> / <b>${ml(bp.b.cons)}</b>`, mv: po == null ? null : (p - po) * 100, pa: p }; }
  return { open: "—", close: "—", mv: null, pa: null };
}
function resultText(f) {
  const r = f.result; if (!r) return "";
  if (r.kind === "nc") return "No contest";
  if (r.kind === "draw") return `Draw · ${shortMethod(r.method)}`;
  const w = r.winner === "a" ? f.a.name : f.b.name;
  return `${esc(w)} · ${esc(shortMethod(r.method))} · R${r.round} ${esc(r.time)}`;
}
function cardTable(ev) {
  const final = ev.status === "final";
  let html = "", group = null;
  const nMain = Math.min(ev.fights.length, ev.fights.length >= 12 ? (ev.fights.some(f => f.title) ? 5 : 6) : 5);
  ev.fights.forEach((f, i) => {
    const o = oddsCells(f), m = f.model;
    const g = i === 0 ? "Main event" : i < nMain ? "Main card" : "Prelims";
    if (g !== group && i !== 1) { html += `<tr class="grp"><td colspan="12">${g === "Main event" ? "Main card" : g}</td></tr>`; group = g === "Main event" ? "Main card" : g; }
    let model = "—", edge = "—";
    if (m && m.a && m.a.win != null) {
      model = `${m.a.win.toFixed(0)} / ${m.b.win.toFixed(0)}`;
      const mkp = f.sheet && f.sheet.listed != null && m.src === "sheet" ? f.sheet.listed : o.pa;
      if (mkp != null) { const e = m.a.win - mkp * 100; const side = e >= 0 ? f.a.name : f.b.name; edge = `<span class="${Math.abs(e) >= 3 ? "pos b" : "dim"}" title="Model minus no-vig market">${esc(side.split(" ").slice(-1)[0])} ${signed(Math.abs(e))}</span>`; }
    }
    const rec = m && m.rec ? `<span class="pill y" title="${esc(m.rec_text || "Model bet recommendation")}">BET ${esc((m.rec === "a" ? f.a.name : f.b.name).split(" ").slice(-1)[0])}</span>` : (m && m.rec_text && /^lean/i.test(m.rec_text) ? `<span class="pill" title="${esc(m.rec_text)}">${esc(m.rec_text.split("[")[0].trim())}</span>` : "");
    const wa = f.result && f.result.winner === "a", wb = f.result && f.result.winner === "b";
    html += `<tr class="click" data-href="#/fight/${ev.slug}/${f.n}">
      <td class="c dim">${f.n}</td>
      <td class="name"><span class="${wa ? "W" : ""}">${esc(f.a.name)}</span> <span class="dim">vs</span> <span class="${wb ? "W" : ""}">${esc(f.b.name)}</span> ${f.title ? '<span class="pill k">Title</span>' : ""} ${rec}
        <small>${esc(f.wc || "")}${f.sched ? " · " + f.sched + "R" : ""} · Fig ${f.form ? f.form.ra.toFixed(0) + " / " + f.form.rb.toFixed(0) : "—"}</small></td>
      <td>${o.open}</td><td>${o.close}</td>
      <td class="${cls(o.mv)}" title="Move in ${esc(f.a.name)} implied win %">${o.mv == null ? "—" : signed(o.mv)}</td>
      <td title="Bias-adjusted fair win % for ${esc(f.a.name)}">${o.pa == null ? "—" : (fair(o.pa) * 100).toFixed(0) + "%"}</td>
      <td class="dim" title="Form Line: stats-only win % for ${esc(f.a.name)}">${f.form && f.form.p != null ? (f.form.p * 100).toFixed(0) + "%" : "—"}</td>
      <td class="dim" title="Form goes-the-distance %">${(() => { const M = methodRows(f); return M ? (M.gtd * 100).toFixed(0) + "%" : (f.form && f.form.g != null ? (f.form.g * 100).toFixed(0) + "%" : "—"); })()}</td>
      <td>${model}</td><td>${edge}</td>
      <td class="l">${final ? resultText(f) : '<span class="dim">' + (f.start ? new Date(f.start.replace(" ", "T") + "Z").toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) : "") + "</span>"}</td>
      <td class="c">›</td></tr>`;
  });
  return `<div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Bout</th><th>Open</th><th>${final ? "Close" : "Current"}</th><th title="Open→now move in first fighter's no-vig win %">Move</th><th title="Market win % for the first fighter after correcting the favorite-longshot bias">Fair</th><th title="Form Line: stats-only win % for the first fighter">Form</th><th title="Form Line: chance the fight goes the distance">GTD</th><th title="Model win % (first / second)">Model</th><th>Edge</th><th class="l">${final ? "Result" : "Local time"}</th><th></th></tr></thead><tbody>${html}</tbody></table></div>`;
}
async function overlayLive(ev) {
  if (ev.status !== "upcoming" || !ev.bp_file || ev.__live) return;
  try { const d = await fetch(ev.bp_file + "?t=" + Math.floor(Date.now() / 6e5)).then(r => r.json());
    const nm = (x) => (x || "").toLowerCase().normalize("NFD").replace(/[^a-z ]/g, "");
    for (const bf of d.fights || []) { const sel = (bf.markets || {}).moneyline || []; if (sel.length < 2) continue;
      const f = ev.fights.find(x => x.n === bf.n); if (!f) continue;
      const pick = (name) => { const l = last(nm(name)); const s_ = sel.find(z => nm(z.label).includes(l)); return s_ && s_.books && s_.books.consensus ? s_.books.consensus.cost : null; };
      const ma = pick(f.a.name), mb = pick(f.b.name); if (ma != null && mb != null && bf.status !== "live") f.live = { ma, mb }; }
    ev.__live = d.updated_at; ev.odds_updated = d.updated_at; } catch (e) { /* keep baked odds */ }
}
/* ---------- live model sheet overlay (upcoming card) ---------- */
function parseCSV(text) { const rows = []; let row = [], cur = "", q = false;
  for (let i = 0; i < text.length; i++) { const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
    else if (c === '"') q = true; else if (c === ",") { row.push(cur); cur = ""; } else if (c === "\n") { row.push(cur); rows.push(row); row = []; cur = ""; } else if (c !== "\r") cur += c; }
  if (cur || row.length) { row.push(cur); rows.push(row); } return rows; }
const pf = (v) => { v = (v || "").trim(); if (!v || v === "-") return null; const x = parseFloat(v.replace(/[%,+]/g, "")); if (!isFinite(x)) return null; return v.endsWith("%") ? x / 100 : (x > 1.0001 ? x / 100 : x); };
const pmlv = (v) => { const x = parseInt((v || "").replace("+", ""), 10); return isFinite(x) ? x : null; };
const nm = (x) => (x || "").toLowerCase().normalize("NFD").replace(/[^a-z ]/g, "").trim();
const sameFighter = (a, b) => { const A = nm(a).split(" "), B = nm(b).split(" "); return A[A.length - 1] === B[B.length - 1] || nm(a) === nm(b); };
async function overlaySheet(ev) {
  const S = null; if (!S) return; // sheet is read at build time only; its ID is never shipped to the browser
  try {
    const get = (tab) => fetch(`https://docs.google.com/spreadsheets/d/${S.id}/export?format=csv&gid=${S.gids[tab]}`).then(r => { if (!r.ok) throw new Error("sheet " + r.status); return r.text(); }).then(parseCSV);
    const [mc, pr, calc] = await Promise.all([get("Main Card"), get("Prelims"), get("Calculator")]);
    const C = {}; for (const r of calc.slice(1, 40)) if (r[0] && r[1]) C[nm(r[0]) + "|" + nm(r[1])] = r;
    let n = 0;
    for (const r of mc.slice(1, 14).concat(pr.slice(1, 14))) {
      if (!r[1] || !r[2] || pf(r[5]) == null || r[1] === "Underdog") continue;
      const f = ev.fights.find(x => (sameFighter(x.a.name, r[1]) && sameFighter(x.b.name, r[2])) || (sameFighter(x.a.name, r[2]) && sameFighter(x.b.name, r[1]))); if (!f) continue;
      const aDog = sameFighter(f.a.name, r[1]), c = C[nm(r[1]) + "|" + nm(r[2])] || [];
      const sd = (x) => x == null ? null : (aDog ? x : 1 - x);
      const dm = [pf(r[21]), pf(r[22]), pf(r[23])], fm = [pf(r[25]), pf(r[26]), pf(r[27])];
      const so = { dog: aDog ? "a" : "b", tap: sd(pf(c[2])), junk: sd(pf(c[3])), tip: sd(pf(c[4])), open: sd(pf(c[5])), listed: sd(pf(c[6])), markov: sd(pf(c[9])),
        model: aDog ? pf(r[5]) : pf(r[10]), flag: (c[26] || "").trim(), momentum: (c[27] || "").trim(), rec: (r[13] || "").trim(), play: (r[15] || "").trim(), ou_play: (c[21] || "").trim(),
        gtd: pf(r[16]), gtd_listed: pf(r[18]), o25_listed: pf(c[13]), o25_model: pf(c[14]), hold: pf(r[14]), tag: (r[0] || "").trim(),
        k: (c[10] || "").trim(), w: (c[8] || "").trim() === "1" ? 1 : 0, par: [0.15, parseFloat((calc[41] || [])[1]) || 0, isFinite(parseFloat((calc[42] || [])[1])) ? parseFloat(calc[42][1]) : 0.15, isFinite(parseFloat((calc[43] || [])[1])) ? parseFloat(calc[43][1]) : 0.075],
        ml: { a: aDog ? pmlv(r[3]) : pmlv(r[8]), b: aDog ? pmlv(r[8]) : pmlv(r[3]) }, edge: { a: aDog ? pf(r[7]) : pf(r[12]), b: aDog ? pf(r[12]) : pf(r[7]) },
        meth: { a: aDog ? dm : fm, b: aDog ? fm : dm }, best: { a: (aDog ? c[28] : c[29]) || "", b: (aDog ? c[29] : c[28]) || "" }, live: true };
      f.sheet = so;
      if (!f.model || f.model.src === "sheet") { const pa = so.model, mk = (p, sh) => ({ win: +(p * 100).toFixed(1), dec: sh[0] == null ? null : +(p * sh[0] * 100).toFixed(1), ko: sh[1] == null ? null : +(p * sh[1] * 100).toFixed(1), sub: sh[2] == null ? null : +(p * sh[2] * 100).toFixed(1) });
        const A = mk(pa, so.meth.a), B = mk(1 - pa, so.meth.b); A.ml = so.ml.a; B.ml = so.ml.b;
        let rec = null; if (/^BET/i.test(so.rec)) rec = nm(so.rec).includes(last(nm(f.a.name))) ? "a" : nm(so.rec).includes(last(nm(f.b.name))) ? "b" : null;
        f.model = { a: A, b: B, gtd: so.gtd == null ? null : +(so.gtd * 100).toFixed(1), rec, rec_text: so.rec, src: "sheet" }; }
      if (so.tag) f.sched = /-5$/.test(so.tag) ? 5 : 3;
      n++; }
    ev.__sheet = n;
  } catch (e) { console.warn("sheet overlay failed", e); }
}
function chip(t, k) { return t && t !== "-" ? `<span class="pill ${k || ""}" style="margin:0 4px 4px 0;white-space:normal;text-transform:none;letter-spacing:0;font-weight:600;font-size:11px">${esc(t)}</span>` : ""; }
function sheetBox(f, final) {
  const s = f.sheet; if (!s) return "";
  const P = (x) => x == null ? "—" : (x * 100).toFixed(1) + "%", inv = (x) => x == null ? null : 1 - x;
  const row = (lab, x, tip) => x == null ? "" : `<tr><td class="l b" title="${tip || ""}">${lab}</td><td>${P(x)}</td><td>${P(inv(x))}</td></tr>`;
  let h = `<h3>Model sheet${s.live ? ' <span class="pill g">live from sheet</span>' : ""}</h3><div class="tw"><table><thead><tr><th class="l">Input</th><th>${esc(last(f.a.name))}</th><th>${esc(last(f.b.name))}</th></tr></thead><tbody>
    ${row("Tapology picks", s.tap, "Share of Tapology users picking each fighter")}${row("MMA Junkie picks", s.junk)}${row("Tipsters", s.tip)}
    ${row("Opening line (no-vig)", s.open)}${row("Listed line", s.listed)}${row("Closing line", s.close)}${row("Exchange fair price", s.exch)}
    ${row("Markov sim", s.markov, "Markov fight simulator win %")}
    ${s.model == null ? "" : `<tr style="background:var(--hl)"><td class="l b">Sheet model</td><td class="b">${P(s.model)} · ${ml(p2ml(s.model))}</td><td class="b">${P(1 - s.model)} · ${ml(p2ml(1 - s.model))}</td></tr>`}
    ${s.edge ? `<tr><td class="l b">Edge vs listed</td><td class="${cls(s.edge.a)}">${s.edge.a == null ? "—" : signed(s.edge.a * 100) + "%"}</td><td class="${cls(s.edge.b)}">${s.edge.b == null ? "—" : signed(s.edge.b * 100) + "%"}</td></tr>` : ""}
    ${s.meth && s.meth.a && s.meth.a[0] != null ? `<tr><td class="l b" title="Share of each fighter's wins">Wins by DEC / KO / SUB</td><td>${s.meth.a.map(x => x == null ? "—" : (x * 100).toFixed(0)).join(" / ")}</td><td>${s.meth.b.map(x => x == null ? "—" : (x * 100).toFixed(0)).join(" / ")}</td></tr>` : ""}
    ${s.gtd != null ? `<tr><td class="l b">Fight GTD</td><td colspan="2" class="c">model ${P(s.gtd)}${s.gtd_listed != null ? " · listed " + P(s.gtd_listed) : ""}${s.gtd_close != null ? " · close " + P(s.gtd_close) : ""}${s.markov_dec != null ? " · Markov " + P(s.markov_dec) : ""}</td></tr>` : ""}
    ${s.o25_model != null ? `<tr><td class="l b">Over 2.5</td><td colspan="2" class="c">model ${P(s.o25_model)}${s.o25_listed != null ? " · listed " + P(s.o25_listed) : ""}</td></tr>` : ""}
  </tbody></table></div><div style="margin-top:6px">${chip(s.rec, /^BET/i.test(s.rec) ? "y" : "")}${chip(s.play)}${chip(s.ou_play)}${chip(s.flag && s.flag !== "ok" ? s.flag : "", "r")}${chip(s.momentum && s.momentum !== "flat" ? s.momentum : "")}${s.best && s.best.a ? chip(last(f.a.name) + ": " + s.best.a) + chip(last(f.b.name) + ": " + s.best.b) : ""}${s.pl != null ? chip("Rec result " + signed(s.pl, 2) + "u", s.pl > 0 ? "g" : "r") : ""}</div>`;
  return h;
}
function buildUp(f) { // how the sheet's underdog number is built: listed + Markov pull - women - code - public overage
  const s = f.sheet; if (!s || s.listed == null || !s.par) return "";
  const dogSide = s.dog, dog = f[dogSide], inv = (x) => x == null ? null : (dogSide === "a" ? x : 1 - x);
  const G = inv(s.listed), J = inv(s.markov), T = inv(s.tap), K = inv(s.junk), [beta, shift, p1, p2] = s.par;
  const kc = (s.k || "").trim(), kAdj = kc === "G" || kc === "R" ? -0.04 : kc === "GF" ? 0.04 : (isFinite(parseFloat(kc)) ? parseFloat(kc) : 0);
  const steps = [["Listed line (best bettable price, no vig)", null, G]];
  let q = G;
  const add = (lab, d) => { if (Math.abs(d) < 1e-9) return; q += d; steps.push([lab, d, q]); };
  if (J != null) add(`Markov pull: ${beta} × (${((J - shift) * 100).toFixed(1)}% − listed)${shift ? ", Markov shifted " + signed(-shift * 100) + " pts to the market's level" : ""}`, beta * ((J - shift) - G));
  if (s.w) add("Women's underdog", -0.04);
  if (kAdj) add(`Context code ${esc(kc)}`, kAdj);
  if (T != null && K != null) { add(`Public fade, primary: ${p1} × overage of ${(Math.max(0, Math.max(T, K) - G) * 100).toFixed(1)} pts`, -p1 * Math.max(0, Math.max(T, K) - G)); add(`Public fade, secondary: ${p2} × overage of ${(Math.max(0, Math.min(T, K) - G) * 100).toFixed(1)} pts`, -p2 * Math.max(0, Math.min(T, K) - G)); }
  q = Math.min(0.98, Math.max(0.02, q));
  if (steps.length < 2) return `<div class="note">Sheet number for ${esc(dog.name)} equals the listed line: no Markov, public or context inputs entered yet.${kc === "D" ? " Context code D: debut underdog, no dog bet." : ""}</div>`;
  return `<div class="tw" style="margin-top:6px"><table><thead><tr><th class="l">How ${esc(last(dog.name))}'s number is built</th><th>Change</th><th>Running</th></tr></thead><tbody>${steps.map(([l, d, r]) => `<tr><td class="l">${l}</td><td class="${cls(d)}">${d == null ? "" : signed(d * 100, 2)}</td><td>${(r * 100).toFixed(1)}%</td></tr>`).join("")}<tr style="background:var(--hl)"><td class="l b">Sheet model, ${esc(dog.name)}</td><td></td><td class="b">${(q * 100).toFixed(1)}%</td></tr></tbody></table></div>${kc === "D" ? '<div class="note">Context code D: debut underdog. It blocks the dog bet and changes nothing else.</div>' : ""}`;
}
function markovBox(f) {
  const m = f.markov; if (!m) return "";
  const mx = Math.max(...m.r, m.dec * 100, 1), bar = (lab, v) => `<div style="display:grid;grid-template-columns:70px 1fr 46px;gap:6px;align-items:center;font:12px var(--mono);margin:2px 0"><span class="dim">${lab}</span><span style="background:var(--paper2);height:12px"><i style="display:block;height:12px;width:${(v / mx * 100).toFixed(1)}%;background:${lab === "Decision" ? "#1d3f77" : "#a81c1c"}"></i></span><span>${v.toFixed(1)}%</span></div>`;
  return `<h3>Markov simulation</h3><div class="box"><div class="kv"><span>${esc(f.a.name)} win (shrunk / raw)</span><span>${(m.p * 100).toFixed(1)}% / ${(m.raw * 100).toFixed(1)}%</span></div><div class="kv"><span>${esc(f.b.name)} win (shrunk / raw)</span><span>${((1 - m.p) * 100).toFixed(1)}% / ${((1 - m.raw) * 100).toFixed(1)}%</span></div><div class="kv"><span>Expected fight time</span><span>${m.exp} min</span></div><div style="height:6px"></div>
    ${m.r.map((v, i) => v > 0 || i < (f.sched || 3) ? bar("Ends R" + (i + 1), v) : "").join("")}${bar("Decision", m.dec * 100)}</div>`;
}
function propsBox(f) {
  const p = f.props; if (!p) return "";
  const order = [["ML a", last(f.a.name) + " ML"], ["ML b", last(f.b.name) + " ML"], ["a DEC", last(f.a.name) + " by DEC"], ["a KO", last(f.a.name) + " by KO"], ["a SUB", last(f.a.name) + " by SUB"], ["b DEC", last(f.b.name) + " by DEC"], ["b KO", last(f.b.name) + " by KO"], ["b SUB", last(f.b.name) + " by SUB"], ["GTD", "Goes the distance"], ["O1.5", "Over 1.5"], ["O2.5", "Over 2.5"], ["O3.5", "Over 3.5"], ["O4.5", "Over 4.5"]];
  const cell = (x) => x && x[0] != null ? `${(x[0] * 100).toFixed(1)}% <span class="dim">${ml(x[1])}</span>` : "—";
  const rows = order.filter(([k]) => p[k]).map(([k, lab]) => `<tr><td class="l b">${esc(lab)}</td><td>${cell(p[k].books)}</td><td>${p[k]["best-book"] ? ml(p[k]["best-book"][1]) + ' <span class="dim">' + esc(p[k]["best-book"][2]) + "</span>" : "—"}</td><td>${cell(p[k].exch)}</td></tr>`).join("");
  return rows ? `<h3>Prop market at the close</h3><div class="tw"><table><thead><tr><th class="l">Market</th><th title="No-vig book consensus">Books</th><th>Best price</th><th title="Exchange price (Kalshi / Polymarket / Novig)">Exchange</th></tr></thead><tbody>${rows}</tbody></table></div>` : "";
}
function priceBoard(ev) {
  const rows = [];
  for (const f of ev.fights) { const od = f.odds; if (!od) continue; const pa = od.close.p;
    for (const s_ of ["a", "b"]) { const b = bestPrice(od, s_); if (!b) continue; const fp_ = s_ === "a" ? fair(pa) : 1 - fair(pa); const e = fp_ * ml2dec(b.ml) - 1;
      rows.push({ f, s: s_, b, fp: fp_, e }); } }
  rows.sort((x, y) => y.e - x.e);
  const top = rows.filter(r => r.e > -0.005).slice(0, 8);
  if (!top.length) return "";
  return `<h3>Price board · best available price vs the bias-adjusted fair line</h3><div class="tw"><table><thead><tr><th class="l">Fighter</th><th class="l">Opponent</th><th>Consensus</th><th>Best price</th><th class="l">Book</th><th>Fair %</th><th>Fair ML</th><th>Edge</th></tr></thead><tbody>` +
    top.map(r => `<tr class="click" data-href="#/fight/${ev.slug}/${r.f.n}"><td class="l b">${esc(r.f[r.s].name)}</td><td class="l dim">${esc(r.f[r.s === "a" ? "b" : "a"].name)}</td><td>${ml(r.f.odds.close[r.s === "a" ? "ma" : "mb"])}</td><td class="b">${ml(r.b.ml)}</td><td class="l">${esc(bookName(r.b.book))}</td><td>${(r.fp * 100).toFixed(1)}%</td><td>${ml(p2ml(r.fp))}</td><td class="${cls(r.e)} b">${signed(r.e * 100)}%</td></tr>`).join("") +
    `</tbody></table></div><div class="note">Fair line = no-vig consensus pushed toward the favorite by the measured bias (see <a href="#/research" style="text-decoration:underline">Research</a>). Prices are from the last odds snapshot, so check the book before betting. Use it to find the best price on a bet the rules already call for. An off-market price is not a reason to bet on its own: 2% edges broke even in the backtest here, and the model's five-year study found the same bet lost on clean books.</div>`;
}
function wireRows() { $app.querySelectorAll("tr.click").forEach(tr => tr.addEventListener("click", e => { if (e.target.closest("a")) return; location.hash = tr.dataset.href; })); }

/* ---------- views ---------- */
async function vHome() {
  const idx = await getJSON("index.json");
  let html = "";
  for (const u of idx.upcoming) {
    const ev = await getJSON(`events/${u.slug}.json`); await Promise.all([overlayLive(ev), overlaySheet(ev)]);
    html += `<h2>Next up · ${esc(ev.name)}</h2><div class="sub">${fdate(ev.date)} · ${esc(ev.location)} · <a href="#/card/${ev.slug}" style="text-decoration:underline">full card page</a></div><div style="height:8px"></div>${cardTable(ev)}${priceBoard(ev)}${methodBoard(ev)}<p><a class="btn" href="#/sheet/${ev.slug}">Printable form sheet →</a></p>`;
  }
  if (!idx.upcoming.length) html += `<div class="banner">No upcoming card loaded yet.</div>`;
  html += `<h2>Recent cards</h2><div class="cards">` + idx.events.slice(0, 12).map(e => `<a href="#/card/${e.slug}"><b>${esc(e.name)}</b><span>${fdate(e.date)} · ${e.nf} fights${e.model ? " · model" : ""}</span><br><span>${esc(e.main)}</span></a>`).join("") + `</div>
    <p><a class="btn" href="#/cards">All ${idx.counts.events} cards →</a></p>
    <h2>What's in the Form</h2>
    <div class="stats"><div><b>${idx.counts.events.toLocaleString()}</b><span>UFC cards</span></div><div><b>${idx.counts.fights.toLocaleString()}</b><span>Fights with stats</span></div><div><b>${idx.counts.fighters.toLocaleString()}</b><span>Fighter pages</span></div><div><b>${idx.counts.odds_fights.toLocaleString()}</b><span>Fights with line history</span></div></div>
    <p class="note">Every fight page carries a tale of the tape computed as of fight night, both fighters' past performances with closing lines, the open-to-close line chart, common opponents, and the model's projection where one was published.</p>`;
  $app.innerHTML = html; wireRows();
}

async function vCard(slug) {
  const ev = await getJSON(`events/${slug}.json`); await Promise.all([overlayLive(ev), overlaySheet(ev)]);
  const withOdds = ev.fights.filter(f => f.odds);
  const movers = withOdds.map(f => ({ f, mv: (f.odds.close.p - f.odds.open.p) * 100 })).sort((a, b) => Math.abs(b.mv) - Math.abs(a.mv)).slice(0, 5);
  let html = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/cards">Cards</a> › ${esc(ev.name)}</div>
    <h2>${esc(ev.name)} ${ev.status === "upcoming" ? '<span class="pill y">Upcoming</span>' : ""}</h2>
    <div class="sub">${fdate(ev.date)} · ${esc(ev.location)}${ev.odds_updated ? " · odds as of " + new Date(ev.odds_updated).toLocaleString() : ""}</div>
    <div class="links" style="margin-top:8px">${ev.widget ? `<a href="${ev.widget.file}" target="_blank" rel="noopener">Projection tables (widget)</a>` : ""}${ev.url ? `<a href="${esc(ev.url)}" target="_blank" rel="noopener">UFCStats event</a>` : ""}<a href="#/sheet/${ev.slug}">Printable form sheet</a></div>
    ${cardTable(ev)}${ev.status === "upcoming" ? priceBoard(ev) : ""}${methodBoard(ev)}`;
  if (movers.length) html += `<h3>Biggest line moves (open → ${ev.status === "final" ? "close" : "now"})</h3><div class="tw"><table><thead><tr><th class="l">Bout</th><th>Open</th><th>${ev.status === "final" ? "Close" : "Now"}</th><th>Move</th><th class="l">Toward</th><th class="l">Result</th></tr></thead><tbody>` +
    movers.map(({ f, mv }) => { const side = mv >= 0 ? "a" : "b"; const hit = f.result && f.result.winner ? (f.result.winner === side ? '<span class="W">steam won</span>' : '<span class="L">steam lost</span>') : ""; return `<tr class="click" data-href="#/fight/${ev.slug}/${f.n}"><td class="l">${esc(f.a.name)} vs ${esc(f.b.name)}</td><td>${ml(f.odds.open.ma)} / ${ml(f.odds.open.mb)}</td><td>${ml(f.odds.close.ma)} / ${ml(f.odds.close.mb)}</td><td class="b">${signed(Math.abs(mv))}</td><td class="l">${esc(f[side].name)}</td><td class="l">${hit}</td></tr>`; }).join("") + `</tbody></table></div>`;
  $app.innerHTML = html; wireRows();
}

function tapeRow(k, a, b, better, force) { // better: "hi" | "lo" | null; force: "a" | "b" overrides
  let ea = "", eb = "";
  const na = parseFloat(a), nb = parseFloat(b);
  if (force === "a") ea = " edge"; else if (force === "b") eb = "edge";
  else if (better && isFinite(na) && isFinite(nb) && na !== nb) { const aw = better === "hi" ? na > nb : na < nb; if (aw) ea = " edge"; else eb = "edge"; }
  return `<div class="row"><div class="a${ea}">${a}</div><div class="k">${k}</div><div class="${eb}">${b}</div></div>`;
}
const inches = (ht) => { const m = /(\d+)'(\d+)/.exec(ht || ""); return m ? +m[1] * 12 + +m[2] : null; };

async function vFight(slug, n) {
  const ev = await getJSON(`events/${slug}.json`); await Promise.all([overlayLive(ev), overlaySheet(ev)]);
  const f = ev.fights.find(x => String(x.n) === String(n));
  if (!f) { $app.innerHTML = `<div class="banner">Fight not found.</div>`; return; }
  const [A, B] = await Promise.all([f.a.slug ? getJSON(`fighters/${f.a.slug}.json`).catch(() => null) : null, f.b.slug ? getJSON(`fighters/${f.b.slug}.json`).catch(() => null) : null]);
  const prior = (F) => F ? F.fights.filter(x => x.d < ev.date) : [];
  const pa = prior(A), pb = prior(B), ga = agg(pa), gb = agg(pb);
  const final = ev.status === "final";
  const o = f.odds, m = f.model;
  const v = (x, d = 2) => x == null ? "—" : x.toFixed(d);
  const pc = (x) => x == null ? "—" : (x * 100).toFixed(0) + "%";
  const ba = (A && A.bio) || {}, bb = (B && B.bio) || {};
  const agA = ageAt(ba.dob, ev.date), agB = ageAt(bb.dob, ev.date);
  const layA = pa[0] ? daysBetween(ev.date, pa[0].d) : null, layB = pb[0] ? daysBetween(ev.date, pb[0].d) : null;

  let html = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/card/${ev.slug}">${esc(ev.name)}</a> › Fight ${f.n}</div>
  <div class="sub"><span class="pill k">Fight ${f.n}</span> ${f.title ? '<span class="pill y">Title</span>' : ""} ${esc(f.wc || "")}${f.sched ? " · " + f.sched + " rounds" : ""} · ${fdate(ev.date)} · ${esc(ev.location)}</div>
  <div class="bout"><div class="f r">${flink(f.a)}<small>UFC ${ga.rec} · Fig ${f.form ? f.form.ra.toFixed(0) : "—"} · Elo ${f.a.elo || "—"} · ${streak(pa)}</small></div><div class="vs">vs</div><div class="f">${flink(f.b)}<small>UFC ${gb.rec} · Fig ${f.form ? f.form.rb.toFixed(0) : "—"} · Elo ${f.b.elo || "—"} · ${streak(pb)}</small></div></div>`;
  if (final && f.result) html += `<div class="banner"><b>Result:</b> ${resultText(f)}${f.result.details ? " — " + esc(f.result.details) : ""}${f.result.ref ? " · Ref " + esc(f.result.ref) : ""}</div>`;

  // tale of the tape (as of fight night)
  html += `<div class="grid2"><div><h3>Tale of the tape · entering this fight</h3><div class="tape">
    ${tapeRow("Age", agA ? agA.toFixed(1) : "—", agB ? agB.toFixed(1) : "—", "lo")}
    ${tapeRow("Height", esc(ba.ht || "—"), esc(bb.ht || "—"), null, inches(ba.ht) && inches(bb.ht) && inches(ba.ht) !== inches(bb.ht) ? (inches(ba.ht) > inches(bb.ht) ? "a" : "b") : null)}
    ${tapeRow("Reach", ba.reach ? ba.reach + '"' : "—", bb.reach ? bb.reach + '"' : "—", "hi")}
    ${tapeRow("Stance", esc(ba.stance || "—"), esc(bb.stance || "—"), null)}
    ${tapeRow("UFC record", ga.rec, gb.rec, null)}
    ${tapeRow("Form Figure rating", f.form ? f.form.ra.toFixed(1) : "—", f.form ? f.form.rb.toFixed(1) : "—", "hi")}
    ${tapeRow("Last 3 figures", pa.slice(0, 3).map(x => x.fg == null ? "–" : Math.round(x.fg)).join(" · ") || "—", pb.slice(0, 3).map(x => x.fg == null ? "–" : Math.round(x.fg)).join(" · ") || "—", null)}
    ${tapeRow("Elo", f.a.elo || "—", f.b.elo || "—", "hi")}
    ${tapeRow("Layoff (days)", layA == null ? "debut" : layA, layB == null ? "debut" : layB, null)}
    ${tapeRow("SLpM", v(ga.slpm), v(gb.slpm), "hi")}
    ${tapeRow("SApM", v(ga.sapm), v(gb.sapm), "lo")}
    ${tapeRow("Strike diff /min", ga.diff == null ? "—" : signed(ga.diff, 2), gb.diff == null ? "—" : signed(gb.diff, 2), "hi")}
    ${tapeRow("R1 strike diff /min", ga.r1diff == null ? "—" : signed(ga.r1diff, 2), gb.r1diff == null ? "—" : signed(gb.r1diff, 2), "hi")}
    ${tapeRow("R3+ strike diff /min", ga.latediff == null ? "—" : signed(ga.latediff, 2), gb.latediff == null ? "—" : signed(gb.latediff, 2), "hi")}
    ${tapeRow("Str acc / def", pc(ga.acc) + " / " + pc(ga.def), pc(gb.acc) + " / " + pc(gb.def), null)}
    ${tapeRow("TD per 15", v(ga.td15), v(gb.td15), "hi")}
    ${tapeRow("TD acc / def", pc(ga.tdacc) + " / " + pc(ga.tdd), pc(gb.tdacc) + " / " + pc(gb.tdd), null)}
    ${tapeRow("Control %", ga.ctrlp == null ? "—" : (ga.ctrlp * 100).toFixed(0), gb.ctrlp == null ? "—" : (gb.ctrlp * 100).toFixed(0), "hi")}
    ${tapeRow("Controlled %", ga.octrlp == null ? "—" : (ga.octrlp * 100).toFixed(0), gb.octrlp == null ? "—" : (gb.octrlp * 100).toFixed(0), "lo")}
    ${tapeRow("KD per 15 (for-agst)", v(ga.kd15) + " - " + v(ga.okd15), v(gb.kd15) + " - " + v(gb.okd15), null)}
    ${tapeRow("Wins KO-SUB-DEC", `${ga.ko}-${ga.subw}-${ga.dec}`, `${gb.ko}-${gb.subw}-${gb.dec}`, null)}
    ${tapeRow("Losses KO-SUB-DEC", `${ga.kol}-${ga.subl}-${ga.decl}`, `${gb.kol}-${gb.subl}-${gb.decl}`, null)}
    ${tapeRow("UFC minutes", ga.min.toFixed(0), gb.min.toFixed(0), null)}
  </div><div class="note">UFC fights only, computed from fights before ${fdate(ev.date)}. Green = edge.</div></div><div>`;

  // market
  html += `<h3>Market · ${final ? "open to close" : "open to now"}</h3><div class="box">`;
  if (o) {
    const mv = (o.close.p - o.open.p) * 100;
    html += lineChart(o, f.a.name, f.b.name) + `<div style="height:8px"></div>
      <div class="kv"><span>First seen (${fdate(o.open.t.slice(0, 10))})</span><span>${esc(f.a.name)} ${ml(o.open.ma)} · ${esc(f.b.name)} ${ml(o.open.mb)} · ${pct(o.open.p)}</span></div>
      <div class="kv"><span>${final ? "Close" : "Now"} (${o.close.nb} books)</span><span><b>${esc(f.a.name)} ${ml(o.close.ma)} · ${esc(f.b.name)} ${ml(o.close.mb)}</b> · ${pct(o.close.p)}</span></div>
      <div class="kv"><span>Move</span><span class="${cls(Math.abs(mv) >= 1 ? 1 : 0)}">${signed(Math.abs(mv))} pts toward ${esc(mv >= 0 ? f.a.name : f.b.name)}</span></div>
      ${o.total ? `<div class="kv"><span>Total rounds</span><span>${o.total.pt} · O ${ml(o.total.over)} / U ${ml(o.total.under)} · over ${pct(o.total.p_over)}</span></div>` : ""}
      <div class="kv"><span>Snapshots</span><span>${o.n}</span></div>`;
    const bk = Object.entries(o.books || {});
    if (bk.length) html += `<div style="height:8px"></div><div class="tw"><table><thead><tr><th class="l">Book</th><th>${esc(f.a.name.split(" ").slice(-1)[0])}</th><th>${esc(f.b.name.split(" ").slice(-1)[0])}</th><th>No-vig</th></tr></thead><tbody>` +
      bk.map(([b, x]) => `<tr><td class="l">${esc((window.__books || {})[b] || b)}</td><td>${ml(x.ma)}</td><td>${ml(x.mb)}</td><td>${pct(x.p)}</td></tr>`).join("") + `</tbody></table></div>`;
  } else if (f.bp && f.bp.a && f.bp.a.cons != null) {
    html += `<div class="kv"><span>Open</span><span>${esc(f.a.name)} ${ml(f.bp.a.open)} · ${esc(f.b.name)} ${ml(f.bp.b.open)}</span></div><div class="kv"><span>${final ? "Close" : "Now"} (consensus)</span><span><b>${esc(f.a.name)} ${ml(f.bp.a.cons)} · ${esc(f.b.name)} ${ml(f.bp.b.cons)}</b></span></div><div class="kv"><span>DraftKings</span><span>${ml(f.bp.a.dk)} / ${ml(f.bp.b.dk)}</span></div><div class="kv"><span>FanDuel</span><span>${ml(f.bp.a.fd)} / ${ml(f.bp.b.fd)}</span></div>`;
  } else html += `<div class="note">No line history on file for this fight.</div>`;
  html += `</div>`;

  // model
  if (m && m.a && m.a.win != null) {
    const mk = o ? o.close.p * 100 : null;
    const row = (lab, X, name, mkp) => `<tr><td class="l b">${esc(name)}</td><td>${X.win.toFixed(1)}%</td><td>${ml(p2ml(X.win / 100))}</td><td>${ml(X.ml)}</td><td class="${cls(X.ml != null ? X.win - ml2p(X.ml) * 100 : null)}">${X.ml != null ? signed(X.win - ml2p(X.ml) * 100) : "—"}</td><td class="${cls(mkp != null ? X.win - mkp : null)}">${mkp != null ? signed(X.win - mkp) : "—"}</td><td>${X.dec != null ? X.dec.toFixed(0) : "—"}</td><td>${X.ko != null ? X.ko.toFixed(0) : "—"}</td><td>${X.sub != null ? X.sub.toFixed(0) : "—"}</td></tr>`;
    html += `<h3>Model projection${m.src === "sheet" ? " · from the model sheet" : ""} ${m.rec ? `<span class="pill y">Bet ${esc(m.rec === "a" ? f.a.name : f.b.name)}</span>` : ""}</h3><div class="tw"><table><thead><tr><th class="l">Fighter</th><th>Win</th><th>Fair</th><th title="Listed price when published">Listed</th><th title="Model minus listed implied %">Edge</th><th title="Model minus no-vig ${final ? "close" : "current"}">vs ${final ? "close" : "now"}</th><th>DEC%</th><th>KO%</th><th>SUB%</th></tr></thead><tbody>${row("a", m.a, f.a.name, mk)}${row("b", m.b, f.b.name, mk == null ? null : 100 - mk)}</tbody></table></div>
    ${m.gtd != null ? `<div class="note">Model goes-the-distance: ${m.gtd}%${o && o.total ? ` · market over ${o.total.pt}: ${pct(o.total.p_over)}` : ""}</div>` : ""}`;
  }
  html += sheetBox(f, final) + buildUp(f) + markovBox(f) + propsBox(f);
  // form numbers + angles
  const fm = f.form;
  if (fm) {
    const pm = o ? o.close.p : null, fa_ = pm == null ? null : fair(pm);
    const bA = bestPrice(o, "a"), bB = bestPrice(o, "b");
    const eA = fa_ != null && bA ? fa_ * ml2dec(bA.ml) - 1 : null, eB = fa_ != null && bB ? (1 - fa_) * ml2dec(bB.ml) - 1 : null;
    html += `<h3>Form numbers</h3><div class="tw"><table><thead><tr><th class="l"></th><th>${esc(last(f.a.name))}</th><th>${esc(last(f.b.name))}</th><th class="l">What it is</th></tr></thead><tbody>
      <tr><td class="l b">Fair line</td><td>${fa_ == null ? "—" : (fa_ * 100).toFixed(1) + "% · " + ml(p2ml(fa_))}</td><td>${fa_ == null ? "—" : ((1 - fa_) * 100).toFixed(1) + "% · " + ml(p2ml(1 - fa_))}</td><td class="l dim">Market, corrected for favorite-longshot bias</td></tr>
      <tr><td class="l b">Best price</td><td>${bA ? ml(bA.ml) + " " + esc(bookName(bA.book)) : "—"}</td><td>${bB ? ml(bB.ml) + " " + esc(bookName(bB.book)) : "—"}</td><td class="l dim">${final ? "At the close" : "Last snapshot"}</td></tr>
      <tr><td class="l b">Edge at best price</td><td class="${cls(eA)}">${eA == null ? "—" : signed(eA * 100) + "%"}</td><td class="${cls(eB)}">${eB == null ? "—" : signed(eB * 100) + "%"}</td><td class="l dim">Fair % × payout − 1</td></tr>
      <tr><td class="l b">Form Line</td><td>${fm.p == null ? "—" : (fm.p * 100).toFixed(1) + "%"}</td><td>${fm.p == null ? "—" : ((1 - fm.p) * 100).toFixed(1) + "%"}</td><td class="l dim">Stats-only model. Context, not a bet signal</td></tr>
${(() => { const M = methodRows(f); if (!M) return `<tr><td class="l b">Goes the distance</td><td colspan="2" class="c">${fm.g == null ? "—" : (fm.g * 100).toFixed(0) + "%"}</td><td class="l dim">Form distance model</td></tr>`;
        const r_ = (lab, k) => `<tr><td class="l b">${lab}</td><td>${(M.a[k] * 100).toFixed(0)}% · ${ml(p2ml(M.a[k]))}</td><td>${(M.b[k] * 100).toFixed(0)}% · ${ml(p2ml(M.b[k]))}</td><td class="l dim">${k === "dec" ? "Form method model on the " + M.src : ""}</td></tr>`;
        return r_("By decision", "dec") + r_("By KO/TKO", "ko") + r_("By submission", "sub") + r_("Inside distance", "itd") + `<tr><td class="l b">Goes the distance</td><td colspan="2" class="c">${(M.gtd * 100).toFixed(0)}% · ${ml(p2ml(M.gtd))} <span class="dim">(division base ${fm.base == null ? "—" : (fm.base * 100).toFixed(0) + "%"})</span></td><td class="l dim">Both decision chances added</td></tr>`; })()}
    </tbody></table></div>`;
    const A_ = window.__angles || {}, ang = Object.entries(fm.ang || {}).filter(([k]) => A_[k] && !/^(fav|dog)_all$/.test(k));
    if (ang.length) html += `<h3>Angles in play</h3><div class="tw"><table><thead><tr><th class="l">Angle</th><th class="l">Side</th><th title="Fights since 2022">N</th><th title="Actual win %">Won</th><th title="Win % the closing line implied">Mkt</th><th title="Flat bet at the consensus close">ROI</th></tr></thead><tbody>` +
      ang.map(([k, s_]) => { const a = A_[k]; return `<tr><td class="l">${esc(a[0])}</td><td class="l b">${esc(last(f[s_].name))}</td><td>${a[1]}</td><td>${(a[2] * 100).toFixed(1)}%</td><td class="dim">${(a[3] * 100).toFixed(1)}%</td><td class="${cls(a[4])}">${signed(a[4] * 100)}%</td></tr>`; }).join("") + `</tbody></table></div>`;
  }
  html += `</div></div>`;

  // fight stats if final
  if (final && f.stats && f.stats.a && f.stats.b) {
    const s = f.stats, r = (k, x, y) => `<div class="row"><div class="a">${x}</div><div class="k">${k}</div><div>${y}</div></div>`;
    html += `<h3>Fight stats</h3><div class="tape">${r("Sig. strikes", s.a.sl + " of " + s.a.sa, s.b.sl + " of " + s.b.sa)}${r("Head / body / leg", `${s.a.head} / ${s.a.body} / ${s.a.leg}`, `${s.b.head} / ${s.b.body} / ${s.b.leg}`)}${r("Dist / clinch / ground", `${s.a.dist} / ${s.a.clinch} / ${s.a.ground}`, `${s.b.dist} / ${s.b.clinch} / ${s.b.ground}`)}${r("Knockdowns", s.a.kd, s.b.kd)}${r("Takedowns", s.a.tl + " of " + s.a.ta, s.b.tl + " of " + s.b.ta)}${r("Control", mmss(s.a.ctrl), mmss(s.b.ctrl))}${r("Sub attempts", s.a.sub, s.b.sub)}</div>`;
  }

  // common opponents
  const ma = new Map(pa.map(x => [x.o, x])), common = pb.filter(x => ma.has(x.o));
  if (common.length) html += `<h3>Common opponents</h3><div class="tw"><table><thead><tr><th class="l">Opponent</th><th class="l">${esc(f.a.name)}</th><th class="l">${esc(f.b.name)}</th></tr></thead><tbody>` +
    common.map(x => { const y = ma.get(x.o); const c = (z) => `<span class="${z.r}">${z.r}</span> ${esc(shortMethod(z.m))} R${z.rd} · ${sdate(z.d)} · close ${ml((z.od || {}).mc)}`; return `<tr><td class="l b">${x.os ? `<a href="#/fighter/${x.os}">${esc(x.o)}</a>` : esc(x.o)}</td><td class="l">${c(y)}</td><td class="l">${c(x)}</td></tr>`; }).join("") + `</tbody></table></div>`;

  // links
  html += `<h3>Film & references</h3><div class="links"><a href="${yt(f.a.name, f.b.name)}" target="_blank" rel="noopener">▶ YouTube: this fight</a><a href="${fp(f.a.name, f.b.name)}" target="_blank" rel="noopener">UFC Fight Pass search</a>${f.url ? `<a href="${esc(f.url)}" target="_blank" rel="noopener">UFCStats fight detail</a>` : ""}${ev.widget && m ? `<a href="${ev.widget.file}?embed=fight&n=${m.widget_n}" target="_blank" rel="noopener">Projection widget</a>` : ""}</div>`;

  // past performances
  for (const [F, P, fx] of [[A, pa, f.a], [B, pb, f.b]]) {
    html += `<div class="pp-head"><div class="n">${flink(fx)} — past performances</div><div class="sub">${P.length} UFC fights before this one${F && F.dup_name ? ' · <span class="neg">name shared by two fighters; lines may be mixed</span>' : ""}</div></div>${ppTable(P, { name: fx.name, limit: 12 })}${P.length > 12 ? `<div class="note">Showing last 12 of ${P.length}. <a href="#/fighter/${fx.slug}" style="text-decoration:underline">Full history →</a></div>` : ""}`;
  }
  $app.innerHTML = html; wireRows();
}

async function vFighter(slug) {
  const F = await getJSON(`fighters/${slug}.json`);
  const g = agg(F.fights), b = F.bio || {};
  const v = (x, d = 2) => x == null ? "—" : x.toFixed(d), pc = (x) => x == null ? "—" : (x * 100).toFixed(0) + "%";
  // betting record at the close
  let bets = 0, pnl = 0, favW = 0, favN = 0, dogW = 0, dogN = 0, clv = 0, clvN = 0;
  for (const x of F.fights) { const od = x.od; if (!od || od.mc == null || (x.r !== "W" && x.r !== "L")) continue; bets++; const win = x.r === "W";
    pnl += win ? (od.mc > 0 ? od.mc / 100 : 100 / -od.mc) : -1; if (od.mc < 0) { favN++; if (win) favW++; } else { dogN++; if (win) dogW++; }
    if (od.po != null && od.pc != null) { clv += (od.pc - od.po) * 100; clvN++; } }
  // elo sparkline
  const FG = F.fights.slice().reverse().map(x => x.fg).filter(x => x != null);
  let figBars = "";
  if (FG.length > 1) { const W = 300, H = 60, bw = W / FG.length; figBars = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:60px"><line x1="0" x2="${W}" y1="${H / 2}" y2="${H / 2}" stroke="#cfc6ae"/>` + FG.map((v, i) => { const h = Math.max(1, Math.min(H, v / 120 * H)); return `<rect x="${(i * bw + 1).toFixed(1)}" y="${(H - h).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${h.toFixed(1)}" fill="${v >= 50 ? "#14663a" : "#a81c1c"}" opacity=".8"/>`; }).join("") + `</svg><div class="legend"><span>Form Figure by fight, oldest to newest (line = 50)</span></div>`; }
  const E = F.fights.slice().reverse().map(x => x.el).concat([F.elo]).filter(x => x != null);
  let spark = "";
  if (E.length > 2) { const W = 300, H = 60, lo = Math.min(...E) - 10, hi = Math.max(...E) + 10; const d = E.map((e, i) => (i ? "L" : "M") + (i / (E.length - 1) * W).toFixed(1) + " " + (H - (e - lo) / (hi - lo) * H).toFixed(1)).join("");
    spark = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:60px"><path d="${d}" fill="none" stroke="#17140f" stroke-width="1.8"/></svg><div class="legend"><span>Elo by fight: ${E[0]} → ${E[E.length - 1]} (peak ${Math.max(...E)})</span></div>`; }
  const age = ageAt(b.dob, new Date().toISOString().slice(0, 10));
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/fighters">Fighters</a> › ${esc(F.name)}</div>
    <h2>${esc(F.name)}</h2>
    ${F.dup_name ? '<div class="banner">Two UFC fighters share this name. Their fights are combined on this page.</div>' : ""}
    <div class="stats"><div><b>${g.rec}</b><span>UFC record</span></div><div><b>${F.fig == null ? "—" : F.fig.toFixed(1)}</b><span>Form Figure rating</span></div><div><b>${F.elo || "—"}</b><span>Elo</span></div><div><b>${streak(F.fights)}</b><span>Streak</span></div><div><b>${age ? age.toFixed(1) : "—"}</b><span>Age</span></div><div><b>${esc(b.ht || "—")}</b><span>Height</span></div><div><b>${b.reach ? b.reach + '"' : "—"}</b><span>Reach</span></div><div><b>${esc(b.stance || "—")}</b><span>Stance</span></div><div><b>${F.fights[0] ? esc(F.fights[0].wc.replace("Women's ", "W ")) : "—"}</b><span>Last weight</span></div></div>
    <div class="grid3" style="margin-top:14px">
      <div class="box"><h3 style="margin-top:0">Striking</h3><div class="kv"><span>SLpM</span><span>${v(g.slpm)}</span></div><div class="kv"><span>SApM</span><span>${v(g.sapm)}</span></div><div class="kv"><span>Diff / min</span><span class="${cls(g.diff)}">${g.diff == null ? "—" : signed(g.diff, 2)}</span></div><div class="kv"><span>Accuracy / defense</span><span>${pc(g.acc)} / ${pc(g.def)}</span></div><div class="kv"><span>R1 diff / min</span><span class="${cls(g.r1diff)}">${g.r1diff == null ? "—" : signed(g.r1diff, 2)}</span></div><div class="kv"><span>R3+ diff / min (${g.latemin.toFixed(0)} min)</span><span class="${cls(g.latediff)}">${g.latediff == null ? "—" : signed(g.latediff, 2)}</span></div><div class="kv"><span>KD per 15 (for-against)</span><span>${v(g.kd15)} - ${v(g.okd15)}</span></div></div>
      <div class="box"><h3 style="margin-top:0">Grappling</h3><div class="kv"><span>TD per 15</span><span>${v(g.td15)}</span></div><div class="kv"><span>TD acc / def</span><span>${pc(g.tdacc)} / ${pc(g.tdd)}</span></div><div class="kv"><span>Control %</span><span>${pc(g.ctrlp)}</span></div><div class="kv"><span>Controlled %</span><span>${pc(g.octrlp)}</span></div><div class="kv"><span>Sub att per 15</span><span>${v(g.sub15)}</span></div></div>
      <div class="box"><h3 style="margin-top:0">At the window</h3><div class="kv"><span>Flat 1u at the close</span><span class="${cls(pnl)}">${bets ? signed(pnl, 2) + "u / " + bets : "—"}</span></div><div class="kv"><span>As favorite</span><span>${favN ? favW + "-" + (favN - favW) : "—"}</span></div><div class="kv"><span>As underdog</span><span>${dogN ? dogW + "-" + (dogN - dogW) : "—"}</span></div><div class="kv"><span>Avg line move toward</span><span class="${cls(clvN ? clv / clvN : null)}">${clvN ? signed(clv / clvN) + " pts" : "—"}</span></div><div class="kv"><span>Wins KO-SUB-DEC</span><span>${g.ko}-${g.subw}-${g.dec}</span></div><div class="kv"><span>Losses KO-SUB-DEC</span><span>${g.kol}-${g.subl}-${g.decl}</span></div></div>
    </div>
    ${spark || figBars ? `<h3>Rating history</h3><div class="grid2"><div class="box">${figBars || ""}</div><div class="box">${spark || ""}</div></div>` : ""}
    ${splitsTable(F)}
    <div class="box noprint" style="margin-top:12px"><span class="sub">Compare with another fighter: </span><input id="cmpq" placeholder="type a name…" style="padding:5px 8px;border:1px solid var(--rule);background:#fffdf6;width:220px"> <span id="cmpdd"></span></div>
    <div class="pp-head"><div class="n">Past performances</div><div class="sub">${F.fights.length} UFC fights · closing lines from 2022 on</div></div>
    ${ppTable(F.fights, { name: F.name })}
    <div class="links" style="margin-top:10px"><a href="https://www.youtube.com/results?search_query=${encodeURIComponent(F.name + " UFC full fight")}" target="_blank" rel="noopener">▶ YouTube: full fights</a><a href="https://ufcfightpass.com/search?q=${encodeURIComponent(F.name)}" target="_blank" rel="noopener">UFC Fight Pass search</a>${b.url ? `<a href="${esc(b.url)}" target="_blank" rel="noopener">UFCStats profile</a>` : ""}</div>`;
  const cq = document.getElementById("cmpq"), cd = document.getElementById("cmpdd");
  if (cq) cq.addEventListener("input", async () => { const q = cq.value.trim().toLowerCase(); if (q.length < 2) { cd.innerHTML = ""; return; }
    const S = await getJSON("search.json"); cd.innerHTML = S.filter(x => x[0].toLowerCase().includes(q) && x[1] !== F.slug).slice(0, 6).map(x => `<a class="btn" style="margin:2px" href="#/compare/${F.slug}/${x[1]}">${esc(x[0])}</a>`).join(""); });
}

function splitsTable(F) {
  const L = F.fights, defs = [
    ["As favorite", x => x.od && x.od.mc != null && x.od.mc < 0], ["As underdog", x => x.od && x.od.mc != null && x.od.mc > 0],
    ["Five-round fights", x => x.sc === 5], ["Three-round fights", x => x.sc === 3], ["Title fights", x => x.ti],
    ["Off a layoff of 300+ days", (x, i) => L[i + 1] && daysBetween(x.d, L[i + 1].d) >= 300], ["Within 120 days of last fight", (x, i) => L[i + 1] && daysBetween(x.d, L[i + 1].d) <= 120],
    ["After a win", (x, i) => L[i + 1] && L[i + 1].r === "W"], ["After a loss", (x, i) => L[i + 1] && L[i + 1].r === "L"],
    ["Vs opponents rated 1575+ Elo", x => x.oe >= 1575], ["Vs opponents under 1500 Elo", x => x.oe && x.oe < 1500], ["Last 5 fights", (x, i) => i < 5]];
  const rows = [];
  for (const [name, fn] of defs) { const S = L.filter((x, i) => fn(x, i)); if (S.length < 2) continue; const g = agg(S);
    let pnl = 0, nb = 0; for (const x of S) { if (!x.od || x.od.mc == null || (x.r !== "W" && x.r !== "L")) continue; nb++; pnl += x.r === "W" ? (x.od.mc > 0 ? x.od.mc / 100 : 100 / -x.od.mc) : -1; }
    const figs = S.map(x => x.fg).filter(v => v != null);
    rows.push(`<tr><td class="l b">${name}</td><td>${g.rec}</td><td>${figs.length ? (figs.reduce((a, b) => a + b, 0) / figs.length).toFixed(0) : "—"}</td><td class="${cls(g.diff)}">${g.diff == null ? "—" : signed(g.diff, 2)}</td><td>${g.td15 == null ? "—" : g.td15.toFixed(2)}</td><td>${g.ctrlp == null ? "—" : (g.ctrlp * 100).toFixed(0) + "%"}</td><td>${g.ko}-${g.subw}-${g.dec}</td><td class="${cls(nb ? pnl : null)}">${nb ? signed(pnl, 2) + "u / " + nb : "—"}</td></tr>`); }
  return rows.length ? `<h3>Splits</h3><div class="tw"><table><thead><tr><th class="l">Situation</th><th>Record</th><th title="Average Form Figure">Avg fig</th><th>Str ±/min</th><th>TD/15</th><th>Ctrl</th><th title="Wins by KO-SUB-DEC">Wins K-S-D</th><th title="Flat 1u at the closing line">At the close</th></tr></thead><tbody>${rows.join("")}</tbody></table></div>` : "";
}

async function vCompare(sa, sb) {
  const [A, B] = await Promise.all([getJSON(`fighters/${sa}.json`), getJSON(`fighters/${sb}.json`)]);
  const ga = agg(A.fights), gb = agg(B.fights), ba = A.bio || {}, bb = B.bio || {}, today = new Date().toISOString().slice(0, 10);
  const v = (x, d = 2) => x == null ? "—" : x.toFixed(d), pc = (x) => x == null ? "—" : (x * 100).toFixed(0) + "%";
  const aA = ageAt(ba.dob, today), aB = ageAt(bb.dob, today);
  const ma = new Map(A.fights.map(x => [x.o, x])), common = B.fights.filter(x => ma.has(x.o));
  const h2h = A.fights.filter(x => x.os === B.slug);
  let html = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/fighters">Fighters</a> › Compare</div>
  <div class="bout"><div class="f r"><a href="#/fighter/${A.slug}">${esc(A.name)}</a><small>UFC ${ga.rec} · Fig ${A.fig == null ? "—" : A.fig.toFixed(0)} · Elo ${A.elo || "—"} · ${streak(A.fights)}</small></div><div class="vs">vs</div><div class="f"><a href="#/fighter/${B.slug}">${esc(B.name)}</a><small>UFC ${gb.rec} · Fig ${B.fig == null ? "—" : B.fig.toFixed(0)} · Elo ${B.elo || "—"} · ${streak(B.fights)}</small></div></div>
  <h3>Tale of the tape · today</h3><div class="tape">
    ${tapeRow("Age", aA ? aA.toFixed(1) : "—", aB ? aB.toFixed(1) : "—", "lo")}
    ${tapeRow("Height", esc(ba.ht || "—"), esc(bb.ht || "—"), null, inches(ba.ht) && inches(bb.ht) && inches(ba.ht) !== inches(bb.ht) ? (inches(ba.ht) > inches(bb.ht) ? "a" : "b") : null)}
    ${tapeRow("Reach", ba.reach ? ba.reach + '"' : "—", bb.reach ? bb.reach + '"' : "—", "hi")}
    ${tapeRow("Stance", esc(ba.stance || "—"), esc(bb.stance || "—"), null)}
    ${tapeRow("Form Figure rating", A.fig == null ? "—" : A.fig.toFixed(1), B.fig == null ? "—" : B.fig.toFixed(1), "hi")}
    ${tapeRow("Last 3 figures", A.fights.slice(0, 3).map(x => x.fg == null ? "–" : Math.round(x.fg)).join(" · "), B.fights.slice(0, 3).map(x => x.fg == null ? "–" : Math.round(x.fg)).join(" · "), null)}
    ${tapeRow("Elo", A.elo || "—", B.elo || "—", "hi")}
    ${tapeRow("SLpM", v(ga.slpm), v(gb.slpm), "hi")}${tapeRow("SApM", v(ga.sapm), v(gb.sapm), "lo")}
    ${tapeRow("Strike diff /min", ga.diff == null ? "—" : signed(ga.diff, 2), gb.diff == null ? "—" : signed(gb.diff, 2), "hi")}
    ${tapeRow("R1 strike diff /min", ga.r1diff == null ? "—" : signed(ga.r1diff, 2), gb.r1diff == null ? "—" : signed(gb.r1diff, 2), "hi")}
    ${tapeRow("R3+ strike diff /min", ga.latediff == null ? "—" : signed(ga.latediff, 2), gb.latediff == null ? "—" : signed(gb.latediff, 2), "hi")}
    ${tapeRow("TD per 15", v(ga.td15), v(gb.td15), "hi")}${tapeRow("TD acc / def", pc(ga.tdacc) + " / " + pc(ga.tdd), pc(gb.tdacc) + " / " + pc(gb.tdd), null)}
    ${tapeRow("Control %", ga.ctrlp == null ? "—" : (ga.ctrlp * 100).toFixed(0), gb.ctrlp == null ? "—" : (gb.ctrlp * 100).toFixed(0), "hi")}
    ${tapeRow("KD per 15 (for-agst)", v(ga.kd15) + " - " + v(ga.okd15), v(gb.kd15) + " - " + v(gb.okd15), null)}
    ${tapeRow("Wins KO-SUB-DEC", `${ga.ko}-${ga.subw}-${ga.dec}`, `${gb.ko}-${gb.subw}-${gb.dec}`, null)}
    ${tapeRow("Losses KO-SUB-DEC", `${ga.kol}-${ga.subl}-${ga.decl}`, `${gb.kol}-${gb.subl}-${gb.decl}`, null)}
  </div>`;
  if (h2h.length) html += `<h3>Head to head</h3>${ppTable(h2h, { name: A.name })}<div class="note">From ${esc(A.name)}'s side.</div>`;
  if (common.length) html += `<h3>Common opponents</h3><div class="tw"><table><thead><tr><th class="l">Opponent</th><th class="l">${esc(A.name)}</th><th class="l">${esc(B.name)}</th></tr></thead><tbody>` +
    common.map(x => { const y = ma.get(x.o); const c = (z) => `<span class="${z.r}">${z.r}</span> ${esc(shortMethod(z.m))} R${z.rd} · ${sdate(z.d)} · fig ${z.fg == null ? "—" : Math.round(z.fg)} · close ${ml((z.od || {}).mc)}`; return `<tr><td class="l b">${x.os ? `<a href="#/fighter/${x.os}">${esc(x.o)}</a>` : esc(x.o)}</td><td class="l">${c(y)}</td><td class="l">${c(x)}</td></tr>`; }).join("") + `</tbody></table></div>`;
  html += `<div class="pp-head"><div class="n">${esc(A.name)}</div></div>${ppTable(A.fights, { name: A.name, limit: 8 })}<div class="pp-head"><div class="n">${esc(B.name)}</div></div>${ppTable(B.fights, { name: B.name, limit: 8 })}`;
  $app.innerHTML = html; wireRows();
}

async function vCards() {
  const idx = await getJSON("index.json");
  const byYear = {};
  for (const e of idx.events) (byYear[e.date.slice(0, 4)] = byYear[e.date.slice(0, 4)] || []).push(e);
  let html = `<div class="crumbs"><a href="#/">Home</a> › Cards</div><h2>All cards</h2>`;
  for (const u of idx.upcoming) html += `<p><a class="btn" href="#/card/${u.slug}">Upcoming: ${esc(u.name)} · ${fdate(u.date)}</a></p>`;
  for (const y of Object.keys(byYear).sort().reverse()) html += `<h3>${y} · ${byYear[y].length} cards</h3><div class="tw"><table><thead><tr><th class="l">Date</th><th class="l">Card</th><th class="l">Main event</th><th>Fights</th><th>Lines</th><th>Model</th></tr></thead><tbody>` +
    byYear[y].map(e => `<tr class="click" data-href="#/card/${e.slug}"><td class="l">${sdate(e.date)}</td><td class="l b">${esc(e.name)}</td><td class="l">${esc(e.main)}</td><td>${e.nf}</td><td>${e.odds || "—"}</td><td>${e.model ? "✓" : ""}</td></tr>`).join("") + `</tbody></table></div>`;
  $app.innerHTML = html; wireRows();
}

async function vFighters() {
  const S = await getJSON("search.json");
  const top = S.filter(x => x[2] >= String(new Date().getFullYear() - 2)).filter(x => x[7] >= 3).sort((a, b) => (b[6] || 0) - (a[6] || 0)).slice(0, 60);
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › Fighters</div><h2>Fighters</h2><p class="sub">${S.length.toLocaleString()} fighters. Use the search box above, or start from the highest-rated active fighters.</p>
    <div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Fighter</th><th class="l">Last weight</th><th>UFC record</th><th>Fig</th><th>Elo</th><th class="l">Last fight</th></tr></thead><tbody>` +
    top.map((x, i) => `<tr class="click" data-href="#/fighter/${x[1]}"><td class="c dim">${i + 1}</td><td class="l b">${esc(x[0])}</td><td class="l">${esc(x[3])}</td><td>${x[4]}</td><td class="b">${x[6] == null ? "—" : x[6].toFixed(1)}</td><td>${x[5] || "—"}</td><td class="l">${sdate(x[2])}</td></tr>`).join("") + `</tbody></table></div>
    <p><a class="btn" href="#/rankings">Rankings by division →</a></p><p class="note">Form Figure rating is the recency-weighted average of a fighter's performance figures (50 = average). Elo is a simple results-only rating over every UFC fight (1500 start, K=48 for a fighter's first four fights, then 32). It is a context number for opponent quality, not the betting model.</p>`;
  wireRows();
}

async function vModel() {
  const M = await getJSON("model.json");
  const R = M.recs, w = R.filter(x => x.won).length, pnl = R.reduce((s, x) => s + (x.pnl || 0), 0), risk = R.reduce((s, x) => s + (x.risk || 0), 0);
  const withClose = R.filter(x => x.close_p != null && x.ml != null), beat = withClose.filter(x => x.close_ml != null && ml2p(x.ml) < ml2p(x.close_ml)).length;
  const SB = M.sheet, B = (v) => v && v[0] != null ? `${v[0]} <span class="dim">(${v[1]})</span>` : "—";
  const sbHtml = SB && SB.n ? `<h2>Model sheet tracker · v4.x</h2><p class="sub">${SB.n} graded fights over ${SB.cards} cards, read from the sheet's Snapshots tab. Brier score: lower is better; fight counts in brackets.</p>
    <div class="stats"><div><b>${SB.rec.w}-${SB.rec.n - SB.rec.w}</b><span>Moneyline recs</span></div><div><b class="${cls(SB.rec.pnl)}">${signed(SB.rec.pnl, 2)}u</b><span>Rec P/L</span></div><div><b>${SB.plays.w}-${SB.plays.n - SB.plays.w}</b><span>GTD / ITD plays</span></div><div><b class="${cls(SB.plays.pnl)}">${signed(SB.plays.pnl, 2)}u</b><span>Play P/L</span></div></div>
    <div class="grid3" style="margin-top:12px">
      <div><h3>Moneyline</h3><div class="tw"><table><thead><tr><th class="l">Source</th><th>Brier</th></tr></thead><tbody>${SB.ml.map(x => `<tr><td class="l b">${x.k}</td><td>${B(x.v)}</td></tr>`).join("")}</tbody></table></div></div>
      <div><h3>Goes the distance</h3><div class="tw"><table><thead><tr><th class="l">Source</th><th>Brier</th></tr></thead><tbody>${SB.gtd.map(x => `<tr><td class="l b">${x.k}</td><td>${B(x.v)}</td></tr>`).join("")}</tbody></table></div></div>
      <div><h3>Method (six outcomes)</h3><div class="tw"><table><thead><tr><th class="l">Source</th><th>Brier</th></tr></thead><tbody>${SB.method.map(x => `<tr><td class="l b">${x.k}</td><td>${B(x.v)}</td></tr>`).join("")}</tbody></table></div></div>
    </div>
    <h3>Flags · how the underdog did</h3><div class="tw"><table><thead><tr><th class="l">Flag</th><th>Fights</th><th>Dog won</th><th>Dog win %</th><th>Close implied</th></tr></thead><tbody>${SB.flags.map(x => `<tr><td class="l b">${esc(x.flag)}</td><td>${x.n}</td><td>${x.dog_w}</td><td class="b">${(x.dog_w / x.n * 100).toFixed(0)}%</td><td class="dim">${(x.dog_exp * 100).toFixed(0)}%</td></tr>`).join("")}${SB.public_dog.n ? `<tr><td class="l b">Public 10+ pts above the close on the dog</td><td>${SB.public_dog.n}</td><td>${SB.public_dog.dog_w}</td><td class="b">${(SB.public_dog.dog_w / SB.public_dog.n * 100).toFixed(0)}%</td><td class="dim">${(SB.public_dog.dog_exp * 100).toFixed(0)}%</td></tr>` : ""}</tbody></table></div>
    <p class="note">Fight pages for these cards show every input (public picks, opener, Markov, sheet model), the flags and the closing prop market.</p>` : "";
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › Model</div>${sbHtml}<h2>Published projections · June to November</h2>
    <p class="sub">Every moneyline bet the projection widgets flagged, graded automatically against UFCStats results. Stakes: risk 1u on plus money, to win 1u on minus money, at the price listed when the projection was published.</p>
    <div class="stats"><div><b>${w}-${R.length - w}</b><span>Flagged bets</span></div><div><b class="${cls(pnl)}">${signed(pnl, 2)}u</b><span>Profit / loss</span></div><div><b class="${cls(pnl)}">${risk ? signed(pnl / risk * 100) + "%" : "—"}</b><span>ROI on ${risk.toFixed(1)}u risked</span></div><div><b>${withClose.length ? beat + "/" + withClose.length : "—"}</b><span>Beat the closing line</span></div><div><b>${M.brier_model ?? "—"}</b><span>Brier · model (${M.n_both} fights)</span></div><div><b>${M.brier_close ?? "—"}</b><span>Brier · closing line</span></div></div>
    <p class="note">Brier score: lower is better. Compared on fights with both a model win % and a no-vig closing line.</p>
    ${M.splits ? `<div class="tw"><table><thead><tr><th class="l">Flagged bets</th><th>Record</th><th>P/L</th><th>ROI</th></tr></thead><tbody>` + Object.entries(M.splits).map(([k, v]) => `<tr><td class="l b">${k}</td><td>${v.w}-${v.n - v.w}</td><td class="${cls(v.pnl)}">${signed(v.pnl, 2)}u</td><td class="${cls(v.pnl)}">${v.risk ? signed(v.pnl / v.risk * 100) + "%" : "—"}</td></tr>`).join("") + `</tbody></table></div>` : ""}
    ${M.blend ? `<div class="box" style="margin-top:10px;font:13.5px/1.5 var(--serif)"><b>Model against the market, all ${M.blend.n} projected fights.</b> Log loss: model ${M.ll_model}, closing line ${M.ll_close}. A blend fit on these fights weights the close ${M.blend.w_close} and the model ${M.blend.w_model}, so the model carries some information the close does not. When the model was higher than the market on the favorite, the favorite went ${M.edge_fav.w}-${M.edge_fav.n - M.edge_fav.w}. When it was higher on the underdog, the underdog went ${M.edge_dog.w}-${M.edge_dog.n - M.edge_dog.w}. Small sample; the blend weights are fit in-sample.${M.method6 ? ` On method of victory (who wins and how, six outcomes, ${M.method6.n} fights) the model's log loss is ${M.method6.ll_model} against ${M.method6.ll_form} for the Form method board, so the model's method splits are the better of the two.` : ""}</div>` : ""}
    <div class="tw"><table><thead><tr><th class="l">Date</th><th class="l">Pick</th><th class="l">Over</th><th>Listed</th><th>Model</th><th>Close</th><th title="Listed price vs closing price, in implied %">CLV</th><th class="c">Res</th><th>P/L</th></tr></thead><tbody>` +
    R.map(x => { const clv = x.close_ml != null && x.ml != null ? (ml2p(x.close_ml) - ml2p(x.ml)) * 100 : null; return `<tr class="click" data-href="#/fight/${x.es}/${x.n}"><td class="l">${sdate(x.d)}</td><td class="l b">${esc(x.pick)}</td><td class="l">${esc(x.opp)}</td><td>${ml(x.ml)}</td><td>${x.win != null ? x.win.toFixed(1) + "%" : "—"}</td><td>${ml(x.close_ml)}</td><td class="${cls(clv)}">${clv == null ? "—" : signed(clv)}</td><td class="c ${x.won ? "W" : "L"}">${x.won ? "W" : "L"}</td><td class="${cls(x.pnl)}">${x.pnl == null ? "—" : signed(x.pnl, 2)}</td></tr>`; }).join("") + `</tbody></table></div>`;
  wireRows();
}

async function vAbout() {
  const idx = await getJSON("index.json");
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › About</div><h2>About the Form</h2>
  <div class="box" style="font:14px/1.55 var(--serif)">
  <p><b>MMA Fight Form</b> is a past-performance sheet for fights: everything a handicapper wants on one page, in the same place every time.</p>
  <p><b>Past performances.</b> One line per UFC fight: opponent and their rating going in, result, method, round and time, the closing moneyline and how far it moved from the open, significant strikes for and against, knockdowns, takedowns, control time and the layoff since the previous fight.</p>
  <p><b>Tale of the tape.</b> Rates are rebuilt as of fight night from fights before that date, so a historical page shows what was knowable then.</p>
  <p><b>Lines.</b> Consensus is the median no-vig price across the US books and Pinnacle in the odds archive. From 2022 through 2025 there are two snapshots a day; 2026 has fight-weekend snapshots plus the live feed, so "first seen" can be later than the true opener.</p>
  <p><b>Model.</b> Where a projection was published, the fight page shows win and method probabilities, the listed price at the time, and the edge against both that price and the close.</p>
  <p><b>Model.</b> The projection is market-anchored, not a prediction from scratch. Five years of UFC fights say the closing line is well calibrated and that fighter stats, Elo, fan and tipster consensus, sharp money, offshore books and line drift add nothing to it. So the model starts from the listed line and makes a few small, evidence-backed moves: a 15% pull toward an independent Markov-chain simulation of the fight, a 4-point cut for women's underdogs, context codes for debutant, regional decision-grinder and retiring fighters, and a fade when the public is heavier on the underdog than the price is. Each fight page shows that build-up line by line.</p>
  <p><b>Bet rules.</b> Underdogs need 8 points of edge and a clean flag (no debut code, no sharp or public pile-on, no 4-point drift). Favorites need 3 points. Favorites priced 80% or higher are a standing bet at the best price. Five-round fights with the distance priced at 40% or more are a standing GTD bet. Inside-the-distance, unders and method props are shown as information because they lose most years.</p>
  <p><b>Distance and method.</b> Each fighter gets a finish rate for wins and for losses, regressed toward the division. Fight GTD blends those with the Markov decision share, the division rate and the listed GTD price. Decision shares are then set so the two fighters' decision chances add up exactly to the fight GTD, and the KO-versus-submission split is anchored halfway to the market's.</p>
  <p><b>Grading.</b> Every card is snapshotted at the first walkout and graded on Sunday: Brier scores for the close, the model and Markov, and profit and loss on each recommendation. The <a href="#/model" style="text-decoration:underline">Model page</a> shows the running result.</p>
  <p><b>Sources.</b> Fight results and round-by-round stats: UFCStats, via the open <a href="https://github.com/Greco1899/scrape_ufc_stats" target="_blank" rel="noopener" style="text-decoration:underline">scrape_ufc_stats</a> dataset (GPL-3.0). Odds: The Odds API history and BettingPros. Film links are searches on YouTube and UFC Fight Pass; nothing is hosted here.</p>
  <p class="dim">Data built ${new Date(idx.built).toLocaleString()} · ${idx.counts.events} cards · ${idx.counts.fights.toLocaleString()} fights · ${idx.counts.fighters.toLocaleString()} fighters · ${idx.counts.odds_fights.toLocaleString()} fights with line history.</p></div>`;
}


async function vRankings() {
  const S = await getJSON("search.json");
  const cut = new Date(Date.now() - 550 * 864e5).toISOString().slice(0, 10);
  const act = S.filter(x => x[2] >= cut && x[7] >= 2 && x[6] != null);
  const order = ["Heavyweight", "Light Heavyweight", "Middleweight", "Welterweight", "Lightweight", "Featherweight", "Bantamweight", "Flyweight", "Women's Bantamweight", "Women's Flyweight", "Women's Strawweight"];
  const by = {}; for (const x of act) { const k = x[3].replace("Interim ", ""); (by[k] = by[k] || []).push(x); }
  let html = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/fighters">Fighters</a> › Rankings</div><h2>Form rankings</h2><p class="sub">By Form Figure rating. Fighters with 2+ UFC fights who fought in the last 18 months, listed at the weight of their last fight.</p><div class="grid2">`;
  for (const d of order) { const L = (by[d] || []).sort((a, b) => b[6] - a[6]).slice(0, 15); if (!L.length) continue;
    html += `<div><h3>${esc(d)}</h3><div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Fighter</th><th>UFC</th><th>Fig</th><th>Elo</th></tr></thead><tbody>` + L.map((x, i) => `<tr class="click" data-href="#/fighter/${x[1]}"><td class="c dim">${i + 1}</td><td class="l b">${esc(x[0])}</td><td>${x[4]}</td><td class="b">${x[6].toFixed(1)}</td><td class="dim">${x[5] || "—"}</td></tr>`).join("") + `</tbody></table></div></div>`; }
  $app.innerHTML = html + `</div>`; wireRows();
}

async function vResearch() {
  const R = await getJSON("research.json");
  const P = (x, d = 1) => x == null ? "—" : (x * 100).toFixed(d) + "%";
  const sg = (x, d = 1) => x == null ? "—" : `<span class="${cls(x)}">${signed(x * 100, d)}%</span>`;
  const tbl = (head, rows) => `<div class="tw"><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>`;
  const A = Object.fromEntries(R.angles.map(a => [a.id, a]));
  const s0 = R.scores[0], s2 = R.scores[2], fav = A.fav_all, dog = A.dog_all, simBest = R.sims[1], sim70 = R.sims[5];
  const yrs = (o) => Object.entries(o || {}).map(([y, v]) => `${y.slice(2)}: ${signed((v[1] !== undefined && v.length === 2 ? v[1] : v[2] / v[0]) * 100, 0)}%`).join(" · ");
  let html = `<div class="crumbs"><a href="#/">Home</a> › Research</div><h2>Research · what the data says</h2>
  <p class="sub">${R.n.toLocaleString()} UFC fights with line history, ${fdate(R.from)} to ${fdate(R.to)}. Every return is a flat one-unit bet. "Mkt" is the win rate the no-vig closing line implied.</p>
  <div class="box" style="font:14.5px/1.55 var(--serif)">
    <p><b>1. The closing line is very hard to beat with stats.</b> Its log loss is ${s0.ll} and it picks ${P(s0.acc)} of winners. The stats-only Form Line scores ${s2.ll} and ${P(s2.acc)}. Betting where the Form Line disagreed with the close by 10+ points lost ${P(-A.fl10.roi_c)} per bet.</p>
    <p><b>2. Favorites are underpriced and underdogs overpriced.</b> Favorites won ${P(fav.act)} against an implied ${P(fav.exp)}. Blind favorites at the consensus close returned ${sg(fav.roi_c)}; blind underdogs returned ${sg(dog.roi_c)}. The bias slope is ${R.k}: a 70% no-vig favorite has really been about ${P(1 / (1 + Math.exp(-R.k * Math.log(0.7 / 0.3))), 0)}.</p>
    <p><b>3. Price shopping turns that into a small edge.</b> Every favorite at the best closing price across books returned ${sg(simBest.roi)} over ${simBest.n.toLocaleString()} bets. Favorites of 70%+ at the best price returned ${sg(sim70.roi)} and were positive every year.</p>
    <p><b>4. Favorites get shorter.</b> ${R.drift ? `The opening favorite's price shortened in ${P(R.drift.shorter, 0)} of fights and lengthened in ${P(R.drift.longer, 0)}.` : ""} Favorites at the first-seen price returned ${sg(fav.roi_o)}. Take favorites early and underdogs late.</p>
    <p><b>5. Steam is already in the price.</b> Fighters the line moved 3+ points toward won ${P(A.steam3.act)} against an implied ${P(A.steam3.exp)} and returned ${sg(A.steam3.roi_c)} at the close. The value was in having the earlier number.</p>
    <p><b>6. Totals are priced tightly.</b> Blind overs and unders both lose at 1.5 and 2.5 rounds, and the Form distance model added nothing to the market's number. The one lean is the over 4.5 in five-round fights (${(R.totals.find(x => x.pt === 4.5) || {}).n || 0} fights, ${sg((R.totals.find(x => x.pt === 4.5) || {}).roi_over)}), which is a small sample.</p>
  </div>
  <div class="note">Robustness: the favorite bias and the 70%+ result hold when the price is taken at least three hours before the fight (bias slope 1.19, 70%+ favorites +4.3% at the best price), and no book's closing price sat more than 6 points from the median in more than 0.1% of fights, so live in-fight prices are not driving it.</div>
  <h3>Scoreboard</h3>` + tbl(`<th class="l">Predictor</th><th>Fights</th><th>Log loss</th><th>Brier</th><th>Winner picked</th>`, R.scores.map(x => `<tr><td class="l b">${esc(x.k)}</td><td>${x.n}</td><td>${x.ll}</td><td>${x.brier}</td><td>${P(x.acc)}</td></tr>`).join("")) +
  (R.blend ? `<div class="note">Adding the Form Line to the close in a walk-forward blend moves log loss from ${R.blend.ll_close} to ${R.blend.ll_blend} (weights: close ${R.blend.w_close}, Form Line ${R.blend.w_form}).</div>` : "") +
  `<div class="grid2"><div><h3>Is the close calibrated? (favorite side)</h3>` + tbl(`<th class="l">No-vig favorite</th><th>Fights</th><th>Mkt</th><th>Won</th><th>Gap</th>`, R.calib_close.map(x => `<tr><td class="l">${x.band}</td><td>${x.n}</td><td>${P(x.exp)}</td><td class="b">${P(x.act)}</td><td>${sg(x.act - x.exp)}</td></tr>`).join("")) +
  `</div><div><h3>Which book closes sharpest?</h3>` + (R.books ? tbl(`<th class="l">Book</th><th>Log loss</th><th>Brier</th>`, R.books.rows.map(x => `<tr><td class="l b">${esc(bookName(x.book))}</td><td>${x.ll}</td><td>${x.brier}</td></tr>`).join("")) + `<div class="note">${R.books.n.toLocaleString()} fights where all seven books had a closing price. The differences are tiny.</div>` : "") + `</div></div>
  <h3>Simple strategies</h3>` + tbl(`<th class="l">Strategy</th><th>Bets</th><th>Won</th><th>ROI</th><th>Units</th><th class="l">ROI by year</th>`, R.sims.map(x => `<tr><td class="l b">${esc(x.name)}</td><td>${x.n}</td><td>${P(x.win)}</td><td>${sg(x.roi)}</td><td class="${cls(x.pnl)}">${signed(x.pnl, 1)}</td><td class="l dim">${Object.entries(x.years).map(([y, v]) => `${y.slice(2)}: ${signed(v[1] * 100, 0)}%`).join(" · ")}</td></tr>`).join("")) +
  `<h3>Angles · every one graded against the closing line</h3>` + tbl(`<th class="l">Angle (bet the fighter described)</th><th>Fights</th><th>Won</th><th>Mkt</th><th title="Standard errors above or below the market's expectation">z</th><th>ROI at close</th><th title="Uses the first-seen price">ROI at open</th><th class="l">ROI by year (close)</th>`,
    R.angles.map(a => `<tr><td class="l b">${esc(a.name)}</td><td>${a.n}</td><td>${P(a.act)}</td><td class="dim">${P(a.exp)}</td><td class="${Math.abs(a.z) >= 2 ? "b " + cls(a.z) : "dim"}">${signed(a.z, 2)}</td><td>${sg(a.roi_c)}</td><td>${sg(a.roi_o)}</td><td class="l dim">${Object.entries(a.years).map(([y, v]) => `${y.slice(2)}: ${signed(v[2] / v[0] * 100, 0)}%`).join(" · ")}</td></tr>`).join("")) +
  `<div class="note">With ${R.angles.length} angles tested, one or two will clear z = 2 by luck. Steam angles at the "open" price use information you would not have had at the open. 2026 first-seen prices are often fight-week prices.</div>
  <div class="grid2"><div><h3>Totals · is the over priced right?</h3>` + tbl(`<th class="l">Line</th><th>Fights</th><th>Mkt over</th><th>Went over</th><th>Gap</th><th>Over ROI</th><th>Under ROI</th>`, R.totals.map(x => `<tr><td class="l b">${x.pt}</td><td>${x.n}</td><td>${P(x.exp)}</td><td class="b">${P(x.act)}</td><td>${sg(x.act - x.exp)}</td><td>${sg(x.roi_over)}</td><td>${sg(x.roi_under)}</td></tr>`).join("")) +
  (R.gtd ? `<h3>Form distance model</h3>` + tbl(`<th class="l">Model said</th><th>Fights</th><th>Avg</th><th>Went distance</th>`, R.gtd_calib.map(x => `<tr><td class="l">${x.band}</td><td>${x.n}</td><td>${P(x.exp)}</td><td class="b">${P(x.act)}</td></tr>`).join("")) + `<div class="note">Log loss ${R.gtd.ll_model} against ${R.gtd.ll_base} for the division base rate alone, on ${R.gtd.n.toLocaleString()} fights since 2022.</div>` : "") +
  `</div><div><h3>Division base rates · last five years</h3>` + tbl(`<th class="l">Division</th><th>Rds</th><th>Fights</th><th>Decision</th><th>KO/TKO</th><th>Sub</th><th>R1 finish</th><th>Avg min</th>`, R.wc.filter(x => x.n >= 40).map(x => `<tr><td class="l b">${esc(x.wc)}</td><td>${x.sched}</td><td>${x.n}</td><td>${P(x.dec, 0)}</td><td>${P(x.ko, 0)}</td><td>${P(x.sub, 0)}</td><td>${P(x.r1, 0)}</td><td>${x.avg_min}</td></tr>`).join("")) + `</div></div>
  ${R.method ? `<h3>Method model · is it calibrated?</h3>` + tbl(`<th class="l">Method</th><th class="l">Model said</th><th>Fights</th><th>Avg</th><th>Happened</th>`, R.method_calib.map(x => `<tr><td class="l b">${x.m}</td><td class="l">${x.band}</td><td>${x.n}</td><td>${P(x.exp)}</td><td class="b">${P(x.act)}</td></tr>`).join("")) + `<div class="note">How the winner won, ${R.method.n.toLocaleString()} fights since 2022, each predicted from earlier years only. Log loss ${R.method.ll_model} against ${R.method.ll_base} for division base rates. There is no method-prop price history in the archive, so this is graded on calibration, not on betting return.</div>` : ""}
  <h3>Does the Form Figure rating mean anything?</h3>` + tbl(`<th class="l">Rating gap</th><th>Fights</th><th>Higher-rated fighter won</th>`, R.fig_bands.map(x => `<tr><td class="l b">${x.band} pts</td><td>${x.n}</td><td class="b">${P(x.act)}</td></tr>`).join("")) +
  `<div class="note">Fights since 2015 where both fighters had a UFC fight on record. The figure blends the result (how and when) with in-fight dominance (strikes, knockdowns, takedowns, control, submission attempts) and adjusts for the opponent's rating coming in. It beats Elo as a predictor and still loses to the market.</div>`;
  $app.innerHTML = html;
}

async function vSheet(slug) {
  const ev = await getJSON(`events/${slug}.json`); await Promise.all([overlayLive(ev), overlaySheet(ev)]);
  let html = `<div class="crumbs noprint"><a href="#/">Home</a> › <a href="#/card/${ev.slug}">${esc(ev.name)}</a> › Form sheet · <a href="javascript:window.print()" style="text-decoration:underline">Print</a></div><h2>${esc(ev.name)} · Form sheet</h2><div class="sub">${fdate(ev.date)} · ${esc(ev.location)}</div>`;
  for (const f of ev.fights) {
    const [A, B] = await Promise.all([f.a.slug ? getJSON(`fighters/${f.a.slug}.json`).catch(() => null) : null, f.b.slug ? getJSON(`fighters/${f.b.slug}.json`).catch(() => null) : null]);
    const pa = A ? A.fights.filter(x => x.d < ev.date) : [], pb = B ? B.fights.filter(x => x.d < ev.date) : [], ga = agg(pa), gb = agg(pb), o = oddsCells(f), fm = f.form || {};
    const ba = (A && A.bio) || {}, bb = (B && B.bio) || {}, v = (x, d = 2) => x == null ? "—" : x.toFixed(d), ag = (b_) => { const a_ = ageAt(b_.dob, ev.date); return a_ ? a_.toFixed(1) : "—"; };
    const side = (x, g, b_, fig, P) => `<b>${esc(x.name)}</b> · UFC ${g.rec} · Fig ${fig == null ? "—" : fig.toFixed(0)} · age ${ag(b_)} · ${esc(b_.ht || "—")} / ${b_.reach ? b_.reach + '"' : "—"} · ${esc(b_.stance || "—")} · SLpM ${v(g.slpm)} / SApM ${v(g.sapm)} · TD15 ${v(g.td15)} · TDD ${g.tdd == null ? "—" : (g.tdd * 100).toFixed(0) + "%"} · Ctrl ${g.ctrlp == null ? "—" : (g.ctrlp * 100).toFixed(0) + "%"} · layoff ${P[0] ? daysBetween(ev.date, P[0].d) + "d" : "debut"}`;
    html += `<section class="sheet"><div class="pp-head"><div class="n"><span class="pill k">${f.n}</span> <a href="#/fight/${ev.slug}/${f.n}">${esc(f.a.name)} vs ${esc(f.b.name)}</a></div><div class="sub">${esc(f.wc || "")}${f.sched ? " · " + f.sched + "R" : ""} · ${o.close.replace(/<\/?b>/g, "")}${o.pa != null ? " · fair " + (fair(o.pa) * 100).toFixed(0) + "%" : ""}${fm.p != null ? " · Form " + (fm.p * 100).toFixed(0) + "%" : ""}${(() => { const M = methodRows(f); return M ? " · GTD " + (M.gtd * 100).toFixed(0) + "%" : ""; })()}${f.model && f.model.a.win != null ? " · model " + f.model.a.win.toFixed(0) + "/" + f.model.b.win.toFixed(0) : ""}</div></div>
      <div class="box" style="font:12px/1.5 var(--mono)">${side(f.a, ga, ba, fm.ra, pa)}<br>${side(f.b, gb, bb, fm.rb, pb)}</div>
      <div style="height:4px"></div>${ppTable(pa, { name: f.a.name, limit: 6 }).replace("<thead>", `<caption>${esc(f.a.name)}</caption><thead>`)}<div style="height:4px"></div>${ppTable(pb, { name: f.b.name, limit: 6 }).replace("<thead>", `<caption>${esc(f.b.name)}</caption><thead>`)}</section>`;
  }
  $app.innerHTML = html; wireRows();
}

/* ---------- router + search ---------- */
const routes = [[/^#\/?$/, vHome, "home"], [/^#\/cards$/, vCards, "cards"], [/^#\/card\/([^/]+)$/, vCard, "cards"], [/^#\/fight\/([^/]+)\/(\d+)$/, vFight, "cards"],
  [/^#\/fighters$/, vFighters, "fighters"], [/^#\/fighter\/([^/]+)$/, vFighter, "fighters"], [/^#\/model$/, vModel, "model"], [/^#\/research$/, vResearch, "research"], [/^#\/compare\/([^/]+)\/([^/]+)$/, vCompare, "fighters"], [/^#\/rankings$/, vRankings, "fighters"], [/^#\/sheet\/([^/]+)$/, vSheet, "cards"], [/^#\/about$/, vAbout, "about"]];
async function route() {
  const h = location.hash || "#/";
  for (const [re, fn, tab] of routes) { const m = re.exec(h); if (!m) continue;
    document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("on", a.dataset.tab === tab));
    $app.innerHTML = `<div class="loading">Loading…</div>`;
    try { await boot; await fn(...m.slice(1).map(decodeURIComponent)); } catch (e) { console.error(e); $app.innerHTML = `<div class="banner">Couldn't load this page (${esc(e.message)}).</div>`; }
    window.scrollTo(0, 0); return; }
  $app.innerHTML = `<div class="banner">Page not found.</div>`;
}
window.addEventListener("hashchange", route);
const boot = getJSON("index.json").then(i => { window.__books = i.books; window.__k = i.k; window.__angles = i.angles; }).catch(() => {});
const $q = document.getElementById("q"), $dd = document.getElementById("dd");
if ($q) {
  let S = null;
  $q.addEventListener("input", async () => {
    const q = $q.value.trim().toLowerCase(); if (q.length < 2) { $dd.innerHTML = ""; return; }
    S = S || await getJSON("search.json");
    const hits = S.filter(x => x[0].toLowerCase().includes(q)).slice(0, 12);
    $dd.innerHTML = hits.map(x => `<a href="#/fighter/${x[1]}">${esc(x[0])}<span>${x[4]} · ${esc(x[3])}</span></a>`).join("");
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search") || e.target.closest(".dd a")) { $dd.innerHTML = ""; if (e.target.closest(".dd a")) $q.value = ""; } });
}
route();
})();
