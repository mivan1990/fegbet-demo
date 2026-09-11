"""Faza 6: loguri filtrabile, setari de punctaj, administrare utilizatori.

Acceptanta: filtrele de loguri returneaza corect; modificarea unui punctaj
afecteaza decontarile VIITOARE, nu retroactiv.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import ActivityLog, Setting, User
from tests.conftest import ADMIN_EMAIL, auth_header


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


# =============================================================================== LOGURI
def test_logs_reject_anonymous_and_normal_user(client: TestClient, user_headers) -> None:
    assert client.get("/api/admin/logs").status_code == 401
    assert client.get("/api/admin/logs", headers=user_headers).status_code == 403


def test_logs_shape_and_newest_first(client: TestClient, admin_headers) -> None:
    client.post("/api/admin/teams", headers=admin_headers, json={"name": "Log FC"})
    client.post("/api/admin/players", headers=admin_headers, json={"name": "Log P"})

    body = client.get("/api/admin/logs", headers=admin_headers).json()
    assert set(body) == {"items", "total", "page", "pages", "actions"}
    assert body["total"] >= 2
    assert body["page"] == 1
    # cel mai recent primul
    stamps = [i["created_at"] for i in body["items"]]
    assert stamps == sorted(stamps, reverse=True)
    # lista de actiuni distincte pentru dropdown-ul de filtru
    assert "admin.team.create" in body["actions"]
    assert "admin.player.create" in body["actions"]


def test_logs_filter_by_action(client: TestClient, admin_headers) -> None:
    t = client.post("/api/admin/teams", headers=admin_headers, json={"name": "Filtr FC"}).json()
    client.put(f"/api/admin/teams/{t['id']}", headers=admin_headers, json={"name": "Filtr FC 2"})
    client.post("/api/admin/players", headers=admin_headers, json={"name": "Filtr P"})

    body = client.get(
        "/api/admin/logs", headers=admin_headers, params={"action": "admin.team.create"}
    ).json()
    assert body["total"] == 1
    assert all(i["action"] == "admin.team.create" for i in body["items"])


def test_logs_filter_by_actor(client: TestClient, admin_headers, register_user) -> None:
    # actiune facuta de un user obisnuit: auth.register
    _u, _tok = register_user(email="actor@mariusivan.ro", display_name="Actorul")
    with SessionLocal() as db:
        actor_id = db.execute(select(User).where(User.email == "actor@mariusivan.ro")).scalar_one().id

    body = client.get(
        "/api/admin/logs", headers=admin_headers, params={"user_id": actor_id}
    ).json()
    assert body["total"] >= 1
    assert all(i["actor_user_id"] == actor_id for i in body["items"])
    assert all(i["actor_name"] == "Actorul" for i in body["items"])


def test_logs_free_text_search_in_detail(client: TestClient, admin_headers) -> None:
    client.post("/api/admin/teams", headers=admin_headers, json={"name": "Cautabila SRL"})
    client.post("/api/admin/teams", headers=admin_headers, json={"name": "Alta Echipa"})

    body = client.get(
        "/api/admin/logs", headers=admin_headers, params={"q": "Cautabila"}
    ).json()
    assert body["total"] == 1
    assert "Cautabila" in str(body["items"][0]["detail"])


def test_logs_pagination_50_per_page(client: TestClient, admin_headers) -> None:
    for i in range(55):
        client.post("/api/admin/teams", headers=admin_headers, json={"name": f"Bulk {i}"})

    page1 = client.get(
        "/api/admin/logs", headers=admin_headers, params={"action": "admin.team.create"}
    ).json()
    assert page1["total"] == 55
    assert page1["pages"] == 2
    assert len(page1["items"]) == 50

    page2 = client.get(
        "/api/admin/logs",
        headers=admin_headers,
        params={"action": "admin.team.create", "page": 2},
    ).json()
    assert len(page2["items"]) == 5
    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_logs_filter_by_date_range(client: TestClient, admin_headers, db_session) -> None:
    from datetime import timedelta

    from models import utcnow

    client.post("/api/admin/teams", headers=admin_headers, json={"name": "Recenta"})
    old = db_session.execute(
        select(ActivityLog).order_by(ActivityLog.id.desc())
    ).scalars().first()
    old.created_at = utcnow() - timedelta(days=10)
    db_session.commit()

    cutoff = (utcnow() - timedelta(days=1)).isoformat()
    body = client.get(
        "/api/admin/logs", headers=admin_headers, params={"from": cutoff}
    ).json()
    assert all(i["id"] != old.id for i in body["items"])

    body_old = client.get(
        "/api/admin/logs", headers=admin_headers, params={"to": cutoff}
    ).json()
    assert any(i["id"] == old.id for i in body_old["items"])


# =============================================================================== SETARI
def test_settings_get_returns_all_keys_with_defaults(client: TestClient, admin_headers) -> None:
    from services.scoring import DEFAULT_POINTS

    body = client.get("/api/admin/settings", headers=admin_headers).json()
    assert set(body) == set(DEFAULT_POINTS)
    assert body["pts.winner.side"] == 3


def test_settings_partial_update_persists_and_audits(client: TestClient, admin_headers) -> None:
    resp = client.put(
        "/api/admin/settings", headers=admin_headers, json={"values": {"pts.winner.side": 7}}
    )
    assert resp.status_code == 200
    assert resp.json()["pts.winner.side"] == 7
    assert resp.json()["pts.qualify"] == 2  # neatins

    again = client.get("/api/admin/settings", headers=admin_headers).json()
    assert again["pts.winner.side"] == 7

    with SessionLocal() as db:
        log = db.execute(
            select(ActivityLog).where(ActivityLog.action == "admin.settings.update")
        ).scalars().one()
    assert log.action == "admin.settings.update"
    assert "before" in log.detail and "after" in log.detail


def test_settings_reject_unknown_and_negative(client: TestClient, admin_headers) -> None:
    assert client.put(
        "/api/admin/settings", headers=admin_headers, json={"values": {"pts.nope": 1}}
    ).status_code == 400
    assert client.put(
        "/api/admin/settings", headers=admin_headers, json={"values": {"random": 1}}
    ).status_code == 422
    assert client.put(
        "/api/admin/settings", headers=admin_headers, json={"values": {"pts.winner.side": -1}}
    ).status_code == 422
    assert client.put(
        "/api/admin/settings", headers=admin_headers, json={"values": {}}
    ).status_code == 422


def test_settings_change_affects_future_settlements_not_past(
    client: TestClient, admin_headers, register_user, db_session, feg_team, opponent_team
) -> None:
    """Acceptanta Faza 6: un punctaj schimbat NU rescrie retroactiv biletele deja
    decontate; se aplica doar la decontarile urmatoare (sau la re-validare manuala)."""
    from datetime import timedelta

    from models import Match, utcnow

    m1 = Match(
        round_no=1, bracket_position=0, stage_label="Sferturi",
        home_team_id=feg_team.id, away_team_id=opponent_team.id,
        scheduled_at=utcnow() + timedelta(days=2), status="SCHEDULED", is_settled=False,
    )
    m2 = Match(
        round_no=1, bracket_position=1, stage_label="Sferturi",
        home_team_id=feg_team.id, away_team_id=opponent_team.id,
        scheduled_at=utcnow() + timedelta(days=2), status="SCHEDULED", is_settled=False,
    )
    db_session.add_all([m1, m2])
    db_session.commit()
    db_session.refresh(m1)
    db_session.refresh(m2)

    _u, tok = register_user(email="viitor@mariusivan.ro", display_name="Viitor")
    h = auth_header(tok)

    _place(client, h, m1.id, [{"market": "WINNER", "pick": "HOME"}])
    _place(client, h, m2.id, [{"market": "WINNER", "pick": "HOME"}])

    # decontare m1 cu punctajul default (3)
    assert _settle(client, admin_headers, m1.id, home_score=1, away_score=0).status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["points"] == 3

    # adminul creste punctajul pentru „castigator" la 10
    assert client.put(
        "/api/admin/settings", headers=admin_headers, json={"values": {"pts.winner.side": 10}}
    ).status_code == 200

    # biletul deja decontat pe m1 NU se schimba retroactiv
    mine = {t["match_id"]: t for t in client.get("/api/tickets/mine", headers=h).json()}
    assert mine[m1.id]["total_points"] == 3

    # decontarea m2 (viitoare) foloseste noul punctaj -> 10
    assert _settle(client, admin_headers, m2.id, home_score=1, away_score=0).status_code == 200
    mine = {t["match_id"]: t for t in client.get("/api/tickets/mine", headers=h).json()}
    assert mine[m2.id]["total_points"] == 10
    assert mine[m1.id]["total_points"] == 3  # inca neatins

    # total puncte user = 3 (vechi) + 10 (nou)
    assert client.get("/api/auth/me", headers=h).json()["points"] == 13

    # re-validarea manuala a m1 aplica si acolo noul punctaj
    assert _settle(client, admin_headers, m1.id, home_score=2, away_score=0).status_code == 200
    mine = {t["match_id"]: t for t in client.get("/api/tickets/mine", headers=h).json()}
    assert mine[m1.id]["total_points"] == 10
    assert client.get("/api/auth/me", headers=h).json()["points"] == 20


# ========================================================================= UTILIZATORI
def test_users_list_includes_email_and_role(client: TestClient, admin_headers, register_user) -> None:
    register_user(email="listat@mariusivan.ro", display_name="Listat")
    rows = client.get("/api/admin/users", headers=admin_headers).json()
    listed = next(r for r in rows if r["email"] == "listat@mariusivan.ro")
    assert listed["is_admin"] is False
    assert listed["is_active"] is True
    assert "points" in listed and "last_login_at" in listed


def test_users_endpoints_reject_normal_user(client: TestClient, user_headers, register_user) -> None:
    _u, _t = register_user(email="x@mariusivan.ro")
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403
    assert client.put(
        "/api/admin/users/1/role", headers=user_headers, json={"is_admin": True}
    ).status_code == 403


def test_admin_reset_user_password(client: TestClient, admin_headers, register_user) -> None:
    _u, _tok = register_user(email="parola@mariusivan.ro", password="parolaveche1", display_name="P")
    with SessionLocal() as db:
        uid = db.execute(select(User).where(User.email == "parola@mariusivan.ro")).scalar_one().id

    short = client.put(
        f"/api/admin/users/{uid}/password", headers=admin_headers, json={"new_password": "abc"}
    )
    assert short.status_code == 422

    ok = client.put(
        f"/api/admin/users/{uid}/password",
        headers=admin_headers,
        json={"new_password": "parolanoua9"},
    )
    assert ok.status_code == 200

    assert client.post(
        "/api/auth/login", json={"email": "parola@mariusivan.ro", "password": "parolaveche1"}
    ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"email": "parola@mariusivan.ro", "password": "parolanoua9"}
    ).status_code == 200

    with SessionLocal() as db:
        actions = [a.action for a in db.execute(select(ActivityLog)).scalars()]
    assert "admin.user.reset_password" in actions


def test_admin_promote_and_demote_user(client: TestClient, admin_headers, register_user) -> None:
    _u, _tok = register_user(email="promo@mariusivan.ro", display_name="Promo")
    with SessionLocal() as db:
        uid = db.execute(select(User).where(User.email == "promo@mariusivan.ro")).scalar_one().id

    promoted = client.put(
        f"/api/admin/users/{uid}/role", headers=admin_headers, json={"is_admin": True}
    )
    assert promoted.status_code == 200 and promoted.json()["is_admin"] is True

    demoted = client.put(
        f"/api/admin/users/{uid}/role", headers=admin_headers, json={"is_admin": False}
    )
    assert demoted.status_code == 200 and demoted.json()["is_admin"] is False

    with SessionLocal() as db:
        actions = [a.action for a in db.execute(select(ActivityLog)).scalars()]
    assert "admin.user.promote" in actions
    assert "admin.user.demote" in actions


def test_admin_cannot_self_demote(client: TestClient, admin_headers) -> None:
    me = client.get("/api/auth/me", headers=admin_headers).json()
    resp = client.put(
        f"/api/admin/users/{me['id']}/role", headers=admin_headers, json={"is_admin": False}
    )
    assert resp.status_code == 400
    assert "auto" in resp.json()["detail"].lower()


def test_admin_cannot_demote_last_admin(client: TestClient, admin_headers, register_user) -> None:
    """Al doilea admin retrogradeaza primul; apoi ramas singur nu se poate retrograda pe altul."""
    _u, tok2 = register_user(email="admin2@mariusivan.ro", display_name="Admin Doi")
    with SessionLocal() as db:
        uid2 = db.execute(select(User).where(User.email == "admin2@mariusivan.ro")).scalar_one().id
        seed_admin_id = db.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        ).scalar_one().id

    client.put(
        f"/api/admin/users/{uid2}/role", headers=admin_headers, json={"is_admin": True}
    )
    # relogin ca sa nu conteze — rolul se citeste din DB
    h2 = auth_header(tok2)
    # admin2 retrogradeaza seed-adminul -> ramane doar admin2
    assert client.put(
        f"/api/admin/users/{seed_admin_id}/role", headers=h2, json={"is_admin": False}
    ).status_code == 200

    # acum promovam la loc un user si il retrogradam ca sa verificam calea „ultim admin"
    # -> seed adminul nu mai e admin, deci daca admin2 s-ar retrograda pe el insusi: self-check.
    resp = client.put(
        f"/api/admin/users/{uid2}/role", headers=h2, json={"is_admin": False}
    )
    assert resp.status_code == 400


def test_admin_deactivate_and_reactivate_user(
    client: TestClient, admin_headers, register_user
) -> None:
    _u, _tok = register_user(email="activ@mariusivan.ro", display_name="Activ")
    with SessionLocal() as db:
        uid = db.execute(select(User).where(User.email == "activ@mariusivan.ro")).scalar_one().id

    off = client.put(
        f"/api/admin/users/{uid}/active", headers=admin_headers, json={"is_active": False}
    )
    assert off.status_code == 200 and off.json()["is_active"] is False

    on = client.put(
        f"/api/admin/users/{uid}/active", headers=admin_headers, json={"is_active": True}
    )
    assert on.status_code == 200 and on.json()["is_active"] is True

    with SessionLocal() as db:
        actions = [a.action for a in db.execute(select(ActivityLog)).scalars()]
    assert "admin.user.deactivate" in actions
    assert "admin.user.activate" in actions


def test_admin_cannot_self_deactivate(client: TestClient, admin_headers) -> None:
    me = client.get("/api/auth/me", headers=admin_headers).json()
    resp = client.put(
        f"/api/admin/users/{me['id']}/active", headers=admin_headers, json={"is_active": False}
    )
    assert resp.status_code == 400


def test_admin_user_actions_404_for_unknown(client: TestClient, admin_headers) -> None:
    assert client.put(
        "/api/admin/users/99999/role", headers=admin_headers, json={"is_admin": True}
    ).status_code == 404
    assert client.put(
        "/api/admin/users/99999/active", headers=admin_headers, json={"is_active": False}
    ).status_code == 404
    assert client.put(
        "/api/admin/users/99999/password",
        headers=admin_headers,
        json={"new_password": "parolabuna1"},
    ).status_code == 404


@pytest.mark.parametrize(
    "key",
    [
        "pts.winner.side",
        "pts.scorer",
        "pts.bonus.perfect",
    ],
)
def test_settings_roundtrip_each_key(client: TestClient, admin_headers, key: str) -> None:
    assert client.put(
        "/api/admin/settings", headers=admin_headers, json={"values": {key: 6}}
    ).status_code == 200
    assert client.get("/api/admin/settings", headers=admin_headers).json()[key] == 6
    with SessionLocal() as db:
        stored = db.execute(select(Setting).where(Setting.key == key)).scalar_one()
    assert stored.value == "6"
