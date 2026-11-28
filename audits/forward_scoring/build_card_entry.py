"""Build one forward-scoring card entry (cards_forward.json) from the walkout lock on audit-locks and the site's card data.
No hand-typed times: the lock time is the git commit that first added the lock file on audit-locks, and the first bout is the
earliest start found in the event file, the odds-bot feed (scheduled_utc) and cards.yml (first_fight_utc).

  python3 -I audits/forward_scoring/build_card_entry.py --date 2026-12-05 --slug fn_adesanya_magomedov \
      [--audit-ref origin/audit-locks] [--main-ref origin/main] [--cards audits/forward_scoring/cards_forward.json] \
      [--cache ~/.cache/ufc_forward_locks]

Checks (exit 1 on any, with the reason; the entry is still written for a LATE lock, marked late, so no card is dropped by choice):
  L1 the lock file exists on the audit-locks ref
  L2 it was never changed after the commit that added it
  L3 analysis/MANIFEST.txt on that ref holds its sha256 and it matches the file
  L4 the lock commit time is before the first bout (else: entry written with "late": true, and the harness will not count it)
  L5 the lock has LF line endings (as snapshot_t0.gs writes), the columns the harness reads, and one row per bout (a count
     mismatch is a warning)
The lock holds private sheet values, so it is exported to --cache (outside the repo) and the entry points there, with its
audit-locks commit and sha256 recorded. forward_score.py (frozen by the PREREG addendum) is not changed.
Run from a szerillo/ufc-projections checkout."""
import argparse, csv, datetime as dt, glob, hashlib, io, json, os, subprocess, sys

NEED = ["dog", "fav", "dog price (D)", "fav price (I)", "model Q", "T0 params"]


def git(*a, check=True):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    if check and r.returncode: raise RuntimeError(r.stderr.strip())
    return r.stdout


def gitb(*a):
    return subprocess.run(["git", *a], capture_output=True, check=True).stdout


def ts(s):
    s = str(s).strip().replace(" ", "T")
    if s.endswith("Z"): s = s[:-1] + "+00:00"
    d = dt.datetime.fromisoformat(s)
    return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)


def iso(d): return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def first_bout(main, date, slug):
    """Earliest known start across the three sources; returns (utc, source, event_path)."""
    found, evp = [], None
    evs = [p for p in git("ls-tree", "--name-only", main, "form/data/events/").splitlines() if os.path.basename(p).startswith(date)]
    if evs:
        evp = evs[0]; ev = json.loads(git("show", f"{main}:{evp}"))
        found += [(ts(f["start"]), "event file") for f in ev["fights"] if f.get("start")]
    try:
        feed = json.loads(git("show", f"{main}:data/{slug}_odds.json"))
        found += [(ts(f["scheduled_utc"]), "odds feed") for f in feed.get("fights") or [] if f.get("scheduled_utc")]
    except RuntimeError:
        pass
    try:
        y = git("show", f"{main}:cards.yml"); blk = y.split(f'slug: "{slug}"', 1)
        if len(blk) == 2:
            for l in blk[1].splitlines()[:6]:
                if "first_fight_utc" in l: found.append((ts(l.split(":", 1)[1].strip().strip('"')), "cards.yml")); break
    except RuntimeError:
        pass
    if not found: return None, None, evp
    t, src = min(found); return t, src, evp


def build(a):
    fails, warns = [], []
    lp = f"analysis/snap_locks/{a.date}.csv"
    # L1
    if git("ls-tree", "--name-only", a.audit_ref, lp).strip() != lp:
        print(f"L1 FAIL: no walkout lock {lp} on {a.audit_ref} (T0 must have fired and its CSV been pushed before the card)"); return 1
    hist = [l.split(" ", 1) for l in git("log", "--format=%H %cI", a.audit_ref, "--", lp).splitlines()]
    add_h, add_t = hist[-1]
    # L2
    if len(hist) > 1:
        fails.append(f"L2 FAIL: {lp} changed after it was added ({len(hist) - 1} later commit(s), newest {hist[0][0][:8]})")
    raw = gitb("show", f"{add_h}:{lp}"); sha = hashlib.sha256(raw).hexdigest()
    # L3
    try:
        man = git("show", f"{a.audit_ref}:analysis/MANIFEST.txt")
        mline = [l for l in man.splitlines() if l.strip().endswith(lp) or l.split()[-1:] == [lp]]
        if not mline: fails.append(f"L3 FAIL: analysis/MANIFEST.txt has no line for {lp}")
        elif mline[0].split()[0] != sha: fails.append(f"L3 FAIL: MANIFEST sha {mline[0].split()[0][:16]} != file {sha[:16]}")
    except RuntimeError:
        fails.append("L3 FAIL: no analysis/MANIFEST.txt on the audit ref")
    # L4
    fb, fsrc, evp = first_bout(a.main_ref, a.date, a.slug)
    lock_t = ts(add_t); late = None
    if fb is None:
        fails.append("L4 FAIL: no start time for the card in the event file, odds feed or cards.yml")
    else:
        late = not lock_t < fb
        if late: fails.append(f"L4 FAIL (LATE LOCK): lock committed {iso(lock_t)}, first bout {iso(fb)} ({fsrc}); the card will not count")
    if evp is None: fails.append(f"no event file for {a.date} on {a.main_ref}")
    # L5
    if b"\r\n" in raw:
        fails.append("L5 FAIL: the lock has CRLF line endings (snapshot_t0.gs writes LF; a converted copy would misparse and its sha would not match)")
    snap = raw.decode("utf-8").split("\n#PropSnap\n")[0]
    rows = list(csv.DictReader(io.StringIO(snap)))
    miss = [c for c in NEED if rows and c not in rows[0]]
    if not rows: fails.append("L5 FAIL: the lock has no rows")
    elif miss: fails.append(f"L5 FAIL: lock is missing columns {miss}")
    if evp:
        nb = len(json.loads(git("show", f"{a.main_ref}:{evp}"))["fights"])
        if rows and len(rows) != nb: warns.append(f"L5 warn: lock has {len(rows)} rows, event file {nb} bouts")
    # export + entry (written unless the lock itself is unusable)
    usable = not any(f.startswith(("L2", "L3", "L5")) for f in fails) and fb is not None and evp is not None
    if usable:
        os.makedirs(os.path.expanduser(a.cache), exist_ok=True)
        lpath = os.path.join(os.path.expanduser(a.cache), f"{a.date}.csv"); open(lpath, "wb").write(raw)
        entry = {"date": a.date, "lock": lpath, "event": evp, "lock_commit_utc": iso(lock_t), "first_bout_utc": iso(fb), "test": False,
                 "late": bool(late), "first_bout_source": fsrc, "lock_git": f"{a.audit_ref}:{lp}@{add_h[:12]}", "lock_sha256": sha,
                 "built_at": iso(dt.datetime.now(dt.timezone.utc))}
        C = json.load(open(a.cards)) if os.path.exists(a.cards) else []
        C = [c for c in C if c.get("date") != a.date and "<" not in str(c.get("event", ""))] + [entry]
        C.sort(key=lambda c: c["date"]); json.dump(C, open(a.cards, "w"), indent=1)
        print(f"entry {'written' if not late else 'written, marked LATE'}: {a.date} lock {add_h[:8]} at {iso(lock_t)}, first bout {iso(fb)} ({fsrc}), "
              f"{len(rows)} rows, sha {sha[:16]} -> {a.cards}")
    for w in warns: print(w)
    for f in fails: print(f)
    print("CARD ENTRY OK" if not fails else f"CARD ENTRY NOT OK ({len(fails)})")
    return 0 if not fails else 1


ap = argparse.ArgumentParser()
ap.add_argument("--date", required=True); ap.add_argument("--slug", required=True)
ap.add_argument("--audit-ref", default="origin/audit-locks"); ap.add_argument("--main-ref", default="origin/main")
ap.add_argument("--cards", default="audits/forward_scoring/cards_forward.json"); ap.add_argument("--cache", default="~/.cache/ufc_forward_locks")
if __name__ == "__main__":
    sys.exit(build(ap.parse_args()))
