#!/usr/bin/env python3
"""One fighter-name rule for the card pages: odds-feed matching at build time, and (as NAME_MATCH_JS) the page's
live-odds overlay and its projections matcher. Replaces one-off aliases (the odds feed's "Charlie Radke" for Charles
Radtke broke UFC 334's prelim panels on Nov 11) with a rule that also covers the next misspelling.

Two names match when, after normalising (accents, case, punctuation, Jr/Sr/II/III dropped):
  1. the letters are the same with the tokens joined or in any order ("Alateng Heili" = "Alatengheili"), or
  2. both have at least two tokens, the surnames are equal or (both 5+ letters) one edit apart (a swap of two
     neighbouring letters counts as one edit), and the first names
     are equal, or one is a 3+ letter prefix of the other (Josh / Joshua), or they share their first 4 letters
     (Charlie / Charles), or they are a listed nickname pair (Mike / Michael).
It still rejects a different fighter with the same surname: Josh vs Jake Hokit, Yana vs Luana Santos.
Tests: scripts/test_fighter_names.py (runs the Python and the JS copy on the same fixture).
"""
from __future__ import annotations

import unicodedata

NICKNAMES = {  # nickname -> formal first name; both directions are checked
    "mike": "michael", "mick": "michael", "tom": "thomas", "tommy": "thomas", "bill": "william", "will": "william",
    "bob": "robert", "rob": "robert", "bobby": "robert", "jim": "james", "jimmy": "james", "joe": "joseph",
    "dan": "daniel", "danny": "daniel", "tony": "anthony", "chuck": "charles", "charlie": "charles",
    "steve": "stephen", "ed": "edward", "eddie": "edward", "rick": "richard", "dick": "richard", "kate": "katherine",
    "liz": "elizabeth", "beth": "elizabeth", "pete": "peter", "andy": "andrew", "drew": "andrew", "manny": "manuel",
    "alex": "alexander", "sasha": "alexander", "zach": "zachary", "zack": "zachary", "timmy": "timothy", "tim": "timothy",
}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def tokens(name: str) -> list[str]:
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = "".join(ch if "a" <= ch <= "z" else " " for ch in s)
    return [t for t in s.split() if t not in SUFFIXES]


def _edit1(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    if len(a) > len(b):
        a, b = b, a
    return any(a == b[:i] + b[i + 1:] for i in range(len(b)))


def _first_ok(a: str, b: str) -> bool:
    if a == b:
        return True
    if min(len(a), len(b)) >= 3 and (a.startswith(b) or b.startswith(a)):
        return True
    if min(len(a), len(b)) >= 4 and a[:4] == b[:4]:
        return True
    fa, fb = NICKNAMES.get(a, a), NICKNAMES.get(b, b)
    return fa == fb


def name_match(x: str, y: str) -> bool:
    a, b = tokens(x), tokens(y)
    if not a or not b:
        return False
    if "".join(a) == "".join(b) or sorted(a) == sorted(b):
        return True
    if len(a) < 2 or len(b) < 2:
        return False
    la, lb = a[-1], b[-1]
    surname_ok = la == lb or (min(len(la), len(lb)) >= 5 and _edit1(la, lb))
    return surname_ok and _first_ok(a[0], b[0])


# The same rule in JavaScript, injected into each card page by scripts/build_card_page.py.
NAME_MATCH_JS = r"""
// ============== FIGHTER NAME RULE (scripts/fighter_names.py; tested by scripts/test_fighter_names.py) ==============
const NAME_NICKS = %NICKS%;
const NAME_SUFFIX_SET = new Set(["jr", "sr", "ii", "iii", "iv"]);
function nameTokensRule(s) {
  return (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z]/g, " ").split(/\s+/).filter(t => t && !NAME_SUFFIX_SET.has(t));
}
function nameEdit1(a, b) {
  if (a === b) return true;
  if (Math.abs(a.length - b.length) > 1) return false;
  if (a.length === b.length) {
    const d = []; for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) d.push(i);
    return d.length === 1 || (d.length === 2 && d[1] === d[0] + 1 && a[d[0]] === b[d[1]] && a[d[1]] === b[d[0]]);
  }
  if (a.length > b.length) [a, b] = [b, a];
  for (let i = 0; i < b.length; i++) if (a === b.slice(0, i) + b.slice(i + 1)) return true;
  return false;
}
function nameFirstOk(a, b) {
  if (a === b) return true;
  if (Math.min(a.length, b.length) >= 3 && (a.startsWith(b) || b.startsWith(a))) return true;
  if (Math.min(a.length, b.length) >= 4 && a.slice(0, 4) === b.slice(0, 4)) return true;
  return (NAME_NICKS[a] || a) === (NAME_NICKS[b] || b);
}
function fighterNameMatch(x, y) {
  const a = nameTokensRule(x), b = nameTokensRule(y);
  if (!a.length || !b.length) return false;
  if (a.join("") === b.join("") || [...a].sort().join(" ") === [...b].sort().join(" ")) return true;
  if (a.length < 2 || b.length < 2) return false;
  const la = a[a.length - 1], lb = b[b.length - 1];
  const surnameOk = la === lb || (Math.min(la.length, lb.length) >= 5 && nameEdit1(la, lb));
  return surnameOk && nameFirstOk(a[0], b[0]);
}
""".replace("%NICKS%", "{" + ", ".join(f'"{k}": "{v}"' for k, v in sorted(NICKNAMES.items())) + "}")
