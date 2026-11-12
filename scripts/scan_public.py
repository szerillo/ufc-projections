#!/usr/bin/env python3
"""Public-build scan (Kirk round 16, call 2). The repo is served as-is by GitHub Pages, so everything in audits/ and every
file this branch adds relative to the live branch is public once merged. Stops (exit 1) on any hit of:
  secrets/tokens (GitHub, Anthropic/OpenAI, AWS, Slack, Google API keys, private keys, a Google Sheets URL with an ID),
  offshore sportsbook names, local paths (/Users/, /home/, C:\\Users), email addresses.
Code that must hold book keys to filter them out (the offshore list in the odds scripts) is listed in ALLOW with a reason;
an allowed file is still scanned for every other category.

  python3 scripts/scan_public.py [--base origin/main] [--paths extra files or dirs]
"""
import argparse, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAT = {
    "secret": re.compile(r"(ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-ant-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9]{32,}"
                         r"|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
                         r"|docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]{20,})"),
    "offshore": re.compile(r"\b(pinnacle|bovada|betonline(?:ag)?|lowvig|mybookie|betus|sportsbetting\.ag|everygame|betanysports)\b", re.I),
    "local path": re.compile(r"(/Users/[A-Za-z]|/home/[a-z]|C:\\\\Users)"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}\b"),
}
# file -> categories allowed, with the reason
ALLOW = {
    "scripts/build_line_history.py": ({"offshore"}, "OFF tuple names offshore keys so they can be kept out of current lines"),
    "scripts/scan_public.py": ({"offshore", "local path", "email", "secret"}, "the patterns themselves"),
    ".github/workflows/price_freshness.yml": ({"email"}, "git bot identity for the report commit (users.noreply.github.com), not a person"),
}
SKIP_SUFFIX = (".png", ".jpg", ".gif", ".gz", ".ico", ".woff", ".woff2")


def files(base, extra):
    added = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", "--diff-filter=A", f"{base}...HEAD"], capture_output=True, text=True, check=True).stdout.split()
    out = set(added) | {str(p.relative_to(REPO)) for p in (REPO / "audits").rglob("*") if p.is_file()}
    for e in extra:
        p = (REPO / e) if not Path(e).is_absolute() else Path(e)
        out |= {str(q) for q in ([p] if p.is_file() else p.rglob("*")) if Path(q).is_file()}
    return sorted(out)


def scan(paths):
    hits = []
    for rel in paths:
        if rel.endswith(SKIP_SUFFIX): continue
        p = REPO / rel if not Path(rel).is_absolute() else Path(rel)
        if not p.exists(): continue
        allowed = ALLOW.get(rel, (set(), ""))[0]
        try: text = p.read_text(errors="ignore")
        except Exception: continue
        for cat, rx in PAT.items():
            if cat in allowed: continue
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append((rel, line, cat, m.group(0)[:12] + ("..." if cat == "secret" else m.group(0)[12:40])))
    return hits


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--base", default="origin/main"); ap.add_argument("--paths", nargs="*", default=[])
    a = ap.parse_args()
    fs = files(a.base, a.paths); hits = scan(fs)
    print(f"PUBLIC SCAN: {len(fs)} files (audits/ + added vs {a.base}), {len(hits)} hits")
    for h in hits[:60]: print(f"  HIT {h[0]}:{h[1]} [{h[2]}] {h[3]}")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
