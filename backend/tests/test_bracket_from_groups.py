"""Faza 9: POST /api/admin/bracket/generate-from-groups (PLAN_GRUPE.md 6.2)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from database import SessionLocal
from models import Match, Team, Ticket, utcnow


def _make_teams(db_session, n: int, prefix: str = "Echipa") -> list[int]:
    ids = []
    for i in range(n):
        t = Team(name=f"{prefix} {i + 1}", short_name=f"{prefix[:1]}{i + 1}", is_active=True)
        db_session.add(t)
        db_session.flush()
        ids.append(t.id)
    db_session.commit()
    return ids


def _generate_four_groups(client, admin_headers, db_session) -> dict[str, dict]:
    ids = _make_teams(db_session, 16)
    by_group = {"A": ids[0:4], "B": ids[4:8], "C": ids[8:12], "D": ids[12:16]}
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": n, "team_ids": t} for n, t in by_group.items()]},
    )
    assert resp.status_code == 201, resp.text
    groups = {g["name"]: g for g in resp.json()}
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()
    return groups


def _clear_win_scorelines(ids: list[int]) -> dict[frozenset, tuple[int, int]]:
    t1, t2, t3, t4 = ids
    return {
        frozenset((t1, t4)): (3, 0),
        frozenset((t2, t3)): (2, 0),
        frozenset((t4, t3)): (0, 1),
        frozenset((t1, t2)): (2, 0),
        frozenset((t2, t4)): (2, 0),
        frozenset((t3, t1)): (0, 3),
    }


def _settle_group(client, admin_headers, group_id: int, team_ids: list[int]) -> None:
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.group_id == group_id)).scalars().all()
        by_pair = {frozenset((m.home_team_id, m.away_team_id)): m for m in matches}
    scorelines = _clear_win_scorelines(team_ids)
    for pair, m in by_pair.items():
        home, away = scorelines[pair]
        resp = client.post(
            f"/api/admin/matches/{m.id}/settle", headers=admin_headers,
            json={"home_score": home, "away_score": away},
        )
        assert resp.status_code == 200, resp.text


def _finalize_all(client, admin_headers, groups: dict[str, dict], teams_by_group: dict[str, list[int]]) -> None:
    for name, group in groups.items():
        _settle_group(client, admin_headers, group["id"], teams_by_group[name])
        resp = client.post(f"/api/admin/groups/{group['id']}/finalize", headers=admin_headers, json={})
        assert resp.status_code == 200, resp.text


def _generate_from_groups(client, admin_headers):
    return client.post("/api/admin/bracket/generate-from-groups", headers=admin_headers, json={})


# ==================================================================== fericit
def test_generate_from_groups_cross_pairing(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 16)
    teams_by_group = {"A": ids[0:4], "B": ids[4:8], "C": ids[8:12], "D": ids[12:16]}
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": n, "team_ids": t} for n, t in teams_by_group.items()]},
    )
    groups = {g["name"]: g for g in resp.json()}
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()

    _finalize_all(client, admin_headers, groups, teams_by_group)

    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 201, resp.text
    bracket_matches = resp.json()

    with SessionLocal() as db:
        r1 = (
            db.execute(select(Match).where(Match.phase == "KNOCKOUT", Match.round_no == 1))
            .scalars()
            .all()
        )
    assert len(r1) == 4

    # 1A vs 2B, 1C vs 2D, 1B vs 2A, 1D vs 2C
    a1, a2 = teams_by_group["A"][0], teams_by_group["A"][1]
    b1, b2 = teams_by_group["B"][0], teams_by_group["B"][1]
    c1, c2 = teams_by_group["C"][0], teams_by_group["C"][1]
    d1, d2 = teams_by_group["D"][0], teams_by_group["D"][1]

    pairs = {frozenset((m.home_team_id, m.away_team_id)) for m in r1}
    assert frozenset((a1, b2)) in pairs
    assert frozenset((c1, d2)) in pairs
    assert frozenset((b1, a2)) in pairs
    assert frozenset((d1, c2)) in pairs
    assert len(bracket_matches) == 7  # 4+2+1, bracket de 8


def test_generate_from_groups_requires_admin(client, user_headers, db_session) -> None:
    resp = client.post(
        "/api/admin/bracket/generate-from-groups", headers=user_headers, json={}
    )
    assert resp.status_code == 403


# ==================================================================== refuz
def test_generate_from_groups_rejects_when_no_groups(client, admin_headers) -> None:
    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 400


def test_generate_from_groups_rejects_when_group_not_finalized(
    client, admin_headers, db_session
) -> None:
    _generate_four_groups(client, admin_headers, db_session)

    # nu finalizam nicio grupa
    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 400
    assert "finalizat" in resp.json()["detail"].lower()


# ============================================= nu atinge meciurile/biletele de grupa
def test_generate_from_groups_does_not_delete_group_matches(
    client, admin_headers, db_session
) -> None:
    ids = _make_teams(db_session, 16)
    teams_by_group = {"A": ids[0:4], "B": ids[4:8], "C": ids[8:12], "D": ids[12:16]}
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": n, "team_ids": t} for n, t in teams_by_group.items()]},
    )
    groups = {g["name"]: g for g in resp.json()}
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()

    _finalize_all(client, admin_headers, groups, teams_by_group)

    with SessionLocal() as db:
        group_matches_before = len(
            db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        )
    assert group_matches_before == 24

    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 201, resp.text

    with SessionLocal() as db:
        group_matches_after = len(
            db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        )
    assert group_matches_after == 24  # neatinse


def test_generate_from_groups_not_blocked_by_group_ticket_style_predictions(
    client, admin_headers, db_session, register_user
) -> None:
    """Nu exista bilete pe meciuri de grupa in acest scenariu (doar pronosticuri de grupa,
    care nu sunt Ticket-uri) — bracket-ul nu trebuie sa refuze din cauza lor.
    """
    ids = _make_teams(db_session, 16)
    teams_by_group = {"A": ids[0:4], "B": ids[4:8], "C": ids[8:12], "D": ids[12:16]}
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": n, "team_ids": t} for n, t in teams_by_group.items()]},
    )
    groups = {g["name"]: g for g in resp.json()}
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()

    _u, tok = register_user(email="grpbet@mariusivan.ro")
    from tests.conftest import auth_header

    h = auth_header(tok)
    group_a = groups["A"]
    client.post(
        "/api/group-predictions", headers=h,
        json={"group_id": group_a["id"], "team_ids": [teams_by_group["A"][0], teams_by_group["A"][1]]},
    )

    _finalize_all(client, admin_headers, groups, teams_by_group)

    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 201, resp.text

    with SessionLocal() as db:
        assert db.execute(select(Ticket.id)).first() is None  # nu exista bilete deloc


# ==================================================== configuratii necanonice (fallback)
def test_generate_from_groups_fallback_ordering_when_not_four_groups_of_two(
    client, admin_headers, db_session
) -> None:
    """2 grupe x 2 calificati = 4 echipe -> nu e cazul canonic (4 grupe), foloseste
    ordinea simpla (sort_order, rank) in loc de imperecherea incrucisata."""
    ids = _make_teams(db_session, 8)
    teams_by_group = {"A": ids[0:4], "B": ids[4:8]}
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": n, "team_ids": t} for n, t in teams_by_group.items()]},
    )
    groups = {g["name"]: g for g in resp.json()}
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()

    _finalize_all(client, admin_headers, groups, teams_by_group)

    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 201, resp.text
    assert len(resp.json()) == 3  # bracket de 4: 2+1

    with SessionLocal() as db:
        r1 = (
            db.execute(select(Match).where(Match.phase == "KNOCKOUT", Match.round_no == 1))
            .scalars()
            .all()
        )
    seeded = {m.home_team_id for m in r1} | {m.away_team_id for m in r1}
    expected = {teams_by_group["A"][0], teams_by_group["A"][1], teams_by_group["B"][0], teams_by_group["B"][1]}
    assert seeded == expected


def test_generate_from_groups_rejects_when_total_not_4_8_16(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": "A", "team_ids": ids}]},
    )
    group = resp.json()[0]
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()

    resp = client.put(
        f"/api/admin/groups/{group['id']}", headers=admin_headers, json={"qualifiers_count": 3}
    )
    assert resp.status_code == 200, resp.text

    _settle_group(client, admin_headers, group["id"], ids)
    resp = client.post(f"/api/admin/groups/{group['id']}/finalize", headers=admin_headers, json={})
    assert resp.status_code == 200, resp.text

    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 400
    assert "3 echipe" in resp.json()["detail"] or "acceptă doar 4, 8 sau 16" in resp.json()["detail"]


def test_generate_from_groups_reraises_bracket_error_as_400(
    client, admin_headers, db_session
) -> None:
    ids = _make_teams(db_session, 16)
    teams_by_group = {"A": ids[0:4], "B": ids[4:8], "C": ids[8:12], "D": ids[12:16]}
    resp = client.post(
        "/api/admin/groups/generate", headers=admin_headers,
        json={"groups": [{"name": n, "team_ids": t} for n, t in teams_by_group.items()]},
    )
    groups = {g["name"]: g for g in resp.json()}
    with SessionLocal() as db:
        matches = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        for m in matches:
            m.scheduled_at = utcnow() + timedelta(days=1)
        db.commit()
    _finalize_all(client, admin_headers, groups, teams_by_group)

    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 201, resp.text

    # valideaza un meci de bracket -> a doua generare trebuie sa refuze (BracketError propagat)
    with SessionLocal() as db:
        knockout_match = (
            db.execute(select(Match).where(Match.phase == "KNOCKOUT", Match.round_no == 1))
            .scalars()
            .first()
        )
        match_id = knockout_match.id
    settle_resp = client.post(
        f"/api/admin/matches/{match_id}/settle", headers=admin_headers,
        json={"home_score": 1, "away_score": 0},
    )
    assert settle_resp.status_code == 200, settle_resp.text

    resp = _generate_from_groups(client, admin_headers)
    assert resp.status_code == 400
    assert "validate" in resp.json()["detail"].lower()
