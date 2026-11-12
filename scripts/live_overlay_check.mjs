// Block 55: CI version of live_overlay_check.py, no browser needed. Runs form/app.js's own overlayLive() unchanged
// on the repo files and counts the bouts that get a live price. RED (exit 1) if N < M (M = bouts on the card) or a
// side gets a price that is not that fighter's own feed price (full-name match after form/data/name_aliases.json).
// Usage: node scripts/live_overlay_check.mjs [event slug ...]   (default: every upcoming card in form/data/index.json)
import fs from "node:fs";
const R = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const src = fs.readFileSync("form/app.js", "utf8");
const i = src.indexOf("async function overlayLive(ev)");
if (i < 0) { console.log("RED: overlayLive not found in form/app.js"); process.exit(1); }
const body = src.slice(i, src.indexOf("\n}\n", i) + 2);
const lastLine = src.split("\n").find((l) => /^const last = /.test(l));
globalThis.fetch = async (u) => { const p = String(u).split("?")[0].replace(/^\//, ""); // the page fetches relative to the site root
  if (!fs.existsSync(p)) return { ok: false, json: async () => { throw new Error("404 " + p); } };
  return { ok: true, json: async () => R(p) }; };
const overlayLive = new Function(lastLine + "\n" + body + "\nreturn overlayLive;")();
const nm = (x) => (x || "").toLowerCase().normalize("NFD").replace(/[^a-z]/g, "");
const al = fs.existsSync("form/data/name_aliases.json") ? R("form/data/name_aliases.json") : {};
const slugs = process.argv.slice(2).length ? process.argv.slice(2) : (R("form/data/index.json").upcoming || []).map((u) => u.slug);
let red = false;
for (const slug of slugs) {
  const ev = R(`form/data/events/${slug}.json`);
  if (!ev.bp_file || !fs.existsSync(ev.bp_file)) { console.log(`${slug}: no odds feed file (${ev.bp_file}); skipped`); continue; }
  await overlayLive(ev);
  const d = R(ev.bp_file), full = {};
  for (const bf of d.fights || []) for (const z of (bf.markets || {}).moneyline || []) {
    const k = (z.label || "").toLowerCase().normalize("NFD").replace(/[^a-z ]/g, "").replace(/\s+/g, " ").trim();
    if (z.books && z.books.consensus) full[nm(al[k] || z.label)] = z.books.consensus.cost; }
  let N = 0, wrong = 0;
  for (const f of ev.fights) {
    const e = { ma: full[nm(f.a.name)] ?? null, mb: full[nm(f.b.name)] ?? null };
    if (f.live) { N++; if (f.live.ma !== e.ma || f.live.mb !== e.mb) wrong++; }
    console.log(`  ${f.live ? "ok  " : "MISS"} #${f.n} ${f.a.name} vs ${f.b.name}: ${f.live ? f.live.ma + " / " + f.live.mb : "-"}${f.live && (f.live.ma !== e.ma || f.live.mb !== e.mb) ? "  WRONG SIDE" : ""}`);
  }
  const M = ev.fights.length, bad = N < M || wrong > 0; red = red || bad;
  console.log(`${slug}: live prices applied to ${N} of ${M} bouts (feed ${d.updated_at}); ${wrong} wrong side -> ${bad ? "RED" : "GREEN"}`);
}
process.exit(red ? 1 : 0);
