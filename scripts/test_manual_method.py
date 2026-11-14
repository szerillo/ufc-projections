#!/usr/bin/env python3
"""MM-1 plants (Kirk round 36, pre-registered in audits/round36/MM1_PREREG.md). Sean's typed method cells are taken as his
values; every other cell (KO when only DEC is typed, SUB, the fight GTD) must still equal the tab formula recomputed from
them within 0.0001. Fixtures: the Nov 14 06:09Z export (DEC typed on 9 fights) and the Nov 12 22:47Z export (none typed).
python3 -I scripts/test_manual_method.py   -> exit 1 on any failure"""
import copy, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); import verify_projections as V, sheet_v47 as S  # noqa: E402
NOV14 = json.loads((HERE / "fixtures/ufc_334_projections_mm.json").read_text())
NOV12 = json.loads((HERE / "fixtures/ufc_334_projections_1112.json").read_text())
METH = (" dec sheet", " ko sheet", " sub sheet", "GTD sheet", "method shares")
res = []
def run(doc):
    errs = V.check(copy.deepcopy(doc), Path("ufc_334_projections.json"), odds_doc=None)
    return [e for e in errs if any(m in e for m in METH)], [(m["fighter"], tuple(m["typed"])) for m in V.MANUAL_METHOD]
def fight(doc, fav): return next(x for x in doc["fights"] if x["fav"] == fav)
def case(name, doc, want_errs, want_manual=None):
    errs, man = run(doc)
    ok = (bool(errs) == want_errs) and (want_manual is None or sorted(man) == sorted(want_manual))
    res.append(("PASS " if ok else "FAIL ") + name + f" | method errors {len(errs)}" + (f": {errs[:2]}" if errs else "") + f" | manual {len(man)}")
NOV14_MANUAL = [("Kevin Holland", ("dec",)), ("Uros Medic", ("dec",)), ("Luis Gurule", ("dec",)), ("Bilal Hasan", ("dec", "ko")),
                ("Stephen Thompson", ("dec",)), ("Terrance McKinney", ("dec",)), ("Donte Johnson", ("dec",)), ("Bia Mesquita", ("dec",)),
                ("Alatengheili", ("dec",)), ("Samuel Sanches", ("dec",))]
case("M1 Nov 14 export (Sean's typed DEC on 9 fights, DEC + KO on Hasan) -> passes, 10 manual sides recorded", NOV14, False, NOV14_MANUAL)
case("M2 Nov 12 export (nothing typed) -> passes, no manual method", NOV12, False, [])
d = copy.deepcopy(NOV14); fight(d, "Ciryl Gane")["method"]["dog"]["dec"] += 0.03
case("M3 a DEC changed on an untyped fight, KO/SUB/GTD not following -> fails", d, True)
d = copy.deepcopy(NOV14); fight(d, "Uros Medic")["method"]["dog"]["dec"] = 0.31
case("M4 Holland's typed DEC changed (0.27 -> 0.31) without KO/SUB/GTD following -> fails", d, True)
d = copy.deepcopy(NOV14); fight(d, "Bilal Hasan")["method"]["fav"]["sub"] += 0.01
case("M5 Hasan typed DEC + KO, SUB not 1 - DEC - KO -> fails", d, True)
d = copy.deepcopy(NOV14); fight(d, "Uros Medic")["gtd"] += 0.005
case("M6 GTD off by 0.5 pts on a typed fight -> fails", d, True)
d = copy.deepcopy(NOV14); f = fight(d, "Uros Medic"); mi = {**f["method_inputs"], "b41": d["params"].get("b41"), "b45": d["params"].get("b45")}
pin = {"dog": {"dec": 0.31}, "fav": {"dec": f["method"]["fav"]["dec"]}}; r = S.method_gtd(float(f["sheet"]["true_dog"]), mi, pin=pin)
f["method"]["dog"] = dict(r["dog"]); f["gtd"] = r["gtd"]
case("M7 control: Holland DEC retyped to 0.31 with the sheet's own KO/SUB/GTD following -> passes as manual", d, False,
     [m if m[0] != "Kevin Holland" else ("Kevin Holland", ("dec",)) for m in NOV14_MANUAL])
for r_ in res: print(r_)
nf = sum(r_.startswith("FAIL") for r_ in res); print(f"manual method (MM-1): {len(res) - nf}/{len(res)} as expected"); sys.exit(1 if nf else 0)
