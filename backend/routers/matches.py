"""Public: meciuri, detaliu meci, structura bracket-ului.

Daca cererea e autentificata, fiecare meci include `my_ticket` (rezumatul
biletului userului pe acel meci).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import Match, Ticket, User
from schemas.matches import BracketRoundOut, MatchDetailOut, MatchOut, MyTicketSummary
from services.match_state import build_match_out, now_utc
from services.scoring import Selection, points_for
from services.security import get_optional_user
from services.tickets import load_points_settings

router = APIRouter(prefix="/api", tags=["matches"])


def _all_matches(db: Session) -> list[Match]:
    return list(
        db.execute(
            select(Match)
            .options(
                selectinload(Match.home_team),
                selectinload(Match.away_team),
                selectinload(Match.scorers),
                selectinload(Match.group),
            )
            .order_by(Match.round_no, Match.bracket_position)
        ).scalars()
    )


def _my_tickets_by_match(db: Session, user: User | None) -> dict[int, MyTicketSummary]:
    if user is None:
        return {}
    points_settings = load_points_settings(db)
    result: dict[int, MyTicketSummary] = {}
    tickets = db.execute(
        select(Ticket)
        .options(selectinload(Ticket.selections))
        .where(Ticket.user_id == user.id)
    ).scalars()
    for t in tickets:
        potential = sum(
            points_for(
                Selection(market=s.market, pick=s.pick, line=s.line, player_id=s.player_id),
                points_settings,
            )
            for s in t.selections
        )
        result[t.match_id] = MyTicketSummary(
            ticket_id=t.id,
            selection_count=len(t.selections),
            potential_points=potential,
            status=t.status,
            total_points=t.total_points,
        )
    return result


@router.get("/matches", response_model=list[MatchOut])
def list_matches(
    db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
) -> list[MatchOut]:
    now = now_utc()
    mine = _my_tickets_by_match(db, user)
    return [
        build_match_out(m, now=now, my_ticket=mine.get(m.id)) for m in _all_matches(db)
    ]


@router.get("/matches/{match_id}", response_model=MatchDetailOut)
def get_match(
    match_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> MatchDetailOut:
    match = db.execute(
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.scorers),
            selectinload(Match.group),
        )
        .where(Match.id == match_id)
    ).scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Meciul nu există.")
    mine = _my_tickets_by_match(db, user)
    return build_match_out(match, with_scorers=True, my_ticket=mine.get(match.id))


@router.get("/bracket", response_model=list[BracketRoundOut])
def get_bracket(db: Session = Depends(get_db)) -> list[BracketRoundOut]:
    """Doar meciurile knockout — bracket-ul se stabileste dupa grupe (PLAN_GRUPE.md 6.1)."""
    now = now_utc()
    rounds: dict[int, BracketRoundOut] = {}
    for match in _all_matches(db):
        if match.phase != "KNOCKOUT":
            continue
        rnd = rounds.get(match.round_no)
        if rnd is None:
            rnd = BracketRoundOut(round_no=match.round_no, stage_label=match.stage_label, matches=[])
            rounds[match.round_no] = rnd
        rnd.matches.append(build_match_out(match, now=now))
    return [rounds[k] for k in sorted(rounds)]
