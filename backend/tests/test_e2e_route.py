"""Curatenie Sarcina 1 (decuplarea specurilor e2e de grupe): ruta de test
`POST /api/e2e/reset-groups` (routers/e2e.py) NU trebuie sa existe in aplicatie
decat cu `E2E_TEST_MODE=1` — testul de mai jos, care ruleaza in configuratia
IMPLICITA (variabila nesetata, ca in orice pornire normala/de productie), e cel mai
important test din tot ce ține de Sarcina 1: confirma ca ruta lipseste TOTAL din
routing, nu doar ca raspunde cu 403.

`services.groups.reset_all_groups` (functia pe care o cheama ruta) e testata direct,
fara HTTP — ruta insasi nu exista in app-ul de test (E2E_TEST_MODE nesetat), asa cum
trebuie.
"""
from __future__ import annotations

from sqlalchemy import select

from config import settings
from database import SessionLocal
from models import Group, GroupPrediction, GroupPredictionPick, GroupQualifier, Match, Team
from services.groups import reset_all_groups


def _make_teams(db_session, n: int, prefix: str = "Echipa") -> list[int]:
    ids = []
    for i in range(n):
        t = Team(name=f"{prefix} {i + 1}", short_name=f"{prefix[:1]}{i + 1}", is_active=True)
        db_session.add(t)
        db_session.flush()
        ids.append(t.id)
    db_session.commit()
    return ids


# ==================================================== ruta absenta in configuratia implicita
def test_e2e_test_mode_is_off_by_default() -> None:
    """Pytest ruleaza cu mediul de test din conftest.py, care NU seteaza
    E2E_TEST_MODE — exact ca pe serverul de productie."""
    assert settings.e2e_test_mode is False


def test_e2e_reset_route_not_registered_in_app_by_default() -> None:
    """CEL MAI IMPORTANT test al Sarcinii 1: fara `E2E_TEST_MODE=1`, ruta nu exista
    deloc in tabela de rutare a aplicatiei — verificat direct pe `main.app.routes`,
    nu doar prin codul HTTP intors (vezi cele doua teste de mai jos pentru de ce
    codul HTTP, singur, nu e o dovada suficienta)."""
    import main

    paths = {getattr(r, "path", None) for r in main.app.routes}
    assert "/api/e2e/reset-groups" not in paths


def test_e2e_reset_route_absent_by_default(client, admin_headers) -> None:
    """Fara `E2E_TEST_MODE=1`, ruta nu raspunde niciodata cu 200/2xx pentru POST —
    adica handler-ul de reset nu se executa niciodata.

    NU verificam strict 404: daca `frontend/dist` exista (build facut), fallback-ul
    SPA (`main.py`: `@app.get("/{full_path:path}")`) prinde ORICE path pentru GET —
    inclusiv `/api/e2e/reset-groups` — deci Starlette raspunde 405 (Method Not
    Allowed) unei cereri POST pe acel path, nu 404 (path „gasit", dar fara metoda
    POST). Fara `frontend/dist`, acelasi POST da 404 (nimic nu prinde path-ul).
    Ambele sunt corecte si echivalente ca garantie de siguranta: in NICIUN caz nu
    ajunge la `reset_all_groups`. Dovada tare, independenta de asta, e testul de mai
    sus (`main.app.routes`) si cel de mai jos (schema OpenAPI)."""
    resp = client.post("/api/e2e/reset-groups", headers=admin_headers)
    assert resp.status_code in (404, 405)


def test_e2e_reset_route_absent_even_without_auth(client) -> None:
    """La fel, dar fara token — tot 404/405, niciodata 401/403: ruta lipseste
    inainte de orice dependinta de autentificare (require_admin nici nu apuca sa se
    execute). Vezi comentariul din testul de mai sus pentru 404 vs 405."""
    resp = client.post("/api/e2e/reset-groups")
    assert resp.status_code in (404, 405)


def test_e2e_route_not_in_openapi_schema_by_default(client) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/e2e/reset-groups" not in schema["paths"]


# ==================================================== reset_all_groups (functie, fara HTTP)
def test_reset_all_groups_wipes_everything_unconditionally(client, admin_headers, db_session) -> None:
    """`reset_all_groups` nu verifica nimic (spre deosebire de `generate_groups`) —
    sterge tot chiar daca exista meciuri validate, pronosticuri SI o grupa finalizata."""
    ids = _make_teams(db_session, 4)
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    assert resp.status_code == 201, resp.text
    group = resp.json()[0]

    with SessionLocal() as db:
        from models import User

        user = User(email="reset-fixture@mariusivan.ro", password_hash="x", display_name="Fixture")
        db.add(user)
        db.flush()
        matches = db.execute(select(Match).where(Match.group_id == group["id"])).scalars().all()
        for m in matches:
            m.is_settled = True
            m.home_score, m.away_score = 1, 0
        pred = GroupPrediction(user_id=user.id, group_id=group["id"], status="OPEN")
        pred.picks.append(GroupPredictionPick(team_id=ids[0]))
        pred.picks.append(GroupPredictionPick(team_id=ids[1]))
        db.add(pred)
        db.add(GroupQualifier(group_id=group["id"], team_id=ids[0], rank=1))
        db.add(GroupQualifier(group_id=group["id"], team_id=ids[1], rank=2))
        db.commit()

        reset_all_groups(db)

    with SessionLocal() as db:
        assert db.execute(select(Group)).first() is None
        assert db.execute(select(Match).where(Match.phase == "GROUP")).first() is None
        assert db.execute(select(GroupPrediction)).first() is None
        assert db.execute(select(GroupPredictionPick)).first() is None
        assert db.execute(select(GroupQualifier)).first() is None
        for tid in ids:
            assert db.get(Team, tid).group_id is None
