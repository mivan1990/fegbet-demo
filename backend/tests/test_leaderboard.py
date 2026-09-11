"""Faza 6: clasamentul public.

Acceptanta din PLAN_SONNET.md: „clasamentul corespunde sumei bilelor".
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from database import SessionLocal
from models import Ticket, User
from tests.conftest import auth_header


def _place(client: TestClient, headers, match_id: int, selections) -> dict:
    resp = client.post(
        "/api/tickets", headers=headers, json={"match_id": match_id, "selections": selections}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _settle(client: TestClient, admin_headers, match_id: int, **body):
    return client.post(
        f"/api/admin/matches/{match_id}/settle", headers=admin_headers, json=body
    )


def _row(leaderboard: list[dict], name: str) -> dict:
    return next(r for r in leaderboard if r["display_name"] == name)


# --------------------------------------------------------------------------- acces
def test_leaderboard_is_public(client: TestClient) -> None:
    resp = client.get("/api/leaderboard")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_leaderboard_lists_all_active_users_ranked(client: TestClient, register_user) -> None:
    register_user(email="a@mariusivan.ro", display_name="Ana")
    register_user(email="b@mariusivan.ro", display_name="Bogdan")

    rows = client.get("/api/leaderboard").json()
    names = {r["display_name"] for r in rows}
    assert {"Ana", "Bogdan"} <= names
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    assert all(r["points"] == 0 for r in rows)


def test_leaderboard_excludes_inactive_users(
    client: TestClient, register_user, db_session
) -> None:
    register_user(email="gone@mariusivan.ro", display_name="Plecat")
    user = db_session.execute(select(User).where(User.email == "gone@mariusivan.ro")).scalar_one()
    user.is_active = False
    db_session.commit()

    names = {r["display_name"] for r in client.get("/api/leaderboard").json()}
    assert "Plecat" not in names


# -------------------------------------------------------- corespondenta cu biletele
def test_leaderboard_points_match_settled_tickets(
    client: TestClient, admin_headers, register_user, scheduled_match
) -> None:
    _u1, t1 = register_user(email="u1@mariusivan.ro", display_name="Unu")
    _u2, t2 = register_user(email="u2@mariusivan.ro", display_name="Doi")
    h1, h2 = auth_header(t1), auth_header(t2)

    # Unu: WINNER HOME (3) + OVER 1.5 (2)  -> la 2-1 ambele corecte = 5
    _place(client, h1, scheduled_match.id, [
        {"market": "WINNER", "pick": "HOME"},
        {"market": "TOTAL_GOALS", "pick": "OVER", "line": 1.5},
    ])
    # Doi: WINNER AWAY (gresit) + BTTS YES (corect la 2-1) = 2
    _place(client, h2, scheduled_match.id, [
        {"market": "WINNER", "pick": "AWAY"},
        {"market": "BTTS", "pick": "YES"},
    ])

    assert _settle(
        client, admin_headers, scheduled_match.id, home_score=2, away_score=1
    ).status_code == 200

    rows = client.get("/api/leaderboard").json()
    assert _row(rows, "Unu")["points"] == 5
    assert _row(rows, "Doi")["points"] == 2

    # fiecare rand == /api/auth/me
    assert _row(rows, "Unu")["points"] == client.get("/api/auth/me", headers=h1).json()["points"]

    # suma din clasament == suma total_points a biletelor decontate
    with SessionLocal() as db:
        db_sum = db.scalar(
            select(func.coalesce(func.sum(Ticket.total_points), 0)).where(
                Ticket.status == "SETTLED"
            )
        )
    assert sum(r["points"] for r in rows) == db_sum


def test_leaderboard_ordering_points_then_wins_then_name(
    client: TestClient, admin_headers, register_user, scheduled_match
) -> None:
    _a, ta = register_user(email="alfa@mariusivan.ro", display_name="Alfa")
    _b, tb = register_user(email="beta@mariusivan.ro", display_name="Beta")
    ha, hb = auth_header(ta), auth_header(tb)

    _place(client, ha, scheduled_match.id, [{"market": "WINNER", "pick": "HOME"}])  # 3
    _place(client, hb, scheduled_match.id, [{"market": "WINNER", "pick": "AWAY"}])  # 0

    _settle(client, admin_headers, scheduled_match.id, home_score=1, away_score=0)

    rows = client.get("/api/leaderboard").json()
    assert rows[0]["display_name"] == "Alfa"
    assert rows[0]["rank"] == 1
    assert _row(rows, "Alfa")["won_tickets"] == 1
    assert _row(rows, "Beta")["won_tickets"] == 0


def test_leaderboard_counts_tickets_and_selections(
    client: TestClient, admin_headers, register_user, scheduled_match
) -> None:
    _u, tok = register_user(email="stats@mariusivan.ro", display_name="Statistician")
    h = auth_header(tok)

    _place(client, h, scheduled_match.id, [
        {"market": "WINNER", "pick": "HOME"},   # corect la 2-0
        {"market": "BTTS", "pick": "YES"},      # gresit la 2-0
    ])
    _settle(client, admin_headers, scheduled_match.id, home_score=2, away_score=0)

    row = _row(client.get("/api/leaderboard").json(), "Statistician")
    assert row["tickets"] == 1
    assert row["settled_tickets"] == 1
    assert row["won_tickets"] == 1
    assert row["total_selections"] == 2
    assert row["correct_selections"] == 1


def test_leaderboard_ignores_open_tickets(
    client: TestClient, register_user, scheduled_match
) -> None:
    _u, tok = register_user(email="open@mariusivan.ro", display_name="Deschis")
    h = auth_header(tok)
    _place(client, h, scheduled_match.id, [{"market": "WINNER", "pick": "HOME"}])

    row = _row(client.get("/api/leaderboard").json(), "Deschis")
    assert row["points"] == 0
    assert row["tickets"] == 1
    assert row["settled_tickets"] == 0


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_leaderboard_is_read_only(client: TestClient, method: str) -> None:
    assert client.request(method, "/api/leaderboard").status_code == 405
