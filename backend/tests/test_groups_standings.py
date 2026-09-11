"""Faza 9: services/groups.py — functii PURE, fara DB (PLAN_GRUPE.md sectiunea 5.3).

TDD: scrise INAINTE de implementare, la fel ca test_scoring.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.groups import (
    GroupError,
    GroupResult,
    assert_group_open_for_prediction,
    group_lock_reason,
    group_locks_at,
    group_missed_prediction_reason,
    qualified_team_ids,
    round_robin_pairs,
    standings,
)


def _row(rows, team_id):
    return next(r for r in rows if r.team_id == team_id)


# ============================================================== puncte de baza 3/1/0
def test_win_gives_three_points_loss_gives_zero() -> None:
    rows = standings([1, 2], [GroupResult(1, 2, 2, 0)])
    r1, r2 = _row(rows, 1), _row(rows, 2)
    assert r1.points == 3 and r1.won == 1 and r1.drawn == 0 and r1.lost == 0
    assert r1.goals_for == 2 and r1.goals_against == 0 and r1.goal_diff == 2
    assert r1.played == 1
    assert r2.points == 0 and r2.won == 0 and r2.drawn == 0 and r2.lost == 1
    assert r1.rank == 1 and r2.rank == 2
    assert r1.tied_with == () and r2.tied_with == ()


def test_draw_gives_one_point_each() -> None:
    rows = standings([1, 2], [GroupResult(1, 2, 1, 1)])
    r1, r2 = _row(rows, 1), _row(rows, 2)
    assert r1.points == 1 and r2.points == 1
    assert r1.drawn == 1 and r2.drawn == 1


def test_multiple_results_accumulate() -> None:
    rows = standings([1, 2, 3], [GroupResult(1, 2, 2, 0), GroupResult(1, 3, 1, 1)])
    r1 = _row(rows, 1)
    assert r1.played == 2 and r1.won == 1 and r1.drawn == 1 and r1.lost == 0
    assert r1.points == 4
    assert r1.goals_for == 3 and r1.goals_against == 1 and r1.goal_diff == 2


# ==================================================================== departajare
def test_ranked_by_points_first() -> None:
    # team1: 1 victorie (3p); team2: 1 egal + 1 infrangere (1p)
    rows = standings(
        [1, 2, 3],
        [GroupResult(1, 3, 1, 0), GroupResult(2, 3, 0, 0)],
    )
    assert _row(rows, 1).rank == 1
    assert _row(rows, 2).rank == 2


def test_tiebreak_by_goal_difference_when_points_equal() -> None:
    # team1 si team2 ambele au 3p (o victorie), dar golaveraje diferite, fara sa se fi
    # intalnit intre ele.
    rows = standings(
        [1, 2, 10, 11],
        [GroupResult(1, 10, 3, 0), GroupResult(2, 11, 1, 0)],
    )
    assert _row(rows, 1).goal_diff == 3
    assert _row(rows, 2).goal_diff == 1
    assert _row(rows, 1).rank == 1
    assert _row(rows, 2).rank == 2
    assert _row(rows, 1).tied_with == () and _row(rows, 2).tied_with == ()


def test_tiebreak_by_goals_scored_when_points_and_diff_equal() -> None:
    rows = standings(
        [1, 2, 10, 11],
        [GroupResult(1, 10, 5, 2), GroupResult(2, 11, 4, 1)],
    )
    r1, r2 = _row(rows, 1), _row(rows, 2)
    assert r1.points == r2.points == 3
    assert r1.goal_diff == r2.goal_diff == 3
    assert r1.goals_for == 5 and r2.goals_for == 4
    assert r1.rank == 1 and r2.rank == 2
    assert r1.tied_with == () and r2.tied_with == ()


def test_tiebreak_by_direct_result_when_fully_tied_otherwise() -> None:
    """Echipele 1 si 2 au exact acelasi (puncte, golaveraj, goluri marcate) in total,
    dar meciul direct dintre ele il castiga echipa 1 -> trebuie sa iasa inaintea ei.
    """
    results = [
        GroupResult(1, 2, 1, 0),  # meciul direct: 1 bate 2
        GroupResult(1, 100, 2, 3),  # 1 pierde cu un tert
        GroupResult(2, 101, 3, 2),  # 2 bate un alt tert
    ]
    rows = standings([1, 2, 100, 101], results)
    r1, r2 = _row(rows, 1), _row(rows, 2)
    # verificare ca testul e cu adevarat construit pe o egalitate totala in prealabil
    assert (r1.points, r1.goal_diff, r1.goals_for) == (r2.points, r2.goal_diff, r2.goals_for)
    assert r1.rank == 2 and r2.rank == 3  # echipa 100 e peste amandoua (golaveraj +1)
    assert r1.tied_with == () and r2.tied_with == ()


def test_completely_tied_teams_share_rank_and_list_each_other() -> None:
    """Ciclu clasic 1-0 / 1-0 / 1-0 intre 3 echipe: raman perfect egale si dupa
    mini-clasamentul direct -> nedepartajabile.
    """
    results = [
        GroupResult(1, 2, 1, 0),
        GroupResult(2, 3, 1, 0),
        GroupResult(3, 1, 1, 0),
    ]
    rows = standings([1, 2, 3], results)
    for r in rows:
        assert r.rank == 1
        assert set(r.tied_with) == {1, 2, 3} - {r.team_id}


def test_teams_with_no_matches_appear_with_zero_stats() -> None:
    rows = standings([1, 2, 3, 4], [])
    for r in rows:
        assert r.played == 0 and r.points == 0 and r.goal_diff == 0
        assert r.rank == 1
    assert {r.team_id for r in rows} == {1, 2, 3, 4}


# ============================================================== qualified_team_ids
def test_qualified_team_ids_happy_path() -> None:
    rows = standings(
        [1, 2, 3],
        [GroupResult(1, 3, 1, 0), GroupResult(2, 3, 0, 0)],
    )
    assert qualified_team_ids(rows, 2) == [1, 2]


def test_qualified_team_ids_raises_when_cut_is_ambiguous() -> None:
    results = [
        GroupResult(1, 2, 1, 0),
        GroupResult(2, 3, 1, 0),
        GroupResult(3, 1, 1, 0),
    ]
    rows = standings([1, 2, 3], results)
    with pytest.raises(GroupError):
        qualified_team_ids(rows, 2)


def test_qualified_team_ids_all_tied_and_count_equals_total_is_not_ambiguous() -> None:
    results = [
        GroupResult(1, 2, 1, 0),
        GroupResult(2, 3, 1, 0),
        GroupResult(3, 1, 1, 0),
    ]
    rows = standings([1, 2, 3], results)
    assert set(qualified_team_ids(rows, 3)) == {1, 2, 3}


def test_qualified_team_ids_rejects_non_positive_count() -> None:
    rows = standings([1, 2], [GroupResult(1, 2, 1, 0)])
    with pytest.raises(GroupError):
        qualified_team_ids(rows, 0)


def test_qualified_team_ids_rejects_count_bigger_than_group() -> None:
    rows = standings([1, 2], [GroupResult(1, 2, 1, 0)])
    with pytest.raises(GroupError):
        qualified_team_ids(rows, 3)


# ================================================================= round_robin_pairs
def test_round_robin_pairs_has_six_matches_in_three_rounds() -> None:
    pairs = round_robin_pairs([10, 20, 30, 40])
    assert len(pairs) == 6
    assert {p[0] for p in pairs} == {1, 2, 3}
    assert sum(1 for p in pairs if p[0] == 1) == 2
    assert sum(1 for p in pairs if p[0] == 2) == 2
    assert sum(1 for p in pairs if p[0] == 3) == 2


def test_round_robin_pairs_every_pair_exactly_once() -> None:
    teams = [10, 20, 30, 40]
    pairs = round_robin_pairs(teams)
    seen = set()
    for _round_no, home, away in pairs:
        key = frozenset((home, away))
        assert key not in seen
        seen.add(key)
    from itertools import combinations

    expected = {frozenset(c) for c in combinations(teams, 2)}
    assert seen == expected


def test_round_robin_pairs_rejects_wrong_team_count() -> None:
    with pytest.raises(GroupError):
        round_robin_pairs([1, 2, 3])


# ================================================================== group_locks_at
def test_group_locks_at_returns_earliest() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    later = now + timedelta(days=1)
    assert group_locks_at([later, now, None]) == now


def test_group_locks_at_none_when_nothing_scheduled() -> None:
    assert group_locks_at([None, None]) is None
    assert group_locks_at([]) is None


# ================================================== assert_group_open_for_prediction
def test_assert_group_open_raises_when_no_schedule() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        assert_group_open_for_prediction(None, has_settled_match=False, is_finalized=False)
    assert exc.value.status_code == 400
    assert "program" in exc.value.detail.lower()


def test_assert_group_open_raises_when_started() -> None:
    from fastapi import HTTPException

    now = datetime.now(timezone.utc)
    past = now - timedelta(minutes=1)
    with pytest.raises(HTTPException) as exc:
        assert_group_open_for_prediction(
            past, has_settled_match=False, is_finalized=False, now=now
        )
    assert exc.value.status_code == 400
    assert "început" in exc.value.detail.lower()


def test_assert_group_open_passes_when_in_future() -> None:
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    assert (
        assert_group_open_for_prediction(
            future, has_settled_match=False, is_finalized=False, now=now
        )
        is None
    )


def test_assert_group_open_raises_when_match_settled_even_before_scheduled_time() -> None:
    """Bug PLAN_GRUPE.md: un meci validat devreme (sau ora gresita, in viitor) tot
    trebuie sa blocheze pronosticul — nu doar ceasul."""
    from fastapi import HTTPException

    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    with pytest.raises(HTTPException) as exc:
        assert_group_open_for_prediction(
            future, has_settled_match=True, is_finalized=False, now=now
        )
    assert exc.value.status_code == 400
    assert "validat" in exc.value.detail.lower()


def test_assert_group_open_raises_when_finalized_even_before_scheduled_time() -> None:
    from fastapi import HTTPException

    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    with pytest.raises(HTTPException) as exc:
        assert_group_open_for_prediction(
            future, has_settled_match=True, is_finalized=True, now=now
        )
    assert exc.value.status_code == 400
    assert "încheiat" in exc.value.detail.lower()


# ======================================================================= group_lock_reason
def test_group_lock_reason_none_when_open() -> None:
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    assert (
        group_lock_reason(
            locks_at=future, has_settled_match=False, is_finalized=False, now=now
        )
        is None
    )
    assert (
        group_lock_reason(locks_at=None, has_settled_match=False, is_finalized=False, now=now)
        is None
    )


def test_group_lock_reason_prioritizes_finalized_over_settled_match() -> None:
    """Mesajele trebuie sa fie distincte si sa reflecte cea mai specifica cauza."""
    now = datetime.now(timezone.utc)
    reason = group_lock_reason(
        locks_at=now + timedelta(days=1), has_settled_match=True, is_finalized=True, now=now
    )
    assert reason is not None and "încheiat" in reason.lower()


# ==================================================== group_missed_prediction_reason
# Curatenie Sarcina 2: GroupCard.tsx afisa mereu "a inceput deja" in empty state-ul unui
# user fara pronostic, chiar si cand grupa era de fapt INCHEIATA (finalizata). Mesajele
# lui `group_lock_reason` sunt gandite pentru un raspuns de eroare la o actiune ("nu mai
# poti SCHIMBA pronosticul") — gresite pentru cineva care n-a pus niciunul.
def test_group_missed_prediction_reason_none_when_open() -> None:
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    assert (
        group_missed_prediction_reason(
            locks_at=future, has_settled_match=False, is_finalized=False, now=now
        )
        is None
    )
    assert (
        group_missed_prediction_reason(
            locks_at=None, has_settled_match=False, is_finalized=False, now=now
        )
        is None
    )


def test_group_missed_prediction_reason_says_incheiat_not_inceput_when_finalized() -> None:
    """O grupa finalizata s-a INCHEIAT, nu "a inceput" — bug-ul concret raportat."""
    now = datetime.now(timezone.utc)
    reason = group_missed_prediction_reason(
        locks_at=now - timedelta(days=1), has_settled_match=True, is_finalized=True, now=now
    )
    assert reason is not None
    assert "încheiat" in reason.lower()
    assert "a început" not in reason.lower()


def test_group_missed_prediction_reason_never_says_schimba() -> None:
    """Userul n-a pus niciun pronostic — "schimba" (din group_lock_reason) ar fi gresit
    aici in toate cele 3 ramuri blocate."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=1)

    finalized = group_missed_prediction_reason(
        locks_at=past, has_settled_match=False, is_finalized=True, now=now
    )
    settled = group_missed_prediction_reason(
        locks_at=None, has_settled_match=True, is_finalized=False, now=now
    )
    past_lock = group_missed_prediction_reason(
        locks_at=past, has_settled_match=False, is_finalized=False, now=now
    )

    for reason in (finalized, settled, past_lock):
        assert reason is not None
        assert "schimb" not in reason.lower()


def test_group_missed_prediction_reason_distinguishes_settled_match_from_past_lock() -> None:
    now = datetime.now(timezone.utc)
    settled = group_missed_prediction_reason(
        locks_at=now + timedelta(days=1), has_settled_match=True, is_finalized=False, now=now
    )
    past_lock = group_missed_prediction_reason(
        locks_at=now - timedelta(days=1), has_settled_match=False, is_finalized=False, now=now
    )
    assert settled != past_lock
    assert "validat" in settled.lower()


# ============================================= _group_setting_int (fallback pe DEFAULT_POINTS)
def test_group_setting_int_falls_back_to_default_when_missing() -> None:
    """La fel ca services.scoring._setting_int: daca lipseste din `settings`, cade pe
    DEFAULT_POINTS. In productie seed.py populeaza mereu cheile, deci ramura asta se
    exercita doar direct, cu un dict de settings gol (ca in test_scoring.py)."""
    from services.groups import _group_setting_int

    assert _group_setting_int({}, "pts.group.qualify") == 2
    assert _group_setting_int({"pts.group.qualify": "9"}, "pts.group.qualify") == 9
