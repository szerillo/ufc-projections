"""One place for how a fight result maps to graded outcomes (audit, props tests, Markov grading).

Result dicts follow the site event files: {"kind": "win" | "draw" | "nc", "winner": "a" | "b",
"method": "...", "round": n}. UFCStats files overturned results as NC.

gtd(result)    -> 1 went to the scorecards (unanimous, split, majority, any draw)
                  0 finished inside the distance (KO/TKO, submission, doctor or corner stoppage, DQ)
                  None no contest or no result: excluded
a_won(result)  -> 1 / 0 for fighter A; None for draws and no contests (excluded from win grading)
"""

DEC_WORDS = ("decision", "dec")


def _is_decision_method(method: str) -> bool:
    m = (method or "").lower()
    return any(w in m for w in DEC_WORDS)


def gtd(result):
    if not result:
        return None
    kind = result.get("kind")
    if kind == "nc":
        return None
    if kind == "draw":
        return 1          # a draw is reached on the scorecards (BFO "goes to decision" pays)
    if kind == "win":
        return 1 if _is_decision_method(result.get("method")) else 0
    return None


def a_won(result, flip=False):
    if not result or result.get("kind") != "win":
        return None
    won = result.get("winner") == "a"
    return int(won != flip)
