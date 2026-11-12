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
    ap.add_argument("--allow-publish-and-bot", action="store_true", help="Kirk round 22: accept main moving only by the export and the odds bot (explicit allowlist)")
    ap.add_argument("--slug", default="ufc_334")
    ap.add_argument("--allow-path", action="append", default=[], help="one more exact path main may change (repeatable, no patterns); Kirk names each one")
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
    # Kirk round 22 call 1 (on): between the check and the merge, main may move ONLY by the sheet's Publish to site export and
    # the odds bot, named path by path (no patterns). Main must still contain the checked commit, the branch's served set and
    # main's new versions of the allowed files must be clean, and a conflict is allowed only in the odds file. That conflict is
    # NOT resolved blindly: the guard reads both copies' "updated_at" and names the newer one; scripts/merge_main.sh takes the
    # newer copy and, if it is main's, rebuilds and re-verifies the embeds on it before anything is pushed.
    ALLOWED = {f"data/pending/{a.slug}_projections.json", f"data/{a.slug}_projections.json", f"data/{a.slug}_odds.json"}
    ALLOWED |= set(a.allow_path) | {p_ for p_ in __import__("os").environ.get("GUARD_ALLOW_PATHS", "").split() if p_}
    ODDS = f"data/{a.slug}_odds.json"
    if a.allow_publish_and_bot and git("merge-base", exp, cur, check=False) == exp:
        chg_ = [l.split("\t")[-1] for l in git("diff", "--name-status", exp, cur, check=False).splitlines()]
        mt_ = subprocess.run(["git", "-C", str(REPO), "merge-tree", "--write-tree", "--name-only", cur, "HEAD"], capture_output=True, text=True)
        conf_ = [l for l in mt_.stdout.split("\n\n")[0].splitlines()[1:] if l.strip()] if mt_.returncode == 1 else []
        # Kirk round 22 C: an allowed path is not proof of a data-only change. Main's new version of each allowed file must pass
        # every blocking public-scan pattern (secrets, emails, sheet internals, offshore names, ...) and keep the key layout of
        # the checked commit's version (no new or dropped fields; list positions collapsed, the odds file's book names ignored).
        import json as _j
        def keys_(o, pre="", odds=False):
            out = set()
            if isinstance(o, dict):
                for k, v in o.items():
                    k_ = "*" if odds and pre.endswith(".books") else k
                    out.add(pre + "." + k_); out |= keys_(v, pre + "." + k_, odds)
            elif isinstance(o, list):
                for v in o: out |= keys_(v, pre + "[]", odds)
            return out
        main_hits_ = {}
        for f in chg_:
            txt_ = git("show", f"{cur}:{f}", check=False)
            h_ = sorted(c for c, rx in scan_public.PAT.items() if c not in scan_public.REPORT_ONLY and rx.search(txt_)) if hasattr(scan_public, "REPORT_ONLY") else sorted(c for c, rx in scan_public.PAT.items() if rx.search(txt_))
            try:
                old_ = git("show", f"{exp}:{f}", check=False)
                ko_, kn_ = keys_(_j.loads(old_), odds=f == ODDS) if old_ else None, keys_(_j.loads(txt_), odds=f == ODDS)
                if ko_ is not None and ko_ != kn_: h_.append(f"key layout changed: +{sorted(kn_ - ko_)[:4]} -{sorted(ko_ - kn_)[:4]}")
            except ValueError: h_.append("not valid JSON")
            if h_: main_hits_[f] = h_
        newer_ = ""
        if conf_ == [ODDS]:
            import json as _j
            tm_ = _j.loads(git("show", f"{cur}:{ODDS}")).get("updated_at"); tb_ = _j.loads(git("show", f"HEAD:{ODDS}")).get("updated_at")
            newer_ = "main" if (tm_ and tb_ and tm_ > tb_) else "branch" if (tm_ and tb_ and tb_ > tm_) else ""
            newer_ = newer_ and f" odds file: main {tm_}, branch {tb_} -> take {newer_.upper()}'s copy" + (" and rebuild the embeds on it" if newer_ == "main" else "") + "."
        if chg_ and set(chg_) <= ALLOWED and mt_.returncode in (0, 1) and conf_ in ([], [ODDS]) and (not conf_ or newer_) and not main_hits_:
            n_, hits_ = served_scan("HEAD")
            if not hits_:
                print(f"MAIN GUARD: {a.ref} is {cur[:8]}; since {exp[:8]} main changed only {chg_} (allowlist: export, odds bot). "
                      f"Conflicts: {conf_ or 'none'}.{newer_} Branch served set {n_} files, 0 offshore hits; main's new versions pass the full scan and keep their key layout. "
                      f"OK as a --no-ff merge via scripts/merge_main.sh (not a fast-forward).")
                return
        print(f"  (allow-publish-and-bot: not accepted; changed {chg_[:8]}, conflicts {conf_[:8]}, newer copy {'known' if newer_ else 'UNKNOWN' if conf_ else 'n/a'}, problems in main's new files {main_hits_})")
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
