// Render site pages (form/app.js) headless, with no browser: a tiny DOM stub, fetch served from the repo (or --data DIR).
//   node scripts/site_render.js [--data form/data] '#/card/<slug>' '#/fight/<slug>/13' ...   -> JSON {hash: html} on stdout
// Used by scripts/check_site_projections.py to read the numbers exactly as the page prints them.
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const REPO = path.resolve(__dirname, "..");
let args = process.argv.slice(2), dataDir = path.join(REPO, "form", "data");
if (args[0] === "--data") { dataDir = path.resolve(args[1]); args = args.slice(2); }
const app = { innerHTML: "", querySelectorAll: () => [], querySelector: () => null, addEventListener() {} }, listeners = {};
const location = { hash: "#/", search: "", href: "http://local/index.html" };
const document = {
  getElementById: (id) => (id === "app" ? app : null),
  querySelectorAll: () => [], querySelector: () => null, addEventListener: () => {},
  documentElement: { setAttribute() {}, getAttribute() { return null; }, dataset: {} },
};
const fetchLocal = async (url) => {
  const u = String(url).split("?")[0];
  const p = u.startsWith("form/data/") ? path.join(dataDir, u.slice("form/data/".length)) : path.join(REPO, u);
  if (!fs.existsSync(p)) return { ok: false, status: 404, json: async () => { throw new Error("404 " + u); }, text: async () => "" };
  const body = fs.readFileSync(p, "utf8");
  return { ok: true, status: 200, json: async () => JSON.parse(body), text: async () => body };
};
const window = { addEventListener: (t, fn) => { (listeners[t] = listeners[t] || []).push(fn); }, scrollTo() {} };
const ctx = { window, document, location, fetch: fetchLocal, console: { log() {}, warn() {}, error: (...a) => process.stderr.write(a.join(" ") + "\n") },
  setTimeout, clearTimeout, Promise, Date, Math, JSON, Intl, URLSearchParams, encodeURIComponent, decodeURIComponent };
window.window = window; Object.assign(window, { document, location });
vm.createContext(ctx);
const src = fs.readFileSync(path.join(REPO, "form", "app.js"), "utf8");
const settle = () => new Promise((r) => setTimeout(r, 30));
(async () => {
  vm.runInContext(src, ctx, { filename: "form/app.js" });
  await settle();
  const out = {};
  for (const h of args) {
    location.hash = h;
    for (const fn of listeners.hashchange || []) await fn();
    for (let i = 0; i < 50 && /class="loading"/.test(app.innerHTML); i++) await settle();
    out[h] = app.innerHTML;
  }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String(e && e.stack || e) + "\n"); process.exit(2); });
