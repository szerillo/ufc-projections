"""Every page served from the Pages site carries <meta name="robots" content="noindex,nofollow"> (Sean, Nov 20 2026).
  python3 -I scripts/noindex.py --fix    add the tag to any tracked .html that lacks it (right after <head ...>), idempotent
  python3 -I scripts/noindex.py          check only: exit 1 if a tracked .html, or the Jekyll layout for .md pages, lacks it
No robots.txt Disallow on purpose: it would stop Google from reading the tag (and a project site cannot serve a root robots.txt)."""
import re, subprocess, sys, pathlib
REPO = pathlib.Path(__file__).resolve().parent.parent
TAG = '<meta name="robots" content="noindex,nofollow">'
HAS = re.compile(r'<meta\s+name="robots"\s+content="noindex,\s*nofollow"\s*/?>', re.I)
files = [REPO / f for f in subprocess.check_output(["git", "ls-files", "*.html"], cwd=REPO, text=True).split()
         if not f.startswith("_") and "/_" not in f and (REPO / f).exists()]
fix, bad = "--fix" in sys.argv, []
for p in files:
    s = p.read_text(errors="replace")
    if HAS.search(s.split("</head>", 1)[0]): continue
    if fix and re.search(r"<head[^>]*>", s, re.I):
        p.write_text(re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + TAG, s, count=1, flags=re.I)); continue
    bad.append(str(p.relative_to(REPO)))
lay = REPO / "_layouts/default.html"
if not lay.exists() or not HAS.search(lay.read_text()): bad.append("_layouts/default.html (Jekyll layout for rendered .md pages)")
print(f"NOINDEX: {len(files)} served .html files + the .md layout checked; missing: {len(bad)} {bad[:8]}")
sys.exit(1 if bad else 0)
