"""Faza 2: generarea bracket-ului knockout."""
from __future__ import annotations

import math

from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from models import Match, Team
from services.bracket import stage_label


def _make_teams(db_session, n: int) -> list[int]:
    ids = []
    for i in range(n):
        t = Team(name=f"Echipa {i + 1}", short_name=f"E{i + 1}", is_active=True)
        db_session.add(t)
        db_session.flush()
        ids.append(t.id)
    db_session.commit()
    return ids


def _generate(client: TestClient, admin_headers, size: int, team_ids: list[int]):
    return client.post(
        "/api/admin/bracket/generate",
        headers=admin_headers,
        json={"size": size, "team_ids": team_ids},
    )


# --------------------------------------------------------------------------- size 8
def test_bracket_of_8_shape(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 8)
    resp = _generate(client, admin_headers, 8, ids)
    assert resp.status_code == 201, resp.text

    with SessionLocal() as db:
        matches = db.execute(select(Match).order_by(Match.round_no, Match.bracket_position)).scalars().all()

    assert len(matches) == 7  # 4 + 2 + 1
    by_round: dict[int, list[Match]] = {}
    for m in matches:
        by_round.setdefault(m.round_no, []).append(m)
    assert [len(by_round[r]) for r in sorted(by_round)] == [4, 2, 1]

    assert {m.stage_label for m in by_round[1]} == {"Sferturi"}
    assert {m.stage_label for m in by_round[2]} == {"Semifinală"}
    assert {m.stage_label for m in by_round[3]} == {"Finală"}


def test_bracket_of_8_links_are_correct(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 8)
    _generate(client, admin_headers, 8, ids)

    with SessionLocal() as db:
        matches = db.execute(select(Match).order_by(Match.round_no, Match.bracket_position)).scalars().all()
    by_key = {(m.round_no, m.bracket_position): m for m in matches}
    final = by_key[(3, 0)]

    # Runda 1: pozitia p -> runda 2 pozitia p//2, slot home daca p par, away daca p impar.
    for p in range(4):
        qf = by_key[(1, p)]
        target = by_key[(2, p // 2)]
        assert qf.next_match_id == target.id
        assert qf.next_slot == ("home" if p % 2 == 0 else "away")

    for p in range(2):
        sf = by_key[(2, p)]
        assert sf.next_match_id == final.id
        assert sf.next_slot == ("home" if p % 2 == 0 else "away")

    assert final.next_match_id is None
    assert final.next_slot is None


def test_bracket_of_8_round1_has_teams_paired_in_order(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 8)
    _generate(client, admin_headers, 8, ids)

    with SessionLocal() as db:
        r1 = db.execute(
            select(Match).where(Match.round_no == 1).order_by(Match.bracket_position)
        ).scalars().all()

    for pos, m in enumerate(r1):
        assert m.home_team_id == ids[pos * 2]
        assert m.away_team_id == ids[pos * 2 + 1]

    with SessionLocal() as db:
        later = db.execute(select(Match).where(Match.round_no > 1)).scalars().all()
    assert all(m.home_team_id is None and m.away_team_id is None for m in later)


# ------------------------------------------------------------------------ size 4/16
def test_bracket_of_4(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    assert _generate(client, admin_headers, 4, ids).status_code == 201
    with SessionLocal() as db:
        matches = db.execute(select(Match)).scalars().all()
    assert len(matches) == 3
    counts = sorted(len([m for m in matches if m.round_no == r]) for r in {m.round_no for m in matches})
    assert counts == [1, 2]
    assert {m.stage_label for m in matches if m.round_no == 1} == {"Semifinală"}
    assert {m.stage_label for m in matches if m.round_no == 2} == {"Finală"}


def test_bracket_of_16(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 16)
    assert _generate(client, admin_headers, 16, ids).status_code == 201
    with SessionLocal() as db:
        matches = db.execute(select(Match)).scalars().all()
    assert len(matches) == 15
    per_round = sorted(
        len([m for m in matches if m.round_no == r]) for r in {m.round_no for m in matches}
    )
    assert per_round == [1, 2, 4, 8]
    assert {m.stage_label for m in matches if m.round_no == 1} == {"Optimi"}


def test_every_non_final_match_points_forward(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 16)
    _generate(client, admin_headers, 16, ids)
    with SessionLocal() as db:
        matches = db.execute(select(Match)).scalars().all()
    total_rounds = int(math.log2(16))
    for m in matches:
        if m.round_no < total_rounds:
            assert m.next_match_id is not None and m.next_slot in {"home", "away"}
        else:
            assert m.next_match_id is None


# ------------------------------------------------------------------------ validari
def test_bracket_rejects_bad_size(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    assert _generate(client, admin_headers, 6, ids).status_code == 422


def test_bracket_rejects_wrong_team_count(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    resp = _generate(client, admin_headers, 8, ids)
    assert resp.status_code == 400
    assert "8 echipe" in resp.json()["detail"]


def test_bracket_rejects_duplicate_team(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 4)
    resp = _generate(client, admin_headers, 4, [ids[0], ids[0], ids[1], ids[2]])
    assert resp.status_code == 422


def test_bracket_rejects_unknown_team(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 3)
    resp = _generate(client, admin_headers, 4, [*ids, 99999])
    assert resp.status_code == 400
    assert "inexistente" in resp.json()["detail"].lower()


def test_bracket_regenerate_replaces_when_clean(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 8)
    _generate(client, admin_headers, 8, ids)
    # a doua generare: sterge si reface
    resp = _generate(client, admin_headers, 4, ids[:4])
    assert resp.status_code == 201
    with SessionLocal() as db:
        assert len(db.execute(select(Match)).scalars().all()) == 3


def test_bracket_regenerate_blocked_when_settled(client, admin_headers, db_session) -> None:
    ids = _make_teams(db_session, 8)
    _generate(client, admin_headers, 8, ids)
    with SessionLocal() as db:
        m = db.execute(select(Match).where(Match.round_no == 1)).scalars().first()
        m.is_settled = True
        db.commit()
    resp = _generate(client, admin_headers, 8, ids)
    assert resp.status_code == 400
    assert "validate" in resp.json()["detail"].lower()


def test_stage_label_helper() -> None:
    assert stage_label(1, 4) == "Optimi"
    assert stage_label(2, 4) == "Sferturi"
    assert stage_label(3, 4) == "Semifinală"
    assert stage_label(4, 4) == "Finală"
    assert stage_label(1, 3) == "Sferturi"
    assert stage_label(1, 2) == "Semifinală"
