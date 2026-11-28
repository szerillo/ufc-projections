#!/usr/bin/env python3
"""Odds-feed input guard for an upcoming card (read-only; never edits the feed, the overrides or the event file).

Checks the odds bot's data/<slug>_odds.json against the official bout list before anything is priced off it:
  STALE    updated_at must parse with a time zone (odds_newer._ts), may not be in the future (5 min slack), and may not
           be older than --max-age-h (default 4 h, the fight-week freshness threshold used by check_price_freshness.py).
  MISSING  every official bout needs exactly one feed fight, with a consensus moneyline price on BOTH fighters.
  EXTRA    a feed fight on no official bout is a FAIL (the BettingPros feed keeps cancelled bouts), unless
           data/card_overrides.json lists it under "cancel" for this slug; then it is reported as dropped, not failed.
  SURNAME  every moneyline label must match exactly one fighter on the card by full name (card_overrides.same), and that
           fighter must be in the bout the label sits in. A surname-only label, a label that fits two card fighters, or
           a price that sits under the wrong bout (same-surname mix-up, e.g. Mairon Santos / Gabriel Santos) FAILS.

  python3 -I scripts/odds_feed_guard.py --odds data/<slug>_odds.json --official data/official/<date>.txt --slug <slug>
          [--allow-draft] [--overrides data/card_overrides.json] [--max-age-h 4] [--now ISO] [--status out.json]
          [--override "<reason>"] [--override-log audits/odds_guard/overrides.log]
Exit 0 = clean, 1 = a FAIL, 2 = could not read an input.
Override (Sean approved Nov 27, option A: a bad feed blocks the Friday refresh unless overridden): --override with a non-empty
reason turns a FAIL into exit 0, prints OVERRIDDEN with every failure, and appends one JSON line (time, slug, reason, failures)
to the override log. It never overrides an unreadable input (exit 2) or a DRAFT list without --allow-draft. A .DRAFT.txt list is refused unless --allow-draft (then every
line of output says DRAFT)."""
import argparse, datetime as dt, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from card_overrides import same, bout_is   # noqa: E402
from odds_newer import _ts                  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def official_bouts(path):
    out = []
    for l in open(path, encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#") and " vs " in l:
            out.append(tuple(x.strip() for x in l.split(" vs ", 1)))
    return out


def consensus(sel):
    return ((sel.get("books") or {}).get("consensus") or {}).get("cost")


def check(odds, bouts, slug, overrides, now, max_age_h):
    fails, info = [], []
    # STALE
    try:
        t = _ts(str(odds.get("updated_at")))
        age = (now - t).total_seconds() / 3600
        if age < -5 / 60: fails.append(f"STALE: updated_at {odds['updated_at']} is in the future ({-age:.2f} h ahead)")
        elif age > max_age_h: fails.append(f"STALE: updated_at {odds['updated_at']} is {age:.1f} h old (limit {max_age_h:g} h)")
        else: info.append(f"updated_at {odds['updated_at']} ({age:.1f} h old)")
    except Exception as ex:
        fails.append(f"STALE: updated_at unreadable ({ex})")
    cancel = (overrides.get(slug) or {}).get("cancel", []) if overrides else []
    fights = [f for f in odds.get("fights") or [] if isinstance(f, dict)]
    card = [n for b in bouts for n in b]
    # map each feed fight to official bouts
    used = {}
    for f in fights:
        a, b = (f.get("fighter_a") or {}).get("name", ""), (f.get("fighter_b") or {}).get("name", "")
        hit = [i for i, (x, y) in enumerate(bouts) if bout_is(a, b, x, y)]
        if len(hit) == 1:
            used.setdefault(hit[0], []).append(f)
        elif len(hit) > 1:
            fails.append(f"SURNAME: feed fight {a} vs {b} fits {len(hit)} official bouts")
        elif any(bout_is(a, b, x, y) for x, y in cancel):
            info.append(f"dropped by card_overrides cancel: {a} vs {b}")
        else:
            fails.append(f"EXTRA: feed fight {a} vs {b} is on no official bout (cancelled or replaced? add it to card_overrides)")
    for i, (x, y) in enumerate(bouts):
        fs = used.get(i, [])
        if not fs:
            fails.append(f"MISSING: {x} vs {y} has no feed fight"); continue
        if len(fs) > 1:
            fails.append(f"MISSING: {x} vs {y} has {len(fs)} feed fights (duplicate)"); continue
        ml = [s for s in ((fs[0].get("markets") or {}).get("moneyline") or []) if isinstance(s, dict)]
        for side in (x, y):
            sel = [s for s in ml if same(s.get("label", ""), side)]
            if not sel or consensus(sel[0]) is None:
                fails.append(f"MISSING: no consensus moneyline price for {side} ({x} vs {y})")
    # SURNAME: each label must fit exactly one card fighter, and that fighter must belong to the label's own bout
    for f in fights:
        a, b = (f.get("fighter_a") or {}).get("name", ""), (f.get("fighter_b") or {}).get("name", "")
        for s in ((f.get("markets") or {}).get("moneyline") or []):
            if not isinstance(s, dict): continue
            lab = s.get("label", "")
            fits = [n for n in card if same(lab, n)]
            if len(lab.split()) < 2 and lab.strip():
                fails.append(f"SURNAME: label '{lab}' in {a} vs {b} is a single name; cannot tell same-surname fighters apart")
            elif len(fits) > 1:
                fails.append(f"SURNAME: label '{lab}' in {a} vs {b} fits {len(fits)} card fighters ({', '.join(fits)})")
            elif len(fits) == 1 and not (same(fits[0], a) or same(fits[0], b)):
                fails.append(f"SURNAME: price for '{lab}' sits under {a} vs {b}, but {fits[0]} is in another bout")
    return fails, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--odds", required=True); ap.add_argument("--official", required=True); ap.add_argument("--slug", required=True)
    ap.add_argument("--allow-draft", action="store_true"); ap.add_argument("--overrides", default=str(REPO / "data" / "card_overrides.json"))
    ap.add_argument("--max-age-h", type=float, default=4.0); ap.add_argument("--now"); ap.add_argument("--status")
    ap.add_argument("--override", default="", help="reason; lets a failing feed through and logs it")
    ap.add_argument("--override-log", default=str(REPO / "audits" / "odds_guard" / "overrides.log"))
    a = ap.parse_args()
    draft = a.official.endswith(".DRAFT.txt")
    if draft and not a.allow_draft:
        print("REFUSED: the official list is a DRAFT; pass --allow-draft for a draft-labelled check"); sys.exit(2)
    try:
        odds = json.load(open(a.odds)); bouts = official_bouts(a.official)
        ov = json.load(open(a.overrides)) if a.overrides and Path(a.overrides).exists() else {}
    except Exception as ex:
        print(f"ERROR: could not read an input: {ex}"); sys.exit(2)
    now = _ts(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    fails, info = check(odds, bouts, a.slug, ov, now, a.max_age_h)
    tag = "DRAFT " if draft else ""
    for i in info: print(f"{tag}info: {i}")
    for f in fails: print(f"{tag}FAIL {f}")
    reason = a.override.strip()
    over = bool(fails and reason)
    verdict = "ODDS FEED GUARD PASS" if not fails else (f"ODDS FEED GUARD OVERRIDDEN ({len(fails)} failure(s) let through: {reason})" if over else f"ODDS FEED GUARD FAIL ({len(fails)})")
    print(f"{tag}{verdict}: {len(bouts)} official bouts, {len(odds.get('fights') or [])} feed fights")
    if over:
        Path(a.override_log).parent.mkdir(parents=True, exist_ok=True)
        with open(a.override_log, "a") as fh:
            fh.write(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "slug": a.slug, "odds": a.odds,
                                 "official": a.official, "reason": reason, "fails": fails}) + "\n")
        print(f"{tag}override logged to {a.override_log}")
    elif not fails and reason:
        print(f"{tag}note: override reason given but nothing failed; not logged")
    if a.status:
        json.dump({"draft": draft, "ok": not fails, "overridden": over, "override_reason": reason if over else None, "fails": fails,
                   "info": info, "checked_at": now.isoformat()}, open(a.status, "w"), indent=1)
    sys.exit(1 if fails and not over else 0)


if __name__ == "__main__":
    main()
