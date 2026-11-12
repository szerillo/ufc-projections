#!/usr/bin/env python3
"""Public-build scan (Kirk round 16 call 2; scope widened in round 17 call 1). The repo is served as-is by GitHub Pages, so
everything in audits/ and every file this branch adds OR modifies relative to the live branch is public once merged.
Stops (exit 1) on any hit of:
  secrets/tokens (GitHub, Anthropic/OpenAI, AWS, Slack, Google API keys, private keys, a Google Sheets URL with an ID),
  offshore sportsbook names, local paths (/Users/, /home/, C:\\Users), email addresses, sheet internals, working notes,
  paper trades, unit stakes.
KNOWN GAPS (Kirk round 19): a note that names a reviewer without a keyword ("Kirk says hold..."); a 1u stake ("1u on X");
  a signed P&L line ("+0.35u on X"). The wide units count is printed as a report so these can be eyeballed.
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
    # Kirk round 17 B: internal sheet references, working notes and paper trades (keywords only; see the round-17 report
    # for what still gets through: names alone, and bare unit stakes, are too common in legitimate public text to match)
    "sheet internals": re.compile(r"(gid=\d{6,}|\b(Calculator|Snapshots|PropSnap|Main Card|Prelims)![A-Z]{1,2}\d+|\b(Calculator|PropSnap|Snapshots) (tab|sheet)\b)"),
    "working note": re.compile(r"\b(TODO|FIXME|NOTE FROM|DO NOT PUBLISH|INTERNAL ONLY)\b"),
    "paper trade": re.compile(r"paper[- ]trad", re.I),
    # Kirk round 19 call 1: a stake in units ("0.35u", "2u"), blocking. Skips "1u" (methodology: "Flat 1u at the close") and
    # signed P&L ("+4.68u"). KNOWN GAPS, not caught: a real 1u stake ("1u on Hokit") and a signed P&L line ("+0.35u on Hokit").
    "unit stake": re.compile(r"(?<![+\-\d.])(?!1u\b)\d+(\.\d+)?u\b"),
}
WIDE_UNITS = re.compile(r"\d+(\.\d+)?u\b")   # report-only: any units figure, printed as a count in the rehearsal
# file -> categories allowed, with the reason. Secrets, local paths and emails are never allowed outside this file.
CODE_KEYS = "code: the odds archive's own book keys, needed to read it and to keep those books out of published lines; not rendered on any page"
ALLOW = {
    "scripts/build_line_history.py": ({"offshore"}, "OFF tuple names offshore keys so they can be kept out of current lines"),
    "scripts/build_form.py": ({"offshore"}, CODE_KEYS),
    "scripts/form_model.py": ({"offshore"}, CODE_KEYS),
    "scripts/verify_fight_embeds.py": ({"offshore"}, CODE_KEYS),
    "scripts/scan_public.py": ({"offshore", "local path", "email", "secret", "sheet internals", "working note", "paper trade", "unit stake"}, "the patterns themselves"),
    "form/app.js": ({"sheet internals"}, "Model page says the tracker is read from the sheet's Snapshots tab (public on main since Nov 10)"),
    ".github/workflows/price_freshness.yml": ({"email"}, "git bot identity for the report commit (users.noreply.github.com), not a person"),
    # Kirk round 32 B (publish-to-site merged into go-live-334): same bot-identity case, and code comments naming the sheet
    # cell whose formula the mirror reproduces (no sheet ID, no values)
    ".github/workflows/projections.yml": ({"email"}, "git bot identity for the verified-file commit (users.noreply.github.com), not a person"),
    ".github/workflows/rollback.yml": ({"email"}, "git bot identity for the rollback commit (users.noreply.github.com), not a person"),
    "scripts/sheet_v47.py": ({"sheet internals"}, "comments name the formula cell (Main Card!N2) the mirror reproduces; no sheet ID or values"),
    "scripts/test_sheet_v47.py": ({"sheet internals"}, "test provenance note names the formula cells the expected values come from"),
}
SKIP_SUFFIX = (".png", ".jpg", ".gif", ".gz", ".ico", ".woff", ".woff2")


def files(base, extra):
    added = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD"], capture_output=True, text=True, check=True).stdout.split()
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
    wide = sum(len(WIDE_UNITS.findall((REPO / f).read_text(errors="ignore"))) for f in fs if (REPO / f).is_file() and not f.endswith(SKIP_SUFFIX))
    print(f"UNITS (report only, wide pattern \\d+(\\.\\d+)?u): {wide} figures in the scanned files; the blocking 'unit stake' pattern is below")
    print(f"PUBLIC SCAN: {len(fs)} files (audits/ + added or modified vs {a.base}), {len(hits)} hits")
    for h in hits[:60]: print(f"  HIT {h[0]}:{h[1]} [{h[2]}] {h[3]}")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
