"""Bilete (user): GET /mine, POST (creeaza sau inlocuieste), PUT, DELETE.

Toate verificarile de lock se fac AICI, pe server. Frontend-ul doar ascunde butoane.
"""
# Fara `from __future__ import annotations` (FastAPI are nevoie de tipurile reale).

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import Match, Ticket, User
from schemas.tickets import TicketIn, TicketOut, TicketUpdateIn
from services.audit import log_action
from services.rate_limit import limiter
from services.security import get_current_user
from services.tickets import (
    assert_match_open_for_betting,
    build_ticket_out,
    get_user_ticket_for_match,
    load_points_settings,
    replace_selections,
    validate_selections_for_match,
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _selections_snapshot(ticket: Ticket) -> list[dict]:
    return [
        {"market": s.market, "pick": s.pick, "line": s.line, "player_id": s.player_id}
        for s in ticket.selections
    ]


def _load_match(db: Session, match_id: int) -> Match:
    match = db.execute(
        select(Match)
        .options(selectinload(Match.home_team), selectinload(Match.away_team))
        .where(Match.id == match_id)
    ).scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Meciul nu există.")
    return match


def _owned_ticket(db: Session, ticket_id: int, user: User) -> Ticket:
    ticket = db.execute(
        select(Ticket)
        .options(selectinload(Ticket.selections), selectinload(Ticket.match))
        .where(Ticket.id == ticket_id)
    ).scalar_one_or_none()
    # 404 (nu 403) daca nu e al userului — nu confirmam existenta biletelor altora.
    if ticket is None or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Biletul nu există.")
    return ticket


@router.get("/mine", response_model=list[TicketOut])
def my_tickets(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[TicketOut]:
    points_settings = load_points_settings(db)
    tickets = (
        db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.selections),
                selectinload(Ticket.match).selectinload(Match.home_team),
                selectinload(Ticket.match).selectinload(Match.away_team),
            )
            .where(Ticket.user_id == user.id)
        )
        .scalars()
        .all()
    )
    tickets.sort(key=lambda t: (t.match.scheduled_at is None, t.match.scheduled_at or t.created_at))
    return [build_ticket_out(db, t, points_settings, with_match=True) for t in tickets]


@router.post("", response_model=TicketOut, status_code=201)
@limiter.limit("30/minute")
def create_or_replace_ticket(
    payload: TicketIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketOut:
    match = _load_match(db, payload.match_id)
    assert_match_open_for_betting(match)
    validate_selections_for_match(db, match, payload.selections)

    existing = get_user_ticket_for_match(db, user.id, match.id)
    if existing is not None:
        before = _selections_snapshot(existing)
        replace_selections(db, existing, payload.selections)
        db.flush()
        log_action(
            db, "ticket.update", actor=user, entity_type="ticket", entity_id=existing.id,
            detail={"before": before, "after": _selections_snapshot(existing)}, request=request,
        )
        db.commit()
        db.refresh(existing)
        return build_ticket_out(db, existing, load_points_settings(db))

    ticket = Ticket(user_id=user.id, match_id=match.id, status="OPEN")
    replace_selections(db, ticket, payload.selections)
    db.add(ticket)
    try:
        db.flush()
    except IntegrityError:
        # Cursa: alt request al aceluiasi user a creat deja biletul intre timp.
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Ai deja un bilet pe meciul ăsta. Reîncarcă pagina."
        ) from None
    log_action(
        db, "ticket.create", actor=user, entity_type="ticket", entity_id=ticket.id,
        detail={"match_id": match.id, "selections": _selections_snapshot(ticket)}, request=request,
    )
    db.commit()
    db.refresh(ticket)
    return build_ticket_out(db, ticket, load_points_settings(db))


@router.put("/{ticket_id}", response_model=TicketOut)
@limiter.limit("30/minute")
def update_ticket(
    ticket_id: int,
    payload: TicketUpdateIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketOut:
    ticket = _owned_ticket(db, ticket_id, user)
    if ticket.status != "OPEN":
        raise HTTPException(status_code=400, detail="Biletul e deja decontat.")
    match = _load_match(db, ticket.match_id)
    assert_match_open_for_betting(match)
    validate_selections_for_match(db, match, payload.selections)

    before = _selections_snapshot(ticket)
    replace_selections(db, ticket, payload.selections)
    db.flush()
    log_action(
        db, "ticket.update", actor=user, entity_type="ticket", entity_id=ticket.id,
        detail={"before": before, "after": _selections_snapshot(ticket)}, request=request,
    )
    db.commit()
    db.refresh(ticket)
    return build_ticket_out(db, ticket, load_points_settings(db))


@router.delete("/{ticket_id}", status_code=200)
@limiter.limit("30/minute")
def delete_ticket(
    ticket_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ticket = _owned_ticket(db, ticket_id, user)
    match = _load_match(db, ticket.match_id)
    assert_match_open_for_betting(match)

    log_action(
        db, "ticket.delete", actor=user, entity_type="ticket", entity_id=ticket.id,
        detail={"match_id": ticket.match_id, "selections": _selections_snapshot(ticket)},
        request=request,
    )
    db.delete(ticket)
    db.commit()
    return {"ok": True}
