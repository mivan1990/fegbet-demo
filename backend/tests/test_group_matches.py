"""Faza 9: meciuri de grupa — egal fara penalty, fara piata QUALIFY (PLAN_GRUPE.md 5.1-5.2)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from database import SessionLocal
from models import Match, Team, utcnow


def _make_teams(db_session, n: int, prefix: str = "Echipa") -> list[int]:
    ids = []
    for i in range(n):
        t = Team(name=f"{prefix} {i + 1}", short_name=f"{prefix[:1]}{i + 1}", is_active=True)
        db_session.add(t)
        db_session.flush()
        ids.append(t.id)
    db_session.commit()
    return ids


def _generate_group_with_feg(client, admin_headers, db_session, feg_team, opponent_team) -> dict:
    """Grupa A: FEG + 3 adverse — ca sa avem un meci de grupa cu FEG (pentru SCORER)."""
    extra = _make_teams(db_session, 2)
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": [feg_team.id, opponent_team.id, *extra]}]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()[0]


def _place(client, headers, match_id, selections):
    return client.post(
        "/api/tickets", headers=headers, json={"match_id": match_id, "selections": selections}
    )


def _settle(client, admin_headers, match_id, **body):
    return client.post(f"/api/admin/matches/{match_id}/settle", headers=admin_headers, json=body)


# =================================================== egal fara penalty la grupa
def test_group_match_draw_settles_without_penalties(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    with SessionLocal() as db:
        m = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().first()
        match_id = m.id

    resp = _settle(client, admin_headers, match_id, home_score=1, away_score=1)
    assert resp.status_code == 200, resp.text

    with SessionLocal() as db:
        m = db.get(Match, match_id)
        assert m.is_settled is True
        assert m.winner_team_id is None
        assert m.penalties_home is None
        assert m.penalties_away is None


def test_group_match_draw_ignores_penalties_sent_by_admin(client, admin_headers, db_session) -> None:
    """Chiar daca adminul trimite penalty-uri, ele se forteaza la NULL la un meci de grupa."""
    ids = _make_teams(db_session, 4)
    client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    with SessionLocal() as db:
        m = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().first()
        match_id = m.id

    resp = _settle(
        client, admin_headers, match_id, home_score=2, away_score=2,
        penalties_home=5, penalties_away=3,
    )
    assert resp.status_code == 200, resp.text
    with SessionLocal() as db:
        m = db.get(Match, match_id)
        assert m.penalties_home is None
        assert m.penalties_away is None
        assert m.winner_team_id is None


def test_group_match_decisive_result_sets_winner(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    with SessionLocal() as db:
        m = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().first()
        match_id, home_id = m.id, m.home_team_id

    resp = _settle(client, admin_headers, match_id, home_score=2, away_score=0)
    assert resp.status_code == 200
    with SessionLocal() as db:
        m = db.get(Match, match_id)
        assert m.winner_team_id == home_id


# =============================================== KNOCKOUT egal cere in continuare penalty
def test_knockout_match_draw_still_requires_penalties(
    client, admin_headers, scheduled_match
) -> None:
    resp = _settle(client, admin_headers, scheduled_match.id, home_score=1, away_score=1)
    assert resp.status_code == 400
    assert "penalty" in resp.json()["detail"].lower()


# =============================================================== piata QUALIFY pe grupa
def test_qualify_market_rejected_at_bet_time_on_group_match(
    client, admin_headers, db_session, user_headers
) -> None:
    ids = _make_teams(db_session, 4)
    client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    with SessionLocal() as db:
        m = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().first()
        m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()
        match_id, home_id = m.id, m.home_team_id

    resp = _place(client, user_headers, match_id, [{"market": "QUALIFY", "pick": "HOME"}])
    assert resp.status_code == 400
    assert "grupă" in resp.json()["detail"] or "grupa" in resp.json()["detail"].lower()
    assert home_id  # doar ca sa fie folosita variabila


def test_qualify_market_not_available_in_matches_listing_for_group_match(
    client, admin_headers, db_session
) -> None:
    ids = _make_teams(db_session, 4)
    client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    with SessionLocal() as db:
        m = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().first()
        match_id = m.id

    resp = client.get(f"/api/matches/{match_id}")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "GROUP"


def test_qualify_selection_on_group_match_rejected_at_settlement(
    client, admin_headers, db_session, user_headers
) -> None:
    """Selectie QUALIFY corupta in DB (ar fi trebuit refuzata la pariere) -> decontarea da 400."""
    ids = _make_teams(db_session, 4)
    client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    with SessionLocal() as db:
        m = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().first()
        match_id = m.id

        from models import Ticket, TicketSelection, User

        user = db.execute(select(User).where(User.is_admin.is_(False))).scalar_one_or_none()
        if user is None:
            from services.security import hash_password

            user = User(email="corupt@mariusivan.ro", password_hash=hash_password("x" * 8), display_name="c")
            db.add(user)
            db.flush()
        ticket = Ticket(user_id=user.id, match_id=match_id, status="OPEN")
        ticket.selections.append(TicketSelection(market="QUALIFY", pick="HOME"))
        db.add(ticket)
        db.commit()

    resp = _settle(client, admin_headers, match_id, home_score=2, away_score=0)
    assert resp.status_code == 400


# ======================================================================= SCORER la grupa
def test_scorer_market_works_on_group_match_with_feg(
    client, admin_headers, db_session, feg_team, opponent_team, user_headers, players
) -> None:
    group = _generate_group_with_feg(client, admin_headers, db_session, feg_team, opponent_team)
    with SessionLocal() as db:
        m = (
            db.execute(
                select(Match).where(
                    Match.group_id == group["id"],
                    Match.home_team_id.in_([feg_team.id]) | Match.away_team_id.in_([feg_team.id]),
                )
            )
            .scalars()
            .first()
        )
        m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()
        match_id = m.id
        feg_is_home = m.home_team_id == feg_team.id

    scorer_id = players[0].id
    resp = _place(client, user_headers, match_id, [{"market": "SCORER", "pick": "SCORER", "player_id": scorer_id}])
    assert resp.status_code == 201, resp.text

    if feg_is_home:
        settle_resp = _settle(
            client, admin_headers, match_id, home_score=1, away_score=0,
            scorers=[{"player_id": scorer_id, "goals": 1}],
        )
    else:
        settle_resp = _settle(
            client, admin_headers, match_id, home_score=0, away_score=1,
            scorers=[{"player_id": scorer_id, "goals": 1}],
        )
    assert settle_resp.status_code == 200, settle_resp.text

    mine = client.get("/api/tickets/mine", headers=user_headers).json()
    ticket = next(t for t in mine if t["match_id"] == match_id)
    assert ticket["selections"][0]["is_correct"] is True
