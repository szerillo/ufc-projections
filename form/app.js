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
    grid += `<line x1="${L}" x2="${W - R}" y1="${yy}" y2="${yy}" stroke="#e5e1d8" stroke-width="1"/><text x="${L - 6}" y="${+yy + 4}" text-anchor="end" font-size="10" font-family="monospace" fill="#6b6b6b">${(p * 100).toFixed(0)}%</text><text x="${W - R + 6}" y="${+yy + 4}" font-size="10" font-family="monospace" fill="#6b6b6b">${ml(p2ml(p))}</text>`; }
  const ticks = [0, 0.5, 1].map(f => { const t = new Date(t0 + (t1 - t0) * f); return `<text x="${(L + (W - L - R) * f).toFixed(1)}" y="${H - 8}" text-anchor="${f === 0 ? "start" : f === 1 ? "end" : "middle"}" font-size="10" font-family="monospace" fill="#6b6b6b">${t.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" })}</text>`; }).join("");
  const last = S[S.length - 1];
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Line history">
    ${grid}${ticks}
    <path d="${path(3)}" fill="none" stroke="#0a8842" stroke-width="1" opacity=".75"/>
    <path d="${path(4)}" fill="none" stroke="#1b4fb0" stroke-width="1" opacity=".75"/>
    <path d="${path(2)}" fill="none" stroke="#d63636" stroke-width="1.4" stroke-dasharray="4 3"/>
    <path d="${path(1)}" fill="none" stroke="#1a1a1a" stroke-width="2.2"/>
    <circle cx="${x(S[0][0]).toFixed(1)}" cy="${y(S[0][1]).toFixed(1)}" r="3.5" fill="#1a1a1a"/>
    <circle cx="${x(last[0]).toFixed(1)}" cy="${y(last[1]).toFixed(1)}" r="3.5" fill="#1a1a1a"/>
  </svg>
  <div class="legend"><span><i style="border-color:#1a1a1a"></i>Consensus (no-vig) — ${esc(aName)} win %</span><span><i style="border-color:#d63636;border-top-style:dashed"></i>Pinnacle</span><span><i style="border-color:#0a8842"></i>DraftKings</span><span><i style="border-color:#1b4fb0"></i>FanDuel</span><span>right axis = ${esc(aName)} fair moneyline</span></div>`;
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
  const mx = Math.max(...m.r, m.dec * 100, 1), bar = (lab, v) => `<div style="display:grid;grid-template-columns:70px 1fr 46px;gap:6px;align-items:center;font:12px var(--mono);margin:2px 0"><span class="dim">${lab}</span><span style="background:var(--paper2);height:12px"><i style="display:block;height:12px;width:${(v / mx * 100).toFixed(1)}%;background:${lab === "Decision" ? "#1b4fb0" : "#d63636"}"></i></span><span>${v.toFixed(1)}%</span></div>`;
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
  if (FG.length > 1) { const W = 300, H = 60, bw = W / FG.length; figBars = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:60px"><line x1="0" x2="${W}" y1="${H / 2}" y2="${H / 2}" stroke="#e5e1d8"/>` + FG.map((v, i) => { const h = Math.max(1, Math.min(H, v / 120 * H)); return `<rect x="${(i * bw + 1).toFixed(1)}" y="${(H - h).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${h.toFixed(1)}" fill="${v >= 50 ? "#0a8842" : "#d63636"}" opacity=".8"/>`; }).join("") + `</svg><div class="legend"><span>Form Figure by fight, oldest to newest (line = 50)</span></div>`; }
  const E = F.fights.slice().reverse().map(x => x.el).concat([F.elo]).filter(x => x != null);
  let spark = "";
  if (E.length > 2) { const W = 300, H = 60, lo = Math.min(...E) - 10, hi = Math.max(...E) + 10; const d = E.map((e, i) => (i ? "L" : "M") + (i / (E.length - 1) * W).toFixed(1) + " " + (H - (e - lo) / (hi - lo) * H).toFixed(1)).join("");
    spark = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:60px"><path d="${d}" fill="none" stroke="#1a1a1a" stroke-width="1.8"/></svg><div class="legend"><span>Elo by fight: ${E[0]} → ${E[E.length - 1]} (peak ${Math.max(...E)})</span></div>`; }
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
    <div class="box noprint" style="margin-top:12px"><span class="sub">Compare with another fighter: </span><input id="cmpq" placeholder="type a name…" style="padding:5px 8px;border:1px solid var(--rule);background:#ffffff;width:220px"> <span id="cmpdd"></span></div>
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


/* ================= Duration Model (Markov) section: renders data/cards/*.json as given ================= */
const DM_NAME = "The Duration Model";
const GLOSS = {
  "Shrunk win %": "Model win probability after a confidence blend toward 50% on thin UFC samples. The default column.",
  "Raw win %": "The unblended Markov simulation output. Archived alongside shrunk; both are being graded to decide which survives.",
  "P(dec)": "Probability the fight reaches the judges' scorecards.",
  "Market GTD (de-vigged)": "The sportsbook \"goes the distance\" price with the vig removed (multiplicative method on the GTD/ITD pair).",
  "Gap": "Model P(dec) minus market GTD, in points. Flags require 8 or more with a stated mechanism.",
  "DEC% of wins": "Of the sims this fighter wins, the share won by decision (their \"win condition shape\").",
  "Round distribution": "Share of all sims ending in each round; the remainder is the decision.",
  "TD P(≥1/≥2/≥3)": "Probability the fighter lands at least 1, 2 or 3 takedowns.",
  "P(KD)": "Probability the fighter scores at least one knockdown. \"Clamped\" means it hit the model's 40% cap (treat as \"high\").",
  "Spread (per-card)": "Fav −3.5 = wins by finish or a decision containing a 10-8 round; fav −9.5 in a three-round fight = wins by finish.",
  "§1d prior": "Pre-UFC (regional) record data blended in for fighters with three or fewer UFC fights.",
  "D-code": "Automatic no-bet veto: underdog with three or fewer UFC fights whose last pre-UFC bout was in LFA or a minor regional promotion (historically −36.6% ROI). DWCS, Bellator, PFL, ONE, KSW and Rizin graduates are exempt.",
  "SYN": "The fight's positional data was synthesized (matchup missing from the positional data source); treat pace and takedown projections as low-confidence.",
  "Mechanism": "The one-line fighter-specific reason a flag exists. No mechanism, no flag.",
  "Confidence labels": "real (mechanism + data), lean (regime or rule-driven), sprinkle (thin data), artifact (statistical artifact of the shrinkage, not a read), vetoed (read exists but a standing rule blocks it).",
};
const dmJSON = (p) => cache["dm:" + p] || (cache["dm:" + p] = fetch("data/" + p).then(r => { if (!r.ok) throw new Error(p + " " + r.status); return r.json(); }));
const p1 = (x) => x == null ? "not yet posted" : (+x).toFixed(1) + "%";
const tip = (label, key) => `<span title="${esc(GLOSS[key || label] || "")}" style="border-bottom:1px dotted var(--ink2);cursor:help">${esc(label)}</span>`;
const badge = (b) => `<span class="pill ${b === "D-CODE" ? "r" : b === "§1d" ? "" : ""}" title="${esc(GLOSS[b === "D-CODE" ? "D-code" : b === "§1d" ? "§1d prior" : b] || "")}" style="${b === "SYN" ? "color:var(--ink2);border-color:var(--ink2)" : b === "§1d" ? "color:var(--blue);border-color:var(--blue)" : ""}">${esc(b)}</span>`;
const implied = (o) => o == null ? null : (o < 0 ? -o / (-o + 100) : 100 / (o + 100));
function roundBar(d, rounds) {
  const cols = ["#7a1414", "#d63636", "#c9503e", "#dc8a6a", "#e9b79c"], segs = (d.round_dist || []).map((v, i) => `<i title="Ends R${i + 1}: ${v.toFixed(1)}%" style="display:inline-block;height:12px;width:${v}%;background:${cols[i]}"></i>`).join("");
  return `<span style="display:inline-block;width:150px;height:12px;background:#1b4fb0;vertical-align:middle;line-height:0;text-align:left" title="Decision: ${d.p_dec}%">${segs}</span>`;
}
async function dmFormEvent(card) { // matching Fight Form event (for results when the card JSON has none, and for links)
  try { const idx = await getJSON("index.json"); const t0 = Date.parse(card.date);
    const hit = idx.events.concat(idx.upcoming).find(e => Math.abs(Date.parse(e.date) - t0) <= 864e5 * 1.5); return hit ? await getJSON(`events/${hit.slug}.json`) : null; } catch (e) { return null; }
}
function dmMatch(ev, f) { if (!ev) return null; const [a, b] = f.fighters.map(x => x.name);
  return ev.fights.find(x => (sameFighter(x.a.name, a) && sameFighter(x.b.name, b)) || (sameFighter(x.a.name, b) && sameFighter(x.b.name, a))) || null; }
function dmResult(f, ff) { // -> {winner, method, round, time, src}
  if (f.result && f.result.winner) return Object.assign({ src: "card" }, f.result);
  if (ff && ff.result && ff.result.kind) { const r = ff.result; const m = r.kind === "nc" ? "NC" : r.kind === "draw" ? "DRAW" : /Decision/.test(r.method) ? "DEC" : /Sub/.test(r.method) ? "SUB" : /KO/.test(r.method) ? "KO" : r.method;
    return { winner: r.winner ? ff[r.winner].name : null, method: m, round: r.round, time: r.time, src: "UFCStats" }; }
  return null;
}
async function vDM() {
  const M = await dmJSON("manifest.json");
  const chip = (s) => `<span class="pill ${s === "graded" ? "k" : s === "live" ? "r" : "y"}">${s}</span>`;
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › ${DM_NAME}</div><h2>${DM_NAME}</h2>
  <div class="box" style="font:14px/1.55 var(--serif)">A market-blind Markov-chain simulator runs every fight 100,000 times and publishes how it ends: the chance it reaches the scorecards, the round-by-round finish split and prop projections. Its win probabilities are shown shrunk and raw, and both are being graded in public against the closing line. Reads that a standing rule blocks are shown struck through with the reason. <a href="#/methodology" style="text-decoration:underline">How it works</a> · <a href="#/glossary" style="text-decoration:underline">Glossary</a> · <a href="#/duration-grading" style="text-decoration:underline">Grading</a></div>
  <h3>Cards</h3><div class="tw"><table><thead><tr><th class="l">Date</th><th class="l">Card</th><th class="c">Status</th><th>Fights</th><th class="l">Summary</th></tr></thead><tbody>` +
  M.cards.map(c => `<tr class="click" data-href="#/duration/${c.slug}"><td class="l">${sdate(c.date)}</td><td class="l b">${esc(c.title)}</td><td class="c">${chip(c.status)}</td><td>${c.fights}</td><td class="l dim">${c.partial ? "tables only (from the weekly doc)" : esc(c.summary || "")}</td></tr>`).join("") + `</tbody></table></div>`;
  wireRows();
}
async function vDMCard(slug) {
  const C = await dmJSON(`cards/${slug}.json`), ev = await dmFormEvent(C);
  const F = C.fights.slice().sort((a, b) => a.order - b.order);
  const vetoed = new Set((C.vetoes || []).map(v => v.fight_order + "|" + nm(v.side)));
  const dogOf = (f) => f.fighters.find(x => x.side === "dog") || f.fighters.find(x => x.side === "pickem") || f.fighters.slice().sort((a, b) => a.model_win_shrunk - b.model_win_shrunk)[0];
  const favOf = (f) => f.fighters.find(x => x !== dogOf(f));
  let html = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/duration">${DM_NAME}</a> › ${esc(C.title)}</div><h2>${esc(C.title)}</h2>
  <div class="sub">${C.date ? fdate(C.date) : ""} · ${esc(C.venue || "")} · engine ${esc(C.engine_version || "—")}${C.grading_window_index ? " · card " + C.grading_window_index + " of the 10-card grading window" : ""}</div>
  <div class="links" style="margin-top:8px"><a href="#/duration/${slug}/tape">Tale of the tape</a>${ev ? `<a href="#/card/${ev.slug}">Fight Form card page</a>` : ""}<a href="#/duration-grading">Grading</a></div>
  ${(C.notes || []).length ? `<div class="box" style="font:13px/1.5 var(--serif)"><b>Card notes.</b><ul style="margin:4px 0 0 18px;padding:0">${C.notes.map(n => `<li>${esc(n)}</li>`).join("")}</ul></div>` : ""}
  <h3>Sheet input table</h3><div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Underdog (odds)</th><th>${tip("Dog win % shrunk", "Shrunk win %")}</th><th>${tip("Dog win % raw", "Raw win %")}</th><th>${tip("Dog DEC% of wins", "DEC% of wins")}</th><th>${tip("Fav DEC% of wins", "DEC% of wins")}</th><th class="l">Flags</th></tr></thead><tbody>` +
  F.map(f => { const d = dogOf(f), fv = favOf(f), div = Math.abs(d.model_win_shrunk - d.model_win_raw) >= 10, bs = [...new Set(f.fighters.flatMap(x => x.badges || []))];
    return `<tr><td class="c dim">${f.order}</td><td class="l b">${esc(d.name)} <span class="dim">(${ml(d.market_odds)}${d.side === "pickem" ? ", pick'em" : ""})</span></td><td class="b" ${div ? 'style="background:var(--hl)"' : ""}>${p1(d.model_win_shrunk)}</td><td class="dim" ${div ? 'style="background:var(--hl)"' : ""}>${p1(d.model_win_raw)}</td><td>${d.dec_share_of_wins == null ? "—" : d.dec_share_of_wins + "%"}</td><td>${esc(last(fv.name))} ${fv.dec_share_of_wins == null ? "—" : fv.dec_share_of_wins + "%"}</td><td class="l">${bs.map(badge).join(" ")}</td></tr>`; }).join("") + `</tbody></table></div><div class="note">Highlighted pairs differ by 10+ points between shrunk and raw: the number is data-starved.</div>
  <h3>Duration</h3><div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Fight</th><th>${tip("P(dec)")}</th><th>${tip("Market GTD", "Market GTD (de-vigged)")}</th><th>${tip("Gap")}</th><th class="l">${tip("Rounds → decision", "Round distribution")}</th><th>Exp. min</th><th class="l">Result</th></tr></thead><tbody>` +
  F.map(f => { const d = f.duration || {}, ff = dmMatch(ev, f), r = dmResult(f, ff), fl = (C.duration_flags || []).find(x => x.fight_order === f.order);
    return `<tr><td class="c dim">${f.order}</td><td class="l b">${ff && ev ? `<a href="#/fight/${ev.slug}/${ff.n}">${esc(f.bout)}</a>` : esc(f.bout)} <span class="dim">${f.rounds}R</span></td><td class="b">${p1(d.p_dec)}</td><td>${p1(d.market_gtd_devig)}</td><td class="${d.gap != null && Math.abs(d.gap) >= 8 ? "b " + cls(d.gap) : "dim"}">${d.gap == null ? "—" : signed(d.gap)}</td><td class="l">${roundBar(d, f.rounds)}</td><td>${d.exp_minutes ?? "—"}</td><td class="l dim">${r ? esc((r.winner || "—") + " · " + r.method + (r.round ? " R" + r.round : "")) : ""}</td></tr>` +
      (fl ? `<tr><td></td><td colspan="7" class="l" style="white-space:normal;background:var(--paper2)"><span class="pill ${fl.confidence === "vetoed" ? "r" : "y"}">${esc(fl.confidence)}</span> <span style="${fl.confidence === "vetoed" ? "text-decoration:line-through" : ""}"><b>${esc(fl.title)}</b></span> — ${esc(fl.mechanism)}</td></tr>` : ""); }).join("") + `</tbody></table></div><div class="legend"><span><i style="border-color:#7a1414"></i>early rounds</span><span><i style="border-color:#e9b79c"></i>late rounds</span><span><i style="border-color:#1b4fb0"></i>decision</span></div>`;
  const item = (title, body, conf) => `<div class="box" style="margin:6px 0;font:13.5px/1.5 var(--serif)"><span class="pill ${conf === "vetoed" ? "r" : conf === "artifact" ? "" : conf === "real" ? "g" : "y"}">${esc(conf)}</span> <span style="${conf === "vetoed" ? "text-decoration:line-through" : ""}"><b>${title}</b></span><br>${body}</div>`;
  const reads = [];
  for (const x of C.duration_flags || []) reads.push(item(esc(x.title), `Market ${esc(x.market_price)} (${p1(x.market_value)}) · model ${p1(x.model_value)}<br>${esc(x.mechanism)}`, x.confidence));
  for (const x of C.ml_flags || []) reads.push(item(`${esc(x.side)} ${ml(x.market_odds)}`, `Model ${p1(x.model_shrunk)} shrunk / ${p1(x.model_raw)} raw · market ${p1(x.market_implied)} · edge ${signed(x.edge_pts)} pts<br><b>Mechanism:</b> ${esc(x.mechanism)}${x.counter ? `<br><b>Counter:</b> ${esc(x.counter)}` : ""}`, x.confidence));
  for (const x of C.vetoes || []) reads.push(item(`${esc(x.side)} ${ml(x.market_odds)}`, `${esc(x.reason)}`, "vetoed"));
  for (const x of C.prop_notes || []) reads.push(`<div class="box" style="margin:6px 0;font:13.5px/1.5 var(--serif)"><span class="pill">prop note</span> Fight ${x.fight_order}: ${esc(x.text)}</div>`);
  html += `<h3>Flags and reads</h3>${reads.length ? reads.join("") : `<div class="note">${C.partial ? "This card was built from the weekly output doc; its flag write-ups are in the source doc." : "No flags on this card."}</div>`}<div class="note">Vetoed reads are shown, struck through, with the rule that blocks them. They are never picks.</div>
  <h3>Per-fight detail</h3>`;
  for (const f of F) { const full = f.fighters.every(x => x.finish_pct != null);
    const fr = (x) => `<tr><td class="l b">${esc(x.name)} ${(x.badges || []).map(badge).join(" ")}</td><td>${ml(x.market_odds)}</td><td class="b">${p1(x.model_win_shrunk)}</td><td class="dim">${p1(x.model_win_raw)}</td>${full ? `<td>${p1(x.finish_ko)}</td><td>${p1(x.finish_sub)}</td><td>${x.ss_mean} / ${x.ss_median}</td><td>${x.td_proj}</td><td>${x.td_p1} / ${x.td_p2} / ${x.td_p3}%</td><td>${x.p_kd}%${x.p_kd_clamped ? " (clamped)" : ""}</td>` : `<td colspan="6" class="c dim">prop projections not in this file</td>`}</tr>`;
    const tp = (x) => x.tape ? `<div class="kv"><span>${esc(x.name)}</span><span>${x.tape.age} · ${esc(x.tape.height)} / ${x.tape.reach}" · ${esc(x.tape.stance)} · ${esc(x.tape.record)} · SLpM ${x.tape.slpm} / SApM ${x.tape.sapm} · TD ${x.tape.td_avg} (${(x.tape.td_acc * 100).toFixed(0)}% / def ${(x.tape.td_def * 100).toFixed(0)}%) · <span class="dim">${esc(x.data_quality || "")}</span></span></div>` : "";
    html += `<details class="box" style="margin:6px 0"><summary style="cursor:pointer;font:700 13px var(--sans)">${f.order}. ${esc(f.bout)} <span class="dim" style="font-weight:400">${esc(f.weight_class || "")} · ${f.rounds}R · P(dec) ${p1((f.duration || {}).p_dec)}</span></summary>
      <div class="tw" style="margin-top:8px"><table><thead><tr><th class="l">Fighter</th><th>Odds</th><th>Shrunk</th><th>Raw</th><th>Finish KO</th><th>Finish sub</th><th title="Sig strikes mean / median">SS mean / med</th><th>TD proj</th><th>${tip("TD ≥1/2/3", "TD P(≥1/≥2/≥3)")}</th><th>${tip("P(KD)")}</th></tr></thead><tbody>${f.fighters.map(fr).join("")}</tbody></table></div>
      ${f.spread ? `<div class="note">${tip("Spread", "Spread (per-card)")}: fav −3.5 covers ${p1(f.spread.fav_minus35)} · fav −9.5 covers ${p1(f.spread.fav_minus95)} (${esc(f.spread.convention)} convention)</div>` : ""}${f.fighters.map(tp).join("")}</details>`; }
  html += `<details class="box" style="margin-top:12px"><summary style="cursor:pointer;font:700 13px var(--sans)">ARCHIVE block (paste into the sheet)</summary><p><a class="btn" id="cpy">Copy</a></p><pre id="arch" style="font:11.5px var(--mono);overflow:auto;white-space:pre">${esc(C.archive_tsv || "")}</pre></details>`;
  $app.innerHTML = html;
  const cp = document.getElementById("cpy"); if (cp) cp.addEventListener("click", () => { navigator.clipboard.writeText(C.archive_tsv || "").then(() => { cp.textContent = "Copied"; }); });
}
async function vDMTape(slug) {
  const C = await dmJSON(`cards/${slug}.json`);
  const rows = []; for (const f of C.fights.slice().sort((a, b) => a.order - b.order)) for (const x of f.fighters) if (x.tape) rows.push({ f, x });
  const cols = [["Fight", r => r.f.order], ["Fighter", r => r.x.name], ["Side", r => r.x.side], ["Age", r => r.x.tape.age], ["Ht", r => r.x.tape.height], ["Reach", r => r.x.tape.reach], ["Stance", r => r.x.tape.stance], ["Record", r => r.x.tape.record], ["SLpM", r => r.x.tape.slpm], ["SApM", r => r.x.tape.sapm], ["Str acc", r => r.x.tape.str_acc], ["Str def", r => r.x.tape.str_def], ["TD avg", r => r.x.tape.td_avg], ["TD acc", r => r.x.tape.td_acc], ["TD def", r => r.x.tape.td_def], ["Sub avg", r => r.x.tape.sub_avg], ["Shrunk", r => r.x.model_win_shrunk], ["Raw", r => r.x.model_win_raw], ["Odds", r => r.x.market_odds], ["Data quality", r => r.x.data_quality]];
  let sort = 0, dir = 1;
  const draw = () => { const R = rows.slice().sort((a, b) => { const va = cols[sort][1](a), vb = cols[sort][1](b); return (typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb))) * dir; });
    $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/duration">${DM_NAME}</a> › <a href="#/duration/${slug}">${esc(C.title)}</a> › Tape</div><h2>Tale of the tape</h2><div class="sub">${esc(C.title)} · tap a column to sort${rows.length < C.fights.length * 2 ? " · only fights with tape data in this file are listed" : ""}</div>
      <div class="links" style="margin-top:8px"><a href="data/cards/${slug}.csv" download>Download raw stats CSV</a></div>
      ${rows.length ? `<div class="tw"><table><thead><tr>${cols.map((c, i) => `<th class="${i === 1 || i === 19 ? "l" : ""}" data-i="${i}" style="cursor:pointer${i === 1 ? ";position:sticky;left:0;background:var(--paper2)" : ""}">${c[0]}${i === sort ? (dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("")}</tr></thead><tbody>${R.map(r => `<tr>${cols.map((c, i) => { const v = c[1](r); return `<td class="${i === 1 || i === 19 ? "l" : ""}" style="${i === 1 ? "position:sticky;left:0;background:#ffffff;font-weight:700" : ""}${i === 19 ? "white-space:normal;min-width:180px" : ""}">${i === 18 ? ml(v) : esc(v == null ? "—" : v)}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>` : `<div class="banner">No tape data in this card file.</div>`}`;
    $app.querySelectorAll("th[data-i]").forEach(th => th.addEventListener("click", () => { const i = +th.dataset.i; if (i === sort) dir = -dir; else { sort = i; dir = 1; } draw(); })); };
  draw();
}
async function vDMGrading() {
  const M = await dmJSON("manifest.json"); const rows = []; const flags = []; const vets = []; let graded = 0;
  for (const c of M.cards) { const C = await dmJSON(`cards/${c.slug}.json`), ev = await dmFormEvent(C); let any = false;
    for (const f of C.fights) { const ff = dmMatch(ev, f), r = dmResult(f, ff); if (!r) continue; any = true;
      const A = f.fighters[0], B = f.fighters[1], ia = implied(A.market_odds), ib = implied(B.market_odds);
      let pm = ia != null && ib != null ? ia / (ia + ib) : null, pmSrc = "card odds";
      if (pm == null && ff && ff.odds) { const pa = ff.odds.close.p; pm = sameFighter(ff.a.name, A.name) ? pa : 1 - pa; pmSrc = "Fight Form close"; }
      const void_ = r.method === "NC" || r.method === "DRAW" || !r.winner, won = void_ ? null : (sameFighter(r.winner, A.name) ? 1 : 0), dist = void_ ? null : (r.method === "DEC" ? 1 : 0);
      rows.push({ c: C, f, r, A, B, pm, pmSrc, won, dist, void_ }); }
    if (any) graded++;
    const res = (order) => { const f = C.fights.find(x => x.order === order); return f ? dmResult(f, dmMatch(ev, f)) : null; };
    const settle = (odds, win) => win == null ? 0 : win ? (odds > 0 ? odds / 100 : 100 / -odds) : -1;
    for (const x of C.ml_flags || []) { const r = res(x.fight_order); if (!r) continue; const v = r.method === "NC" || r.method === "DRAW"; flags.push({ c: C, kind: "ML", t: x.side, odds: x.market_odds, conf: x.confidence, pnl: settle(x.market_odds, v ? null : sameFighter(r.winner || "", x.side)), v }); }
    for (const x of C.duration_flags || []) { const r = res(x.fight_order); const o = parseInt(String(x.market_price).replace("+", "").replace("−", "-"), 10); if (!r || !isFinite(o)) continue; const v = r.method === "NC" || r.method === "DRAW"; flags.push({ c: C, kind: "GTD", t: x.title, odds: o, conf: x.confidence, pnl: settle(o, v ? null : r.method === "DEC"), v }); }
    for (const x of C.vetoes || []) { const r = res(x.fight_order); if (!r || x.market_odds == null) continue; const v = r.method === "NC" || r.method === "DRAW"; vets.push({ c: C, t: x.side, odds: x.market_odds, pnl: settle(x.market_odds, v ? null : sameFighter(r.winner || "", x.side)), won: !v && sameFighter(r.winner || "", x.side) }); }
  }
  const crumbs = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/duration">${DM_NAME}</a> › Grading</div><h2>Grading · model against the market</h2>`;
  if (!rows.length) { $app.innerHTML = crumbs + `<div class="banner">No graded cards yet — grading begins when results are entered.</div>`; return; }
  const ok = rows.filter(r => !r.void_), brier = (xs) => xs.length ? (xs.reduce((s, v) => s + v, 0) / xs.length).toFixed(4) : "—";
  const mlAll = ok.filter(r => r.pm != null);
  const bS = brier(mlAll.map(r => (r.A.model_win_shrunk / 100 - r.won) ** 2)), bR = brier(mlAll.map(r => (r.A.model_win_raw / 100 - r.won) ** 2)), bM = brier(mlAll.map(r => (r.pm - r.won) ** 2));
  const du = ok.filter(r => r.f.duration && r.f.duration.p_dec != null && r.f.duration.market_gtd_devig != null);
  const bD = brier(du.map(r => (r.f.duration.p_dec / 100 - r.dist) ** 2)), bDM = brier(du.map(r => (r.f.duration.market_gtd_devig / 100 - r.dist) ** 2));
  const live = flags.filter(x => x.conf === "real" || x.conf === "lean"), fw = live.filter(x => x.pnl > 0).length, fl = live.filter(x => x.pnl < 0).length, fp = live.reduce((s, x) => s + x.pnl, 0);
  const vw = vets.filter(x => x.won).length, vp = vets.reduce((s, x) => s + x.pnl, 0);
  $app.innerHTML = crumbs + `<p class="sub">${ok.length} graded fights over ${graded} cards. Brier score: lower is better. This is a small sample. Results come from the card file when present, otherwise from UFCStats.</p>
    <div class="stats"><div><b>${graded}</b><span>Cards graded on this page (window is 10)</span></div><div><b>${bS}</b><span>Win % Brier · shrunk</span></div><div><b>${bR}</b><span>Win % Brier · raw</span></div><div><b>${bM}</b><span>Win % Brier · market (${mlAll.length} fights)</span></div><div><b>${bD}</b><span>P(dec) Brier · model</span></div><div><b>${bDM}</b><span>GTD Brier · market (${du.length} fights)</span></div></div>
    <div class="stats" style="margin-top:10px"><div><b>${fw}-${fl}</b><span>Flags, real + lean (${live.length})</span></div><div><b class="${cls(fp)}">${live.length ? signed(fp, 2) + "u" : "—"}</b><span>Flag result at listed odds, 1u each</span></div><div><b>${vw}-${vets.length - vw}</b><span>D-code vetoed dogs (${vets.length})</span></div><div><b class="${cls(vp)}">${vets.length ? signed(vp, 2) + "u" : "—"}</b><span>Shadow result: what the vetoes skipped</span></div></div>
    <p class="note">A negative shadow result means the vetoes saved money; a positive one means they cost it. Flags are settled only where the card file carries the flag list.</p>
    <h3>Every graded fight</h3><div class="tw"><table><thead><tr><th class="l">Card</th><th class="l">Fight</th><th>Shrunk</th><th>Raw</th><th>Market</th><th>P(dec)</th><th>Mkt GTD</th><th class="l">Result</th><th class="c" title="Did the shrunk number have the winner above 50%?">Win</th><th class="c" title="Was P(dec) on the right side of 50%?">Dist</th></tr></thead><tbody>` +
    rows.map(r => { const d = r.f.duration || {}, hitW = r.void_ ? "" : ((r.A.model_win_shrunk > 50) === (r.won === 1) ? '<span class="W">✓</span>' : '<span class="L">✗</span>'), hitD = r.void_ || d.p_dec == null ? "" : ((d.p_dec > 50) === (r.dist === 1) ? '<span class="W">✓</span>' : '<span class="L">✗</span>');
      return `<tr><td class="l dim">${sdate(r.c.date)}</td><td class="l b"><a href="#/duration/${r.c.slug}">${esc(r.f.bout)}</a></td><td>${p1(r.A.model_win_shrunk)}</td><td class="dim">${p1(r.A.model_win_raw)}</td><td title="${r.pmSrc}">${r.pm == null ? "—" : (r.pm * 100).toFixed(1) + "%"}</td><td>${p1(d.p_dec)}</td><td>${d.market_gtd_devig == null ? "—" : p1(d.market_gtd_devig)}</td><td class="l">${esc((r.r.winner || "—") + " · " + r.r.method + (r.r.round ? " R" + r.r.round : ""))}</td><td class="c">${hitW}</td><td class="c">${hitD}</td></tr>`; }).join("") + `</tbody></table></div><div class="note">Win % columns are for the first-named fighter. Market win % is de-vigged from the card's odds where both sides are in the file, otherwise the Fight Form closing consensus.</div>`;
}
async function vMethodology() {
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/duration">${DM_NAME}</a> › Methodology</div><h2>How the Markov model works</h2><div class="box" style="font:14.5px/1.6 var(--serif)">
  <p><b>The engine in one paragraph.</b> The model is a Markov-chain fight simulator (engine version V4.1b). Each fight is simulated 100,000 times in 30-second intervals across four positional states (distance, clinch, ground A-top, ground B-top), using each fighter's positional pace data, career striking and grappling rates, and a durability layer built on knockdowns landed and absorbed per 15 minutes ("power × chin"), adjusted for age, coming off a KO loss, gender, and division base rates. Fighters with three or fewer UFC fights get priors from their pre-UFC (regional) records. The model is <b>market-blind</b>: it never sees betting odds when producing its numbers; odds are only used afterward to measure disagreement.</p>
  <p><b>Why duration, not winners.</b> Five years of backtesting (2,591 UFC fights against closing lines) showed that the closing moneyline is extremely well calibrated. No public input tested (fan picks, tipster consensus, "sharp money") adds anything to it, and no stats-built win model has come close. What the market systematically misprices is <b>how fights end</b>: five-round fights priced 40% or more to decide go the distance far more than priced (+23% ROI, positive six straight years, 141 fights), heavyweight fights now decide 44–48% while priced near 34%, and the finish side of every prop market carries structural tax. So the model's primary products are P(decision), the round-by-round finish distribution, and the prop projections built from expected fight minutes. The moneyline output is a low-weight input, flagged only on disagreements of 8+ points that come with a named fighter-specific mechanism.</p>
  <p><b>Dual columns: shrunk and raw.</b> The model publishes two win probabilities per fighter. Raw is the pure simulation output. Shrunk applies a confidence blend toward 50% when fighters have thin UFC samples. Both are archived every card and graded against results; early evidence suggests raw tracks the market better on thin-sample fights (the shrink manufactures fake underdog edges), and the blend will be deleted if grading confirms it. Until then shrunk is the official number, raw is the second opinion, and a large gap between them is itself a signal that the number is data-starved.</p>
  <p><b>The discipline layer.</b> Rules learned from the five-year data override model output. No underdog bets under 8 points of edge, and none at all when public or tipster money is heavy on the dog. The D-code veto: underdogs with three or fewer UFC fights whose last pre-UFC stop was LFA or a minor regional promotion are automatic no-bets through their third UFC fight (−36.6% ROI historically on 252 fights, negative every year); the veto applies even when the model loves the dog, and those cases are tracked to test the rule. No unders, no inside-the-distance props, no method props below 50% implied, no submission props. No flag ships without a one-line fighter-specific reason. A number without a mechanism is treated as noise.</p>
  <p><b>Grading.</b> Every card, the model's P(win) (both variants), P(decision), expected minutes and round distribution are archived next to the closing line. After a ten-card window: Brier scores against the close on both channels, the result of the 8-point flags, and the shadow record of vetoed bets. The model's future weight, including whether its moneyline output is used at all, moves with that grade. The expected outcome, stated in advance: the duration channel beats the market and the moneyline channel doesn't.</p>
  <p><b>What this is not.</b> This is a research tool and a public record of a model being graded in real time. It is not betting advice. The numbers are probabilistic model outputs with known blind spots, most importantly <b>opponent quality</b> (a record built against weak competition looks identical to one built against killers) and <b>anything that happened outside the cage</b> (camps, injuries, weight cuts, personal circumstances). Several of the site's own flags each week are labeled artifacts of those blind spots. If you bet, bet with money you can afford to lose and expect variance that dwarfs any edge shown here.</p>
  <p class="dim">Credits: positional data derived from MMAOddsBreaker's public comparison tool; career stats from UFCStats; market prices from BestFightOdds medians.</p></div>`;
}
async function vGlossary() {
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/duration">${DM_NAME}</a> › Glossary</div><h2>Glossary</h2><div class="tw"><table><tbody>${Object.entries(GLOSS).map(([k, v]) => `<tr><td class="l b" style="white-space:nowrap">${esc(k)}</td><td class="l" style="white-space:normal;font:13.5px/1.5 var(--serif)">${esc(v)}</td></tr>`).join("")}</tbody></table></div>`;
}


/* ================= Labs ================= */
const LTABS = [["query", "Query"], ["upsets", "Upsets"], ["size", "Age & size"], ["spots", "Spots"], ["divisions", "Divisions"], ["octagon", "Octagon"], ["metrics", "Fighter metrics"], ["scoring", "Scoring"]];
function barChart(items, { fmt = (v) => (v * 100).toFixed(1) + "%", ref = null, refLabel = "", h = 190, min = null, max = null } = {}) { // items: [{label, v, v2?, n?}]
  const W = 720, pl = 38, pb = 34, pt = 14, vals = items.flatMap(i => [i.v, i.v2]).filter(v => v != null).concat(ref != null ? [ref] : []);
  let lo = min != null ? min : Math.min(...vals), hi = max != null ? max : Math.max(...vals); if (min == null) lo -= (hi - lo) * 0.25 + 0.01; if (max == null) hi += (hi - lo) * 0.12;
  const y = (v) => pt + (h - pt - pb) * (1 - (v - lo) / (hi - lo)), bw = (W - pl - 10) / items.length, two = items.some(i => i.v2 != null);
  let s = `<svg class="chart" viewBox="0 0 ${W} ${h}" role="img">`;
  for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4; s += `<line x1="${pl}" x2="${W - 10}" y1="${y(v)}" y2="${y(v)}" stroke="#e5e1d8"/><text x="${pl - 5}" y="${y(v) + 3}" font-size="9.5" text-anchor="end" fill="#6b6b6b">${fmt(v)}</text>`; }
  items.forEach((it, i) => { const x0 = pl + i * bw + bw * 0.14, w = bw * (two ? 0.34 : 0.72);
    if (it.v != null) s += `<rect x="${x0}" y="${y(it.v)}" width="${w}" height="${Math.max(0, y(lo) - y(it.v))}" fill="#0a8842" rx="2"><title>${esc(it.label)}: ${fmt(it.v)}${it.n ? " (" + it.n + ")" : ""}</title></rect><text x="${x0 + w / 2}" y="${y(it.v) - 3}" font-size="9.5" font-weight="700" text-anchor="middle" fill="#1a1a1a">${fmt(it.v)}</text>`;
    if (it.v2 != null) s += `<rect x="${x0 + w + 2}" y="${y(it.v2)}" width="${w}" height="${Math.max(0, y(lo) - y(it.v2))}" fill="#1b4fb0" rx="2"><title>${fmt(it.v2)}</title></rect><text x="${x0 + w * 1.5 + 2}" y="${y(it.v2) - 3}" font-size="9.5" text-anchor="middle" fill="#6b6b6b">${fmt(it.v2)}</text>`;
    s += `<text x="${pl + i * bw + bw / 2}" y="${h - pb + 13}" font-size="10" text-anchor="middle" fill="#1a1a1a">${esc(it.label)}</text>${it.n ? `<text x="${pl + i * bw + bw / 2}" y="${h - pb + 25}" font-size="9" text-anchor="middle" fill="#6b6b6b">n=${it.n}</text>` : ""}`; });
  if (ref != null) s += `<line x1="${pl}" x2="${W - 10}" y1="${y(ref)}" y2="${y(ref)}" stroke="#d63636" stroke-dasharray="4 3"/><text x="${W - 12}" y="${y(ref) - 3}" font-size="9.5" text-anchor="end" fill="#d63636">${esc(refLabel)}</text>`;
  return s + "</svg>";
}
function multiLine(series, xs, { fmt = (v) => (v * 100).toFixed(0) + "%", h = 220 } = {}) { // series: [{name,color,vals[]}]
  const W = 720, pl = 38, pb = 22, pt = 10, vals = series.flatMap(s => s.vals).filter(v => v != null), lo = Math.min(...vals) * 0.95, hi = Math.max(...vals) * 1.04;
  const X = (i) => pl + (W - pl - 14) * i / (xs.length - 1), Y = (v) => pt + (h - pt - pb) * (1 - (v - lo) / (hi - lo));
  let s = `<svg class="chart" viewBox="0 0 ${W} ${h}">`;
  for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4; s += `<line x1="${pl}" x2="${W - 10}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e5e1d8"/><text x="${pl - 5}" y="${Y(v) + 3}" font-size="9.5" text-anchor="end" fill="#6b6b6b">${fmt(v)}</text>`; }
  xs.forEach((x, i) => { s += `<text x="${X(i)}" y="${h - 6}" font-size="9.5" text-anchor="middle" fill="#6b6b6b">${x}</text>`; });
  for (const S of series) { const pts = S.vals.map((v, i) => v == null ? null : [X(i), Y(v)]).filter(Boolean);
    s += `<polyline fill="none" stroke="${S.color}" stroke-width="${S.bold ? 2.6 : 1.6}" points="${pts.map(p => p.join(",")).join(" ")}"/>` + S.vals.map((v, i) => v == null ? "" : `<circle cx="${X(i)}" cy="${Y(v)}" r="${S.bold ? 3 : 2.2}" fill="${S.color}"><title>${esc(S.name)} ${xs[i]}: ${fmt(v)}</title></circle>`).join(""); }
  return s + `</svg><div class="legend">${series.map(S => `<span><i style="border-color:${S.color}"></i>${esc(S.name)}</span>`).join("")}</div>`;
}
const roiTd = (v) => `<td class="${cls(v)}">${v == null ? "—" : signed(v * 100) + "%"}</td>`;
function studyTable(rows, who) {
  return `<div class="tw"><table><thead><tr><th class="l">Bucket</th><th title="All fights since 2010">Fights</th><th>${who} win %</th><th title="Fights with a closing line (2022 on)">With line</th><th>Win % (line era)</th><th title="No-vig closing probability">Market %</th><th title="Flat 1u at the closing consensus price">ROI at close</th></tr></thead><tbody>` +
    rows.map(r => `<tr><td class="l b">${esc(r.label)}</td><td>${r.n}</td><td class="b">${pct(r.wp)}</td><td class="dim">${r.on}</td><td>${pct(r.owp)}</td><td>${pct(r.imp)}</td>${roiTd(r.roi)}</tr>`).join("") + `</tbody></table></div>`;
}
async function vLabs(tab) {
  tab = tab || "query"; const L = await getJSON("labs.json");
  const head = `<h2>Labs</h2><div class="sub">${L.n_fights.toLocaleString()} UFC fights · ${L.n_odds.toLocaleString()} with closing lines (2022 on) · built from UFCStats and our odds archive</div><div class="links" style="margin:10px 0 4px">${LTABS.map(([k, v]) => `<a href="#/labs/${k}" style="${k === tab ? "background:var(--action-green-dark);border-color:var(--action-green-dark);color:#fff" : ""}">${v}</a>`).join("")}</div>`;
  const fl = (r, txt) => `<a href="#/fight/${r.es}/${r.n}">${txt}</a>`;
  let h = "";
  if (tab === "upsets") {
    h = `<h3>Biggest upsets by closing line</h3><div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Date</th><th class="l">Winner</th><th>Close</th><th>Win %</th><th class="l">Beat</th><th>Close</th><th class="l">How</th><th class="l">Division</th></tr></thead><tbody>` +
      L.upsets.map((u, i) => `<tr><td class="c dim">${i + 1}</td><td class="l dim">${sdate(u.d)}</td><td class="l b">${fl(u, esc(u.w))}</td><td class="b pos">${ml(u.ml)}</td><td>${pct(u.p)}</td><td class="l">${esc(u.l)}</td><td class="dim">${ml(u.lml)}</td><td class="l">${u.m}${u.r ? " R" + u.r : ""}</td><td class="l dim">${esc(u.wc)}</td></tr>`).join("") + `</tbody></table></div>
      <h3>Underdog winners by year</h3>${barChart(L.upsets_by_year.map(y => ({ label: y.yr, v: y.dogs / y.n, n: y.n })), { min: 0.2, max: 0.45 })}<div class="note">Share of fights won by the closing underdog. Win % is the no-vig closing consensus.</div>`;
  } else if (tab === "size") {
    h = `<h3>Age gap · how often the younger fighter wins</h3>${barChart(L.age_gap.map(r => ({ label: r.label, v: r.wp, v2: r.imp, n: r.n })), { ref: 0.5, refLabel: "50%" })}<div class="legend"><span><i style="border-color:#0a8842"></i>younger fighter win % (since 2010)</span><span><i style="border-color:#1b4fb0"></i>market % (line era)</span></div>${studyTable(L.age_gap, "Younger")}
      <h3>Win rate by the fighter's own age</h3>${barChart(L.age_band.map(r => ({ label: r.label, v: r.wp, v2: r.imp, n: r.n })), { ref: 0.5, refLabel: "50%" })}${studyTable(L.age_band, "Fighter")}
      <h3>Reach advantage · how often the longer fighter wins</h3>${barChart(L.reach_gap.map(r => ({ label: r.label, v: r.wp, v2: r.imp, n: r.n })), { ref: 0.5, refLabel: "50%" })}${studyTable(L.reach_gap, "Longer")}
      <h3>Height advantage · how often the taller fighter wins</h3>${barChart(L.height_gap.map(r => ({ label: r.label, v: r.wp, v2: r.imp, n: r.n })), { ref: 0.5, refLabel: "50%" })}${studyTable(L.height_gap, "Taller")}
      <div class="note">Win rates use every fight since 2010 with both fighters' data on UFCStats. Market % and ROI use only fights with a closing line, so they rest on far fewer fights.</div>`;
  } else if (tab === "spots") {
    h = `<h3>Situational spots</h3>${studyTable(L.situational, "Fighter")}<h3>Favorites by card position</h3><div class="tw"><table><thead><tr><th class="l">Slot</th><th>Fights</th><th>Favorite win %</th><th>Market %</th><th>ROI at close</th><th>Goes the distance</th></tr></thead><tbody>${L.position.map(r => `<tr><td class="l b">${esc(r.label)}</td><td>${r.on}</td><td class="b">${pct(r.owp)}</td><td>${pct(r.imp)}</td>${roiTd(r.roi)}<td>${pct(r.dist)}</td></tr>`).join("")}</tbody></table></div><div class="note">Card position comes from UFCStats bout order. The official main card / prelim split is not in the data, so slots are counted from the top of the card.</div>`;
  } else if (tab === "divisions") {
    const yrs = Object.keys(L.divisions[0].years), all = L.divisions.find(d => d.wc === "All"), pal = ["#d63636", "#1b4fb0", "#0a8842", "#8a6a12", "#7a3fb0", "#0e8a9a", "#c9503e", "#555", "#111"];
    const men = L.divisions.filter(d => !/Women|All/.test(d.wc));
    const cell = (v, base, f) => v == null ? "<td>—</td>" : `<td title="3-year baseline ${f(base)}" class="${Math.abs(v - base) / (base || 1) > 0.12 ? (v > base ? "pos b" : "neg b") : ""}">${f(v)}</td>`;
    const P = (v) => pct(v, 0), N2 = (v) => v == null ? "—" : v.toFixed(2);
    h = `<h3>Finish rate by year</h3>${multiLine(men.map((d, i) => ({ name: d.wc, color: pal[i], vals: yrs.map(y => d.years[y] && d.years[y].n >= 15 ? d.years[y].fin : null) })).concat([{ name: "All UFC", color: "#111", bold: true, vals: yrs.map(y => all.years[y] ? all.years[y].fin : null) }]), yrs)}
      <h3>Rolling baselines · last 12 months (as of ${fdate(L.asof)})</h3><div class="tw"><table><thead><tr><th class="l">Division</th><th>Fights</th><th>Finish</th><th>KO/TKO</th><th>Sub</th><th>Decision</th><th>Avg min</th><th title="Sig. strikes landed per minute, per fighter">SLpM</th><th title="Takedowns per 15 min, per fighter">TD/15</th><th title="Knockdowns per 15 min, per fighter">KD/15</th><th title="Share of fight time spent in control">Control</th><th title="Share of sig. strikes to the head">Head</th><th title="Share of sig. strikes at distance">Distance</th></tr></thead><tbody>` +
      L.divisions.map(d => { const a = d.r12, b = d.r36; return a ? `<tr ${d.wc === "All" ? 'style="font-weight:700;background:var(--paper2)"' : ""}><td class="l b">${esc(d.wc)}</td><td class="dim">${a.n}</td>${cell(a.fin, b.fin, P)}${cell(a.ko, b.ko, P)}${cell(a.sub, b.sub, P)}${cell(a.dec, b.dec, P)}${cell(a.min, b.min, N2)}${cell(a.slpm, b.slpm, N2)}${cell(a.td15, b.td15, N2)}${cell(a.kd15, b.kd15, N2)}${cell(a.ctrl, b.ctrl, P)}${cell(a.head, b.head, P)}${cell(a.dist, b.dist, P)}</tr>` : ""; }).join("") + `</tbody></table></div><div class="note">Green or red means the last 12 months sit 12%+ above or below that division's 3-year baseline (hover a cell for the baseline). Small divisions move a lot on few fights.</div>
      <h3>Decision rate by year</h3><div class="tw"><table><thead><tr><th class="l">Division</th>${yrs.map(y => `<th>${y}</th>`).join("")}</tr></thead><tbody>${L.divisions.map(d => `<tr><td class="l b">${esc(d.wc)}</td>${yrs.map(y => `<td title="${d.years[y] ? d.years[y].n + " fights" : ""}">${d.years[y] ? P(d.years[y].dec) : "—"}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  } else if (tab === "octagon") {
    const O = L.octagon, yr = O.years.filter(y => y.apex && y.big);
    h = `<h3>Finish rate · APEX (25-ft cage) vs. full-size cage</h3>${barChart(yr.map(y => ({ label: y.yr, v: y.apex.fin, v2: y.big.fin })), { min: 0.35, max: 0.65 })}<div class="legend"><span><i style="border-color:#0a8842"></i>APEX</span><span><i style="border-color:#1b4fb0"></i>everywhere else</span></div>
      <div class="tw"><table><thead><tr><th class="l">Year</th><th>APEX fights</th><th>Finish</th><th title="Finish rate you'd expect from the weight classes on those cards">Expected</th><th>KO/TKO</th><th>Sub</th><th>Other fights</th><th>Finish</th><th>Expected</th><th>KO/TKO</th><th>Sub</th></tr></thead><tbody>` +
      O.years.concat([{ yr: "All", apex: O.all.apex, big: O.all.big }]).map(y => { const c = (o) => o ? `<td class="dim">${o.n}</td><td class="b">${pct(o.fin)}</td><td class="dim">${pct(o.exp)}</td><td>${pct(o.ko)}</td><td>${pct(o.sub)}</td>` : `<td colspan="5" class="c dim">—</td>`; return `<tr ${y.yr === "All" ? 'style="background:var(--paper2)"' : ""}><td class="l b">${y.yr}</td>${c(y.apex)}${c(y.big)}</tr>`; }).join("") + `</tbody></table></div>
      <div class="banner">Venue is inferred, not read from a source: a fight counts as APEX if the card was in Las Vegas on or after May 30, 2020 and was not a numbered event, plus UFC 250, 252, 255, 256, 258, 259 and 260. UFCStats lists only the city. "Expected" adjusts for which weight classes were on the cards. It does not adjust for APEX cards having weaker, less experienced fighters.</div>`;
  } else if (tab === "metrics") {
    const cols = [["nm", "Fighter", null], ["wc", "Division", null], ["n", "Fights", (v) => v], ["ctd", "Control per TD", (v) => v == null ? "—" : Math.floor(v / 60) + ":" + String(Math.round(v % 60)).padStart(2, "0"), "Seconds of control per takedown landed (min. 5 takedowns)"], ["kd15", "KD / 15", (v) => v.toFixed(2), "Knockdowns scored per 15 minutes"], ["kdr", "KD per 100 head", (v) => v == null ? "—" : v.toFixed(2), "Knockdowns per 100 head strikes landed: power per clean shot"], ["chin", "KD taken per 100", (v) => v == null ? "—" : v.toFixed(2), "Knockdowns suffered per 100 head strikes absorbed: lower is a better chin"], ["hdef", "Head def", (v) => pct(v, 0), "Share of opponents' head strike attempts that missed"], ["bdef", "Body def", (v) => pct(v, 0)], ["ldef", "Leg def", (v) => pct(v, 0)], ["dd", "Distance diff", (v) => signed(v, 2), "Distance strikes landed minus absorbed, per minute"], ["hd", "Head diff", (v) => signed(v, 2), "Head strikes landed minus absorbed, per minute"], ["bd", "Body diff", (v) => signed(v, 2)], ["ld", "Leg diff", (v) => signed(v, 2)]];
    let sort = "dd", dir = -1, wc = "", lg = L.metrics_league;
    const draw = () => { const R = L.metrics.filter(m => !wc || m.wc === wc).filter(m => m[sort] != null).sort((a, b) => (typeof a[sort] === "string" ? a[sort].localeCompare(b[sort]) : a[sort] - b[sort]) * dir).slice(0, 60);
      $app.innerHTML = head + `<h3>Custom fighter metrics · active fighters with 5+ UFC fights</h3><p><select id="mwc" style="padding:5px;border:1px solid var(--rule);border-radius:4px"><option value="">All divisions</option>${[...new Set(L.metrics.map(m => m.wc))].sort().map(w => `<option ${w === wc ? "selected" : ""}>${esc(w)}</option>`).join("")}</select> <span class="dim">Tap a column to sort; top 60 shown. UFC average: control per TD ${Math.floor(lg.ctd / 60)}:${String(lg.ctd % 60).padStart(2, "0")} · KD/15 ${lg.kd15} · KD per 100 head ${lg.kdr} · head def ${pct(lg.hdef, 0)} · body def ${pct(lg.bdef, 0)} · leg def ${pct(lg.ldef, 0)}</span></p>
        <div class="tw"><table><thead><tr>${cols.map(c => `<th class="${c[2] ? "" : "l"}" data-k="${c[0]}" title="${esc(c[3] || "")}" style="cursor:pointer">${c[1]}${c[0] === sort ? (dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("")}</tr></thead><tbody>${R.map(m => `<tr>${cols.map(c => c[0] === "nm" ? `<td class="l b"><a href="#/fighter/${m.s}">${esc(m.nm)}</a></td>` : c[0] === "wc" ? `<td class="l dim">${esc(m.wc)}</td>` : `<td class="${c[0] === sort ? "b" : ""}">${m[c[0]] == null ? "—" : c[2](m[c[0]])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
        <div class="note">Head, body and leg defense are separated, so a fighter who checks few leg kicks but is hard to hit clean shows up as such. UFCStats records target (head/body/leg) and position (distance/clinch/ground) separately, so "head strikes at distance" cannot be isolated exactly; distance diff and head diff are the two closest measures.</div>`;
      $app.querySelectorAll("th[data-k]").forEach(th => th.addEventListener("click", () => { const k = th.dataset.k; if (k === sort) dir = -dir; else { sort = k; dir = (k === "nm" || k === "wc" || k === "chin") ? 1 : -1; } draw(); }));
      document.getElementById("mwc").addEventListener("change", e => { wc = e.target.value; draw(); }); };
    draw(); return;
  } else if (tab === "scoring") {
    const S = L.scoring;
    h = `<h3>What a decision is made of</h3><div class="box" style="font-size:13.5px;line-height:1.55">A model fit to ${S.n.toLocaleString()} UFC decisions since 2010 picks the judges' winner from the stat sheet alone ${pct(S.acc)} of the time. Its weights show what the judges reward, in units of one head strike:</div>
      ${barChart(S.coef.map(c => ({ label: c.label, v: c.head_eq })), { fmt: (v) => v.toFixed(1), min: 0 })}
      <div class="stats"><div><b>${pct(S.unan.agree, 0)}</b><span>Unanimous decisions the stats agree with (${S.unan.n})</span></div><div><b>${pct(S.split.agree, 0)}</b><span>Split / majority decisions the stats agree with (${S.split.n})</span></div><div><b>${pct(S.split.p, 0)}</b><span>Avg. stat-sheet win chance of a split-decision winner</span></div></div>
      <h3>Decisions that went most against the numbers</h3><div class="tw"><table><thead><tr><th class="l">Date</th><th class="l">Got the decision</th><th class="l">Over</th><th title="Chance the stat sheet gave the winner">Stat-sheet chance</th><th class="l">Type</th></tr></thead><tbody>${S.against.map(r => `<tr><td class="l dim">${sdate(r.d)}</td><td class="l b">${fl(r, esc(r.w))}</td><td class="l">${esc(r.l)}</td><td class="neg b">${pct(r.p)}</td><td class="l dim">${r.split ? "split / majority" : "unanimous"} · ${r.sched}R</td></tr>`).join("")}</tbody></table></div>
      <div class="grid2"><div><h3>Luckiest on the cards (active)</h3><div class="tw"><table><thead><tr><th class="l">Fighter</th><th>Decisions</th><th title="Decision wins above what the stat sheets implied">Wins above expected</th></tr></thead><tbody>${S.lucky.map(r => `<tr><td class="l b"><a href="#/fighter/${r.s}">${esc(r.nm)}</a></td><td class="dim">${r.n}</td><td class="pos b">${signed(r.luck, 2)}</td></tr>`).join("")}</tbody></table></div></div>
      <div><h3>Unluckiest on the cards (active)</h3><div class="tw"><table><thead><tr><th class="l">Fighter</th><th>Decisions</th><th>Wins above expected</th></tr></thead><tbody>${S.unlucky.map(r => `<tr><td class="l b"><a href="#/fighter/${r.s}">${esc(r.nm)}</a></td><td class="dim">${r.n}</td><td class="neg b">${signed(r.luck, 2)}</td></tr>`).join("")}</tbody></table></div></div></div>
      <div class="note">Fight totals only, not round by round, and the model is graded on the same fights it was fit to. "Luck" here mixes real judging variance with things the stat sheet misses (damage, round-by-round distribution, who won the close rounds). Treat it as a pointer to fights worth rewatching, not a verdict.</div>`;
  } else { // query
    const Q = await getJSON("labs_fights.json"), ix = Object.fromEntries(Q.cols.map((c, i) => [c, i]));
    const st = { wc: "", side: "fav", lo: 50, hi: 100, mv: "", pos: "", sched: "", y0: "", apex: "", sex: "" };
    const yrs = [...new Set(Q.rows.map(r => r[ix.d].slice(0, 4)))].sort();
    const sel = (id, opts) => `<select id="q_${id}" style="padding:5px;border:1px solid var(--rule);border-radius:4px;margin:0 8px 6px 0">${opts.map(([v, l]) => `<option value="${v}" ${String(st[id]) === String(v) ? "selected" : ""}>${l}</option>`).join("")}</select>`;
    const pay = (o) => o > 0 ? o / 100 : 100 / -o;
    const draw = () => {
      const R = Q.rows.filter(r => { const pf = r[ix.pf] * 100, ps = st.side === "fav" ? pf : 100 - pf, mv = r[ix.po] == null ? null : (r[ix.pf] - r[ix.po]) * 100 * (st.side === "fav" ? 1 : -1);
        return (!st.wc || r[ix.wc] === st.wc) && ps >= st.lo && ps <= st.hi && (!st.pos || (st.pos === "1" ? r[ix.pos] === 1 : st.pos === "5" ? r[ix.pos] <= 5 : r[ix.pos] > 5)) && (!st.sched || r[ix.sched] == st.sched) && (!st.y0 || r[ix.d] >= st.y0) && (!st.apex || r[ix.apex] == st.apex) && (!st.sex || (st.sex === "w") === /Women/.test(r[ix.wc])) &&
          (!st.mv || (mv != null && (st.mv === "in" ? mv >= 2 : st.mv === "out" ? mv <= -2 : Math.abs(mv) < 2))); });
      const won = (r) => st.side === "fav" ? r[ix.fw] === 1 : r[ix.fw] === 0, price = (r) => st.side === "fav" ? r[ix.mf] : r[ix.md];
      const w = R.filter(won).length, pnl = R.reduce((s, r) => s + (won(r) ? pay(price(r)) : -1), 0), imp = R.reduce((s, r) => s + (st.side === "fav" ? r[ix.pf] : 1 - r[ix.pf]), 0) / (R.length || 1);
      const mc = (m) => R.filter(r => r[ix.m] === m).length;
      $app.innerHTML = head + `<h3>Build a query · ${Q.rows.length.toLocaleString()} fights with closing lines</h3><div class="box">
        ${sel("side", [["fav", "Bet the favorite"], ["dog", "Bet the underdog"]])}${sel("wc", [["", "Any division"]].concat([...new Set(Q.rows.map(r => r[ix.wc]))].sort().map(w => [w, w])))}${sel("sex", [["", "Men + women"], ["m", "Men"], ["w", "Women"]])}${sel("pos", [["", "Any card slot"], ["1", "Main event"], ["5", "Top 5 on the card"], ["6", "6th from top or lower"]])}${sel("sched", [["", "3 or 5 rounds"], ["3", "3 rounds"], ["5", "5 rounds"]])}${sel("mv", [["", "Any line move"], ["in", "Moved toward this side 2+ pts"], ["out", "Moved against this side 2+ pts"], ["flat", "Moved under 2 pts"]])}${sel("apex", [["", "Any venue"], ["1", "APEX (inferred)"], ["0", "Not APEX"]])}${sel("y0", [["", "All years"]].concat(yrs.map(y => [y + "-01-01", "Since " + y])))}
        <div style="margin-top:4px">Closing win % of the side: <input id="q_lo" type="number" min="0" max="100" value="${st.lo}" style="width:62px;padding:4px"> to <input id="q_hi" type="number" min="0" max="100" value="${st.hi}" style="width:62px;padding:4px"> <span class="dim">(no-vig consensus; 60 ≈ −150, 70 ≈ −233, 30 ≈ +233)</span></div></div>
        <div class="stats" style="margin-top:10px"><div><b>${w}-${R.length - w}</b><span>Record</span></div><div><b>${R.length ? pct(w / R.length) : "—"}</b><span>Win %</span></div><div><b>${R.length ? pct(imp) : "—"}</b><span>Market %</span></div><div><b class="${cls(pnl)}">${R.length ? signed(pnl, 2) + "u" : "—"}</b><span>Units, 1u flat at close</span></div><div><b class="${cls(pnl)}">${R.length ? signed(pnl / R.length * 100) + "%" : "—"}</b><span>ROI</span></div><div><b>${R.length ? pct(mc("DEC") / R.length, 0) : "—"}</b><span>Went the distance</span></div><div><b>${R.length ? pct(mc("KO") / R.length, 0) + " / " + pct(mc("SUB") / R.length, 0) : "—"}</b><span>KO / sub</span></div></div>
        ${R.length && R.length < 100 ? `<div class="note">Only ${R.length} fights match. Treat the result as noise until the sample is much larger.</div>` : ""}
        <h3>Matching fights (latest 150)</h3><div class="tw"><table><thead><tr><th class="l">Date</th><th class="l">Favorite</th><th>Close</th><th>Open %</th><th>Close %</th><th class="l">Underdog</th><th>Close</th><th class="l">Division</th><th class="l">Result</th><th>Units</th></tr></thead><tbody>${R.slice().sort((a, b) => a[ix.d] < b[ix.d] ? 1 : -1).slice(0, 150).map(r => `<tr><td class="l dim">${sdate(r[ix.d])}</td><td class="l ${r[ix.fw] ? "b" : ""}"><a href="#/fight/${r[ix.es]}/${r[ix.n]}">${esc(r[ix.fav])}</a></td><td>${ml(r[ix.mf])}</td><td class="dim">${r[ix.po] == null ? "—" : pct(r[ix.po])}</td><td>${pct(r[ix.pf])}</td><td class="l ${r[ix.fw] ? "" : "b"}">${esc(r[ix.dog])}</td><td>${ml(r[ix.md])}</td><td class="l dim">${esc(r[ix.wc])} · ${r[ix.sched] || "—"}R</td><td class="l">${r[ix.fw] ? "Fav" : "Dog"} · ${r[ix.m]}${r[ix.r] ? " R" + r[ix.r] : ""}</td><td class="${won(r) ? "pos" : "neg"}">${won(r) ? "+" + pay(price(r)).toFixed(2) : "−1.00"}</td></tr>`).join("")}</tbody></table></div>
        <div class="note">Prices are the closing consensus, so a bettor shopping for the best number does better than shown. Open % is the favorite's opening no-vig probability. Past results in a filtered sample do not predict future ones, and the more filters you stack the more likely a good-looking result is chance.</div>`;
      for (const k of ["side", "wc", "sex", "pos", "sched", "mv", "apex", "y0"]) document.getElementById("q_" + k).addEventListener("change", e => { st[k] = e.target.value; draw(); });
      for (const k of ["lo", "hi"]) document.getElementById("q_" + k).addEventListener("change", e => { st[k] = +e.target.value; draw(); });
    };
    draw(); return;
  }
  $app.innerHTML = head + h;
}

/* ---------- router + search ---------- */
const routes = [[/^#\/?$/, vHome, "home"], [/^#\/cards$/, vCards, "cards"], [/^#\/card\/([^/]+)$/, vCard, "cards"], [/^#\/fight\/([^/]+)\/(\d+)$/, vFight, "cards"],
  [/^#\/fighters$/, vFighters, "fighters"], [/^#\/fighter\/([^/]+)$/, vFighter, "fighters"], [/^#\/model$/, vModel, "model"], [/^#\/duration$/, vDM, "duration"], [/^#\/duration-grading$/, vDMGrading, "duration"], [/^#\/duration\/([^/]+)\/tape$/, vDMTape, "duration"], [/^#\/duration\/([^/]+)$/, vDMCard, "duration"], [/^#\/methodology$/, vMethodology, "duration"], [/^#\/glossary$/, vGlossary, "duration"], [/^#\/research$/, vResearch, "research"], [/^#\/labs$/, vLabs, "labs"], [/^#\/labs\/([a-z]+)$/, vLabs, "labs"], [/^#\/compare\/([^/]+)\/([^/]+)$/, vCompare, "fighters"], [/^#\/rankings$/, vRankings, "fighters"], [/^#\/sheet\/([^/]+)$/, vSheet, "cards"], [/^#\/about$/, vAbout, "about"]];
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
