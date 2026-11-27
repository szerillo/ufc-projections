#!/usr/bin/env python3
"""Tests for the same-name fighter split in scripts/build_form.py load_ufcstats (data/fighter_disambig.json), on synthetic CSVs:
T1 two fighters named Bruno Silva with UFC bouts: the labeled one gets its own name in its bouts, the primary keeps the plain name,
   and each bio comes from its own fighter-details id (not the first tott row).
T2 a same-name fighter with NO UFC bout listed first in tott: the fighter who fought still gets his own bio (Jean Silva case).
T3 no disambiguation file: old behaviour (first tott row, _dup flag) is unchanged.
Run: python3 -I scripts/test_fighter_disambig.py (exit 0 = all pass)."""
import csv, json, os, sys, tempfile
from pathlib import Path
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import build_form as BF

U = "http://ufcstats.com/"


def w(path, hdr, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        c = csv.writer(f); c.writerow(hdr); c.writerows(rows)


def mk(dis):
    r = Path(tempfile.mkdtemp()); (r / "data").mkdir(); cache = r / "cache"; cache.mkdir()
    w(cache / "ufc_event_details.csv", ["EVENT", "URL", "DATE", "LOCATION"],
      [["E1", U + "event-details/e1", "June 06, 2026", "X"], ["E2", U + "event-details/e2", "May 01, 2024", "Y"], ["E3", U + "event-details/e3", "May 01, 2025", "Z"]])
    res = [["E1", "Bruno Silva vs. Edgar Chairez", "L/W", "Flyweight Bout", "Submission", "2", "1:00", "3 Rnd (5-5-5)", "R", "", U + "fight-details/f1"],
           ["E2", "Alex Pereira vs. Bruno Silva", "W/L", "Middleweight Bout", "KO/TKO", "1", "2:00", "3 Rnd (5-5-5)", "R", "", U + "fight-details/f2"],
           ["E3", "Jean Silva vs. Jose Delgado", "W/L", "Featherweight Bout", "KO/TKO", "1", "3:00", "3 Rnd (5-5-5)", "R", "", U + "fight-details/f3"]]
    w(cache / "ufc_fight_results.csv", ["EVENT", "BOUT", "OUTCOME", "WEIGHTCLASS", "METHOD", "ROUND", "TIME", "TIME FORMAT", "REFEREE", "DETAILS", "URL"], res)
    sh = ["EVENT", "BOUT", "ROUND", "FIGHTER", "KD", "SIG.STR.", "SIG.STR. %", "TOTAL STR.", "TD", "TD %", "SUB.ATT", "REV.", "CTRL", "HEAD", "BODY", "LEG", "DISTANCE", "CLINCH", "GROUND"]
    st = []
    for e, b, *_ in res:
        for n in b.split(" vs. "):
            st.append([e, b, "Round 1", n, "0", "10 of 20", "50%", "12 of 22", "0 of 0", "---", "0", "0", "0:10", "5 of 10", "3 of 5", "2 of 5", "8 of 16", "1 of 2", "1 of 2"])
    w(cache / "ufc_fight_stats.csv", sh, st)
    w(cache / "ufc_fighter_tott.csv", ["FIGHTER", "HEIGHT", "WEIGHT", "REACH", "STANCE", "DOB", "URL"],
      [["Bruno Silva", "5' 4\"", "125 lbs.", "65\"", "Orthodox", "Mar 16, 1990", U + "fighter-details/flw"],
       ["Bruno Silva", "6' 0\"", "185 lbs.", "74\"", "Orthodox", "Jul 13, 1989", U + "fighter-details/mw"],
       ["Jean Silva", "5' 6\"", "160 lbs.", "--", "Orthodox", "Oct 08, 1977", U + "fighter-details/old"],
       ["Jean Silva", "5' 7\"", "145 lbs.", "70\"", "Orthodox", "Dec 27, 1996", U + "fighter-details/lord"]])
    if dis:
        json.dump({"labels": {"mw": "Bruno Silva (MW)"}, "fights": {"f1": {"Bruno Silva": "flw"}, "f2": {"Bruno Silva": "mw"}, "f3": {"Jean Silva": "lord"}}},
                  open(r / "data" / "fighter_disambig.json", "w"))
    BF.REPO = r
    return BF.load_ufcstats(cache)


fails = 0
def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name); fails += not cond


ev, bio = mk(True)
f1, f2, f3 = ev["E1"]["fights"][0], ev["E2"]["fights"][0], ev["E3"]["fights"][0]
check("T1 flyweight bout keeps plain name", f1["a"] == "Bruno Silva")
check("T1 middleweight bout renamed", f2["b"] == "Bruno Silva (MW)")
check("T1 stats stay attached after rename", f2["sb"] and f2["sb"]["sl"] == 10)
check("T1 each bio from its own id", bio[BF.norm("Bruno Silva")]["url"].endswith("/flw") and bio[BF.norm("Bruno Silva (MW)")]["url"].endswith("/mw"))
check("T2 Jean Silva bio is the fighter who fought (1996)", bio[BF.norm("Jean Silva")]["dob"] == "1996-12-27")
check("T1/T2 shared names stay flagged", bio[BF.norm("Bruno Silva")].get("_dup") and bio[BF.norm("Jean Silva")].get("_dup"))
ev0, bio0 = mk(False)
check("T3 no file: both bouts keep the shared name", ev0["E2"]["fights"][0]["b"] == "Bruno Silva")
check("T3 no file: first tott row wins, flagged", bio0[BF.norm("Jean Silva")]["dob"] == "1977-10-08" and bio0[BF.norm("Jean Silva")].get("_dup"))
print(f"{8 - fails}/8 pass"); sys.exit(1 if fails else 0)
