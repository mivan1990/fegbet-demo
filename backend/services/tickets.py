"""Logica de bilete: verificarile de lock (server-side) si construirea raspunsului."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Match, Player, Setting, Team, Ticket, TicketSelection
from schemas.tickets import MatchRef, SelectionIn, SelectionOut, TicketOut
from services.match_state import is_locked, match_has_feg, now_utc
from services.scoring import (
    MARKET_QUALIFY,
    MARKET_SCORER,
    Selection,
    market_available,
    points_for,
)

LOCKED_MESSAGE = "Meciul a început — nu mai poți modifica biletul."


def load_points_settings(db: Session) -> dict[str, str]:
    return {
        s.key: s.value
        for s in db.execute(select(Setting).where(Setting.key.like("pts.%"))).scalars()
    }


def assert_match_open_for_betting(match: Match) -> None:
    """Ridica HTTP 400 daca meciul nu accepta bilete acum. Sursa unica de adevar.

    Se poate paria DOAR daca: ambele echipe stabilite ȘI scheduled_at setat
    ȘI scheduled_at > now(UTC) ȘI status == SCHEDULED ȘI nedecontat.
    """
    if match.home_team_id is None or match.away_team_id is None:
        raise HTTPException(status_code=400, detail="Meciul n-are încă ambele echipe stabilite.")
    if match.scheduled_at is None:
        raise HTTPException(status_code=400, detail="Meciul n-are încă o oră de start.")
    if is_locked(match, now_utc()):
        raise HTTPException(status_code=400, detail=LOCKED_MESSAGE)
    if match.status != "SCHEDULED":
        raise HTTPException(status_code=400, detail=LOCKED_MESSAGE)


def validate_selections_for_match(
    db: Session, match: Match, selections: list[SelectionIn]
) -> None:
    """Valideaza fiecare selectie fata de meciul concret (piete disponibile, jucatori FEG)."""
    has_feg = match_has_feg(match)
    both_teams = match.home_team_id is not None and match.away_team_id is not None
    is_group = match.phase == "GROUP"

    feg_player_ids: set[int] = set()
    if has_feg:
        feg_team = db.execute(select(Team).where(Team.is_feg.is_(True))).scalar_one_or_none()
        if feg_team is not None:
            feg_player_ids = {
                pid
                for (pid,) in db.execute(
                    select(Player.id).where(
                        Player.team_id == feg_team.id, Player.is_active.is_(True)
                    )
                ).all()
            }

    for sel in selections:
        if not market_available(
            sel.market, has_feg=has_feg, both_teams_set=both_teams, is_group=is_group
        ):
            if sel.market == MARKET_SCORER:
                raise HTTPException(
                    status_code=400,
                    detail="Piata de marcator e doar la meciurile echipei FEG.",
                )
            if sel.market == MARKET_QUALIFY and is_group:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "La meciurile din grupe nu se pariază cine merge mai departe — "
                        "pronosticul e pe grupă."
                    ),
                )
            raise HTTPException(
                status_code=400,
                detail=f"Piața {sel.market} nu e disponibilă pe acest meci.",
            )
        if sel.market == MARKET_SCORER:
            if sel.player_id not in feg_player_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Alege un jucator FEG activ pentru piata de marcator.",
                )


def replace_selections(db: Session, ticket: Ticket, selections: list[SelectionIn]) -> None:
    """Inlocuieste complet selectiile biletului (nu aduna peste cele vechi).

    Goleste colectia si da flush (emite DELETE pentru orfani) INAINTE de a adauga
    cele noi, altfel INSERT-ul calca constrangerea unique(ticket_id, market).
    """
    ticket.selections.clear()
    db.flush()
    for sel in selections:
        ticket.selections.append(
            TicketSelection(
                market=sel.market,
                pick=sel.pick,
                line=sel.line if sel.market == "TOTAL_GOALS" else None,
                player_id=sel.player_id if sel.market == MARKET_SCORER else None,
            )
        )


def _selection_to_scoring(sel: TicketSelection) -> Selection:
    return Selection(market=sel.market, pick=sel.pick, line=sel.line, player_id=sel.player_id)


def build_ticket_out(
    db: Session,
    ticket: Ticket,
    points_settings: dict[str, str],
    *,
    with_match: bool = False,
) -> TicketOut:
    player_names: dict[int, str] = {}
    scorer_ids = [s.player_id for s in ticket.selections if s.player_id is not None]
    if scorer_ids:
        player_names = {
            p.id: p.name
            for p in db.execute(select(Player).where(Player.id.in_(scorer_ids))).scalars()
        }

    sel_out: list[SelectionOut] = []
    potential = 0
    for s in ticket.selections:
        pts = points_for(_selection_to_scoring(s), points_settings)
        potential += pts
        sel_out.append(
            SelectionOut(
                market=s.market,
                pick=s.pick,
                line=s.line,
                player_id=s.player_id,
                player_name=player_names.get(s.player_id) if s.player_id else None,
                points=pts,
                is_correct=s.is_correct,
                points_awarded=s.points_awarded,
            )
        )

    match_ref = None
    if with_match:
        m = ticket.match
        match_ref = MatchRef(
            id=m.id,
            stage_label=m.stage_label,
            scheduled_at=m.scheduled_at,
            status=m.status,
            is_settled=m.is_settled,
            is_locked=is_locked(m, now_utc()),
            home_name=m.home_team.name if m.home_team else None,
            away_name=m.away_team.name if m.away_team else None,
            home_score=m.home_score,
            away_score=m.away_score,
        )

    return TicketOut(
        id=ticket.id,
        match_id=ticket.match_id,
        status=ticket.status,
        selections=sel_out,
        potential_points=potential,
        total_points=ticket.total_points,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        match=match_ref,
    )


def get_user_ticket_for_match(db: Session, user_id: int, match_id: int) -> Ticket | None:
    return db.execute(
        select(Ticket).where(Ticket.user_id == user_id, Ticket.match_id == match_id)
    ).scalar_one_or_none()
