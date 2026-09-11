"""Fixture-uri comune. DB SQLite pe fisier temporar, recreata la fiecare test."""
from __future__ import annotations

import os
import tempfile

# Mediul TREBUIE setat inainte de a importa `config` / `main`.
os.environ.setdefault("JWT_SECRET", "test-secret-cheie-suficient-de-lunga-0123456789")
os.environ.setdefault("ALLOWED_EMAIL_DOMAIN", "@mariusivan.ro")
os.environ.setdefault("ADMIN_EMAILS", "admin@mariusivan.ro")
os.environ.setdefault("ADMIN_PASSWORD", "parola-admin-de-test")
os.environ.setdefault("APP_NAME", "FEG BET (test)")
os.environ.setdefault("CORS_ORIGINS", "")

_TMPDIR = tempfile.mkdtemp(prefix="fegbet-test-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMPDIR}/test.db")

from collections.abc import Iterator  # noqa: E402
from datetime import timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from database import Base, SessionLocal, engine  # noqa: E402
import main  # noqa: E402
from models import Match, Player, Team, User, utcnow  # noqa: E402
from services.rate_limit import limiter  # noqa: E402

ADMIN_EMAIL = os.environ["ADMIN_EMAILS"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Fara asta, limitele se scurg intre teste."""
    limiter.reset()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """Client HTTP cu DB curata. Lifespan-ul ruleaza migrarea si seed-ul."""
    Base.metadata.drop_all(engine)
    with TestClient(main.app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def register_user(client: TestClient):
    """Inregistreaza un user si intoarce (user_dict, token)."""

    def _register(
        email: str = "colegul@mariusivan.ro",
        password: str = "parolabuna1",
        display_name: str | None = None,
    ) -> tuple[dict, str]:
        body: dict = {"email": email, "password": password}
        if display_name is not None:
            body["display_name"] = display_name
        resp = client.post("/api/auth/register", json=body)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        return data["user"], data["access_token"]

    return _register


@pytest.fixture()
def user_token(register_user) -> str:
    _user, token = register_user()
    return token


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    resp = client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token: str) -> dict[str, str]:
    return auth_header(admin_token)


@pytest.fixture()
def user_headers(user_token: str) -> dict[str, str]:
    return auth_header(user_token)


@pytest.fixture()
def db_session(client: TestClient) -> Iterator:
    """Sesiune DB directa pentru setup de test (client-ul asigura DB curata + seed)."""
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def feg_team(db_session) -> Team:
    return db_session.execute(select(Team).where(Team.is_feg.is_(True))).scalar_one()


@pytest.fixture()
def players(db_session, feg_team) -> list[Player]:
    return list(
        db_session.execute(select(Player).where(Player.team_id == feg_team.id)).scalars()
    )


@pytest.fixture()
def opponent_team(db_session) -> Team:
    team = Team(name="Contabilitate United", short_name="CU", is_feg=False, is_active=True)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture()
def scheduled_match(db_session, feg_team, opponent_team) -> Match:
    """Meci FEG vs advers, programat peste 2 zile, deschis la pariere."""
    match = Match(
        round_no=1,
        bracket_position=0,
        stage_label="Sferturi",
        home_team_id=feg_team.id,
        away_team_id=opponent_team.id,
        scheduled_at=utcnow() + timedelta(days=2),
        status="SCHEDULED",
        is_settled=False,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


@pytest.fixture()
def non_feg_match(db_session, opponent_team) -> Match:
    """Meci intre doua echipe adverse (fara FEG), programat peste 2 zile."""
    other = Team(name="HR United", short_name="HR", is_feg=False, is_active=True)
    db_session.add(other)
    db_session.flush()
    match = Match(
        round_no=1,
        bracket_position=1,
        stage_label="Sferturi",
        home_team_id=opponent_team.id,
        away_team_id=other.id,
        scheduled_at=utcnow() + timedelta(days=2),
        status="SCHEDULED",
        is_settled=False,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


@pytest.fixture()
def normal_user(register_user, db_session) -> User:
    user_dict, _token = register_user(email="colegul@mariusivan.ro", password="parolabuna1")
    return db_session.execute(select(User).where(User.id == user_dict["id"])).scalar_one()
