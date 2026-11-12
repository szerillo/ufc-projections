#!/usr/bin/env python3
"""Kirk round 24 C: after a push to main, prove the LIVE site serves exactly that commit, not a cached older page.

  python3 scripts/post_merge_check.py [--base https://szerillo.github.io/ufc-projections] [--ref origin/main] [--paths ...]

For every served file the commit changed (embeds, data, pages; all of them up to --max), fetch it with a unique query string
and no-cache headers and compare its sha256 with the file in the commit. Only when every file matches does it check that
_audit/locks_history.json is a 404 (a 404 seen on a stale deploy proves nothing). A stale page fails; it can't pass on
"the page contains 'Data as of'" the way an eyeball check can.
"""
import argparse, hashlib, subprocess, sys, time, urllib.request, urllib.error, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
git = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, check=True).stdout


DEADLINE = [None]   # Kirk round 25 C: one overall deadline; no fetch may outlive it (a stalled server must not hang the check)


def fetch(url):
    left = 30 if DEADLINE[0] is None else max(1.0, min(30.0, DEADLINE[0] - time.time()))
    req = urllib.request.Request(f"{url}?cb={uuid.uuid4().hex}", headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=left) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, b""
    except Exception as e: return f"no answer ({type(e).__name__})", b""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--base", default="https://szerillo.github.io/ufc-projections")
    ap.add_argument("--ref", default="origin/main"); ap.add_argument("--paths", nargs="*"); ap.add_argument("--max", type=int, default=80)
    ap.add_argument("--wait", type=int, default=0, help="keep re-checking every 30 s for up to this many seconds (edge caches ignore the query string)")
    a = ap.parse_args()
    if a.paths: paths = a.paths
    else:
        parent = git("rev-parse", f"{a.ref}^1").decode().strip()
        paths = [p for p in git("diff", "--name-only", "--diff-filter=AM", parent, a.ref).decode().split()
                 if not any(s.startswith(("_", ".")) for s in p.split("/")) and not p.endswith((".md", ".py", ".sh", ".yml", ".pyc"))][: a.max]
    t_end = time.time() + a.wait; DEADLINE[0] = t_end + 60   # the last pass may run at most 60 s past --wait
    while True:
        bad = check(a, paths)
        if not bad or time.time() >= t_end:
            if bad: print(f"  gave up after {a.wait} s of rechecks")
            break
        print(f"  {len(bad)} still differ; rechecking in 30 s"); time.sleep(30)
    report(a, paths, bad)


def check(a, paths):
    bad = []
    for p in paths:
        if DEADLINE[0] is not None and time.time() > DEADLINE[0]:
            bad.append(f"{p}: not checked (deadline reached)"); continue
        want = hashlib.sha256(git("show", f"{a.ref}:{p}")).hexdigest()
        st, body = fetch(f"{a.base}/{p}")
        got = hashlib.sha256(body).hexdigest() if st == 200 else None
        if got != want: bad.append(f"{p}: HTTP {st}, served {got and got[:12]}, commit {want[:12]}")
    return bad


def report(a, paths, bad):
    print(f"POST-MERGE: {len(paths)} served files compared with {a.ref} ({git('rev-parse', '--short', a.ref).decode().strip()}); {len(bad)} differ")
    for b in bad[:20]: print("  " + b)
    if bad: print("POST-MERGE CHECK FAIL: the site is not serving this commit yet (deploy or edge cache; query strings do not bypass it). Rerun with --wait 600."); sys.exit(1)
    st, _ = fetch(f"{a.base}/_audit/locks_history.json")
    print(f"  _audit/locks_history.json: HTTP {st}")
    if st != 404: print("POST-MERGE CHECK FAIL: the audit file is served"); sys.exit(1)
    print("POST-MERGE CHECK PASS")


if __name__ == "__main__":
    main()
