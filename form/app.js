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
  const rows = lines.map((x, i) => {
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
      <td class="mth">${esc(shortMethod(x.m))}${x.ti ? " 🏆" : ""}</td>
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
    <th class="l">Date</th><th class="l">Opponent <span style="font-weight:400">Elo</span></th><th class="c">Res</th><th class="l">Method</th><th>Rd Time</th><th class="l">Wt</th>
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
    if (g !== group && i !== 1) { html += `<tr class="grp"><td colspan="9">${g === "Main event" ? "Main card" : g}</td></tr>`; group = g === "Main event" ? "Main card" : g; }
    let model = "—", edge = "—";
    if (m && m.a && m.a.win != null) {
      model = `${m.a.win.toFixed(0)} / ${m.b.win.toFixed(0)}`;
      if (o.pa != null) { const e = m.a.win - o.pa * 100; const side = e >= 0 ? f.a.name : f.b.name; edge = `<span class="${Math.abs(e) >= 3 ? "pos b" : "dim"}" title="Model minus no-vig market">${esc(side.split(" ").slice(-1)[0])} ${signed(Math.abs(e))}</span>`; }
    }
    const rec = m && m.rec ? `<span class="pill y" title="Model bet recommendation">BET ${esc((m.rec === "a" ? f.a.name : f.b.name).split(" ").slice(-1)[0])}</span>` : "";
    const wa = f.result && f.result.winner === "a", wb = f.result && f.result.winner === "b";
    html += `<tr class="click" data-href="#/fight/${ev.slug}/${f.n}">
      <td class="c dim">${f.n}</td>
      <td class="name"><span class="${wa ? "W" : ""}">${esc(f.a.name)}</span> <span class="dim">vs</span> <span class="${wb ? "W" : ""}">${esc(f.b.name)}</span> ${f.title ? '<span class="pill k">Title</span>' : ""} ${rec}
        <small>${esc(f.wc || "")}${f.sched ? " · " + f.sched + "R" : ""} · Elo ${f.a.elo || "—"} / ${f.b.elo || "—"}</small></td>
      <td>${o.open}</td><td>${o.close}</td>
      <td class="${cls(o.mv)}" title="Move in ${esc(f.a.name)} implied win %">${o.mv == null ? "—" : signed(o.mv)}</td>
      <td>${model}</td><td>${edge}</td>
      <td class="l">${final ? resultText(f) : '<span class="dim">' + (f.start ? new Date(f.start.replace(" ", "T") + "Z").toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) : "") + "</span>"}</td>
      <td class="c">›</td></tr>`;
  });
  return `<div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Bout</th><th>Open</th><th>${final ? "Close" : "Current"}</th><th title="Open→now move in first fighter's no-vig win %">Move</th><th title="Model win % (first / second)">Model</th><th>Edge</th><th class="l">${final ? "Result" : "Local time"}</th><th></th></tr></thead><tbody>${html}</tbody></table></div>`;
}
function wireRows() { $app.querySelectorAll("tr.click").forEach(tr => tr.addEventListener("click", e => { if (e.target.closest("a")) return; location.hash = tr.dataset.href; })); }

/* ---------- views ---------- */
async function vHome() {
  const idx = await getJSON("index.json");
  let html = "";
  for (const u of idx.upcoming) {
    const ev = await getJSON(`events/${u.slug}.json`);
    html += `<h2>Next up · ${esc(ev.name)}</h2><div class="sub">${fdate(ev.date)} · ${esc(ev.location)} · <a href="#/card/${ev.slug}" style="text-decoration:underline">full card page</a></div><div style="height:8px"></div>${cardTable(ev)}`;
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
  const ev = await getJSON(`events/${slug}.json`);
  const withOdds = ev.fights.filter(f => f.odds);
  const movers = withOdds.map(f => ({ f, mv: (f.odds.close.p - f.odds.open.p) * 100 })).sort((a, b) => Math.abs(b.mv) - Math.abs(a.mv)).slice(0, 5);
  let html = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/cards">Cards</a> › ${esc(ev.name)}</div>
    <h2>${esc(ev.name)} ${ev.status === "upcoming" ? '<span class="pill y">Upcoming</span>' : ""}</h2>
    <div class="sub">${fdate(ev.date)} · ${esc(ev.location)}${ev.odds_updated ? " · odds as of " + new Date(ev.odds_updated).toLocaleString() : ""}</div>
    <div class="links" style="margin-top:8px">${ev.widget ? `<a href="${ev.widget.file}" target="_blank" rel="noopener">Projection tables (widget)</a>` : ""}${ev.url ? `<a href="${esc(ev.url)}" target="_blank" rel="noopener">UFCStats event</a>` : ""}</div>
    ${cardTable(ev)}`;
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
  const ev = await getJSON(`events/${slug}.json`);
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
  <div class="bout"><div class="f r">${flink(f.a)}<small>UFC ${ga.rec} · Elo ${f.a.elo || "—"} · ${streak(pa)}</small></div><div class="vs">vs</div><div class="f">${flink(f.b)}<small>UFC ${gb.rec} · Elo ${f.b.elo || "—"} · ${streak(pb)}</small></div></div>`;
  if (final && f.result) html += `<div class="banner"><b>Result:</b> ${resultText(f)}${f.result.details ? " — " + esc(f.result.details) : ""}${f.result.ref ? " · Ref " + esc(f.result.ref) : ""}</div>`;

  // tale of the tape (as of fight night)
  html += `<div class="grid2"><div><h3>Tale of the tape · entering this fight</h3><div class="tape">
    ${tapeRow("Age", agA ? agA.toFixed(1) : "—", agB ? agB.toFixed(1) : "—", "lo")}
    ${tapeRow("Height", esc(ba.ht || "—"), esc(bb.ht || "—"), null, inches(ba.ht) && inches(bb.ht) && inches(ba.ht) !== inches(bb.ht) ? (inches(ba.ht) > inches(bb.ht) ? "a" : "b") : null)}
    ${tapeRow("Reach", ba.reach ? ba.reach + '"' : "—", bb.reach ? bb.reach + '"' : "—", "hi")}
    ${tapeRow("Stance", esc(ba.stance || "—"), esc(bb.stance || "—"), null)}
    ${tapeRow("UFC record", ga.rec, gb.rec, null)}
    ${tapeRow("Elo", f.a.elo || "—", f.b.elo || "—", "hi")}
    ${tapeRow("Layoff (days)", layA == null ? "debut" : layA, layB == null ? "debut" : layB, null)}
    ${tapeRow("SLpM", v(ga.slpm), v(gb.slpm), "hi")}
    ${tapeRow("SApM", v(ga.sapm), v(gb.sapm), "lo")}
    ${tapeRow("Strike diff /min", ga.diff == null ? "—" : signed(ga.diff, 2), gb.diff == null ? "—" : signed(gb.diff, 2), "hi")}
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
    html += `<h3>Model projection ${m.rec ? `<span class="pill y">Bet ${esc(m.rec === "a" ? f.a.name : f.b.name)}</span>` : ""}</h3><div class="tw"><table><thead><tr><th class="l">Fighter</th><th>Win</th><th>Fair</th><th title="Listed price when published">Listed</th><th title="Model minus listed implied %">Edge</th><th title="Model minus no-vig ${final ? "close" : "current"}">vs ${final ? "close" : "now"}</th><th>DEC%</th><th>KO%</th><th>SUB%</th></tr></thead><tbody>${row("a", m.a, f.a.name, mk)}${row("b", m.b, f.b.name, mk == null ? null : 100 - mk)}</tbody></table></div>
    ${m.gtd != null ? `<div class="note">Model goes-the-distance: ${m.gtd}%${o && o.total ? ` · market over ${o.total.pt}: ${pct(o.total.p_over)}` : ""}</div>` : ""}`;
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
    html += `<div class="pp-head"><div class="n">${flink(fx)} — past performances</div><div class="sub">${P.length} UFC fights before this one${F && F.dup_name ? ' · <span class="neg">name shared by two fighters; lines may be mixed</span>' : ""}</div></div>${ppTable(P.slice(0, 12), { name: fx.name })}${P.length > 12 ? `<div class="note">Showing last 12 of ${P.length}. <a href="#/fighter/${fx.slug}" style="text-decoration:underline">Full history →</a></div>` : ""}`;
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
  const E = F.fights.slice().reverse().map(x => x.el).concat([F.elo]).filter(x => x != null);
  let spark = "";
  if (E.length > 2) { const W = 300, H = 60, lo = Math.min(...E) - 10, hi = Math.max(...E) + 10; const d = E.map((e, i) => (i ? "L" : "M") + (i / (E.length - 1) * W).toFixed(1) + " " + (H - (e - lo) / (hi - lo) * H).toFixed(1)).join("");
    spark = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:60px"><path d="${d}" fill="none" stroke="#17140f" stroke-width="1.8"/></svg><div class="legend"><span>Elo by fight: ${E[0]} → ${E[E.length - 1]} (peak ${Math.max(...E)})</span></div>`; }
  const age = ageAt(b.dob, new Date().toISOString().slice(0, 10));
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › <a href="#/fighters">Fighters</a> › ${esc(F.name)}</div>
    <h2>${esc(F.name)}</h2>
    ${F.dup_name ? '<div class="banner">Two UFC fighters share this name. Their fights are combined on this page.</div>' : ""}
    <div class="stats"><div><b>${g.rec}</b><span>UFC record</span></div><div><b>${F.elo || "—"}</b><span>Elo</span></div><div><b>${streak(F.fights)}</b><span>Streak</span></div><div><b>${age ? age.toFixed(1) : "—"}</b><span>Age</span></div><div><b>${esc(b.ht || "—")}</b><span>Height</span></div><div><b>${b.reach ? b.reach + '"' : "—"}</b><span>Reach</span></div><div><b>${esc(b.stance || "—")}</b><span>Stance</span></div><div><b>${F.fights[0] ? esc(F.fights[0].wc.replace("Women's ", "W ")) : "—"}</b><span>Last weight</span></div></div>
    <div class="grid3" style="margin-top:14px">
      <div class="box"><h3 style="margin-top:0">Striking</h3><div class="kv"><span>SLpM</span><span>${v(g.slpm)}</span></div><div class="kv"><span>SApM</span><span>${v(g.sapm)}</span></div><div class="kv"><span>Diff / min</span><span class="${cls(g.diff)}">${g.diff == null ? "—" : signed(g.diff, 2)}</span></div><div class="kv"><span>Accuracy / defense</span><span>${pc(g.acc)} / ${pc(g.def)}</span></div><div class="kv"><span>KD per 15 (for-against)</span><span>${v(g.kd15)} - ${v(g.okd15)}</span></div></div>
      <div class="box"><h3 style="margin-top:0">Grappling</h3><div class="kv"><span>TD per 15</span><span>${v(g.td15)}</span></div><div class="kv"><span>TD acc / def</span><span>${pc(g.tdacc)} / ${pc(g.tdd)}</span></div><div class="kv"><span>Control %</span><span>${pc(g.ctrlp)}</span></div><div class="kv"><span>Controlled %</span><span>${pc(g.octrlp)}</span></div><div class="kv"><span>Sub att per 15</span><span>${v(g.sub15)}</span></div></div>
      <div class="box"><h3 style="margin-top:0">At the window</h3><div class="kv"><span>Flat 1u at the close</span><span class="${cls(pnl)}">${bets ? signed(pnl, 2) + "u / " + bets : "—"}</span></div><div class="kv"><span>As favorite</span><span>${favN ? favW + "-" + (favN - favW) : "—"}</span></div><div class="kv"><span>As underdog</span><span>${dogN ? dogW + "-" + (dogN - dogW) : "—"}</span></div><div class="kv"><span>Avg line move toward</span><span class="${cls(clvN ? clv / clvN : null)}">${clvN ? signed(clv / clvN) + " pts" : "—"}</span></div><div class="kv"><span>Wins KO-SUB-DEC</span><span>${g.ko}-${g.subw}-${g.dec}</span></div><div class="kv"><span>Losses KO-SUB-DEC</span><span>${g.kol}-${g.subl}-${g.decl}</span></div></div>
    </div>
    ${spark ? `<h3>Rating history</h3><div class="box">${spark}</div>` : ""}
    <div class="pp-head"><div class="n">Past performances</div><div class="sub">${F.fights.length} UFC fights · closing lines from 2022 on</div></div>
    ${ppTable(F.fights, { name: F.name })}
    <div class="links" style="margin-top:10px"><a href="https://www.youtube.com/results?search_query=${encodeURIComponent(F.name + " UFC full fight")}" target="_blank" rel="noopener">▶ YouTube: full fights</a><a href="https://ufcfightpass.com/search?q=${encodeURIComponent(F.name)}" target="_blank" rel="noopener">UFC Fight Pass search</a>${b.url ? `<a href="${esc(b.url)}" target="_blank" rel="noopener">UFCStats profile</a>` : ""}</div>`;
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
  const top = S.filter(x => x[2] >= String(new Date().getFullYear() - 2)).sort((a, b) => (b[5] || 0) - (a[5] || 0)).slice(0, 60);
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › Fighters</div><h2>Fighters</h2><p class="sub">${S.length.toLocaleString()} fighters. Use the search box above, or start from the highest-rated active fighters.</p>
    <div class="tw"><table><thead><tr><th class="c">#</th><th class="l">Fighter</th><th class="l">Last weight</th><th>UFC record</th><th>Elo</th><th class="l">Last fight</th></tr></thead><tbody>` +
    top.map((x, i) => `<tr class="click" data-href="#/fighter/${x[1]}"><td class="c dim">${i + 1}</td><td class="l b">${esc(x[0])}</td><td class="l">${esc(x[3])}</td><td>${x[4]}</td><td class="b">${x[5] || "—"}</td><td class="l">${sdate(x[2])}</td></tr>`).join("") + `</tbody></table></div>
    <p class="note">Elo is a simple results-only rating over every UFC fight (1500 start, K=48 for a fighter's first four fights, then 32). It is a context number for opponent quality, not the betting model.</p>`;
  wireRows();
}

async function vModel() {
  const M = await getJSON("model.json");
  const R = M.recs, w = R.filter(x => x.won).length, pnl = R.reduce((s, x) => s + (x.pnl || 0), 0), risk = R.reduce((s, x) => s + (x.risk || 0), 0);
  const withClose = R.filter(x => x.close_p != null && x.ml != null), beat = withClose.filter(x => x.close_ml != null && ml2p(x.ml) < ml2p(x.close_ml)).length;
  $app.innerHTML = `<div class="crumbs"><a href="#/">Home</a> › Model</div><h2>Model report card</h2>
    <p class="sub">Every moneyline bet the projection widgets flagged, graded automatically against UFCStats results. Stakes: risk 1u on plus money, to win 1u on minus money, at the price listed when the projection was published.</p>
    <div class="stats"><div><b>${w}-${R.length - w}</b><span>Flagged bets</span></div><div><b class="${cls(pnl)}">${signed(pnl, 2)}u</b><span>Profit / loss</span></div><div><b class="${cls(pnl)}">${risk ? signed(pnl / risk * 100) + "%" : "—"}</b><span>ROI on ${risk.toFixed(1)}u risked</span></div><div><b>${withClose.length ? beat + "/" + withClose.length : "—"}</b><span>Beat the closing line</span></div><div><b>${M.brier_model ?? "—"}</b><span>Brier · model (${M.n_both} fights)</span></div><div><b>${M.brier_close ?? "—"}</b><span>Brier · closing line</span></div></div>
    <p class="note">Brier score: lower is better. Compared on fights with both a model win % and a no-vig closing line.</p>
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
  <p><b>Sources.</b> Fight results and round-by-round stats: UFCStats, via the open <a href="https://github.com/Greco1899/scrape_ufc_stats" target="_blank" rel="noopener" style="text-decoration:underline">scrape_ufc_stats</a> dataset (GPL-3.0). Odds: The Odds API history and BettingPros. Film links are searches on YouTube and UFC Fight Pass; nothing is hosted here.</p>
  <p class="dim">Data built ${new Date(idx.built).toLocaleString()} · ${idx.counts.events} cards · ${idx.counts.fights.toLocaleString()} fights · ${idx.counts.fighters.toLocaleString()} fighters · ${idx.counts.odds_fights.toLocaleString()} fights with line history.</p></div>`;
}

/* ---------- router + search ---------- */
const routes = [[/^#\/?$/, vHome, "home"], [/^#\/cards$/, vCards, "cards"], [/^#\/card\/([^/]+)$/, vCard, "cards"], [/^#\/fight\/([^/]+)\/(\d+)$/, vFight, "cards"],
  [/^#\/fighters$/, vFighters, "fighters"], [/^#\/fighter\/([^/]+)$/, vFighter, "fighters"], [/^#\/model$/, vModel, "model"], [/^#\/about$/, vAbout, "about"]];
async function route() {
  const h = location.hash || "#/";
  for (const [re, fn, tab] of routes) { const m = re.exec(h); if (!m) continue;
    document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("on", a.dataset.tab === tab));
    $app.innerHTML = `<div class="loading">Loading…</div>`;
    try { await fn(...m.slice(1).map(decodeURIComponent)); } catch (e) { console.error(e); $app.innerHTML = `<div class="banner">Couldn't load this page (${esc(e.message)}).</div>`; }
    window.scrollTo(0, 0); return; }
  $app.innerHTML = `<div class="banner">Page not found.</div>`;
}
window.addEventListener("hashchange", route);
getJSON("index.json").then(i => { window.__books = i.books; }).catch(() => {});
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
