#!/usr/bin/env python3
"""One fighter-name rule for the card pages: odds-feed matching at build time, and (as NAME_MATCH_JS) the page's
live-odds overlay and its projections matcher. Replaces one-off aliases (the odds feed's "Charlie Radke" for Charles
Radtke broke UFC 334's prelim panels on Nov 11).

Two tiers and a bout-level gate. The gate was added Nov 11 after a pairwise run over all 4,628 UFCStats fighters
found 18 pairs of different people that the first version merged (Chris Duncan / Christian Leroy Duncan,
Sangwook / SangWon Kim, Shane / Shanna Young, ...):

  strict  the same name: identical tokens, or the same letters joined ("Alateng Heili" = "Alatengheili") or reordered
          ("Wang Cong" = "Cong Wang"). Accents, case and punctuation never matter. Jr/Sr/II/III do matter here.
  loose   strict, or the same after dropping Jr/Sr/II/III, or: the same number of tokens, equal middle tokens,
          a surname equal or (both 5+ letters) one edit apart (a swap of two neighbouring letters is one edit), and
          first names that are equal, a 3+ letter prefix (Josh / Joshua), or a listed nickname pair (Charlie / Charles,
          Mike / Michael). A shared-prefix rule (first 4 letters) was dropped: it merged Sangwook / SangWon Kim.
  bout    two bouts are the same when one fighter matches strictly and the other at least loosely, in either order.
          A loose match never stands on its own: a misspelling is trusted only when the opponent confirms the bout.

Looking one name up in a list (best_match): the strict match, else the only loose match; two loose candidates mean
no match. Tests: scripts/test_fighter_names.py (the Python and the JS copy on the same fixture).
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


def raw_tokens(name: str) -> list[str]:
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return "".join(ch if "a" <= ch <= "z" else " " for ch in s).split()


def tokens(name: str) -> list[str]:
    return [t for t in raw_tokens(name) if t not in SUFFIXES]


def _same_letters(a: list[str], b: list[str]) -> bool:
    return bool(a) and bool(b) and (a == b or "".join(a) == "".join(b) or sorted(a) == sorted(b))


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
    return NICKNAMES.get(a, a) == NICKNAMES.get(b, b)


def strict_match(x: str, y: str) -> bool:
    return _same_letters(raw_tokens(x), raw_tokens(y))


def name_match(x: str, y: str) -> bool:
    """Loose match. Trust it only inside a bout the other fighter confirms (bout_slots), or through best_match."""
    if strict_match(x, y):
        return True
    a, b = tokens(x), tokens(y)
    if _same_letters(a, b):
        return True
    if len(a) < 2 or len(a) != len(b) or a[1:-1] != b[1:-1]:
        return False
    la, lb = a[-1], b[-1]
    surname_ok = la == lb or (min(len(la), len(lb)) >= 5 and _edit1(la, lb))
    return surname_ok and _first_ok(a[0], b[0])


def bout_slots(a1: str, b1: str, a2: str, b2: str) -> str | None:
    """'same' if bout (a1, b1) is bout (a2, b2) in that order, 'swap' if reversed, else None."""
    S, L = strict_match, name_match
    if (S(a1, a2) and L(b1, b2)) or (L(a1, a2) and S(b1, b2)):
        return "same"
    if (S(a1, b2) and L(b1, a2)) or (L(a1, b2) and S(b1, a2)):
        return "swap"
    return None


def best_match(name: str, candidates: list[str]) -> str | None:
    for c in candidates:
        if strict_match(name, c):
            return c
    loose = [c for c in candidates if name_match(name, c)]
    return loose[0] if len(loose) == 1 else None


# The same rule in JavaScript, injected into each card page by scripts/build_card_page.py.
NAME_MATCH_JS = r"""
// ============== FIGHTER NAME RULE (scripts/fighter_names.py; tested by scripts/test_fighter_names.py) ==============
const NAME_NICKS = %NICKS%;
const NAME_SUFFIX_SET = new Set(["jr", "sr", "ii", "iii", "iv"]);
function nameRawTokens(s) {
  return String(s == null ? "" : s).normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z]/g, " ").split(/\s+/).filter(Boolean);
}
function nameTokensRule(s) { return nameRawTokens(s).filter(t => !NAME_SUFFIX_SET.has(t)); }
function nameSameLetters(a, b) {
  return a.length > 0 && b.length > 0 && (a.join(" ") === b.join(" ") || a.join("") === b.join("") || [...a].sort().join(" ") === [...b].sort().join(" "));
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
  return (NAME_NICKS[a] || a) === (NAME_NICKS[b] || b);
}
function fighterStrictMatch(x, y) { return nameSameLetters(nameRawTokens(x), nameRawTokens(y)); }
function fighterNameMatch(x, y) {  // loose: trust it only inside a bout the other fighter confirms
  if (fighterStrictMatch(x, y)) return true;
  const a = nameTokensRule(x), b = nameTokensRule(y);
  if (nameSameLetters(a, b)) return true;
  if (a.length < 2 || a.length !== b.length || a.slice(1, -1).join(" ") !== b.slice(1, -1).join(" ")) return false;
  const la = a[a.length - 1], lb = b[b.length - 1];
  const surnameOk = la === lb || (Math.min(la.length, lb.length) >= 5 && nameEdit1(la, lb));
  return surnameOk && nameFirstOk(a[0], b[0]);
}
function fighterBoutSlots(a1, b1, a2, b2) {
  const S = fighterStrictMatch, L = fighterNameMatch;
  if ((S(a1, a2) && L(b1, b2)) || (L(a1, a2) && S(b1, b2))) return "same";
  if ((S(a1, b2) && L(b1, a2)) || (L(a1, b2) && S(b1, a2))) return "swap";
  return null;
}
""".replace("%NICKS%", "{" + ", ".join(f'"{k}": "{v}"' for k, v in sorted(NICKNAMES.items())) + "}")
