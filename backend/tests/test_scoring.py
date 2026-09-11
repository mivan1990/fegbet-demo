"""Faza 3: motorul de punctaj — functii pure, fara DB (PLAN_SONNET.md sectiunile 6 si 10).

TDD: aceste teste sunt scrise INAINTE de implementare. Minim 30 de cazuri.
"""
from __future__ import annotations

import pytest

from services.scoring import (
    ScoringError,
    Selection,
    grade_selection,
    market_available,
    perfect_bonus,
    points_for,
    resolve_btts,
    resolve_qualify,
    resolve_scorer,
    resolve_total_goals,
    resolve_winner,
)

# Setari default (ca in seed.py). Testele care verifica suprascrierea trec propriul dict.
DEFAULTS: dict[str, str] = {}


# ============================================================== resolve_winner (5)
@pytest.mark.parametrize(
    ("h", "a", "expected"),
    [
        (0, 0, "DRAW"),
        (1, 0, "HOME"),
        (0, 1, "AWAY"),
        (3, 2, "HOME"),
        (2, 2, "DRAW"),  # penalty-urile NU conteaza la WINNER
    ],
)
def test_resolve_winner(h: int, a: int, expected: str) -> None:
    assert resolve_winner(h, a) == expected


# ============================================================= resolve_qualify (7)
def test_qualify_home_wins_in_regular_time() -> None:
    assert resolve_qualify(2, 1, None, None) == "HOME"


def test_qualify_away_wins_in_regular_time() -> None:
    assert resolve_qualify(1, 3, None, None) == "AWAY"


def test_qualify_draw_decided_by_penalties_home() -> None:
    assert resolve_qualify(2, 2, 5, 4) == "HOME"


def test_qualify_draw_decided_by_penalties_away() -> None:
    assert resolve_qualify(1, 1, 3, 5) == "AWAY"


def test_qualify_draw_without_penalties_is_blocked() -> None:
    with pytest.raises(ScoringError):
        resolve_qualify(2, 2, None, None)


def test_qualify_zero_zero_without_penalties_is_blocked() -> None:
    with pytest.raises(ScoringError):
        resolve_qualify(0, 0, None, None)


def test_qualify_equal_penalties_is_blocked() -> None:
    with pytest.raises(ScoringError):
        resolve_qualify(2, 2, 4, 4)


# ======================================================== resolve_total_goals (12)
# Scor de granita: exact 2 goluri (1-1). Toate cele 8 combinatii.
@pytest.mark.parametrize(
    ("pick", "line", "expected"),
    [
        ("OVER", 0.5, True),
        ("OVER", 1.5, True),
        ("OVER", 2.5, False),
        ("OVER", 3.5, False),
        ("UNDER", 0.5, False),
        ("UNDER", 1.5, False),
        ("UNDER", 2.5, True),
        ("UNDER", 3.5, True),
    ],
)
def test_total_goals_boundary_two_goals(pick: str, line: float, expected: bool) -> None:
    assert resolve_total_goals(1, 1, pick, line) is expected


def test_total_goals_zero_zero() -> None:
    assert resolve_total_goals(0, 0, "OVER", 0.5) is False
    assert resolve_total_goals(0, 0, "UNDER", 0.5) is True


def test_total_goals_high_score() -> None:
    assert resolve_total_goals(3, 1, "OVER", 3.5) is True
    assert resolve_total_goals(3, 1, "UNDER", 3.5) is False


def test_total_goals_exactly_three_is_over_two_and_a_half() -> None:
    # PLAN: "OVER 2.5 corect daca H+A >= 3"
    assert resolve_total_goals(2, 1, "OVER", 2.5) is True
    assert resolve_total_goals(2, 1, "UNDER", 2.5) is False


def test_total_goals_rejects_bad_line() -> None:
    with pytest.raises(ScoringError):
        resolve_total_goals(1, 1, "OVER", 2.0)


def test_total_goals_rejects_bad_pick() -> None:
    with pytest.raises(ScoringError):
        resolve_total_goals(1, 1, "MIDDLE", 2.5)


# ============================================================== resolve_btts (5)
@pytest.mark.parametrize(
    ("h", "a", "expected"),
    [
        (3, 0, "NO"),
        (0, 3, "NO"),
        (0, 0, "NO"),
        (1, 1, "YES"),
        (2, 3, "YES"),
    ],
)
def test_resolve_btts(h: int, a: int, expected: str) -> None:
    assert resolve_btts(h, a) == expected


# ============================================================= resolve_scorer (5)
def test_scorer_correct_when_player_scored() -> None:
    assert resolve_scorer(5, [(5, 1), (7, 2)]) is True


def test_scorer_correct_with_multiple_goals() -> None:
    assert resolve_scorer(7, [(5, 1), (7, 2)]) is True


def test_scorer_wrong_when_player_absent() -> None:
    assert resolve_scorer(9, [(5, 1), (7, 2)]) is False


def test_scorer_wrong_when_zero_goals() -> None:
    # autogol / inregistrare cu 0 -> nu conteaza ca marcator FEG
    assert resolve_scorer(5, [(5, 0)]) is False


def test_scorer_wrong_when_no_scorers() -> None:
    assert resolve_scorer(5, []) is False


# ================================================================ points_for (11)
@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        (Selection("WINNER", "HOME"), 3),
        (Selection("WINNER", "AWAY"), 3),
        (Selection("WINNER", "DRAW"), 4),
        (Selection("QUALIFY", "HOME"), 2),
        (Selection("TOTAL_GOALS", "OVER", 0.5), 1),
        (Selection("TOTAL_GOALS", "OVER", 1.5), 2),
        (Selection("TOTAL_GOALS", "OVER", 2.5), 3),
        (Selection("TOTAL_GOALS", "OVER", 3.5), 4),
        (Selection("TOTAL_GOALS", "UNDER", 3.5), 1),
        (Selection("TOTAL_GOALS", "UNDER", 2.5), 2),
        (Selection("TOTAL_GOALS", "UNDER", 1.5), 3),
        (Selection("TOTAL_GOALS", "UNDER", 0.5), 4),
        (Selection("BTTS", "YES"), 2),
        (Selection("BTTS", "NO"), 2),
        (Selection("SCORER", "PLAYER", None, 5), 5),
    ],
)
def test_points_for_defaults(selection: Selection, expected: int) -> None:
    assert points_for(selection, DEFAULTS) == expected


def test_points_for_reads_admin_overrides() -> None:
    assert points_for(Selection("SCORER", "PLAYER", None, 5), {"pts.scorer": "10"}) == 10
    assert points_for(Selection("WINNER", "DRAW"), {"pts.winner.draw": "6"}) == 6


def test_points_for_max_feg_match_is_seventeen() -> None:
    # 4 (under 0.5 / over 3.5) + 2 (qualify) + 4 (winner draw) + 2 (btts) + 5 (scorer)
    total = (
        points_for(Selection("WINNER", "DRAW"), DEFAULTS)
        + points_for(Selection("QUALIFY", "HOME"), DEFAULTS)
        + points_for(Selection("TOTAL_GOALS", "OVER", 3.5), DEFAULTS)
        + points_for(Selection("BTTS", "YES"), DEFAULTS)
        + points_for(Selection("SCORER", "PLAYER", None, 1), DEFAULTS)
    )
    assert total == 17


# =========================================================== market_available (4)
def test_scorer_market_only_on_feg_matches() -> None:
    assert market_available("SCORER", has_feg=True, both_teams_set=True) is True
    assert market_available("SCORER", has_feg=False, both_teams_set=True) is False


def test_winner_and_qualify_need_both_teams() -> None:
    assert market_available("WINNER", has_feg=True, both_teams_set=False) is False
    assert market_available("QUALIFY", has_feg=True, both_teams_set=False) is False


def test_total_goals_and_btts_always_available() -> None:
    assert market_available("TOTAL_GOALS", has_feg=False, both_teams_set=False) is True
    assert market_available("BTTS", has_feg=False, both_teams_set=False) is True


# ============================================================ grade_selection (7)
def _outcome(h: int, a: int, ph=None, pa=None, scorers=None):
    from services.scoring import MatchOutcome

    return MatchOutcome(h, a, ph, pa, tuple(scorers or []))


def test_grade_winner_correct() -> None:
    assert grade_selection(Selection("WINNER", "HOME"), _outcome(2, 1), DEFAULTS) == (True, 3)


def test_grade_winner_wrong_gives_zero() -> None:
    assert grade_selection(Selection("WINNER", "HOME"), _outcome(1, 2), DEFAULTS) == (False, 0)


def test_grade_draw_correct() -> None:
    assert grade_selection(Selection("WINNER", "DRAW"), _outcome(1, 1), DEFAULTS) == (True, 4)


def test_grade_total_goals_over_at_three() -> None:
    assert grade_selection(
        Selection("TOTAL_GOALS", "OVER", 2.5), _outcome(2, 1), DEFAULTS
    ) == (True, 3)


def test_grade_qualify_by_penalties() -> None:
    assert grade_selection(
        Selection("QUALIFY", "AWAY"), _outcome(1, 1, 3, 5), DEFAULTS
    ) == (True, 2)


def test_grade_qualify_draw_without_penalties_raises() -> None:
    with pytest.raises(ScoringError):
        grade_selection(Selection("QUALIFY", "HOME"), _outcome(2, 2), DEFAULTS)


def test_grade_scorer_correct_and_wrong() -> None:
    out = _outcome(2, 0, scorers=[(5, 1), (9, 1)])
    assert grade_selection(Selection("SCORER", "PLAYER", None, 5), out, DEFAULTS) == (True, 5)
    assert grade_selection(Selection("SCORER", "PLAYER", None, 7), out, DEFAULTS) == (False, 0)


def test_grade_btts_no_correct_on_shutout() -> None:
    assert grade_selection(Selection("BTTS", "NO"), _outcome(3, 0), DEFAULTS) == (True, 2)


def test_grade_rejects_unavailable_scorer_market() -> None:
    with pytest.raises(ScoringError):
        grade_selection(
            Selection("SCORER", "PLAYER", None, 5),
            _outcome(1, 0),
            DEFAULTS,
            has_feg=False,
        )


# ============================================================== perfect_bonus (4)
def test_perfect_bonus_disabled_by_default() -> None:
    assert perfect_bonus(correct=3, total=3, settings=DEFAULTS) == 0


def test_perfect_bonus_applies_when_enabled_and_all_correct() -> None:
    assert perfect_bonus(correct=3, total=3, settings={"pts.bonus.perfect": "5"}) == 5


def test_perfect_bonus_needs_at_least_three_selections() -> None:
    assert perfect_bonus(correct=2, total=2, settings={"pts.bonus.perfect": "5"}) == 0


def test_perfect_bonus_not_applied_if_any_wrong() -> None:
    assert perfect_bonus(correct=3, total=4, settings={"pts.bonus.perfect": "5"}) == 0


# ================================================ validari points_for / markets
def test_points_for_rejects_invalid_setting_value() -> None:
    with pytest.raises(ScoringError):
        points_for(Selection("SCORER", "PLAYER", None, 5), {"pts.scorer": "nu-e-numar"})


def test_points_for_rejects_bad_total_goals_line() -> None:
    with pytest.raises(ScoringError):
        points_for(Selection("TOTAL_GOALS", "OVER", 2.0), DEFAULTS)


def test_points_for_rejects_bad_total_goals_pick() -> None:
    with pytest.raises(ScoringError):
        points_for(Selection("TOTAL_GOALS", "SIDEWAYS", 2.5), DEFAULTS)


def test_points_for_rejects_unknown_market() -> None:
    with pytest.raises(ScoringError):
        points_for(Selection("BANANA", "X"), DEFAULTS)


def test_market_available_unknown_market_is_false() -> None:
    assert market_available("BANANA", has_feg=True, both_teams_set=True) is False


def test_grade_scorer_selection_without_player_raises() -> None:
    from services.scoring import MatchOutcome

    with pytest.raises(ScoringError):
        grade_selection(
            Selection("SCORER", "PLAYER", None, None),
            MatchOutcome(1, 0),
            DEFAULTS,
        )


# ============================================================ validari de intrare
def test_resolve_functions_reject_none_scores() -> None:
    with pytest.raises(ScoringError):
        resolve_winner(None, 1)  # type: ignore[arg-type]
    with pytest.raises(ScoringError):
        resolve_btts(1, None)  # type: ignore[arg-type]


def test_resolve_functions_reject_negative_scores() -> None:
    with pytest.raises(ScoringError):
        resolve_winner(-1, 0)
    with pytest.raises(ScoringError):
        resolve_total_goals(2, -1, "OVER", 1.5)
