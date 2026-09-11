"""Faza 4: bilete — validare selectii, GET /mine, my_ticket, izolare intre useri."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import ActivityLog
from tests.conftest import auth_header


def _place(client: TestClient, headers, match_id: int, selections):
    return client.post(
        "/api/tickets", headers=headers, json={"match_id": match_id, "selections": selections}
    )


# --------------------------------------------------------------------- auth needed
def test_ticket_endpoints_require_auth(client: TestClient) -> None:
    assert client.get("/api/tickets/mine").status_code == 401
    assert client.post("/api/tickets", json={"match_id": 1, "selections": []}).status_code == 401
    assert client.put("/api/tickets/1", json={"selections": []}).status_code == 401
    assert client.delete("/api/tickets/1").status_code == 401


# ------------------------------------------------------------------ validare intrare
def test_ticket_needs_at_least_one_selection(client, user_headers, scheduled_match) -> None:
    assert _place(client, user_headers, scheduled_match.id, []).status_code == 422


def test_two_selections_same_market_rejected(client, user_headers, scheduled_match) -> None:
    resp = _place(
        client,
        user_headers,
        scheduled_match.id,
        [{"market": "WINNER", "pick": "HOME"}, {"market": "WINNER", "pick": "AWAY"}],
    )
    assert resp.status_code == 422


def test_total_goals_needs_line(client, user_headers, scheduled_match) -> None:
    assert _place(
        client, user_headers, scheduled_match.id, [{"market": "TOTAL_GOALS", "pick": "OVER"}]
    ).status_code == 422


def test_invalid_pick_rejected(client, user_headers, scheduled_match) -> None:
    assert _place(
        client, user_headers, scheduled_match.id, [{"market": "WINNER", "pick": "MAYBE"}]
    ).status_code == 422


def test_scorer_with_unknown_player_rejected(client, user_headers, scheduled_match) -> None:
    resp = _place(
        client,
        user_headers,
        scheduled_match.id,
        [{"market": "SCORER", "pick": "SCORER", "player_id": 99999}],
    )
    assert resp.status_code == 400


def test_scorer_with_inactive_player_rejected(
    client, user_headers, db_session, scheduled_match, players
) -> None:
    players[0].is_active = False
    db_session.commit()
    resp = _place(
        client,
        user_headers,
        scheduled_match.id,
        [{"market": "SCORER", "pick": "SCORER", "player_id": players[0].id}],
    )
    assert resp.status_code == 400


def test_winner_rejected_on_tbd_match(client, user_headers, db_session, scheduled_match) -> None:
    scheduled_match.home_team_id = None
    db_session.commit()
    assert _place(
        client, user_headers, scheduled_match.id, [{"market": "WINNER", "pick": "HOME"}]
    ).status_code == 400


# ---------------------------------------------------------------------- happy path
def test_full_ticket_potential_points(client, user_headers, scheduled_match, players) -> None:
    resp = _place(
        client,
        user_headers,
        scheduled_match.id,
        [
            {"market": "WINNER", "pick": "DRAW"},       # 4
            {"market": "QUALIFY", "pick": "HOME"},      # 2
            {"market": "TOTAL_GOALS", "pick": "OVER", "line": 3.5},  # 4
            {"market": "BTTS", "pick": "YES"},          # 2
            {"market": "SCORER", "pick": "SCORER", "player_id": players[0].id},  # 5
        ],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["potential_points"] == 17  # maximul pe un meci FEG
    assert body["total_points"] is None
    scorer_sel = next(s for s in body["selections"] if s["market"] == "SCORER")
    assert scorer_sel["player_name"] == players[0].name
    assert scorer_sel["points"] == 5


def test_get_mine_returns_tickets_with_match_info(
    client, user_headers, scheduled_match
) -> None:
    _place(client, user_headers, scheduled_match.id, [{"market": "BTTS", "pick": "YES"}])
    mine = client.get("/api/tickets/mine", headers=user_headers).json()
    assert len(mine) == 1
    assert mine[0]["match"]["home_name"] == "FEG"
    assert mine[0]["match"]["stage_label"] == "Sferturi"


def test_matches_endpoint_includes_my_ticket_when_authed(
    client, user_headers, scheduled_match
) -> None:
    _place(
        client,
        user_headers,
        scheduled_match.id,
        [{"market": "WINNER", "pick": "HOME"}, {"market": "BTTS", "pick": "NO"}],
    )
    # anonim: fara my_ticket
    anon = client.get("/api/matches").json()
    assert all(m["my_ticket"] is None for m in anon)
    # autentificat: cu my_ticket
    authed = client.get("/api/matches", headers=user_headers).json()
    mine = next(m["my_ticket"] for m in authed if m["id"] == scheduled_match.id)
    assert mine["selection_count"] == 2
    assert mine["potential_points"] == 5  # 3 + 2
    assert mine["status"] == "OPEN"


def test_settings_points_endpoint_public(client: TestClient) -> None:
    pts = client.get("/api/settings/points").json()
    assert pts["pts.scorer"] == 5
    assert pts["pts.winner.draw"] == 4
    assert pts["pts.bonus.perfect"] == 0


# ----------------------------------------------------------------- izolare useri
def test_cannot_edit_another_users_ticket(
    client, user_headers, register_user, scheduled_match
) -> None:
    created = _place(client, user_headers, scheduled_match.id, [{"market": "WINNER", "pick": "HOME"}])
    ticket_id = created.json()["id"]

    _other, other_token = register_user(email="altul@mariusivan.ro", password="parolabuna1")
    other_headers = auth_header(other_token)

    assert client.put(
        f"/api/tickets/{ticket_id}",
        headers=other_headers,
        json={"selections": [{"market": "BTTS", "pick": "YES"}]},
    ).status_code == 404
    assert client.delete(f"/api/tickets/{ticket_id}", headers=other_headers).status_code == 404


def test_delete_ticket_removes_it_and_logs(client, user_headers, scheduled_match) -> None:
    created = _place(client, user_headers, scheduled_match.id, [{"market": "WINNER", "pick": "HOME"}])
    tid = created.json()["id"]
    assert client.delete(f"/api/tickets/{tid}", headers=user_headers).status_code == 200
    assert client.get("/api/tickets/mine", headers=user_headers).json() == []
    with SessionLocal() as db:
        actions = [a.action for a in db.execute(select(ActivityLog)).scalars()]
    assert "ticket.create" in actions and "ticket.delete" in actions


def test_ticket_on_missing_match_404(client, user_headers) -> None:
    assert _place(client, user_headers, 99999, [{"market": "BTTS", "pick": "YES"}]).status_code == 404


def test_concurrent_create_race_returns_409(
    client, user_headers, scheduled_match, monkeypatch
) -> None:
    """Simuleaza cursa: SELECT-ul nu gaseste biletul, dar INSERT-ul calca unique."""
    _place(client, user_headers, scheduled_match.id, [{"market": "WINNER", "pick": "HOME"}])
    # a doua oara, fortam ramura "creeaza" desi biletul exista deja
    import routers.tickets as tickets_router

    monkeypatch.setattr(tickets_router, "get_user_ticket_for_match", lambda *a, **k: None)
    resp = _place(client, user_headers, scheduled_match.id, [{"market": "BTTS", "pick": "NO"}])
    assert resp.status_code == 409
