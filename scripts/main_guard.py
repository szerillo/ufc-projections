#!/usr/bin/env python3
"""Main-branch guard for the merge (Kirk round 19 B). Run by rehearse_go_live.sh and right before the merge.

The served-set checks (round 18 A: 0 offshore names outside code, 226/226 live files overwritten, 0 orphans) were proved
for one main commit, recorded in audits/MAIN_AT_CHECK.txt. If origin/main has moved, the merge is no longer the same
fast-forward: this script REFUSES (exit 1), lists main's new commits and files, and recomputes the served-set scan on the
actual merge result (git merge-tree), so the check can be redone and the SHA re-recorded on purpose.

  python3 scripts/main_guard.py [--ref origin/main] [--expected <sha>]
"""
import argparse, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts")); import scan_public  # noqa: E402  (one pattern list, kept in the scanner)
OFF = scan_public.PAT["offshore"]


def git(*a, check=True):
    r = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)
    if check and r.returncode != 0: sys.exit(f"git {' '.join(a)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def served_scan(tree):
    files = [l.split("\t", 1)[1] for l in git("ls-tree", "-r", tree).splitlines()]
    served = [f for f in files if not any(p.startswith(("_", ".")) for p in f.split("/"))]
    hits = {}
    for f in served:
        if f.endswith(".py") or f.endswith((".png", ".jpg", ".gz", ".ico", ".pyc")): continue
        n = len(OFF.findall(git("show", f"{tree}:{f}", check=False)))
        if n: hits[f] = n
    return len(served), hits


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ref", default="origin/main"); ap.add_argument("--expected", default=None)
    a = ap.parse_args()
    exp = a.expected or (REPO / "audits/MAIN_AT_CHECK.txt").read_text().split()[0]
    cur = git("rev-parse", a.ref)
    if cur == exp and subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", cur, "HEAD"]).returncode == 0:
        print(f"MAIN GUARD: {a.ref} is {cur[:8]}, the commit the served-set checks were run against; merge is a fast-forward. OK")
        return
    print(f"MAIN GUARD: {a.ref} is {cur[:8]}, expected {exp[:8]}. REFUSING: the round-18 served-set result no longer applies.")
    new = git("log", "--format=%h %cI %s", f"{exp}..{cur}", check=False)
    print("  main's new commits:\n    " + ("\n    ".join(new.splitlines()) or "(none: main was rewritten)"))
    chg = git("diff", "--name-status", exp, cur, check=False)
    print("  files main changed since the check:\n    " + ("\n    ".join(chg.splitlines()[:40]) or "(none)"))
    mt = subprocess.run(["git", "-C", str(REPO), "merge-tree", "--write-tree", cur, "HEAD"], capture_output=True, text=True)
    if mt.returncode != 0:
        print("  the merge would CONFLICT:\n    " + mt.stdout.strip().replace("\n", "\n    ")[:2000]); sys.exit(1)
    tree = mt.stdout.split()[0]; n, hits = served_scan(tree)
    print(f"  recomputed on the real merge result (tree {tree[:8]}): {n} served files; non-code files naming an offshore book: {len(hits)} {hits}")
    print("  Redo the round-18 checks on this tree, then record the new main SHA in audits/MAIN_AT_CHECK.txt on purpose.")
    sys.exit(1)


if __name__ == "__main__":
    main()
