"""Generare bracket knockout: PLAN_SONNET.md sectiunile 7 si 10 (Faza 2)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Match, MatchScorer, Team, Ticket

# Eticheta rundei dupa distanta pana la finala (0 = finala insasi).
_STAGE_BY_DISTANCE_FROM_FINAL = {
    0: "Finală",
    1: "Semifinală",
    2: "Sferturi",
    3: "Optimi",
}


def _rounds_for(size: int) -> int:
    return size.bit_length() - 1  # log2 pentru puteri ale lui 2 (4/8/16)


def stage_label(round_no: int, total_rounds: int) -> str:
    distance = total_rounds - round_no
    return _STAGE_BY_DISTANCE_FROM_FINAL.get(distance, f"Runda {round_no}")


class BracketError(ValueError):
    """Eroare de validare la generarea bracket-ului (mesaj in romana)."""


def generate_bracket(db: Session, size: int, team_ids: list[int]) -> list[Match]:
    if size not in {4, 8, 16}:
        raise BracketError("Marimea bracket-ului trebuie sa fie 4, 8 sau 16.")
    if len(team_ids) != size:
        raise BracketError(f"Ai nevoie de exact {size} echipe, ai dat {len(team_ids)}.")
    if len(set(team_ids)) != len(team_ids):
        raise BracketError("Ai pus aceeasi echipa de doua ori.")

    teams = db.execute(select(Team).where(Team.id.in_(team_ids))).scalars().all()
    by_id = {t.id: t for t in teams}
    missing = [tid for tid in team_ids if tid not in by_id]
    if missing:
        raise BracketError(f"Echipe inexistente: {missing}.")
    inactive = [by_id[tid].name for tid in team_ids if not by_id[tid].is_active]
    if inactive:
        raise BracketError(f"Echipe dezactivate in bracket: {', '.join(inactive)}.")

    # Nu regeneram peste un bracket cu meciuri validate sau cu bilete plasate.
    # Restrans la faza KNOCKOUT (PLAN_GRUPE.md 6.2) — nu atinge meciurile/biletele de grupa.
    existing = db.execute(select(Match).where(Match.phase == "KNOCKOUT")).scalars().all()
    if existing:
        if any(m.is_settled for m in existing):
            raise BracketError("Exista meciuri deja validate. Nu pot regenera bracket-ul.")
        existing_ids = [m.id for m in existing]
        if (
            db.execute(select(Ticket.id).where(Ticket.match_id.in_(existing_ids)).limit(1))
            .scalar_one_or_none()
            is not None
        ):
            raise BracketError("Exista bilete plasate. Nu pot regenera bracket-ul.")
        for m in existing:
            db.execute(
                MatchScorer.__table__.delete().where(MatchScorer.match_id == m.id)
            )
        for m in existing:
            db.delete(m)
        db.flush()

    total_rounds = _rounds_for(size)
    prev_round: list[Match] = []

    for round_no in range(1, total_rounds + 1):
        count = size // (2**round_no)
        label = stage_label(round_no, total_rounds)
        this_round: list[Match] = []

        for pos in range(count):
            match = Match(
                round_no=round_no,
                bracket_position=pos,
                stage_label=label,
                phase="KNOCKOUT",
                status="SCHEDULED",
                is_settled=False,
            )
            if round_no == 1:
                match.home_team_id = team_ids[pos * 2]
                match.away_team_id = team_ids[pos * 2 + 1]
            db.add(match)
            db.flush()  # avem nevoie de match.id pentru legaturi
            this_round.append(match)

        # Leaga runda precedenta de aceasta: castigatorul meciului i avanseaza in
        # meciul i//2, pe slotul home (i par) sau away (i impar).
        for i, prev_match in enumerate(prev_round):
            prev_match.next_match_id = this_round[i // 2].id
            prev_match.next_slot = "home" if i % 2 == 0 else "away"

        prev_round = this_round

    db.flush()
    return (
        db.execute(
            select(Match)
            .where(Match.phase == "KNOCKOUT")
            .order_by(Match.round_no, Match.bracket_position)
        )
        .scalars()
        .all()
    )
