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
    ap.add_argument("--allow-publish-and-bot", action="store_true", help="PROPOSAL, round 21: accept main moving only by the publish export and the odds bot")
    a = ap.parse_args()
    exp = a.expected or (REPO / "audits/MAIN_AT_CHECK.txt").read_text().split()[0]
    # Kirk round 20 E: never trust the local remote-tracking ref. Fetch main now and ask the remote directly; if either
    # fails or they disagree, refuse (fail safe).
    if a.ref == "origin/main":
        f_ = subprocess.run(["git", "-C", str(REPO), "fetch", "-q", "origin", "+refs/heads/main:refs/remotes/origin/main"], capture_output=True, text=True, timeout=120)
        ls_ = subprocess.run(["git", "-C", str(REPO), "ls-remote", "origin", "refs/heads/main"], capture_output=True, text=True, timeout=120)
        if f_.returncode != 0 or ls_.returncode != 0 or not ls_.stdout.strip():
            print(f"MAIN GUARD: could not fetch or read origin main ({(f_.stderr or ls_.stderr).strip()[:200]}). REFUSING: cannot confirm main."); sys.exit(1)
        remote_ = ls_.stdout.split()[0]
        if remote_ != git("rev-parse", "origin/main"):
            print(f"MAIN GUARD: remote main {remote_[:8]} differs from the fetched ref. REFUSING."); sys.exit(1)
    cur = git("rev-parse", a.ref)
    if cur == exp and subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", cur, "HEAD"]).returncode == 0:
        print(f"MAIN GUARD: {a.ref} is {cur[:8]}, the commit the served-set checks were run against; merge is a fast-forward. OK")
        return
    # PROPOSAL (Kirk round 21 call 1, not active until Kirk's go): between the check and the merge, main may move ONLY by the
    # sheet's Publish to site export (data/pending/<slug>_projections.json) and the odds bot (data/<slug>_odds.json). If every
    # file main changed matches that, main still contains the checked commit, the branch's served set is clean and main's new
    # versions of those files are clean, the merge is OK as a --no-ff merge (not a fast-forward). A conflict is allowed only in
    # data/<slug>_odds.json and is resolved to the branch's version (the embeds were built from it; the bot overwrites it next
    # tick). Anything else still refuses.
    ALLOWED = re.compile(r"^data/(pending/[a-z0-9_]+_projections|[a-z0-9_]+_odds)\.json$"); ODDS = re.compile(r"^data/[a-z0-9_]+_odds\.json$")
    if a.allow_publish_and_bot and git("merge-base", exp, cur, check=False) == exp:
        chg_ = [l.split("\t")[-1] for l in git("diff", "--name-status", exp, cur, check=False).splitlines()]
        mt_ = subprocess.run(["git", "-C", str(REPO), "merge-tree", "--write-tree", "--name-only", cur, "HEAD"], capture_output=True, text=True)
        conf_ = [l for l in mt_.stdout.split("\n\n")[0].splitlines()[1:] if l.strip()] if mt_.returncode == 1 else []
        main_hits_ = {f: len(OFF.findall(git("show", f"{cur}:{f}", check=False))) for f in chg_}
        main_hits_ = {f: n for f, n in main_hits_.items() if n}
        if chg_ and all(ALLOWED.match(f) for f in chg_) and mt_.returncode in (0, 1) and all(ODDS.match(f) for f in conf_) and not main_hits_:
            n_, hits_ = served_scan("HEAD")
            if not hits_:
                print(f"MAIN GUARD: {a.ref} is {cur[:8]}; since {exp[:8]} main changed only {chg_} (publish export / odds bot); "
                      f"conflicts to resolve to the branch version: {conf_ or 'none'}. Branch served set {n_} files, 0 offshore hits; "
                      f"main's new versions 0 hits. OK as a --no-ff merge (not a fast-forward).")
                return
        print(f"  (allow-publish-and-bot: not accepted; changed {chg_[:8]}, conflicts {conf_[:8]}, offshore hits in main's new files {main_hits_})")
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
