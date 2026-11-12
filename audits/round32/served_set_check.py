"""Kirk round 32 A: round-18 served-set check redone on the real merge result (origin/main + go-live-334, odds file = the newer copy)."""
import subprocess, sys, re
sys.path.insert(0, "/tmp/e5/scripts"); import main_guard as G
git = lambda *a: subprocess.run(["git", "-C", "/tmp/e5", *a], capture_output=True, text=True).stdout
main = git("rev-parse", "origin/main").strip(); head = git("rev-parse", "HEAD").strip()
mt = subprocess.run(["git", "-C", "/tmp/e5", "merge-tree", "--write-tree", "-X", "theirs", main, head], capture_output=True, text=True)
tree = mt.stdout.split()[0]
n, hits = G.served_scan(tree)
mn, mhits = G.served_scan(main)
ls = lambda t: set(l.split("\t", 1)[1] for l in git("ls-tree", "-r", t).splitlines())
Tm, Th, Tt = ls(main), ls(head), ls(tree)
served = lambda S: {f for f in S if not any(p.startswith(("_", ".")) for p in f.split("/"))}
over = [f for f in mhits if f in Tt and git("rev-parse", f"{tree}:{f}") != git("rev-parse", f"{main}:{f}")]
orph = sorted(f for f in served(Tt) if f not in Th)
print(f"merge tree {tree[:8]} (origin/main {main[:8]} + HEAD {head[:8]}, conflicts to HEAD's copy; exit {mt.returncode})")
print(f"served files: {n}; non-code served files naming an offshore book: {len(hits)} {hits}")
print(f"main's served files with offshore names: {len(mhits)}; overwritten by the merge: {len(over)}/{len(mhits)}; still present unchanged: {[f for f in mhits if f not in over]}")
print(f"orphans (served in the merge result, not in the branch): {len(orph)} {orph[:10]}")
