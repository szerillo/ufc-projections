#!/usr/bin/env python3
"""Compare every displayed number between two builds of a card's embeds (registry text by description), Block 59k.
    python3 -I scripts/diff_embed_numbers.py OLD_DIR NEW_DIR
Prints per fight: numbers changed, added, removed, and the changed ones grouped by rule (source)."""
import json, sys, collections
from pathlib import Path
old, new = Path(sys.argv[1]), Path(sys.argv[2]); tot = collections.Counter(); by_rule = collections.Counter(); lines = []
for fp in sorted(new.glob("fight_*.registry.json")):
    N = json.load(open(fp)); op = old / fp.name
    O = json.load(open(op)) if op.exists() else {"rows": []}
    o = {r["desc"]: (r["text"], r["rule"]) for r in O["rows"]}; n = {r["desc"]: (r["text"], r["rule"]) for r in N["rows"]}
    ch = [(d, o[d][0], n[d][0], n[d][1]) for d in n if d in o and o[d][0] != n[d][0]]
    ad = [d for d in n if d not in o]; rm = [d for d in o if d not in n]
    tot["changed"] += len(ch); tot["added"] += len(ad); tot["removed"] += len(rm); tot["same"] += sum(1 for d in n if d in o and o[d][0] == n[d][0])
    for x in ch: by_rule[x[3]] += 1
    lines.append(f"{fp.stem.split('.')[0]}: {len(ch)} changed, {len(ad)} added, {len(rm)} removed" + "".join(f"\n    {d}: {a} -> {b} [{r}]" for d, a, b, r in ch[:12]) + (f"\n    ... {len(ch) - 12} more" if len(ch) > 12 else ""))
print("\n".join(lines)); print("TOTAL", dict(tot)); print("changed by source rule", dict(by_rule))
