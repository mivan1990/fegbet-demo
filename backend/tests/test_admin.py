"""Faza 2: CRUD admin (echipe, jucatori, meciuri) + protectii + izolare de rol."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import ActivityLog, Match, MatchScorer, Player, TicketSelection
from tests.conftest import auth_header


ADMIN_ENDPOINTS = [
    ("GET", "/api/admin/teams"),
    ("POST", "/api/admin/teams"),
    ("PUT", "/api/admin/teams/1"),
    ("DELETE", "/api/admin/teams/1"),
    ("GET", "/api/admin/players"),
    ("POST", "/api/admin/players"),
    ("PUT", "/api/admin/players/1"),
    ("DELETE", "/api/admin/players/1"),
    ("GET", "/api/admin/matches"),
    ("POST", "/api/admin/matches"),
    ("PUT", "/api/admin/matches/1"),
    ("DELETE", "/api/admin/matches/1"),
    ("PUT", "/api/admin/matches/1/schedule"),
    ("POST", "/api/admin/matches/1/settle"),
    ("POST", "/api/admin/bracket/generate"),
    ("GET", "/api/admin/stats"),
    ("GET", "/api/admin/logs"),
    ("GET", "/api/admin/settings"),
    ("PUT", "/api/admin/settings"),
    ("GET", "/api/admin/users"),
    ("PUT", "/api/admin/users/1/password"),
    ("PUT", "/api/admin/users/1/role"),
    ("PUT", "/api/admin/users/1/active"),
]


@pytest.mark.parametrize(("method", "path"), ADMIN_ENDPOINTS)
def test_admin_endpoints_reject_anonymous(client: TestClient, method: str, path: str) -> None:
    resp = client.request(method, path, json={})
    assert resp.status_code == 401, f"{method} {path}"


@pytest.mark.parametrize(("method", "path"), ADMIN_ENDPOINTS)
def test_admin_endpoints_reject_normal_user(
    client: TestClient, user_headers, method: str, path: str
) -> None:
    resp = client.request(method, path, headers=user_headers, json={})
    assert resp.status_code == 403, f"{method} {path}"


# --------------------------------------------------------------------------- echipe
def test_team_crud(client: TestClient, admin_headers) -> None:
    created = client.post(
        "/api/admin/teams", headers=admin_headers, json={"name": "Marketing", "short_name": "mkt"}
    )
    assert created.status_code == 201
    tid = created.json()["id"]
    assert created.json()["short_name"] == "MKT"  # normalizat uppercase

    updated = client.put(
        f"/api/admin/teams/{tid}", headers=admin_headers, json={"name": "Marketing FC"}
    )
    assert updated.status_code == 200 and updated.json()["name"] == "Marketing FC"

    listed = client.get("/api/admin/teams", headers=admin_headers)
    assert any(t["name"] == "Marketing FC" for t in listed.json())

    assert client.delete(f"/api/admin/teams/{tid}", headers=admin_headers).status_code == 200


def test_team_duplicate_name_rejected(client: TestClient, admin_headers) -> None:
    client.post("/api/admin/teams", headers=admin_headers, json={"name": "Dubla"})
    dup = client.post("/api/admin/teams", headers=admin_headers, json={"name": "Dubla"})
    assert dup.status_code == 409


def test_only_one_feg_team(client: TestClient, admin_headers) -> None:
    # exista deja echipa FEG din seed
    resp = client.post(
        "/api/admin/teams", headers=admin_headers, json={"name": "FEG 2", "is_feg": True}
    )
    assert resp.status_code == 409
    assert "doar una" in resp.json()["detail"].lower()


def test_cannot_delete_team_used_in_match(client: TestClient, admin_headers, scheduled_match) -> None:
    resp = client.delete(
        f"/api/admin/teams/{scheduled_match.away_team_id}", headers=admin_headers
    )
    assert resp.status_code == 409
    assert "meci" in resp.json()["detail"].lower()


def test_cannot_delete_team_with_players(client: TestClient, admin_headers, feg_team) -> None:
    resp = client.delete(f"/api/admin/teams/{feg_team.id}", headers=admin_headers)
    assert resp.status_code == 409
    assert "jucători" in resp.json()["detail"].lower()


# ------------------------------------------------------------------------- jucatori
def test_player_crud(client: TestClient, admin_headers) -> None:
    created = client.post(
        "/api/admin/players",
        headers=admin_headers,
        json={"name": "Test Jucator", "shirt_number": 7, "position": "att"},
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    assert created.json()["position"] == "ATT"

    updated = client.put(
        f"/api/admin/players/{pid}", headers=admin_headers, json={"position": "MID"}
    )
    assert updated.status_code == 200 and updated.json()["position"] == "MID"

    deleted = client.delete(f"/api/admin/players/{pid}", headers=admin_headers)
    assert deleted.status_code == 200 and deleted.json()["mode"] == "hard"


def test_player_invalid_position_rejected(client: TestClient, admin_headers) -> None:
    resp = client.post(
        "/api/admin/players", headers=admin_headers, json={"name": "X", "position": "ZZ"}
    )
    assert resp.status_code == 422


def test_player_soft_deleted_when_on_scoresheet(
    client: TestClient, admin_headers, db_session, players, scheduled_match
) -> None:
    scorer = players[0]
    db_session.add(MatchScorer(match_id=scheduled_match.id, player_id=scorer.id, goals=1))
    db_session.commit()

    resp = client.delete(f"/api/admin/players/{scorer.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["mode"] == "soft"

    with SessionLocal() as db:
        refreshed = db.get(Player, scorer.id)
        assert refreshed is not None and refreshed.is_active is False


# --------------------------------------------------------------------------- meciuri
def test_match_schedule_set_and_clear(client: TestClient, admin_headers, scheduled_match) -> None:
    when = "2026-09-20T15:30:00+00:00"
    resp = client.put(
        f"/api/admin/matches/{scheduled_match.id}/schedule",
        headers=admin_headers,
        json={"scheduled_at": when},
    )
    assert resp.status_code == 200
    assert resp.json()["scheduled_at"].startswith("2026-09-20T15:30")

    cleared = client.put(
        f"/api/admin/matches/{scheduled_match.id}/schedule",
        headers=admin_headers,
        json={"scheduled_at": None},
    )
    assert cleared.status_code == 200 and cleared.json()["scheduled_at"] is None
    assert cleared.json()["is_bettable"] is False


def test_match_update_blocked_when_settled(
    client: TestClient, admin_headers, db_session, scheduled_match
) -> None:
    scheduled_match.is_settled = True
    db_session.commit()
    resp = client.put(
        f"/api/admin/matches/{scheduled_match.id}",
        headers=admin_headers,
        json={"status": "CANCELLED"},
    )
    assert resp.status_code == 409


def test_match_delete_clears_incoming_links(client: TestClient, admin_headers, db_session) -> None:
    from models import Team

    teams = [Team(name=f"T{i}", is_active=True) for i in range(4)]
    db_session.add_all(teams)
    db_session.commit()
    ids = [t.id for t in teams]
    client.post(
        "/api/admin/bracket/generate",
        headers=admin_headers,
        json={"size": 4, "team_ids": ids},
    )
    with SessionLocal() as db:
        final = db.execute(select(Match).where(Match.round_no == 2)).scalars().one()
        semis_before = db.execute(select(Match).where(Match.next_match_id == final.id)).scalars().all()
        assert len(semis_before) == 2
        final_id = final.id

    assert client.delete(f"/api/admin/matches/{final_id}", headers=admin_headers).status_code == 200
    with SessionLocal() as db:
        orphaned = db.execute(select(Match).where(Match.round_no == 1)).scalars().all()
        assert all(m.next_match_id is None and m.next_slot is None for m in orphaned)


def test_match_delete_blocked_with_tickets(
    client: TestClient, admin_headers, db_session, scheduled_match, normal_user
) -> None:
    from models import Ticket

    db_session.add(Ticket(user_id=normal_user.id, match_id=scheduled_match.id, status="OPEN"))
    db_session.commit()
    resp = client.delete(f"/api/admin/matches/{scheduled_match.id}", headers=admin_headers)
    assert resp.status_code == 409


def test_match_create_and_update(client: TestClient, admin_headers, feg_team, opponent_team) -> None:
    created = client.post(
        "/api/admin/matches",
        headers=admin_headers,
        json={
            "round_no": 1,
            "bracket_position": 0,
            "stage_label": "Sferturi",
            "home_team_id": feg_team.id,
            "away_team_id": opponent_team.id,
        },
    )
    assert created.status_code == 201
    mid = created.json()["id"]
    assert created.json()["has_feg"] is True
    assert created.json()["is_bettable"] is False  # fara scheduled_at

    updated = client.put(
        f"/api/admin/matches/{mid}",
        headers=admin_headers,
        json={"status": "CANCELLED"},
    )
    assert updated.status_code == 200 and updated.json()["status"] == "CANCELLED"


def test_match_create_rejects_unknown_team(client: TestClient, admin_headers) -> None:
    resp = client.post(
        "/api/admin/matches",
        headers=admin_headers,
        json={"round_no": 1, "bracket_position": 0, "home_team_id": 88888},
    )
    assert resp.status_code == 400


def test_match_update_rejects_bad_status(client: TestClient, admin_headers, scheduled_match) -> None:
    resp = client.put(
        f"/api/admin/matches/{scheduled_match.id}",
        headers=admin_headers,
        json={"status": "BANANA"},
    )
    assert resp.status_code == 422


def test_match_create_rejects_bad_next_slot(client: TestClient, admin_headers) -> None:
    resp = client.post(
        "/api/admin/matches",
        headers=admin_headers,
        json={"round_no": 1, "bracket_position": 0, "next_slot": "left"},
    )
    assert resp.status_code == 422


def test_admin_stats(client: TestClient, admin_headers, scheduled_match) -> None:
    stats = client.get("/api/admin/stats", headers=admin_headers).json()
    assert stats["players"] == 11
    assert stats["teams"] >= 2
    assert stats["matches"] == 1
    assert stats["matches_settled"] == 0


# ------------------------------------------------------------------------- public GET
def test_public_teams_only_active(client: TestClient, admin_headers, opponent_team, db_session) -> None:
    opponent_team.is_active = False
    db_session.commit()
    names = [t["name"] for t in client.get("/api/teams").json()]
    assert "FEG" in names
    assert "Contabilitate United" not in names


def test_public_players_are_feg_and_active(client: TestClient) -> None:
    players = client.get("/api/players").json()
    assert len(players) == 11
    assert all(p["is_active"] for p in players)


def test_public_matches_and_bracket(client: TestClient, admin_headers, db_session) -> None:
    from models import Team

    teams = [Team(name=f"B{i}", is_active=True) for i in range(8)]
    db_session.add_all(teams)
    db_session.commit()
    client.post(
        "/api/admin/bracket/generate",
        headers=admin_headers,
        json={"size": 8, "team_ids": [t.id for t in teams]},
    )
    matches = client.get("/api/matches").json()
    assert len(matches) == 7
    assert all("is_locked" in m and "is_bettable" in m for m in matches)

    bracket = client.get("/api/bracket").json()
    assert [len(r["matches"]) for r in bracket] == [4, 2, 1]
    assert [r["stage_label"] for r in bracket] == ["Sferturi", "Semifinală", "Finală"]


def test_match_detail_404(client: TestClient) -> None:
    assert client.get("/api/matches/99999").status_code == 404


# --------------------------------------------------------------------------- audit
def test_admin_actions_are_audited(client: TestClient, admin_headers) -> None:
    t = client.post("/api/admin/teams", headers=admin_headers, json={"name": "Audit FC"}).json()
    client.put(f"/api/admin/teams/{t['id']}", headers=admin_headers, json={"name": "Audit FC 2"})
    client.delete(f"/api/admin/teams/{t['id']}", headers=admin_headers)
    p = client.post("/api/admin/players", headers=admin_headers, json={"name": "Aud P"}).json()

    with SessionLocal() as db:
        actions = [a.action for a in db.execute(select(ActivityLog)).scalars()]
    for expected in (
        "admin.team.create",
        "admin.team.update",
        "admin.team.delete",
        "admin.player.create",
    ):
        assert expected in actions
    assert p["id"]
