"""Faza 9: finalizarea grupei + decontarea pronosticurilor (PLAN_GRUPE.md 5.5-5.6)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from database import SessionLocal
from models import ActivityLog, GroupQualifier, Match, Team, utcnow
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


def _generate_group(client, admin_headers, db_session, team_ids: list[int] | None = None) -> dict:
    ids = team_ids or _make_teams(db_session, 4)
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    assert resp.status_code == 201, resp.text
    group = resp.json()[0]
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.group_id == group["id"])).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()
    return group


def _settle_all(client, admin_headers, group_id: int, scorelines: dict[frozenset, tuple[int, int]]) -> None:
    """scorelines: {frozenset({home_id,away_id}): (home_score, away_score) in ordinea din meci}."""
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


def _finalize(client, admin_headers, group_id: int, team_ids: list[int] | None = None):
    body = {"team_ids": team_ids} if team_ids is not None else {}
    return client.post(f"/api/admin/groups/{group_id}/finalize", headers=admin_headers, json=body)


def _place_prediction(client, headers, group_id: int, team_ids: list[int]):
    resp = client.post(
        "/api/group-predictions", headers=headers, json={"group_id": group_id, "team_ids": team_ids}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _clear_win_scorelines(ids: list[int]) -> dict[frozenset, tuple[int, int]]:
    """4 echipe [t1,t2,t3,t4]: t1 castiga tot, t2 al doilea, t3 al treilea, t4 ultimul.

    Rezultate simple, fara ambiguitate de departajare: fiecare meci il castiga
    echipa cu indice mai mic (t1>t2>t3>t4).
    """
    t1, t2, t3, t4 = ids
    return {
        frozenset((t1, t4)): (3, 0),
        frozenset((t2, t3)): (2, 0),
        frozenset((t4, t3)): (0, 1),  # t3 bate t4
        frozenset((t1, t2)): (2, 0),
        frozenset((t2, t4)): (2, 0),
        frozenset((t3, t1)): (0, 3),  # t1 bate t3
    }


# ==================================================================== validari
def test_finalize_requires_all_matches_settled(client, admin_headers, db_session) -> None:
    group = _generate_group(client, admin_headers, db_session)
    resp = _finalize(client, admin_headers, group["id"])
    assert resp.status_code == 400
    assert "6 meciuri" in resp.json()["detail"] or "nevalidate" in resp.json()["detail"].lower()


def test_finalize_requires_admin(client, user_headers, admin_headers, db_session) -> None:
    group = _generate_group(client, admin_headers, db_session)
    resp = client.post(f"/api/admin/groups/{group['id']}/finalize", headers=user_headers, json={})
    assert resp.status_code == 403


# ==================================================================== automat
def test_finalize_automatic_picks_top_qualifiers(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)
    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))

    resp = _finalize(client, admin_headers, group["id"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_finalized"] is True
    assert [t["id"] for t in body["qualified"]] == [ids[0], ids[1]]

    with SessionLocal() as db:
        quals = db.execute(
            select(GroupQualifier).where(GroupQualifier.group_id == group["id"]).order_by(GroupQualifier.rank)
        ).scalars().all()
        assert [(q.rank, q.team_id) for q in quals] == [(1, ids[0]), (2, ids[1])]


def test_finalize_ambiguous_returns_400_with_message(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)
    t1, t2, t3, t4 = ids
    # t4 pierde tot (0 pct); intre t1,t2,t3 (etapele contin exact meciurile t2-t3, t1-t2,
    # t3-t1) se joaca un ciclu perfect 1-0 -> raman nedepartajabile pe langa t4.
    # Scorurile sunt (home, away) in ordinea reala din round_robin_pairs.
    scorelines = {
        frozenset((t1, t4)): (1, 0),  # etapa1: t1(h) 1-0 t4(a)
        frozenset((t2, t3)): (1, 0),  # etapa1: t2(h) 1-0 t3(a)
        frozenset((t4, t3)): (0, 1),  # etapa2: t4(h) 0-1 t3(a)
        frozenset((t1, t2)): (1, 0),  # etapa2: t1(h) 1-0 t2(a)
        frozenset((t2, t4)): (1, 0),  # etapa3: t2(h) 1-0 t4(a)
        frozenset((t3, t1)): (1, 0),  # etapa3: t3(h) 1-0 t1(a)
    }
    _settle_all(client, admin_headers, group["id"], scorelines)

    resp = _finalize(client, admin_headers, group["id"])
    assert resp.status_code == 400
    assert "departaja" in resp.json()["detail"].lower()


# ==================================================================== manual
def test_finalize_manual_override_validated_and_logged_as_manual(
    client, admin_headers, db_session
) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)
    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))

    # suprascriere: alegem manual echipele 3 si 4 (nu cele calificate normal)
    resp = _finalize(client, admin_headers, group["id"], team_ids=[ids[2], ids[3]])
    assert resp.status_code == 200, resp.text
    assert sorted(t["id"] for t in resp.json()["qualified"]) == sorted([ids[2], ids[3]])

    with SessionLocal() as db:
        log = db.execute(
            select(ActivityLog).where(ActivityLog.action == "admin.group.finalize")
        ).scalars().first()
        assert log is not None
        import json

        detail = json.loads(log.detail)
        assert detail["manual"] is True


def test_finalize_manual_override_rejects_wrong_count(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)
    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))

    resp = _finalize(client, admin_headers, group["id"], team_ids=[ids[0]])
    assert resp.status_code == 400


def test_finalize_manual_override_rejects_team_outside_group(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)
    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))
    outsider = _make_teams(db_session, 1, prefix="Outsider")[0]

    resp = _finalize(client, admin_headers, group["id"], team_ids=[ids[0], outsider])
    assert resp.status_code == 400


# ==================================================================== decontare
def test_finalize_settles_predictions_correct_partial_wrong(
    client, admin_headers, db_session, register_user
) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)

    _u1, t1 = register_user(email="p1@mariusivan.ro")
    _u2, t2 = register_user(email="p2@mariusivan.ro")
    _u3, t3 = register_user(email="p3@mariusivan.ro")
    h1, h2, h3 = auth_header(t1), auth_header(t2), auth_header(t3)

    _place_prediction(client, h1, group["id"], [ids[0], ids[1]])  # ambele corecte
    _place_prediction(client, h2, group["id"], [ids[0], ids[2]])  # o corecta, una gresita
    _place_prediction(client, h3, group["id"], [ids[2], ids[3]])  # ambele gresite

    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))
    resp = _finalize(client, admin_headers, group["id"])
    assert resp.status_code == 200, resp.text

    mine1 = client.get("/api/group-predictions/mine", headers=h1).json()[0]
    mine2 = client.get("/api/group-predictions/mine", headers=h2).json()[0]
    mine3 = client.get("/api/group-predictions/mine", headers=h3).json()[0]

    assert mine1["status"] == "SETTLED" and mine1["total_points"] == 4  # 2 x pts.group.qualify(2)
    assert mine2["total_points"] == 2
    assert mine3["total_points"] == 0

    assert client.get("/api/auth/me", headers=h1).json()["points"] == 4
    assert client.get("/api/auth/me", headers=h2).json()["points"] == 2
    assert client.get("/api/auth/me", headers=h3).json()["points"] == 0


def test_finalize_perfect_bonus_when_enabled(
    client, admin_headers, db_session, register_user
) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)

    resp = client.put(
        "/api/admin/settings", headers=admin_headers, json={"values": {"pts.group.perfect": 5}}
    )
    assert resp.status_code == 200, resp.text

    _u, tok = register_user(email="perfect@mariusivan.ro")
    h = auth_header(tok)
    _place_prediction(client, h, group["id"], [ids[0], ids[1]])

    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))
    _finalize(client, admin_headers, group["id"])

    mine = client.get("/api/group-predictions/mine", headers=h).json()[0]
    assert mine["total_points"] == 4 + 5  # 2x2 + bonusul de 5


# ==================================================================== re-finalizare
def test_refinalize_does_not_double_points(client, admin_headers, db_session, register_user) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)

    _u, tok = register_user(email="refin@mariusivan.ro")
    h = auth_header(tok)
    _place_prediction(client, h, group["id"], [ids[0], ids[1]])

    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))
    _finalize(client, admin_headers, group["id"])
    assert client.get("/api/auth/me", headers=h).json()["points"] == 4

    # re-finalizare identica (acelasi rezultat) -> punctele NU se dubleaza
    resp = _finalize(client, admin_headers, group["id"])
    assert resp.status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["points"] == 4

    with SessionLocal() as db:
        actions = [a.action for a in db.execute(select(ActivityLog)).scalars()]
    assert actions.count("admin.group.finalize") == 2


def test_refinalize_with_different_qualifiers_updates_points_correctly(
    client, admin_headers, db_session, register_user
) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)

    _u, tok = register_user(email="switch@mariusivan.ro")
    h = auth_header(tok)
    _place_prediction(client, h, group["id"], [ids[2], ids[3]])  # picks gresite initial

    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))
    _finalize(client, admin_headers, group["id"])  # calificate reale: ids[0], ids[1]
    assert client.get("/api/auth/me", headers=h).json()["points"] == 0

    # suprascriere manuala: acum ids[2], ids[3] chiar se califica
    resp = _finalize(client, admin_headers, group["id"], team_ids=[ids[2], ids[3]])
    assert resp.status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["points"] == 4


# ============================================================= User.points = bilete+grupe
def test_user_points_combine_tickets_and_group_predictions(
    client, admin_headers, db_session, register_user, feg_team, opponent_team
) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)

    _u, tok = register_user(email="combo@mariusivan.ro")
    h = auth_header(tok)
    _place_prediction(client, h, group["id"], [ids[0], ids[1]])
    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))
    _finalize(client, admin_headers, group["id"])
    assert client.get("/api/auth/me", headers=h).json()["points"] == 4

    # + un bilet pe un meci knockout separat
    match = Match(
        round_no=1, bracket_position=0, stage_label="Semifinală", phase="KNOCKOUT",
        home_team_id=feg_team.id, away_team_id=opponent_team.id,
        scheduled_at=utcnow() + timedelta(days=1), status="SCHEDULED",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    client.post(
        "/api/tickets", headers=h,
        json={"match_id": match.id, "selections": [{"market": "WINNER", "pick": "HOME"}]},
    )
    client.post(
        f"/api/admin/matches/{match.id}/settle", headers=admin_headers,
        json={"home_score": 1, "away_score": 0},
    )
    # 4 (grupa) + 3 (WINNER HOME) = 7
    assert client.get("/api/auth/me", headers=h).json()["points"] == 7


# ==================================================================== leaderboard
def test_leaderboard_exposes_group_points_and_qualifier_counts(
    client, admin_headers, db_session, register_user
) -> None:
    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)

    _u, tok = register_user(email="lb@mariusivan.ro")
    h = auth_header(tok)
    _place_prediction(client, h, group["id"], [ids[0], ids[2]])  # 1 corecta, 1 gresita

    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))
    _finalize(client, admin_headers, group["id"])

    board = client.get("/api/leaderboard").json()
    row = next(r for r in board if r["display_name"])
    row = next(r for r in board if r["points"] == 2)
    assert row["group_points"] == 2
    assert row["correct_qualifiers"] == 1
    assert row["total_qualifiers"] == 2


# ================================= validare directa pe stratul de servicii (fara HTTP)
# GroupFinalizeIn.team_ids e deja validat contra duplicate de Pydantic la nivel de API
# (422 inainte sa ajunga la finalize_group) — testam direct functia de serviciu, ca
# "plasa de siguranta" independenta de API.
def test_finalize_group_service_rejects_duplicate_override_directly(
    client, admin_headers, db_session
) -> None:
    import pytest
    from fastapi import HTTPException

    from models import User
    from services.groups import finalize_group

    ids = _make_teams(db_session, 4)
    group = _generate_group(client, admin_headers, db_session, ids)
    _settle_all(client, admin_headers, group["id"], _clear_win_scorelines(ids))

    with SessionLocal() as db:
        from models import Group

        g = db.execute(select(Group).where(Group.id == group["id"])).scalar_one()
        admin_user = db.execute(select(User).where(User.is_admin.is_(True))).scalar_one()
        with pytest.raises(HTTPException) as exc:
            finalize_group(db, g, [ids[0], ids[0]], actor=admin_user, request=None)
        assert exc.value.status_code == 400
