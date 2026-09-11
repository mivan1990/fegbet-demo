"""Faza 4: blocarea biletului la ora de start — validare EXCLUSIV pe server."""
from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import Match, Ticket, utcnow
from tests.conftest import auth_header


def _winner_sel() -> dict:
    return {"market": "WINNER", "pick": "HOME"}


def _place(client: TestClient, headers, match_id: int, selections=None):
    return client.post(
        "/api/tickets",
        headers=headers,
        json={"match_id": match_id, "selections": selections or [_winner_sel()]},
    )


def test_can_place_ticket_before_start(client, user_headers, scheduled_match) -> None:
    resp = _place(client, user_headers, scheduled_match.id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "OPEN"
    assert body["potential_points"] == 3


def test_cannot_place_when_scheduled_in_the_past(
    client, user_headers, db_session, scheduled_match
) -> None:
    scheduled_match.scheduled_at = utcnow() - timedelta(minutes=1)
    db_session.commit()
    resp = _place(client, user_headers, scheduled_match.id)
    assert resp.status_code == 400
    assert "început" in resp.json()["detail"]


def test_cannot_place_without_scheduled_at(
    client, user_headers, db_session, scheduled_match
) -> None:
    scheduled_match.scheduled_at = None
    db_session.commit()
    assert _place(client, user_headers, scheduled_match.id).status_code == 400


def test_cannot_place_on_tbd_match(client, user_headers, db_session, scheduled_match) -> None:
    scheduled_match.away_team_id = None
    db_session.commit()
    resp = _place(client, user_headers, scheduled_match.id)
    assert resp.status_code == 400
    assert "echipe" in resp.json()["detail"].lower()


def test_update_and_delete_blocked_after_start(
    client, user_headers, db_session, scheduled_match
) -> None:
    created = _place(client, user_headers, scheduled_match.id)
    ticket_id = created.json()["id"]

    # meciul incepe
    scheduled_match.scheduled_at = utcnow() - timedelta(seconds=30)
    db_session.commit()

    put = client.put(
        f"/api/tickets/{ticket_id}",
        headers=user_headers,
        json={"selections": [{"market": "BTTS", "pick": "YES"}]},
    )
    assert put.status_code == 400
    delete = client.delete(f"/api/tickets/{ticket_id}", headers=user_headers)
    assert delete.status_code == 400

    # biletul a ramas neatins
    with SessionLocal() as db:
        ticket = db.get(Ticket, ticket_id)
        assert ticket is not None
        assert {s.market for s in ticket.selections} == {"WINNER"}


def test_status_live_locks_even_if_scheduled_future(
    client, user_headers, db_session, scheduled_match
) -> None:
    scheduled_match.status = "LIVE"
    db_session.commit()
    assert _place(client, user_headers, scheduled_match.id).status_code == 400


def test_repeated_editing_until_start(client, user_headers, scheduled_match) -> None:
    created = _place(client, user_headers, scheduled_match.id)
    tid = created.json()["id"]

    for pick in ("HOME", "AWAY", "DRAW", "HOME"):
        resp = client.put(
            f"/api/tickets/{tid}",
            headers=user_headers,
            json={"selections": [{"market": "WINNER", "pick": pick}]},
        )
        assert resp.status_code == 200
        assert resp.json()["selections"][0]["pick"] == pick

    # fiecare modificare s-a logat
    from models import ActivityLog

    with SessionLocal() as db:
        updates = db.execute(
            select(ActivityLog).where(ActivityLog.action == "ticket.update")
        ).scalars().all()
        assert len(updates) >= 4


def test_scorer_rejected_on_non_feg_match(
    client, user_headers, non_feg_match, players
) -> None:
    resp = _place(
        client,
        user_headers,
        non_feg_match.id,
        selections=[{"market": "SCORER", "pick": "SCORER", "player_id": players[0].id}],
    )
    assert resp.status_code == 400
    assert "marcator" in resp.json()["detail"].lower()


def test_one_ticket_per_user_per_match_post_replaces(
    client, user_headers, scheduled_match
) -> None:
    first = _place(client, user_headers, scheduled_match.id, [{"market": "WINNER", "pick": "HOME"}])
    second = _place(
        client, user_headers, scheduled_match.id, [{"market": "BTTS", "pick": "NO"}]
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]  # acelasi bilet, inlocuit

    with SessionLocal() as db:
        tickets = db.execute(
            select(Ticket).where(Ticket.match_id == scheduled_match.id)
        ).scalars().all()
        assert len(tickets) == 1
        assert {s.market for s in tickets[0].selections} == {"BTTS"}


def test_time_validation_is_server_side_only(client, user_headers, db_session, scheduled_match) -> None:
    """Chiar daca clientul trimite orice, serverul decide dupa scheduled_at din DB."""
    scheduled_match.scheduled_at = utcnow() - timedelta(hours=1)
    db_session.commit()
    resp = client.post(
        "/api/tickets",
        headers=user_headers,
        json={
            "match_id": scheduled_match.id,
            "selections": [_winner_sel()],
            "scheduled_at": (utcnow() + timedelta(days=5)).isoformat(),  # ignorat
        },
    )
    assert resp.status_code == 400
