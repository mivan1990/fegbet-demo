"""Faza 5: decontare + avansare in bracket + re-validare.

TDD: testele sunt scrise INAINTE de services/settlement.py.
Cel mai important: testul de re-validare (punctele vechi dispar complet).
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import ActivityLog, Match, MatchScorer, Setting, Ticket, User, utcnow
from tests.conftest import auth_header


# --------------------------------------------------------------------- helpers
def _place(client: TestClient, headers, match_id: int, selections):
    resp = client.post(
        "/api/tickets", headers=headers, json={"match_id": match_id, "selections": selections}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _settle(client: TestClient, admin_headers, match_id: int, **body):
    return client.post(
        f"/api/admin/matches/{match_id}/settle", headers=admin_headers, json=body
    )


@pytest.fixture()
def bracket(db_session, feg_team, opponent_team):
    """QF: FEG vs opponent  -> avanseaza in Final pe slotul `home`."""
    final = Match(round_no=2, bracket_position=0, stage_label="Finală", status="SCHEDULED")
    db_session.add(final)
    db_session.flush()
    qf = Match(
        round_no=1,
        bracket_position=0,
        stage_label="Semifinală",
        home_team_id=feg_team.id,
        away_team_id=opponent_team.id,
        scheduled_at=utcnow() + timedelta(days=1),
        status="SCHEDULED",
        next_match_id=final.id,
        next_slot="home",
    )
    db_session.add(qf)
    db_session.commit()
    db_session.refresh(qf)
    db_session.refresh(final)
    return {"qf": qf, "final": final, "feg_id": feg_team.id, "opp_id": opponent_team.id}


# ========================================================= permisiuni & validare
def test_settle_requires_admin(client, user_headers, bracket) -> None:
    assert _settle(client, {}, bracket["qf"].id, home_score=1, away_score=0).status_code == 401
    assert _settle(client, user_headers, bracket["qf"].id, home_score=1, away_score=0).status_code == 403


def test_settle_missing_match_404(client, admin_headers) -> None:
    assert _settle(client, admin_headers, 99999, home_score=1, away_score=0).status_code == 404


def test_settle_rejects_negative_score(client, admin_headers, bracket) -> None:
    assert _settle(client, admin_headers, bracket["qf"].id, home_score=-1, away_score=0).status_code == 422


def test_settle_draw_without_penalties_blocked(client, admin_headers, bracket) -> None:
    resp = _settle(client, admin_headers, bracket["qf"].id, home_score=1, away_score=1)
    assert resp.status_code == 400
    assert "penalty" in resp.json()["detail"].lower()


def test_settle_draw_with_equal_penalties_blocked(client, admin_headers, bracket) -> None:
    resp = _settle(
        client, admin_headers, bracket["qf"].id,
        home_score=1, away_score=1, penalties_home=3, penalties_away=3,
    )
    assert resp.status_code == 400


def test_settle_scorers_on_non_feg_match_rejected(client, admin_headers, non_feg_match, players) -> None:
    resp = _settle(
        client, admin_headers, non_feg_match.id,
        home_score=2, away_score=0, scorers=[{"player_id": players[0].id, "goals": 1}],
    )
    assert resp.status_code == 400


def test_settle_scorer_goals_exceed_feg_goals_rejected(client, admin_headers, bracket, players) -> None:
    # FEG (gazde) a marcat 1, dar marcatorul are 2 goluri
    resp = _settle(
        client, admin_headers, bracket["qf"].id,
        home_score=1, away_score=0, scorers=[{"player_id": players[0].id, "goals": 2}],
    )
    assert resp.status_code == 400


def test_settle_scorer_must_be_feg_player(client, admin_headers, bracket) -> None:
    resp = _settle(
        client, admin_headers, bracket["qf"].id,
        home_score=2, away_score=0, scorers=[{"player_id": 99999, "goals": 1}],
    )
    assert resp.status_code == 400


def test_settle_cancelled_match_rejected(client, admin_headers, db_session, bracket) -> None:
    bracket["qf"].status = "CANCELLED"
    db_session.commit()
    resp = _settle(client, admin_headers, bracket["qf"].id, home_score=1, away_score=0)
    assert resp.status_code == 400
    assert "anulat" in resp.json()["detail"].lower()


def test_settle_tbd_match_rejected(client, admin_headers, db_session, bracket) -> None:
    bracket["qf"].away_team_id = None
    db_session.commit()
    resp = _settle(client, admin_headers, bracket["qf"].id, home_score=1, away_score=0)
    assert resp.status_code == 400
    assert "echipe" in resp.json()["detail"].lower()


def test_settle_duplicate_scorer_rejected(client, admin_headers, bracket, players) -> None:
    resp = _settle(
        client, admin_headers, bracket["qf"].id,
        home_score=3, away_score=0,
        scorers=[{"player_id": players[0].id, "goals": 1}, {"player_id": players[0].id, "goals": 1}],
    )
    assert resp.status_code == 400
    assert "de două ori" in resp.json()["detail"]


def test_settle_rejects_selection_on_unavailable_market(
    client, admin_headers, db_session, bracket, players
) -> None:
    """Selectie corupta in DB (SCORER fara player_id) -> decontarea da 400, nu crapa."""
    from models import Ticket, TicketSelection, User

    user = db_session.execute(select(User).where(User.is_admin.is_(False))).scalar_one_or_none()
    if user is None:
        from services.security import hash_password

        user = User(email="corupt@mariusivan.ro", password_hash=hash_password("x" * 8), display_name="c")
        db_session.add(user)
        db_session.flush()
    ticket = Ticket(user_id=user.id, match_id=bracket["qf"].id, status="OPEN")
    ticket.selections.append(TicketSelection(market="SCORER", pick="SCORER", player_id=None))
    db_session.add(ticket)
    db_session.commit()

    resp = _settle(client, admin_headers, bracket["qf"].id, home_score=2, away_score=0)
    assert resp.status_code == 400


# =============================================== decontare: 3 useri, puncte exacte
def test_three_users_get_exactly_computed_points(
    client, admin_headers, register_user, bracket
) -> None:
    feg_id = bracket["feg_id"]
    qf_id = bracket["qf"].id

    _u1, t1 = register_user(email="u1@mariusivan.ro")
    _u2, t2 = register_user(email="u2@mariusivan.ro")
    _u3, t3 = register_user(email="u3@mariusivan.ro")
    h1, h2, h3 = auth_header(t1), auth_header(t2), auth_header(t3)

    scorer_id = client.get("/api/players").json()[0]["id"]

    # U1: WINNER HOME (FEG) 3 + OVER 1.5 (2)  -> daca scor 2-1: HOME corect(3) + over1.5 corect(2) = 5
    _place(client, h1, qf_id, [
        {"market": "WINNER", "pick": "HOME"},
        {"market": "TOTAL_GOALS", "pick": "OVER", "line": 1.5},
    ])
    # U2: WINNER AWAY (gresit, 0) + BTTS YES (2-1 -> ambele au marcat -> corect 2) = 2
    _place(client, h2, qf_id, [
        {"market": "WINNER", "pick": "AWAY"},
        {"market": "BTTS", "pick": "YES"},
    ])
    # U3: SCORER pe scorer_id (marcheaza) 5 + UNDER 2.5 (total 3 -> gresit 0) = 5
    _place(client, h3, qf_id, [
        {"market": "SCORER", "pick": "SCORER", "player_id": scorer_id},
        {"market": "TOTAL_GOALS", "pick": "UNDER", "line": 2.5},
    ])

    resp = _settle(
        client, admin_headers, qf_id,
        home_score=2, away_score=1,
        scorers=[{"player_id": scorer_id, "goals": 1}],
    )
    assert resp.status_code == 200, resp.text

    me1 = client.get("/api/auth/me", headers=h1).json()
    me2 = client.get("/api/auth/me", headers=h2).json()
    me3 = client.get("/api/auth/me", headers=h3).json()
    assert me1["points"] == 5
    assert me2["points"] == 2
    assert me3["points"] == 5

    # verificare si pe bilet
    mine1 = client.get("/api/tickets/mine", headers=h1).json()[0]
    assert mine1["total_points"] == 5
    assert mine1["status"] == "SETTLED"
    assert all(s["is_correct"] for s in mine1["selections"])

    assert feg_id  # keep fixture referenced


# ================================================ RE-VALIDARE (testul critic)
def test_resettle_old_points_disappear_completely(
    client, admin_headers, register_user, bracket
) -> None:
    qf_id = bracket["qf"].id
    _u, tok = register_user(email="rev@mariusivan.ro")
    h = auth_header(tok)

    # Bilet: WINNER HOME (3) + OVER 2.5 (3) + BTTS YES (2)
    _place(client, h, qf_id, [
        {"market": "WINNER", "pick": "HOME"},
        {"market": "TOTAL_GOALS", "pick": "OVER", "line": 2.5},
        {"market": "BTTS", "pick": "YES"},
    ])

    # Prima validare: 3-0. HOME corect(3), OVER 2.5 corect(3), BTTS YES gresit(0) = 6
    r1 = _settle(client, admin_headers, qf_id, home_score=3, away_score=0)
    assert r1.status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["points"] == 6

    # Adminul corecteaza: de fapt a fost 0-1. HOME gresit(0), OVER 2.5 gresit(0), BTTS gresit(0) = 0
    r2 = _settle(client, admin_headers, qf_id, home_score=0, away_score=1)
    assert r2.status_code == 200

    # Punctele VECHI trebuie sa fi disparut complet — nu 6, nu 6+0, ci exact 0.
    assert client.get("/api/auth/me", headers=h).json()["points"] == 0

    mine = client.get("/api/tickets/mine", headers=h).json()[0]
    assert mine["total_points"] == 0
    assert all(s["is_correct"] is False for s in mine["selections"])
    assert all(s["points_awarded"] == 0 for s in mine["selections"])

    # A treia corectie: 2-2 cu penalty-uri, FEG pierde la pen.
    # HOME gresit(0), OVER 2.5 corect(3), BTTS YES corect(2) = 5
    r3 = _settle(
        client, admin_headers, qf_id,
        home_score=2, away_score=2, penalties_home=3, penalties_away=5,
    )
    assert r3.status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["points"] == 5

    # log de re-validare
    with SessionLocal() as db:
        actions = [a.action for a in db.execute(select(ActivityLog)).scalars()]
    assert actions.count("admin.match.settle") == 1
    assert actions.count("admin.match.resettle") == 2


def test_resettle_does_not_double_count_across_users_points(
    client, admin_headers, register_user, bracket
) -> None:
    qf_id = bracket["qf"].id
    _u, tok = register_user(email="dc@mariusivan.ro")
    h = auth_header(tok)
    _place(client, h, qf_id, [{"market": "WINNER", "pick": "HOME"}])

    _settle(client, admin_headers, qf_id, home_score=1, away_score=0)  # HOME corect -> 3
    _settle(client, admin_headers, qf_id, home_score=1, away_score=0)  # identic -> tot 3, nu 6
    assert client.get("/api/auth/me", headers=h).json()["points"] == 3


# ============================================= avansare in bracket
def test_winner_advances_to_correct_slot(client, admin_headers, bracket) -> None:
    _settle(client, admin_headers, bracket["qf"].id, home_score=3, away_score=1)
    with SessionLocal() as db:
        final = db.get(Match, bracket["final"].id)
        assert final.home_team_id == bracket["feg_id"]  # FEG (gazde) a castigat, slot `home`
        assert final.away_team_id is None


def test_resettle_changed_winner_replaces_advanced_team(client, admin_headers, bracket) -> None:
    _settle(client, admin_headers, bracket["qf"].id, home_score=3, away_score=1)
    with SessionLocal() as db:
        assert db.get(Match, bracket["final"].id).home_team_id == bracket["feg_id"]

    # corectie: de fapt a castigat adversarul
    _settle(client, admin_headers, bracket["qf"].id, home_score=0, away_score=2)
    with SessionLocal() as db:
        assert db.get(Match, bracket["final"].id).home_team_id == bracket["opp_id"]


def test_resettle_warns_if_next_match_already_settled(client, admin_headers, bracket) -> None:
    _settle(client, admin_headers, bracket["qf"].id, home_score=3, away_score=1)
    with SessionLocal() as db:
        final = db.get(Match, bracket["final"].id)
        final.is_settled = True
        final.status = "FINISHED"
        db.commit()

    resp = _settle(client, admin_headers, bracket["qf"].id, home_score=0, away_score=2)
    assert resp.status_code == 200
    assert resp.json()["warning"] is not None
    assert "revalid" in resp.json()["warning"].lower()


def test_no_advance_when_no_next_match(client, admin_headers, scheduled_match) -> None:
    # scheduled_match nu are next_match_id
    resp = _settle(client, admin_headers, scheduled_match.id, home_score=1, away_score=0)
    assert resp.status_code == 200


# ============================================= efecte de stare
def test_settle_marks_finished_and_locks_betting(
    client, admin_headers, user_headers, bracket
) -> None:
    _place(client, user_headers, bracket["qf"].id, [{"market": "BTTS", "pick": "YES"}])
    _settle(client, admin_headers, bracket["qf"].id, home_score=1, away_score=0)

    with SessionLocal() as db:
        qf = db.get(Match, bracket["qf"].id)
        assert qf.is_settled is True
        assert qf.settled_at is not None
        assert qf.status == "FINISHED"

    # nu se mai poate modifica biletul
    resp = client.post(
        "/api/tickets",
        headers=user_headers,
        json={"match_id": bracket["qf"].id, "selections": [{"market": "BTTS", "pick": "NO"}]},
    )
    assert resp.status_code == 400


def test_settle_writes_scorers_and_shows_in_detail(client, admin_headers, bracket, players) -> None:
    _settle(
        client, admin_headers, bracket["qf"].id,
        home_score=2, away_score=0,
        scorers=[{"player_id": players[0].id, "goals": 1}, {"player_id": players[1].id, "goals": 1}],
    )
    detail = client.get(f"/api/matches/{bracket['qf'].id}").json()
    names = {s["name"] for s in detail["scorers"]}
    assert names == {players[0].name, players[1].name}

    with SessionLocal() as db:
        assert db.execute(
            select(MatchScorer).where(MatchScorer.match_id == bracket["qf"].id)
        ).scalars().all().__len__() == 2


def test_resettle_replaces_scorers(client, admin_headers, bracket, players) -> None:
    _settle(
        client, admin_headers, bracket["qf"].id,
        home_score=2, away_score=0, scorers=[{"player_id": players[0].id, "goals": 2}],
    )
    _settle(
        client, admin_headers, bracket["qf"].id,
        home_score=1, away_score=0, scorers=[{"player_id": players[1].id, "goals": 1}],
    )
    with SessionLocal() as db:
        rows = db.execute(
            select(MatchScorer).where(MatchScorer.match_id == bracket["qf"].id)
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].player_id == players[1].id


# ============================================= bonus bilet perfect
def test_perfect_bonus_applied_when_admin_enables_it(
    client, admin_headers, register_user, db_session, bracket
) -> None:
    setting = db_session.execute(
        select(Setting).where(Setting.key == "pts.bonus.perfect")
    ).scalar_one()
    setting.value = "7"
    db_session.commit()

    _u, tok = register_user(email="perfect@mariusivan.ro")
    h = auth_header(tok)
    _place(client, h, bracket["qf"].id, [
        {"market": "WINNER", "pick": "HOME"},       # 3
        {"market": "TOTAL_GOALS", "pick": "OVER", "line": 0.5},  # 1
        {"market": "BTTS", "pick": "NO"},           # 2
    ])
    # 2-0: HOME corect(3), OVER 0.5 corect(1), BTTS NO corect(2) = 6 + bonus 7 = 13
    _settle(client, admin_headers, bracket["qf"].id, home_score=2, away_score=0)
    assert client.get("/api/auth/me", headers=h).json()["points"] == 13


def test_settle_full_recompute_across_multiple_matches(
    client, admin_headers, register_user, bracket, db_session, opponent_team
) -> None:
    other = Match(
        round_no=1, bracket_position=1, stage_label="Semifinală",
        home_team_id=bracket["feg_id"], away_team_id=opponent_team.id,
        scheduled_at=utcnow() + timedelta(days=1), status="SCHEDULED",
    )
    db_session.add(other)
    db_session.commit()

    _u, tok = register_user(email="multi@mariusivan.ro")
    h = auth_header(tok)
    _place(client, h, bracket["qf"].id, [{"market": "WINNER", "pick": "HOME"}])  # -> 3
    _place(client, h, other.id, [{"market": "WINNER", "pick": "AWAY"}])          # -> 3

    _settle(client, admin_headers, bracket["qf"].id, home_score=1, away_score=0)
    assert client.get("/api/auth/me", headers=h).json()["points"] == 3
    _settle(client, admin_headers, other.id, home_score=0, away_score=1)
    assert client.get("/api/auth/me", headers=h).json()["points"] == 6
