"""Faza 9: pronosticuri de grupa — creare/editare/stergere + lock (PLAN_GRUPE.md 5.4)."""
from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import Group, GroupPrediction, GroupPredictionPick, Match, Team, utcnow
from tests.conftest import auth_header


def _make_teams(db_session, n: int, prefix: str = "Echipa") -> list[int]:
    ids = []
    for i in range(n):
        t = Team(name=f"{prefix} {i + 1}", short_name=f"{prefix[:1]}{i + 1}", is_active=True)
        db_session.add(t)
        db_session.flush()
        ids.append(t.id)
    db_session.commit()
    return ids


def _schedule_group_matches(db_session, group_id: int, *, delta: timedelta) -> None:
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.group_id == group_id)).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + delta
        db.commit()


def _generate_one_group(
    client: TestClient, admin_headers, db_session, *, scheduled: bool = True
) -> dict:
    """Genereaza o grupa de 4 echipe. Programata 2 zile in viitor implicit (nu blocheaza
    pronosticurile), decat daca scheduled=False (grupa "n-are inca program").
    """
    ids = _make_teams(db_session, 4)
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    assert resp.status_code == 201, resp.text
    group = resp.json()[0]
    if scheduled:
        _schedule_group_matches(db_session, group["id"], delta=timedelta(days=2))
    return group


def _settle_one_match(client: TestClient, admin_headers, match_id: int) -> None:
    resp = client.post(
        f"/api/admin/matches/{match_id}/settle", headers=admin_headers,
        json={"home_score": 1, "away_score": 0},
    )
    assert resp.status_code == 200, resp.text


def _settle_all_matches_clear(client: TestClient, admin_headers, group_id: int, team_ids: list[int]) -> None:
    """Valideaza toate cele 6 meciuri ale grupei, fara ambiguitate de departajare: cu
    team_ids = [t1,t2,t3,t4] castiga mereu echipa cu indice mai mic (t1 > t2 > t3 > t4),
    la fel ca `_clear_win_scorelines` din test_group_finalize.py."""
    t1, t2, t3, t4 = team_ids
    scorelines = {
        frozenset((t1, t4)): (3, 0),
        frozenset((t2, t3)): (2, 0),
        frozenset((t4, t3)): (0, 1),  # t3 bate t4
        frozenset((t1, t2)): (2, 0),
        frozenset((t2, t4)): (2, 0),
        frozenset((t3, t1)): (0, 3),  # t1 bate t3
    }
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.group_id == group_id)).scalars().all()
        by_pair = {frozenset((m.home_team_id, m.away_team_id)): m for m in matches}
    for pair, m in by_pair.items():
        home, away = scorelines[pair]
        resp = client.post(
            f"/api/admin/matches/{m.id}/settle", headers=admin_headers,
            json={"home_score": home, "away_score": away},
        )
        assert resp.status_code == 200, resp.text


def _get_group(client: TestClient, group_id: int) -> dict:
    resp = client.get(f"/api/groups/{group_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ==================================================================== creare
def test_create_prediction_happy_path(client, admin_headers, db_session, user_headers) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    team_ids = [t["id"] for t in group["teams"][:2]]
    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["group_id"] == group["id"]
    assert body["status"] == "OPEN"
    assert sorted(p["team_id"] for p in body["picks"]) == sorted(team_ids)
    assert body["potential_points"] == 2 * 2  # 2 echipe x pts.group.qualify (default 2)


def test_group_out_lock_reasons_are_none_when_open(client, admin_headers, db_session) -> None:
    """Curatenie Sarcina 2: `GroupOut.lock_reason` / `missed_prediction_reason` sunt
    None cat timp grupa e deschisa — abia cand se blocheaza capata text."""
    group = _generate_one_group(client, admin_headers, db_session)
    body = _get_group(client, group["id"])
    assert body["is_locked"] is False
    assert body["lock_reason"] is None
    assert body["missed_prediction_reason"] is None


def test_create_prediction_requires_auth(client, admin_headers, db_session) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    team_ids = [t["id"] for t in group["teams"][:2]]
    resp = client.post(
        "/api/group-predictions", json={"group_id": group["id"], "team_ids": team_ids}
    )
    assert resp.status_code == 401


def test_create_prediction_wrong_count_rejected(client, admin_headers, db_session, user_headers) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    team_ids = [t["id"] for t in group["teams"][:1]]  # trebuie 2
    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    )
    assert resp.status_code == 400
    assert "2 echipe" in resp.json()["detail"]


def test_create_prediction_duplicate_team_rejected(client, admin_headers, db_session, user_headers) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    tid = group["teams"][0]["id"]
    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": [tid, tid]},
    )
    assert resp.status_code == 422  # respins de pydantic (field_validator)


def test_create_prediction_team_from_other_group_rejected(
    client, admin_headers, db_session, user_headers
) -> None:
    ids = _make_teams(db_session, 8)
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={
            "groups": [
                {"name": "A", "team_ids": ids[0:4]},
                {"name": "B", "team_ids": ids[4:8]},
            ]
        },
    )
    groups = resp.json()
    group_a = next(g for g in groups if g["name"] == "A")
    outside_team_id = ids[4]  # din grupa B
    _schedule_group_matches(db_session, group_a["id"], delta=timedelta(days=2))

    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group_a["id"], "team_ids": [group_a["teams"][0]["id"], outside_team_id]},
    )
    assert resp.status_code == 400
    assert "din grupa asta" in resp.json()["detail"]


def test_create_prediction_unique_per_user_and_group(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    team_ids = [t["id"] for t in group["teams"][:2]]
    body = {"group_id": group["id"], "team_ids": team_ids}
    assert client.post("/api/group-predictions", headers=user_headers, json=body).status_code == 201
    resp = client.post("/api/group-predictions", headers=user_headers, json=body)
    assert resp.status_code == 409


def test_create_prediction_group_without_schedule_rejected(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session, scheduled=False)
    team_ids = [t["id"] for t in group["teams"][:2]]
    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    )
    assert resp.status_code == 400
    assert "program" in resp.json()["detail"].lower()


def test_create_prediction_blocked_after_group_started(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    _schedule_group_matches(db_session, group["id"], delta=timedelta(minutes=-5))
    team_ids = [t["id"] for t in group["teams"][:2]]
    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    )
    assert resp.status_code == 400
    assert "început" in resp.json()["detail"].lower()


def test_create_prediction_allowed_before_group_starts(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    _schedule_group_matches(db_session, group["id"], delta=timedelta(days=1))
    team_ids = [t["id"] for t in group["teams"][:2]]
    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    )
    assert resp.status_code == 201


# ============================================ blocare reala: meci validat / grupa finalizata
# Bug PLAN_GRUPE.md: `is_locked` se baza doar pe `locks_at <= now`. Daca adminul valideaza
# un meci inainte de ora programata (sau ora e gresita, in viitor), sau daca grupa e deja
# finalizata, pronosticul trebuia sa fie blocat oricum — nu doar dupa ceas.
def test_create_prediction_blocked_when_match_settled_before_scheduled_time(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)  # programat 2 zile in viitor
    match_id = group["matches"][0]["id"]
    _settle_one_match(client, admin_headers, match_id)

    team_ids = [t["id"] for t in group["teams"][:2]]
    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    )
    assert resp.status_code == 400
    assert "validat" in resp.json()["detail"].lower()

    body = _get_group(client, group["id"])
    assert body["is_locked"] is True
    # Sursa unica: `lock_reason` vine direct din `group_lock_reason`, gandit pentru
    # eroarea de mai sus ("nu mai poti SCHIMBA"); `missed_prediction_reason` e
    # formularea separata pentru un user fara pronostic deloc ("nu mai poti PUNE").
    assert body["lock_reason"] is not None and "schimb" in body["lock_reason"].lower()
    assert body["missed_prediction_reason"] is not None
    assert "schimb" not in body["missed_prediction_reason"].lower()
    assert "a început" in body["missed_prediction_reason"].lower()


def test_create_prediction_blocked_when_group_already_finalized(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)  # programat 2 zile in viitor
    team_ids = [t["id"] for t in group["teams"]]
    _settle_all_matches_clear(client, admin_headers, group["id"], team_ids)

    resp = client.post(f"/api/admin/groups/{group['id']}/finalize", headers=admin_headers, json={})
    assert resp.status_code == 200, resp.text

    resp = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids[:2]},
    )
    assert resp.status_code == 400
    assert "încheiat" in resp.json()["detail"].lower()

    body = _get_group(client, group["id"])
    assert body["is_locked"] is True
    assert body["locks_at"] is not None  # scheduled_at a ramas in viitor — nu ceasul blocheaza
    # Grupa finalizata s-a INCHEIAT, nu "a inceput" — bug-ul concret din Sarcina 2.
    assert body["lock_reason"] == "Grupa s-a încheiat — pronosticurile s-au închis."
    assert body["missed_prediction_reason"] == body["lock_reason"]


# ==================================================================== editare
def test_update_prediction_replaces_picks(client, admin_headers, db_session, user_headers) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    team_ids = [t["id"] for t in group["teams"]]
    created = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids[:2]},
    ).json()

    resp = client.put(
        f"/api/group-predictions/{created['id']}", headers=user_headers,
        json={"team_ids": team_ids[2:4]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert sorted(p["team_id"] for p in body["picks"]) == sorted(team_ids[2:4])


def test_update_prediction_blocked_after_group_started(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    _schedule_group_matches(db_session, group["id"], delta=timedelta(days=1))
    team_ids = [t["id"] for t in group["teams"]]
    created = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids[:2]},
    ).json()

    _schedule_group_matches(db_session, group["id"], delta=timedelta(minutes=-1))
    resp = client.put(
        f"/api/group-predictions/{created['id']}", headers=user_headers,
        json={"team_ids": team_ids[2:4]},
    )
    assert resp.status_code == 400


def test_update_prediction_blocked_when_match_settled_before_scheduled_time(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)  # programat 2 zile in viitor
    team_ids = [t["id"] for t in group["teams"]]
    created = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids[:2]},
    ).json()
    assert created["status"] == "OPEN"

    _settle_one_match(client, admin_headers, group["matches"][0]["id"])

    resp = client.put(
        f"/api/group-predictions/{created['id']}", headers=user_headers,
        json={"team_ids": team_ids[2:4]},
    )
    assert resp.status_code == 400
    assert "validat" in resp.json()["detail"].lower()


def test_update_prediction_blocked_when_group_already_finalized(
    client, admin_headers, db_session, user_headers
) -> None:
    """Regresie: finalize_group deconteaza (SETTLED) toate pronosticurile existente ale
    grupei, deci in flux normal un PUT pe ele pica deja pe verificarea de status. Ca sa
    testam izolat garda noua din assert_group_open_for_prediction (nu doar verificarea de
    status), inseram direct in DB un pronostic OPEN pe o grupa deja finalizata — stare care
    nu ar trebui sa poata aparea prin API dupa fix-ul de la Sarcina 1, dar routerul trebuie
    sa refuze editarea lui oricum, ca a doua linie de aparare."""
    group = _generate_one_group(client, admin_headers, db_session)  # programat 2 zile in viitor
    team_ids = [t["id"] for t in group["teams"]]
    _settle_all_matches_clear(client, admin_headers, group["id"], team_ids)
    resp = client.post(f"/api/admin/groups/{group['id']}/finalize", headers=admin_headers, json={})
    assert resp.status_code == 200, resp.text

    admin_id = client.get("/api/auth/me", headers=admin_headers).json()["id"]
    with SessionLocal() as db:
        stray = GroupPrediction(user_id=admin_id, group_id=group["id"], status="OPEN")
        stray.picks.append(GroupPredictionPick(team_id=team_ids[0]))
        stray.picks.append(GroupPredictionPick(team_id=team_ids[1]))
        db.add(stray)
        db.commit()
        stray_id = stray.id

    resp = client.put(
        f"/api/group-predictions/{stray_id}", headers=admin_headers,
        json={"team_ids": team_ids[2:4]},
    )
    assert resp.status_code == 400
    assert "încheiat" in resp.json()["detail"].lower()


def test_update_prediction_not_owner_returns_404(
    client, admin_headers, db_session, user_headers, register_user
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    team_ids = [t["id"] for t in group["teams"]]
    created = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids[:2]},
    ).json()

    _other, other_token = register_user(email="altul@mariusivan.ro")
    other_headers = auth_header(other_token)
    resp = client.put(
        f"/api/group-predictions/{created['id']}", headers=other_headers,
        json={"team_ids": team_ids[2:4]},
    )
    assert resp.status_code == 404


# ==================================================================== stergere
def test_delete_prediction(client, admin_headers, db_session, user_headers) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    team_ids = [t["id"] for t in group["teams"][:2]]
    created = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    ).json()

    resp = client.delete(f"/api/group-predictions/{created['id']}", headers=user_headers)
    assert resp.status_code == 200
    assert client.get("/api/group-predictions/mine", headers=user_headers).json() == []


def test_delete_prediction_blocked_after_group_started(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    _schedule_group_matches(db_session, group["id"], delta=timedelta(days=1))
    team_ids = [t["id"] for t in group["teams"][:2]]
    created = client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    ).json()

    _schedule_group_matches(db_session, group["id"], delta=timedelta(minutes=-1))
    resp = client.delete(f"/api/group-predictions/{created['id']}", headers=user_headers)
    assert resp.status_code == 400


def test_mine_requires_auth(client) -> None:
    resp = client.get("/api/group-predictions/mine")
    assert resp.status_code == 401


def test_group_out_includes_my_prediction_when_authenticated(
    client, admin_headers, db_session, user_headers
) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    team_ids = [t["id"] for t in group["teams"][:2]]
    client.post(
        "/api/group-predictions", headers=user_headers,
        json={"group_id": group["id"], "team_ids": team_ids},
    )
    resp = client.get(f"/api/groups/{group['id']}", headers=user_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["my_prediction"] is not None
    assert sorted(p["team_id"] for p in body["my_prediction"]["picks"]) == sorted(team_ids)


def test_group_out_my_prediction_null_when_anonymous(client, admin_headers, db_session) -> None:
    group = _generate_one_group(client, admin_headers, db_session)
    resp = client.get(f"/api/groups/{group['id']}")
    assert resp.status_code == 200
    assert resp.json()["my_prediction"] is None
