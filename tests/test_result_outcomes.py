import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from result_outcomes import gtd, a_won  # noqa: E402

CASES = [
    # (result, gtd, a_won)
    ({"kind": "win", "winner": "a", "method": "Decision - Unanimous"}, 1, 1),
    ({"kind": "win", "winner": "b", "method": "Decision - Split"}, 1, 0),
    ({"kind": "win", "winner": "a", "method": "Decision - Majority"}, 1, 1),
    ({"kind": "draw", "method": "Decision - Majority"}, 1, None),     # Kareckaite-Gatto, Oct 10 2026
    ({"kind": "draw", "method": "Decision - Split"}, 1, None),
    ({"kind": "draw", "method": "Decision - Unanimous"}, 1, None),
    ({"kind": "nc", "method": "Overturned"}, None, None),
    ({"kind": "nc", "method": "Could Not Continue"}, None, None),
    ({"kind": "win", "winner": "a", "method": "KO/TKO"}, 0, 1),
    ({"kind": "win", "winner": "b", "method": "Submission"}, 0, 0),
    ({"kind": "win", "winner": "a", "method": "TKO - Doctor's Stoppage"}, 0, 1),
    ({"kind": "win", "winner": "b", "method": "DQ"}, 0, 0),
    (None, None, None),
]


def test_cases():
    for res, g, w in CASES:
        assert gtd(res) == g, (res, gtd(res), g)
        assert a_won(res) == w, (res, a_won(res), w)


def test_flip():
    assert a_won({"kind": "win", "winner": "a", "method": "KO/TKO"}, flip=True) == 0


if __name__ == "__main__":
    test_cases(); test_flip(); print("ok", len(CASES) + 1, "checks")
