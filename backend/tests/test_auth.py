"""Faza 1: autentificare, regula de domeniu ascunsa, audit."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import ActivityLog, Player, Setting, Team, User
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, auth_header


# --------------------------------------------------------------------- inregistrare
def test_register_ok_with_allowed_domain(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register", json={"email": "Ion.Pop@mariusivan.ro", "password": "parolabuna1"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == "ion.pop@mariusivan.ro"  # normalizat lowercase
    assert data["user"]["display_name"] == "ion.pop"  # default = partea dinainte de @
    assert data["user"]["is_admin"] is False


def test_register_custom_display_name(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register",
        json={"email": "x@mariusivan.ro", "password": "parolabuna1", "display_name": "  Xulescu  "},
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["display_name"] == "Xulescu"


def test_register_wrong_domain_and_duplicate_have_identical_response(client: TestClient) -> None:
    ok = client.post(
        "/api/auth/register", json={"email": "real@mariusivan.ro", "password": "parolabuna1"}
    )
    assert ok.status_code == 201

    wrong_domain = client.post(
        "/api/auth/register", json={"email": "cineva@gmail.com", "password": "parolabuna1"}
    )
    duplicate = client.post(
        "/api/auth/register", json={"email": "real@mariusivan.ro", "password": "parolabuna1"}
    )

    assert wrong_domain.status_code == 400
    assert duplicate.status_code == 400
    # Mesaj IDENTIC — altfel s-ar putea deduce domeniul permis.
    assert wrong_domain.json() == duplicate.json()
    assert wrong_domain.json() == {"detail": "Nu am putut crea contul cu acest email."}


def test_register_domain_not_leaked_anywhere(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register", json={"email": "cineva@gmail.com", "password": "parolabuna1"}
    )
    assert "mariusivan.ro" not in resp.text
    # nici prin OpenAPI
    assert "mariusivan.ro" not in client.get("/openapi.json").text


def test_register_short_password_rejected(client: TestClient) -> None:
    resp = client.post("/api/auth/register", json={"email": "y@mariusivan.ro", "password": "scurt"})
    assert resp.status_code == 422


def test_register_not_persisted_on_wrong_domain(client: TestClient) -> None:
    client.post(
        "/api/auth/register", json={"email": "nu@gmail.com", "password": "parolabuna1"}
    )
    with SessionLocal() as db:
        assert db.execute(select(User).where(User.email == "nu@gmail.com")).scalar_one_or_none() is None


# ----------------------------------------------------------------------------- login
def test_login_ok(client: TestClient, register_user) -> None:
    register_user(email="log@mariusivan.ro", password="parolabuna1")
    resp = client.post("/api/auth/login", json={"email": "log@mariusivan.ro", "password": "parolabuna1"})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "log@mariusivan.ro"


def test_login_wrong_password(client: TestClient, register_user) -> None:
    register_user(email="log2@mariusivan.ro", password="parolabuna1")
    resp = client.post("/api/auth/login", json={"email": "log2@mariusivan.ro", "password": "gresita9"})
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Email sau parolă greșite."}


def test_login_unknown_user(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"email": "nimeni@mariusivan.ro", "password": "orice1234"})
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Email sau parolă greșite."}


def test_login_inactive_user_blocked(client: TestClient, register_user) -> None:
    register_user(email="inactiv@mariusivan.ro", password="parolabuna1")
    with SessionLocal() as db:
        u = db.execute(select(User).where(User.email == "inactiv@mariusivan.ro")).scalar_one()
        u.is_active = False
        db.commit()
    resp = client.post(
        "/api/auth/login", json={"email": "inactiv@mariusivan.ro", "password": "parolabuna1"}
    )
    assert resp.status_code == 403


def test_login_updates_last_login_at(client: TestClient, register_user) -> None:
    register_user(email="ll@mariusivan.ro", password="parolabuna1")
    client.post("/api/auth/login", json={"email": "ll@mariusivan.ro", "password": "parolabuna1"})
    with SessionLocal() as db:
        u = db.execute(select(User).where(User.email == "ll@mariusivan.ro")).scalar_one()
        assert u.last_login_at is not None


# -------------------------------------------------------------------------------- me
def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_current_user(client: TestClient, user_token: str) -> None:
    resp = client.get("/api/auth/me", headers=auth_header(user_token))
    assert resp.status_code == 200
    assert "password" not in resp.text and "hash" not in resp.text


def test_me_rejects_garbage_token(client: TestClient) -> None:
    assert client.get("/api/auth/me", headers=auth_header("nu-e-token")).status_code == 401


# ------------------------------------------------------------------ schimbare parola
def test_password_change_flow(client: TestClient, register_user) -> None:
    _user, token = register_user(email="pw@mariusivan.ro", password="parolaveche1")
    bad = client.put(
        "/api/auth/password",
        headers=auth_header(token),
        json={"old_password": "gresita1", "new_password": "parolanoua1"},
    )
    assert bad.status_code == 400

    ok = client.put(
        "/api/auth/password",
        headers=auth_header(token),
        json={"old_password": "parolaveche1", "new_password": "parolanoua1"},
    )
    assert ok.status_code == 200

    assert (
        client.post(
            "/api/auth/login", json={"email": "pw@mariusivan.ro", "password": "parolaveche1"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "pw@mariusivan.ro", "password": "parolanoua1"}
        ).status_code
        == 200
    )


def test_logout_logs_action(client: TestClient, user_token: str) -> None:
    assert client.post("/api/auth/logout", headers=auth_header(user_token)).status_code == 200


# -------------------------------------------------------------------- rate limiting
def test_register_rate_limited_after_5(client: TestClient) -> None:
    codes = [
        client.post(
            "/api/auth/register",
            json={"email": f"rl{i}@mariusivan.ro", "password": "parolabuna1"},
        ).status_code
        for i in range(7)
    ]
    assert codes[:5] == [201, 201, 201, 201, 201]
    assert 429 in codes[5:]
    # mesaj in romana, forma {"detail": ...}
    last = client.post(
        "/api/auth/register", json={"email": "rl99@mariusivan.ro", "password": "parolabuna1"}
    )
    assert last.status_code == 429
    assert "detail" in last.json()


def test_login_rate_limited_after_10(client: TestClient, register_user) -> None:
    register_user(email="rluser@mariusivan.ro", password="parolabuna1")
    codes = [
        client.post(
            "/api/auth/login", json={"email": "rluser@mariusivan.ro", "password": "gresita1"}
        ).status_code
        for _ in range(12)
    ]
    assert codes.count(401) == 10
    assert 429 in codes


# --------------------------------------------------------------------------- seed
def test_seed_creates_feg_team_players_settings_admin(client: TestClient) -> None:
    with SessionLocal() as db:
        feg = db.execute(select(Team).where(Team.is_feg.is_(True))).scalar_one()
        assert feg.name == "FEG"
        assert db.query(Player).filter(Player.team_id == feg.id).count() == 11
        assert {p.name for p in db.query(Player)} >= {"Andrei Mocanu", "Vlad Petrescu"}
        assert db.query(Setting).count() == 17  # + pts.group.qualify / pts.group.perfect (Faza 9)
        assert db.execute(select(Setting).where(Setting.key == "pts.scorer")).scalar_one().value == "5"
        admin = db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one()
        assert admin.is_admin is True


def test_seed_is_idempotent(client: TestClient) -> None:
    from database import SessionLocal as SL
    from seed import seed_all

    with SL() as db:
        seed_all(db)
        seed_all(db)
    with SL() as db:
        assert db.query(Player).count() == 11
        assert db.query(Team).filter(Team.is_feg.is_(True)).count() == 1


def test_admin_can_log_in_with_seeded_credentials(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["is_admin"] is True


# --------------------------------------------------------------------------- audit
def test_actions_are_written_to_activity_logs(client: TestClient, register_user) -> None:
    _user, token = register_user(email="audit@mariusivan.ro", password="parolabuna1")
    client.post("/api/auth/login", json={"email": "audit@mariusivan.ro", "password": "parolabuna1"})
    client.post("/api/auth/login", json={"email": "audit@mariusivan.ro", "password": "gresita1"})
    client.post("/api/auth/logout", headers=auth_header(token))
    client.put(
        "/api/auth/password",
        headers=auth_header(token),
        json={"old_password": "parolabuna1", "new_password": "parolabuna2"},
    )

    with SessionLocal() as db:
        actions = [a.action for a in db.execute(select(ActivityLog)).scalars()]

    for expected in (
        "auth.register",
        "auth.login",
        "auth.login_failed",
        "auth.logout",
        "auth.password_change",
    ):
        assert expected in actions, f"lipseste {expected} din {actions}"


def test_activity_log_has_ip_and_no_secrets(client: TestClient, register_user) -> None:
    register_user(email="ipcheck@mariusivan.ro", password="parolabuna1")
    with SessionLocal() as db:
        entry = db.execute(
            select(ActivityLog).where(ActivityLog.action == "auth.register")
        ).scalars().first()
        assert entry is not None
        assert entry.ip_address is not None
        assert "parolabuna1" not in entry.detail
        assert "hash" not in entry.detail.lower()
