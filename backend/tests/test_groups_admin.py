"""Faza 9: admin — generare/editare/stergere grupe (PLAN_GRUPE.md sectiunea 6.2)."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import Group, GroupPrediction, GroupPredictionPick, Match, Team
from services.groups import (
    GroupError,
    assert_valid_prediction_teams,
    create_group,
    generate_groups,
    update_group,
)


def _make_teams(db_session, n: int, prefix: str = "Echipa") -> list[int]:
    ids = []
    for i in range(n):
        t = Team(name=f"{prefix} {i + 1}", short_name=f"{prefix[:1]}{i + 1}", is_active=True)
        db_session.add(t)
        db_session.flush()
        ids.append(t.id)
    db_session.commit()
    return ids


def _four_groups_payload(db_session) -> tuple[dict, dict[str, list[int]]]:
    """16 echipe -> 4 grupe A-D x 4. Intoarce (payload, {name: team_ids})."""
    ids = _make_teams(db_session, 16)
    by_group = {
        "A": ids[0:4],
        "B": ids[4:8],
        "C": ids[8:12],
        "D": ids[12:16],
    }
    payload = {"groups": [{"name": name, "team_ids": tids} for name, tids in by_group.items()]}
    return payload, by_group


def _generate(client: TestClient, admin_headers, payload):
    return client.post("/api/admin/groups/generate", headers=admin_headers, json=payload)


# ==================================================================== generare
def test_generate_creates_four_groups_of_four(client, admin_headers, db_session) -> None:
    payload, _by_group = _four_groups_payload(db_session)
    resp = _generate(client, admin_headers, payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body) == 4
    assert {g["name"] for g in body} == {"A", "B", "C", "D"}
    assert all(g["qualifiers_count"] == 2 for g in body)
    assert all(len(g["teams"]) == 4 for g in body)
    assert all(len(g["matches"]) == 6 for g in body)


def test_generate_sets_teams_group_id(client, admin_headers, db_session) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        for tid in by_group["A"]:
            team = db.get(Team, tid)
            assert team.group_id == group_a.id


def test_generate_round_robin_every_pair_once_six_matches_three_rounds(
    client, admin_headers, db_session
) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        matches = db.execute(select(Match).where(Match.group_id == group_a.id)).scalars().all()

    assert len(matches) == 6
    assert {m.phase for m in matches} == {"GROUP"}
    assert {m.round_no for m in matches} == {1, 2, 3}
    for round_no in (1, 2, 3):
        assert sum(1 for m in matches if m.round_no == round_no) == 2
        positions = sorted(m.bracket_position for m in matches if m.round_no == round_no)
        assert positions == [0, 1]

    from itertools import combinations

    seen = {frozenset((m.home_team_id, m.away_team_id)) for m in matches}
    expected = {frozenset(c) for c in combinations(by_group["A"], 2)}
    assert seen == expected
    assert all(m.scheduled_at is None and m.status == "SCHEDULED" for m in matches)
    assert all("Grupa A" in (m.stage_label or "") for m in matches)


def test_generate_requires_admin(client, user_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    resp = _generate(client, user_headers, payload)
    assert resp.status_code == 403


def test_generate_rejects_wrong_team_count_per_group(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 3)
    resp = _generate(client, admin_headers, {"groups": [{"name": "A", "team_ids": ids}]})
    assert resp.status_code == 400
    assert "4 echipe" in resp.json()["detail"]


def test_generate_rejects_duplicate_team_across_groups(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 5)
    payload = {
        "groups": [
            {"name": "A", "team_ids": ids[0:4]},
            {"name": "B", "team_ids": [ids[4], ids[0], ids[1], ids[2]]},
        ]
    }
    resp = _generate(client, admin_headers, payload)
    assert resp.status_code == 400
    assert "doua grupe" in resp.json()["detail"].lower() or "două grupe" in resp.json()["detail"]


def test_generate_rejects_unknown_team(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 3)
    resp = _generate(client, admin_headers, {"groups": [{"name": "A", "team_ids": [*ids, 99999]}]})
    assert resp.status_code == 400
    assert "inexistente" in resp.json()["detail"].lower()


def test_generate_regenerates_when_clean(client, admin_headers, db_session) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)

    new_ids = _make_teams(db_session, 4, prefix="Nou")
    resp = _generate(client, admin_headers, {"groups": [{"name": "X", "team_ids": new_ids}]})
    assert resp.status_code == 201, resp.text

    with SessionLocal() as db:
        groups = db.execute(select(Group)).scalars().all()
        assert {g.name for g in groups} == {"X"}
        matches = db.execute(select(Match)).scalars().all()
        assert len(matches) == 6
        # echipele vechi nu mai apartin niciunei grupe
        for tid in by_group["A"]:
            assert db.get(Team, tid).group_id is None


def test_generate_blocked_when_group_match_validated(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        m = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().first()
        m.is_settled = True
        db.commit()

    resp = _generate(client, admin_headers, payload)
    assert resp.status_code == 400
    assert "validate" in resp.json()["detail"].lower()


def test_generate_blocked_when_predictions_exist(client, admin_headers, db_session, normal_user) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        pred = GroupPrediction(user_id=normal_user.id, group_id=group_a.id, status="OPEN")
        pred.picks.append(GroupPredictionPick(team_id=by_group["A"][0]))
        pred.picks.append(GroupPredictionPick(team_id=by_group["A"][1]))
        db.add(pred)
        db.commit()

    resp = _generate(client, admin_headers, payload)
    assert resp.status_code == 400
    assert "pronosticuri" in resp.json()["detail"].lower()


# ================================================== creare aditiva (o singura grupa)
# Curatenie Sarcina 1 (decuplarea specurilor e2e): `POST /api/admin/groups`, spre
# deosebire de `/groups/generate`, nu sterge nimic — nu se loveste de refuzul global
# al lui `generate_groups` cat timp exista undeva meciuri validate/pronosticuri.
def test_create_group_does_not_touch_existing_groups(client, admin_headers, db_session) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)  # A, B, C, D deja exista

    new_ids = _make_teams(db_session, 4, prefix="Adaugata")
    resp = client.post(
        "/api/admin/groups", headers=admin_headers, json={"name": "E", "team_ids": new_ids}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "E"
    assert sorted(t["id"] for t in body["teams"]) == sorted(new_ids)
    assert len(body["matches"]) == 6

    with SessionLocal() as db:
        names = {g.name for g in db.execute(select(Group)).scalars()}
        assert names == {"A", "B", "C", "D", "E"}
        for tid in by_group["A"]:
            assert db.get(Team, tid).group_id is not None  # A neatinsa


def test_create_group_succeeds_even_when_another_group_has_settled_matches_and_predictions(
    client, admin_headers, db_session, normal_user
) -> None:
    """Testul-cheie pentru Sarcina 1: proprietatea aditiva. `generate_groups` ar refuza
    aici (exista un meci validat SI un pronostic plasat pe grupa A) — `create_group`
    nu se uita deloc la asta, doar la grupa noua."""
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        m = db.execute(select(Match).where(Match.group_id == group_a.id)).scalars().first()
        m.is_settled = True
        m.home_score, m.away_score = 2, 0
        pred = GroupPrediction(user_id=normal_user.id, group_id=group_a.id, status="OPEN")
        pred.picks.append(GroupPredictionPick(team_id=by_group["A"][0]))
        pred.picks.append(GroupPredictionPick(team_id=by_group["A"][1]))
        db.add(pred)
        db.commit()

    new_ids = _make_teams(db_session, 4, prefix="ZZ")
    resp = client.post(
        "/api/admin/groups", headers=admin_headers, json={"name": "ZZ", "team_ids": new_ids}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["name"] == "ZZ"

    # Confirma, in oglinda, ca acelasi scenariu chiar BLOCHEAZA generate_groups —
    # altfel testul de mai sus n-ar demonstra nimic.
    blocked = _generate(client, admin_headers, {"groups": [{"name": "Q", "team_ids": new_ids}]})
    assert blocked.status_code == 400


def test_create_group_rejects_duplicate_name(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    new_ids = _make_teams(db_session, 4, prefix="Dubla")
    resp = client.post(
        "/api/admin/groups", headers=admin_headers, json={"name": "A", "team_ids": new_ids}
    )
    assert resp.status_code == 409


def test_create_group_rejects_wrong_team_count(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 3)
    resp = client.post(
        "/api/admin/groups", headers=admin_headers, json={"name": "X", "team_ids": ids}
    )
    assert resp.status_code == 400
    assert "4 echipe" in resp.json()["detail"]


def test_create_group_rejects_team_already_in_another_group(client, admin_headers, db_session) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    new_ids = _make_teams(db_session, 3, prefix="Rezerva")
    resp = client.post(
        "/api/admin/groups", headers=admin_headers,
        json={"name": "X", "team_ids": [*new_ids, by_group["A"][0]]},
    )
    assert resp.status_code == 400
    assert "altă grupă" in resp.json()["detail"]


def test_create_group_rejects_inactive_team(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    with SessionLocal() as db:
        db.get(Team, ids[0]).is_active = False
        db.commit()
    resp = client.post(
        "/api/admin/groups", headers=admin_headers, json={"name": "X", "team_ids": ids}
    )
    assert resp.status_code == 400
    assert "dezactivate" in resp.json()["detail"].lower()


def test_create_group_rejects_unknown_team(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 3)
    resp = client.post(
        "/api/admin/groups", headers=admin_headers, json={"name": "X", "team_ids": [*ids, 999999]}
    )
    assert resp.status_code == 400
    assert "inexistente" in resp.json()["detail"].lower()


def test_create_group_requires_admin(client, user_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    resp = client.post(
        "/api/admin/groups", headers=user_headers, json={"name": "X", "team_ids": ids}
    )
    assert resp.status_code == 403


def test_create_group_assigns_next_sort_order(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)  # sort_order 1..4
    _generate(client, admin_headers, payload)
    new_ids = _make_teams(db_session, 4, prefix="Cinci")
    resp = client.post(
        "/api/admin/groups", headers=admin_headers, json={"name": "E", "team_ids": new_ids}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["sort_order"] == 5


def test_create_group_service_direct_duplicate_team_ids_rejected(db_session) -> None:
    import pytest
    from fastapi import HTTPException

    from models import User

    ids = _make_teams(db_session, 4)
    with SessionLocal() as db:
        admin_user = db.execute(select(User).where(User.is_admin.is_(True))).scalar_one()
        with pytest.raises(HTTPException) as exc:
            create_group(db, "Q", [ids[0], ids[0], ids[1], ids[2]], actor=admin_user, request=None)
        assert exc.value.status_code == 400


# ==================================================================== editare/stergere
def test_update_group_name_and_qualifiers_count(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a_id = db.execute(select(Group).where(Group.name == "A")).scalar_one().id

    resp = client.put(
        f"/api/admin/groups/{group_a_id}", headers=admin_headers,
        json={"name": "Z", "qualifiers_count": 3},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Z"
    assert body["qualifiers_count"] == 3


def test_update_group_team_ids_replaces_roster_and_regenerates_matches(
    client, admin_headers, db_session
) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a_id = db.execute(select(Group).where(Group.name == "A")).scalar_one().id

    new_ids = _make_teams(db_session, 4, prefix="Rezerva")
    resp = client.put(
        f"/api/admin/groups/{group_a_id}", headers=admin_headers, json={"team_ids": new_ids}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert sorted(t["id"] for t in body["teams"]) == sorted(new_ids)
    assert len(body["matches"]) == 6

    with SessionLocal() as db:
        for tid in by_group["A"]:
            assert db.get(Team, tid).group_id is None
        for tid in new_ids:
            assert db.get(Team, tid).group_id == group_a_id


def test_update_group_team_ids_rejects_wrong_count(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a_id = db.execute(select(Group).where(Group.name == "A")).scalar_one().id
    new_ids = _make_teams(db_session, 3, prefix="Rezerva")
    resp = client.put(
        f"/api/admin/groups/{group_a_id}", headers=admin_headers, json={"team_ids": new_ids}
    )
    assert resp.status_code == 400


def test_update_group_team_ids_rejects_unknown_team(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a_id = db.execute(select(Group).where(Group.name == "A")).scalar_one().id
    new_ids = _make_teams(db_session, 3, prefix="Rezerva")
    resp = client.put(
        f"/api/admin/groups/{group_a_id}", headers=admin_headers,
        json={"team_ids": [*new_ids, 999999]},
    )
    assert resp.status_code == 400
    assert "inexistente" in resp.json()["detail"].lower()


def test_update_group_team_ids_rejects_team_in_another_group(client, admin_headers, db_session) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a_id = db.execute(select(Group).where(Group.name == "A")).scalar_one().id
    new_ids = _make_teams(db_session, 3, prefix="Rezerva")
    resp = client.put(
        f"/api/admin/groups/{group_a_id}", headers=admin_headers,
        json={"team_ids": [*new_ids, by_group["B"][0]]},
    )
    assert resp.status_code == 400
    assert "altă grupă" in resp.json()["detail"]


def test_update_group_team_ids_blocked_when_predictions_exist(
    client, admin_headers, db_session, normal_user
) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        pred = GroupPrediction(user_id=normal_user.id, group_id=group_a.id, status="OPEN")
        pred.picks.append(GroupPredictionPick(team_id=by_group["A"][0]))
        pred.picks.append(GroupPredictionPick(team_id=by_group["A"][1]))
        db.add(pred)
        db.commit()
        group_a_id = group_a.id

    new_ids = _make_teams(db_session, 4, prefix="Rezerva")
    resp = client.put(
        f"/api/admin/groups/{group_a_id}", headers=admin_headers, json={"team_ids": new_ids}
    )
    assert resp.status_code == 400
    assert "pronosticuri" in resp.json()["detail"].lower()


def test_update_group_blocked_when_match_validated(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        m = db.execute(select(Match).where(Match.group_id == group_a.id)).scalars().first()
        m.is_settled = True
        db.commit()
        group_a_id = group_a.id

    resp = client.put(
        f"/api/admin/groups/{group_a_id}", headers=admin_headers, json={"name": "Z"}
    )
    assert resp.status_code == 400


def test_delete_group_works_when_no_validated_matches(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a_id = db.execute(select(Group).where(Group.name == "A")).scalar_one().id

    resp = client.delete(f"/api/admin/groups/{group_a_id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    with SessionLocal() as db:
        assert db.get(Group, group_a_id) is None
        assert db.execute(select(Match).where(Match.group_id == group_a_id)).first() is None


def test_delete_group_blocked_when_match_validated(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        m = db.execute(select(Match).where(Match.group_id == group_a.id)).scalars().first()
        m.is_settled = True
        db.commit()
        group_a_id = group_a.id

    resp = client.delete(f"/api/admin/groups/{group_a_id}", headers=admin_headers)
    assert resp.status_code == 400


def test_delete_group_blocked_when_predictions_exist(
    client, admin_headers, db_session, normal_user
) -> None:
    payload, by_group = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        pred = GroupPrediction(user_id=normal_user.id, group_id=group_a.id, status="OPEN")
        pred.picks.append(GroupPredictionPick(team_id=by_group["A"][0]))
        pred.picks.append(GroupPredictionPick(team_id=by_group["A"][1]))
        db.add(pred)
        db.commit()
        group_a_id = group_a.id

    resp = client.delete(f"/api/admin/groups/{group_a_id}", headers=admin_headers)
    assert resp.status_code == 400


def test_update_and_delete_require_admin(client, user_headers, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a_id = db.execute(select(Group).where(Group.name == "A")).scalar_one().id

    assert client.put(
        f"/api/admin/groups/{group_a_id}", headers=user_headers, json={"name": "Z"}
    ).status_code == 403
    assert client.delete(f"/api/admin/groups/{group_a_id}", headers=user_headers).status_code == 403


def test_admin_list_groups(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    resp = client.get("/api/admin/groups", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 4


def test_admin_get_group_detail(client, admin_headers, db_session) -> None:
    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group_a_id = db.execute(select(Group).where(Group.name == "A")).scalar_one().id
    resp = client.get(f"/api/admin/groups/{group_a_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "A"


def test_admin_get_group_detail_404(client, admin_headers) -> None:
    resp = client.get("/api/admin/groups/999999", headers=admin_headers)
    assert resp.status_code == 404


# ============================================================= validari suplimentare (API)
def test_generate_rejects_duplicate_group_names(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 8)
    payload = {
        "groups": [
            {"name": "A", "team_ids": ids[0:4]},
            {"name": "A", "team_ids": ids[4:8]},
        ]
    }
    resp = _generate(client, admin_headers, payload)
    assert resp.status_code == 400
    assert "unice" in resp.json()["detail"].lower()


def test_generate_rejects_inactive_team(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    with SessionLocal() as db:
        team = db.get(Team, ids[0])
        team.is_active = False
        db.commit()
    resp = _generate(client, admin_headers, {"groups": [{"name": "A", "team_ids": ids}]})
    assert resp.status_code == 400
    assert "dezactivate" in resp.json()["detail"].lower()


def test_update_group_name_conflict(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 8)
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids[0:4]}, {"name": "B", "team_ids": ids[4:8]}]},
    )
    groups = {g["name"]: g for g in resp.json()}
    resp = client.put(
        f"/api/admin/groups/{groups['B']['id']}", headers=admin_headers, json={"name": "A"}
    )
    assert resp.status_code == 409


# ========================================= validari directe pe stratul de servicii (fara HTTP)
# Aceste ramuri sunt deja blocate mai devreme de validatorii Pydantic la nivel de API
# (deci nu sunt atinse printr-un request HTTP normal); le testam direct pe functia de
# serviciu ca "plasa de siguranta" sa ramana acoperite si corecte independent de API.
def test_generate_groups_service_direct_validations(db_session) -> None:
    import pytest

    with SessionLocal() as db:
        with pytest.raises(GroupError, match="cel puțin o grupă"):
            generate_groups(db, [])

        ids = _make_teams(db_session, 4)
        with pytest.raises(GroupError, match="echipe duplicate"):
            generate_groups(db, [("A", [ids[0], ids[0], ids[1], ids[2]])])


def test_assert_valid_prediction_teams_rejects_duplicate_directly(client, admin_headers, db_session) -> None:
    import pytest
    from fastapi import HTTPException

    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        from sqlalchemy.orm import selectinload

        group = db.execute(
            select(Group).options(selectinload(Group.teams)).where(Group.name == "A")
        ).scalar_one()
        team_id = group.teams[0].id
        with pytest.raises(HTTPException) as exc:
            assert_valid_prediction_teams(group, [team_id, team_id])
        assert exc.value.status_code == 400


def test_update_group_service_rejects_qualifiers_count_out_of_bounds(client, admin_headers, db_session) -> None:
    import pytest
    from fastapi import HTTPException

    from models import User

    payload, _ = _four_groups_payload(db_session)
    _generate(client, admin_headers, payload)
    with SessionLocal() as db:
        group = db.execute(select(Group).where(Group.name == "A")).scalar_one()
        admin_user = db.execute(select(User).where(User.is_admin.is_(True))).scalar_one()
        with pytest.raises(HTTPException) as exc:
            update_group(
                db, group, name=None, qualifiers_count=7, team_ids=None,
                actor=admin_user, request=None,
            )
        assert exc.value.status_code == 400
