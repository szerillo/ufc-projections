#!/usr/bin/env python3
"""Check a projections file against the frozen fight-embed data contract (contracts/fight_embed_v1.json).

    python3 -I scripts/contract_check.py data/<slug>_projections.json [contracts/fight_embed_v1.json]

RED (exit 1) if a required field is missing, a field has the wrong unit/type, or a fight carries a top-level key the
contract does not name (so a renamed field cannot slip through). Exit 0 = the file matches the contract.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KNOWN_EXTRA = {"publish", "tab", "row", "calc_row", "method_inputs", "price_source", "markov_dec"}   # internal, not for display


def get(d, path):
    for k in path.split("."):
        if not isinstance(d, dict) or k not in d:
            return None, False
        d = d[k]
    return d, True


def ok_unit(unit: str, v) -> bool:
    num = isinstance(v, (int, float)) and not isinstance(v, bool)
    if unit in ("prob", "share"): return num and 0 <= v <= 1
    if unit == "pts": return num and -1 <= v <= 1
    if unit == "american": return isinstance(v, int) or (num and float(v).is_integer() and abs(v) >= 100)
    if unit == "time": return isinstance(v, str) and len(v) >= 16 and v[4] == "-" and "T" in v
    if unit == "string": return isinstance(v, str)
    return True


def main() -> int:
    doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    C = json.loads(Path(sys.argv[2] if len(sys.argv) > 2 else REPO / "contracts" / "fight_embed_v1.json").read_text(encoding="utf-8"))
    bad, n = [], 0
    for path, spec in C["doc_fields"].items():
        v, there = get(doc, path); n += 1
        if spec["required"] and not there: bad.append(f"doc: {path} missing")
        elif there and spec["type"] in ("time", "string") and not ok_unit(spec["type"], v): bad.append(f"doc: {path} = {v!r} is not {spec['type']}")
    tops = {k.split(".")[0] for k in C["fight_fields"]}
    for f in doc.get("fights") or []:
        tag = f"{f.get('fav')} vs {f.get('dog')}"
        for path, spec in C["fight_fields"].items():
            paths = [path.replace("dec|ko|sub", k) for k in ("dec", "ko", "sub")] if "dec|ko|sub" in path else [path]
            for p in paths:
                v, there = get(f, p); n += 1
                if spec["required"] and (not there or v is None): bad.append(f"{tag}: {p} missing (required)")
                elif there and v is not None and spec["type"] in ("prob", "share", "pts", "american", "time", "string") and not ok_unit(spec["type"], v):
                    bad.append(f"{tag}: {p} = {v!r} is not {spec['type']}")
        for k in f:
            if k not in tops and k not in KNOWN_EXTRA:
                bad.append(f"{tag}: field '{k}' is not in the contract (renamed or new? add it in a new contract version)")
    print(f"Contract v{C['version']}: {n} field checks, {len(bad)} problems")
    for x in bad[:30]: print("  -", x)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
