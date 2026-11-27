"""Preflight for a Friday spread-tracker lock (spreads locks approved by Sean: track vs books, Sean judges edges, no auto-bet).
Read-only. Checks every input spread_track.py lock needs, then prints the exact lock commands. It never writes a lock row.

  python3 -I audits/forward_scoring/spread_lock_preflight.py --slug fn_adesanya_magomedov --date 2026-12-05 \
      --books books.json --cache .form_cache [--card-list data/official/2026-12-05.txt] [--allowlist PUBLIC_OK.txt]
  python3 -I audits/forward_scoring/spread_lock_preflight.py --template --card-list data/official/2026-12-05.DRAFT.txt --out books.json

Exit 0 = ready to lock; exit 1 = a blocking check failed (each failure is printed with its fix)."""
import argparse, csv, datetime as dt, glob, json, os, re, sys
sys.path.insert(0, "scripts")
import fighter_names as FN

# US-regulated books (New York first) plus the exchanges the tracker allows. Anything else is refused.
BOOKS = {"DraftKings", "FanDuel", "BetMGM", "Caesars", "BetRivers", "Fanatics", "ESPN BET", "theScore Bet", "bet365",
         "Kalshi", "Novig", "Polymarket"}
NOW = dt.datetime.now(dt.timezone.utc)
fails, warns = [], []


def bouts_from_list(path):
    out = []
    for l in open(path, encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#") and " vs " in l:
            a, b = [x.strip() for x in l.split(" vs ", 1)]; out.append((a, b))
    return out


def template(a):
    rows = []
    for x, y in bouts_from_list(a.card_list):
        for f in (x, y):
            rows.append({"fighter": f, "line": None, "price": None, "book": "DraftKings", "seen_at": None})
    json.dump(rows, open(a.out, "w"), indent=1)
    print(f"template: {len(rows)} rows ({len(rows) // 2} bouts) -> {a.out}. Fill line (e.g. -3.5 / +3.5), price (signed American) "
          "and seen_at (UTC) from the book's page; delete rows for bouts with no spread posted; add rows for other books.")


def ts(s):
    s = s.strip().replace(" ", "T")
    if s.endswith("Z"): s = s[:-1] + "+00:00"
    if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d", s): s += ":00"
    d = dt.datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def main(a):
    # 1. Sean's published export (spread_track refuses staging)
    pj = f"data/{a.slug}_projections.json"
    V = None
    if not os.path.exists(pj):
        fails.append(f"{pj} missing: Sean's publish to the site has not happened yet (lock waits for it)")
    else:
        V = json.load(open(pj))
        if V.get("staging"): fails.append(f"{pj} is a staging export; lock only on Sean's published numbers")
        print(f"[ok] export published_at {V.get('published_at')}, {len(V.get('fights', []))} fights")
    # 2. odds bot file
    oj = f"data/{a.slug}_odds.json"
    if not os.path.exists(oj):
        fails.append(f"{oj} missing: the odds bot has not pulled this card (check cards.yml on main)")
    else:
        up = json.load(open(oj)).get("updated_at")
        age = (NOW - ts(up)).total_seconds() / 3600 if up else None
        (warns if age is None or age > 6 else []).append(f"{oj} updated_at {up} ({'?' if age is None else f'{age:.1f}'} h old); no-vig fav from it feeds the margin term")
        print(f"[ok] odds file updated_at {up}")
    # 3. event file with start times; lock must precede the first bout
    evs = sorted(glob.glob(f"form/data/events/{a.date}-*.json"))
    first = None; ev = None
    if not evs:
        fails.append(f"no form/data/events/{a.date}-*.json on this checkout: the site build for the card has not run")
    else:
        ev = json.load(open(evs[0]))
        st = [ts(f["start"]) for f in ev["fights"] if f.get("start")]
        first = min(st) if st else ts(ev["date"] + "T14:00:00")
        if not st: warns.append("event file has no start times; spread_track falls back to 14:00 UTC card day, which may be AFTER an early prelim")
        print(f"[ok] event {evs[0]}: {len(ev['fights'])} bouts, first bout {first.isoformat()}")
        if NOW >= first: fails.append(f"first bout {first.isoformat()} has started; a lock row would be refused (and must not be forced)")
    # 4. official list agrees with the event file
    if a.card_list and ev:
        L = bouts_from_list(a.card_list)
        miss = [f"{x} vs {y}" for x, y in L if not any({FN.name_match(f["a"]["name"], x) and FN.name_match(f["b"]["name"], y),
                                                       FN.name_match(f["a"]["name"], y) and FN.name_match(f["b"]["name"], x)} & {True} for f in ev["fights"])]
        if miss: fails.append("official list bouts missing from the event file: " + "; ".join(miss))
        if a.card_list.endswith(".DRAFT.txt"): warns.append("card list is the DRAFT; the UFC.com check (Sean) has not renamed it yet")
    # 5. UFCStats cache must hold every card before this one (round-strength q for v1)
    evcsv = os.path.join(a.cache, "ufc_event_details.csv")
    if not os.path.exists(evcsv):
        fails.append(f"{evcsv} missing: download the UFCStats CSVs (build_form.py fetch or scripts/collect)")
    else:
        newest = max(dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").date() for r in csv.DictReader(open(evcsv, encoding="utf-8")))
        gap = (dt.date.fromisoformat(a.date) - newest).days
        (fails if gap > 14 else warns if gap > 8 else []).append(f"UFCStats cache newest event {newest} ({gap} days before the card): refresh it before locking")
        print(f"[ok] UFCStats cache newest event {newest}")
    # 6. books.json
    if not a.books or not os.path.exists(a.books):
        fails.append("books.json missing: pull NY-legal spread prices (DraftKings first) in Sean's Chrome, or paste them; use --template for the shape")
    else:
        B = json.load(open(a.books)); seen = set()
        for i, b in enumerate(B):
            tag = f"books[{i}] {b.get('fighter')}"
            for k in ("fighter", "line", "price", "book", "seen_at"):
                if b.get(k) in (None, ""): fails.append(f"{tag}: {k} empty")
            if b.get("book") and b["book"] not in BOOKS: fails.append(f"{tag}: book '{b['book']}' is not on the US-regulated list")
            if isinstance(b.get("line"), (int, float)) and (abs(b["line"]) * 2) % 2 != 1: fails.append(f"{tag}: line {b['line']} is not a half point")
            if isinstance(b.get("price"), (int, float)) and (not float(b["price"]).is_integer() or -100 < b["price"] < 100): fails.append(f"{tag}: price {b['price']} is not a signed American price")
            if b.get("seen_at"):
                s = ts(b["seen_at"])
                if first and s >= first: fails.append(f"{tag}: seen_at {b['seen_at']} is after the first bout")
                if (NOW - s).total_seconds() > 36 * 3600: warns.append(f"{tag}: price seen {b['seen_at']} is over 36 h old")
            if V and b.get("fighter") and not any(FN.name_match(b["fighter"], f["fav"]) or FN.name_match(b["fighter"], f["dog"]) for f in V.get("fights", [])):
                fails.append(f"{tag}: not on the published export (spelling?)")
            k = (b.get("fighter"), b.get("line"), b.get("book"))
            if k in seen: fails.append(f"{tag}: duplicate fighter/line/book")
            seen.add(k)
        print(f"[ok] books.json {len(B)} rows, books {sorted({b.get('book') for b in B})}")
    # 7. lock target allowlisted and not already locked
    out = f"analysis/spread_locks/{a.date}.jsonl"
    if a.allowlist:
        ok = {l.strip() for l in open(a.allowlist)}
        if out not in ok: fails.append(f"{out} is not on audit-locks PUBLIC_OK.txt (needs its own earlier allowlist push)")
        else: print(f"[ok] {out} is pre-allowlisted")
    if os.path.exists(out) and any(json.loads(l).get("stage") == "lock" for l in open(out) if l.strip()):
        warns.append(f"{out} already has lock rows; a second lock appends, and table/grade use the last row per bout")
    print()
    for w in warns: print("WARN:", w)
    for f in fails: print("BLOCKED:", f)
    print("\nLock commands (run Friday after Sean's publish, from an audit-locks worktree with main's data/ and form/ beside it):")
    ev_arg = evs[0] if evs else f"form/data/events/{a.date}-<card>.json"
    print(f"  python3 -I analysis/spreads_tracker/spread_track.py lock --slug {a.slug} --event {ev_arg} --books {a.books or 'books.json'} --out {out} --cache {a.cache}")
    print(f"  python3 -I analysis/spreads_tracker/spread_track.py table --locks {out}")
    print(f"  sha256sum {out}  # add the line to analysis/MANIFEST.txt, commit, push audit-locks BEFORE the first bout")
    print(f"  Saturday, before each bout: same lock command with --stage close (skips started bouts).")
    print("\nREADY" if not fails else f"\nNOT READY: {len(fails)} blocking item(s)")
    sys.exit(1 if fails else 0)


ap = argparse.ArgumentParser()
ap.add_argument("--slug"); ap.add_argument("--date"); ap.add_argument("--books"); ap.add_argument("--cache", default=".form_cache")
ap.add_argument("--card-list"); ap.add_argument("--allowlist"); ap.add_argument("--template", action="store_true"); ap.add_argument("--out")
a = ap.parse_args()
template(a) if a.template else main(a)
