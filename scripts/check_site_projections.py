#!/usr/bin/env python3
"""Assert that every Sean projection number the site shows for a card equals the sheet's "Publish to site" export.

Renders the real pages with form/app.js (scripts/site_render.js, no browser) and reads the numbers as printed:
  card page   #/card/<event>    Model column (win % a / b)
  home page   #/                same table, when the card is this week's
  print page  #/sheet/<event>   "model a/b"
  fight page  #/fight/<event>/n Model projection table (win %, fair ML, listed ML, DEC% KO% SUB%), GTD note,
                                Model sheet box (sheet model % + ML, wins by DEC / KO / SUB, fight GTD + listed GTD),
                                "How <dog>'s number is built" final line (= true dog %)
Expected values are computed here straight from the export with JavaScript's rounding rules.
Also checks the source marks: event proj_source / fight proj_src, the page labels.

    python3 scripts/check_site_projections.py --slug ufc_334             # exit 1 on any mismatch
    python3 scripts/check_site_projections.py --slug ufc_334 --negative  # planted mismatches must all be caught
Needs node (or bun) on PATH.
"""
import argparse, copy, json, math, os, re, shutil, subprocess, sys, tempfile, unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FD = REPO / "form" / "data"


def tf(x, d):
    """JavaScript Number.prototype.toFixed for x >= 0 (exact binary value, ties away from zero)."""
    q = Decimal(1).scaleb(-d)
    v = Decimal(x).copy_abs().quantize(q, rounding=ROUND_HALF_UP)
    return ("-" if x < 0 and v != 0 else "") + f"{v:.{d}f}"


def p2ml(p):
    if p is None or p <= 0 or p >= 1:
        return None
    return -math.floor(100 * p / (1 - p) + 0.5) if p >= 0.5 else math.floor(100 * (1 - p) / p + 0.5)


def ml(v):
    return "—" if v is None else (f"+{v}" if v > 0 else str(v))


def nm(s):
    return re.sub(r"[^a-z ]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).strip()


def same(a, b):
    a_, b_ = nm(a), nm(b)
    return a_.replace(" ", "") == b_.replace(" ", "") or (a_.split() and b_.split() and a_.split()[-1] == b_.split()[-1] and a_[:1] == b_[:1])


def export_for(slug):
    for p in (REPO / "data" / f"{slug}_projections.json", REPO / "data" / "pending" / f"{slug}_projections.json"):
        if p.exists():
            return json.load(open(p)), str(p.relative_to(REPO))
    return None, None


def event_for(slug, data_dir):
    idx = json.load(open(data_dir / "index.json"))
    for u in idx.get("upcoming", []):
        p = data_dir / "events" / f'{u["slug"]}.json'
        if p.exists() and json.load(open(p)).get("bp_file") == f"data/{slug}_odds.json":
            return p
    raise SystemExit(f"no upcoming event for {slug}")


def render(hashes, data_dir):
    node = shutil.which("node") or shutil.which("bun")
    if not node:
        raise SystemExit("node (or bun) not on PATH")
    out = subprocess.run([node, str(REPO / "scripts" / "site_render.js"), "--data", str(data_dir), *hashes], capture_output=True, text=True, timeout=300)
    if out.returncode:
        raise SystemExit("site_render failed: " + out.stderr[-2000:])
    return json.loads(out.stdout)


def cells(row_html):
    return [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]


def run(slug, data_dir, export, export_file, quiet=False):
    say = (lambda *a: None) if quiet else print
    evp = event_for(slug, data_dir)
    ev = json.load(open(evp))
    es = ev["slug"]
    fights = ev["fights"]
    pages = render(["#/", f"#/card/{es}", f"#/sheet/{es}"] + [f"#/fight/{es}/{f['n']}" for f in fights], data_dir)
    bad, n_cmp, cats = [], 0, {}
    tag = ""

    def eq(where, got, want):
        nonlocal n_cmp
        n_cmp += 1
        c_ = re.sub(r"\b[ab]\b ?", "", where[len(tag) + 1:]).strip()
        cats[c_] = cats.get(c_, 0) + 1
        if got != want:
            bad.append(f"{where}: shown {got!r}, export says {want!r}")

    ps = ev.get("proj_source") or {}
    rows = [r for r in (export or {}).get("fights", []) if r.get("publish") is not False]
    if export and ps.get("src") != "publish":
        bad.append(f"event proj_source.src = {ps.get('src')!r}, want 'publish' (an export exists: {export_file})")
    if export and ps.get("file") != export_file:
        bad.append(f"event proj_source.file = {ps.get('file')!r}, want {export_file!r}")
    if export and ps.get("published_at") != export.get("published_at"):
        bad.append(f"event proj_source.published_at = {ps.get('published_at')!r}, export {export.get('published_at')!r}")
    covered = 0
    for f in fights:
        A, B = f["a"]["name"], f["b"]["name"]
        r = next((r for r in rows if (same(r["dog"], A) and same(r["fav"], B)) or (same(r["dog"], B) and same(r["fav"], A))), None)
        tag = f"fight {f['n']} {A} vs {B}"
        fp = pages[f"#/fight/{es}/{f['n']}"]
        if r is None:
            if f.get("proj_src") == "publish":
                bad.append(f"{tag}: proj_src 'publish' but the export has no row")
            if f.get("model") and 'data-proj-src="publish"' in fp:
                bad.append(f"{tag}: page labels the export but the export has no row")
            continue
        covered += 1
        a_dog = same(r["dog"], A)
        S, M, inp = r["sheet"], r["method"], r.get("inputs") or {}
        role = {"a": "dog" if a_dog else "fav", "b": "fav" if a_dog else "dog"}
        p = {s: S["true_" + role[s]] for s in "ab"}
        lst = {s: inp.get("dog_odds") if role[s] == "dog" else inp.get("fav_odds") for s in "ab"}
        if f.get("proj_src") != "publish":
            bad.append(f"{tag}: proj_src {f.get('proj_src')!r}, want 'publish'")
        # ---- fight page: Model projection table
        if 'data-proj-src="publish"' not in fp or "Publish to site export</h3>" not in fp and "Publish to site export " not in fp:
            bad.append(f"{tag}: fight page does not label the projection as the Publish to site export")
        mp = fp.split("Model projection", 1)
        if len(mp) < 2:
            bad.append(f"{tag}: no Model projection table on the fight page")
            continue
        tb = mp[1].split("</table>", 1)[0]
        trs = re.findall(r"<tr>(<td class=\"l b\">.*?)</tr>", tb, re.S)
        for s, tr in zip("ab", trs):
            c = cells(tr)
            eq(f"{tag} fight page {s} name", c[0], f[s]["name"])
            eq(f"{tag} fight page {s} win %", c[1], tf(p[s] * 100, 1) + "%")
            eq(f"{tag} fight page {s} fair ML", c[2], ml(p2ml(p[s])))
            eq(f"{tag} fight page {s} listed ML", c[3], ml(lst[s]))
            for j, k in ((6, "dec"), (7, "ko"), (8, "sub")):
                eq(f"{tag} fight page {s} {k.upper()}%", c[j], tf(p[s] * M[role[s]][k] * 100, 0))
        if len(trs) != 2:
            bad.append(f"{tag}: Model projection table has {len(trs)} fighter rows")
        g = re.search(r"Model goes-the-distance: ([0-9.]+)%", fp)
        eq(f"{tag} fight page GTD", g and g.group(1), tf(r["gtd"] * 100, 1))
        # ---- Model sheet box
        sm = re.search(r"Sheet model</td><td class=\"b\">([^<]*)</td><td class=\"b\">([^<]*)</td>", fp)
        eq(f"{tag} sheet box model a", sm and sm.group(1), f"{tf(p['a'] * 100, 1)}% · {ml(p2ml(p['a']))}")
        eq(f"{tag} sheet box model b", sm and sm.group(2), f"{tf((1 - p['a']) * 100, 1)}% · {ml(p2ml(1 - p['a']))}")
        wm = re.search(r"Wins by DEC / KO / SUB</td><td>([^<]*)</td><td>([^<]*)</td>", fp)
        for s, gi in (("a", 1), ("b", 2)):
            eq(f"{tag} sheet box DEC/KO/SUB {s}", wm and wm.group(gi), " / ".join(tf(M[role[s]][k] * 100, 0) for k in ("dec", "ko", "sub")))
        gg = re.search(r"Fight GTD</td><td colspan=\"2\" class=\"c\">model ([0-9.]+)%(?: · listed ([0-9.]+)%)?", fp)
        eq(f"{tag} sheet box GTD", gg and gg.group(1), tf(r["gtd"] * 100, 1))
        if r.get("gtd_listed") is not None:
            eq(f"{tag} sheet box listed GTD", gg and gg.group(2), tf(r["gtd_listed"] * 100, 1))
        dog = f["a" if a_dog else "b"]["name"]
        bu = re.search(r"Sheet model, " + re.escape(dog.replace("'", "&#39;")) + r"</td><td></td><td class=\"b\">([0-9.]+)%", fp) or \
             re.search(r"Sheet model, [^<]*</td><td></td><td class=\"b\">([0-9.]+)%", fp)
        if bu or "number is built" in fp:
            eq(f"{tag} build-up final (dog)", bu and bu.group(1), tf(S["true_dog"] * 100, 1))
        # ---- card page / home page / print page
        for h in (f"#/card/{es}", "#/"):
            pg = pages[h]
            m_ = re.search(r'data-href="#/fight/' + re.escape(es) + "/" + str(f["n"]) + r'">(.*?)</tr>', pg, re.S)
            if not m_:
                if h == "#/":
                    continue
                bad.append(f"{tag}: no row on {h}")
                continue
            mm = re.search(r"<td>(\d+) / (\d+)</td>", m_.group(1))
            eq(f"{tag} {h} Model column", mm and f"{mm.group(1)} / {mm.group(2)}", f"{tf(p['a'] * 100, 0)} / {tf(p['b'] * 100, 0)}")
        sp = pages[f"#/sheet/{es}"]
        blk = re.search(r'href="#/fight/' + re.escape(es) + "/" + str(f["n"]) + r'">.*?</div></div>', sp, re.S)
        mm = blk and re.search(r"model (\d+)/(\d+)", blk.group(0))
        if blk:
            eq(f"{tag} print page model", mm and f"{mm.group(1)}/{mm.group(2)}", f"{tf(p['a'] * 100, 0)}/{tf(p['b'] * 100, 0)}")
    if export and covered != len(rows):
        bad.append(f"export has {len(rows)} published rows, {covered} matched a bout on the card")
    say(f"{slug}: {len(fights)} fights, {covered} with an export row ({export_file or 'no export'}); {n_cmp} displayed numbers compared, {len(bad)} mismatches")
    say("   compared: " + ", ".join(f"{k} {v}" for k, v in cats.items()))
    for b in bad:
        say("   ", b)
    return n_cmp, bad


def shadow(data_dir, tmp):
    """data dir copy that shares everything except events/ (symlinks), so an event file can be edited."""
    T = Path(tmp) / "data"
    T.mkdir()
    for p in data_dir.iterdir():
        if p.name != "events":
            os.symlink(p.resolve(), T / p.name)
    (T / "events").mkdir()
    for p in (data_dir / "events").iterdir():
        os.symlink(p.resolve(), T / "events" / p.name)
    return T


def negative(slug, export, export_file):
    evp = event_for(slug, FD)

    def edit_event(fn):
        def go(T, X):
            p = T / "events" / evp.name
            d = json.load(open(evp))
            fn(d)
            p.unlink()
            json.dump(d, open(p, "w"))
        return go

    def fight(d, n):
        return next(f for f in d["fights"] if f["n"] == n)

    def m1(d): fight(d, 13)["model"]["a"]["win"] += 0.3; fight(d, 13)["model"]["b"]["win"] -= 0.3
    def m2(d): s = fight(d, 7)["sheet"]["meth"]["a"]; s[0], s[1] = s[1], s[0]
    def m3(d): fight(d, 2)["model"]["gtd"] += 1.0
    def m4(d): fight(d, 5)["model"]["src"] = "sheet"
    def m5(d): fight(d, 9)["model"]["b"]["ko"] += 1.0
    def m6(d): fight(d, 11)["sheet"]["model"] += 0.004

    def x1(T, X):
        X["fights"][0]["sheet"]["true_fav"] += 0.002; X["fights"][0]["sheet"]["true_dog"] -= 0.002

    def x2(T, X):
        X["fights"][3]["gtd"] += 0.01

    plants = [("site: main event model win % moved 0.3 pts", edit_event(m1)),
              ("site: fight 7 sheet DEC/KO split swapped", edit_event(m2)),
              ("site: fight 2 model GTD moved 1 pt", edit_event(m3)),
              ("site: fight 5 labelled as the old sheet pull", edit_event(m4)),
              ("site: fight 9 KO % moved 1 pt", edit_event(m5)),
              ("site: fight 11 sheet-box model moved 0.4 pts", edit_event(m6)),
              ("export changed after the build: first row true % moved 0.2 pts", x1),
              ("export changed after the build: fourth row GTD moved 1 pt", x2)]
    caught = 0
    for label, fn in plants:
        with tempfile.TemporaryDirectory() as td:
            T = shadow(FD, td)
            X = copy.deepcopy(export)
            fn(T, X)
            _, bad = run(slug, T, X, export_file, quiet=True)
        print(f"  NEGATIVE {'CAUGHT' if bad else 'MISSED'} {len(bad):>3} mismatches · {label}" + (f"  e.g. {bad[0]}" if bad else ""))
        caught += bool(bad)
    print(f"negative test: {caught}/{len(plants)} planted mismatches caught")
    return caught == len(plants)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="ufc_334")
    ap.add_argument("--negative", action="store_true")
    a = ap.parse_args()
    export, export_file = export_for(a.slug)
    n, bad = run(a.slug, FD, export, export_file)
    ok = not bad
    if a.negative:
        if not export:
            raise SystemExit("negative test needs an export")
        ok = negative(a.slug, export, export_file) and ok
    sys.exit(0 if ok else 1)
