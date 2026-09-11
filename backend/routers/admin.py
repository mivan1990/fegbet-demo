"""Rute de administrare: echipe, jucatori, meciuri, bracket. Toate cer require_admin."""
# Fara `from __future__ import annotations` (FastAPI are nevoie de tipurile reale).

import json
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import (
    ActivityLog,
    Match,
    MatchScorer,
    Player,
    Setting,
    Team,
    Ticket,
    TicketSelection,
    User,
)
from schemas.admin import (
    AdminUserOut,
    LogItemOut,
    LogPageOut,
    SetActiveIn,
    SetPasswordIn,
    SetRoleIn,
    SettingsUpdateIn,
)
from schemas.matches import (
    BracketGenerateIn,
    MatchCreate,
    MatchOut,
    MatchUpdate,
    ScheduleIn,
    SettleIn,
    SettleResult,
)
from schemas.players import PlayerCreate, PlayerOut, PlayerUpdate
from schemas.teams import TeamAdminOut, TeamCreate, TeamOut, TeamUpdate
from services.audit import log_action
from services.bracket import BracketError, generate_bracket
from services.match_state import build_match_out, now_utc
from services.scoring import DEFAULT_POINTS
from services.security import hash_password, require_admin
from services.settlement import settle_match

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _get_or_404(db: Session, model, obj_id: int, what: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{what} nu există.")
    return obj


def _feg_team(db: Session) -> Team:
    team = db.execute(select(Team).where(Team.is_feg.is_(True))).scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=400, detail="Nu există o echipă FEG configurată.")
    return team


# ============================================================================ ECHIPE
@router.get("/teams", response_model=list[TeamAdminOut])
def admin_list_teams(db: Session = Depends(get_db)):
    player_counts = dict(
        db.execute(select(Player.team_id, func.count(Player.id)).group_by(Player.team_id)).all()
    )
    match_counts: dict[int, int] = {}
    for (tid,) in db.execute(
        select(Match.home_team_id).where(Match.home_team_id.is_not(None))
    ).all():
        match_counts[tid] = match_counts.get(tid, 0) + 1
    for (tid,) in db.execute(
        select(Match.away_team_id).where(Match.away_team_id.is_not(None))
    ).all():
        match_counts[tid] = match_counts.get(tid, 0) + 1

    teams = db.execute(select(Team).order_by(Team.name)).scalars().all()
    return [
        TeamAdminOut(
            **TeamOut.model_validate(t).model_dump(),
            player_count=player_counts.get(t.id, 0),
            match_count=match_counts.get(t.id, 0),
        )
        for t in teams
    ]


def _assert_single_feg(db: Session, is_feg: bool, exclude_id: int | None = None) -> None:
    if not is_feg:
        return
    q = select(Team.id).where(Team.is_feg.is_(True))
    if exclude_id is not None:
        q = q.where(Team.id != exclude_id)
    if db.execute(q).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Există deja o echipă FEG. Poate fi doar una.",
        )


@router.post("/teams", response_model=TeamOut, status_code=201)
def admin_create_team(
    payload: TeamCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.execute(select(Team.id).where(Team.name == payload.name)).first() is not None:
        raise HTTPException(status_code=409, detail="Există deja o echipă cu numele ăsta.")
    _assert_single_feg(db, payload.is_feg)

    team = Team(**payload.model_dump())
    db.add(team)
    db.flush()
    log_action(db, "admin.team.create", actor=admin, entity_type="team", entity_id=team.id,
               detail={"after": payload.model_dump()}, request=request)
    db.commit()
    db.refresh(team)
    return team


@router.put("/teams/{team_id}", response_model=TeamOut)
def admin_update_team(
    team_id: int,
    payload: TeamUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    team = _get_or_404(db, Team, team_id, "Echipa")
    before = TeamOut.model_validate(team).model_dump()
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] != team.name:
        if db.execute(select(Team.id).where(Team.name == data["name"])).first() is not None:
            raise HTTPException(status_code=409, detail="Există deja o echipă cu numele ăsta.")
    if data.get("is_feg"):
        _assert_single_feg(db, True, exclude_id=team.id)

    for key, value in data.items():
        setattr(team, key, value)
    db.flush()
    log_action(db, "admin.team.update", actor=admin, entity_type="team", entity_id=team.id,
               detail={"before": before, "after": TeamOut.model_validate(team).model_dump()},
               request=request)
    db.commit()
    db.refresh(team)
    return team


@router.delete("/teams/{team_id}", status_code=200)
def admin_delete_team(
    team_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    team = _get_or_404(db, Team, team_id, "Echipa")

    used_in_match = db.execute(
        select(Match.id).where(
            or_(
                Match.home_team_id == team_id,
                Match.away_team_id == team_id,
                Match.winner_team_id == team_id,
            )
        )
    ).first()
    if used_in_match is not None:
        raise HTTPException(
            status_code=409,
            detail="Echipa e folosită într-un meci. Dezactiveaz-o în loc s-o ștergi.",
        )
    if db.execute(select(Player.id).where(Player.team_id == team_id)).first() is not None:
        raise HTTPException(
            status_code=409,
            detail="Echipa are jucători. Șterge-i sau dezactiveaz-o în loc s-o ștergi.",
        )

    log_action(db, "admin.team.delete", actor=admin, entity_type="team", entity_id=team_id,
               detail={"before": TeamOut.model_validate(team).model_dump()}, request=request)
    db.delete(team)
    db.commit()
    return {"ok": True}


# ========================================================================== JUCATORI
@router.get("/players", response_model=list[PlayerOut])
def admin_list_players(db: Session = Depends(get_db)):
    return list(db.execute(select(Player).order_by(Player.name)).scalars())


@router.post("/players", response_model=PlayerOut, status_code=201)
def admin_create_player(
    payload: PlayerCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    feg = _feg_team(db)
    player = Player(team_id=feg.id, is_active=True, **payload.model_dump())
    db.add(player)
    db.flush()
    log_action(db, "admin.player.create", actor=admin, entity_type="player", entity_id=player.id,
               detail={"after": payload.model_dump()}, request=request)
    db.commit()
    db.refresh(player)
    return player


@router.put("/players/{player_id}", response_model=PlayerOut)
def admin_update_player(
    player_id: int,
    payload: PlayerUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    player = _get_or_404(db, Player, player_id, "Jucătorul")
    before = PlayerOut.model_validate(player).model_dump()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(player, key, value)
    db.flush()
    log_action(db, "admin.player.update", actor=admin, entity_type="player", entity_id=player.id,
               detail={"before": before, "after": PlayerOut.model_validate(player).model_dump()},
               request=request)
    db.commit()
    db.refresh(player)
    return player


@router.delete("/players/{player_id}", status_code=200)
def admin_delete_player(
    player_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    player = _get_or_404(db, Player, player_id, "Jucătorul")

    on_ticket = db.execute(
        select(TicketSelection.id).where(TicketSelection.player_id == player_id)
    ).first()
    on_scoresheet = db.execute(
        select(MatchScorer.id).where(MatchScorer.player_id == player_id)
    ).first()

    if on_ticket is not None or on_scoresheet is not None:
        player.is_active = False
        mode = "soft"
        log_action(db, "admin.player.delete", actor=admin, entity_type="player", entity_id=player_id,
                   detail={"mode": "soft", "reason": "apare pe bilete sau in marcatori"},
                   request=request)
        db.commit()
        return {"ok": True, "mode": mode, "detail": "Jucătorul a fost dezactivat (apare pe bilete)."}

    log_action(db, "admin.player.delete", actor=admin, entity_type="player", entity_id=player_id,
               detail={"mode": "hard", "before": PlayerOut.model_validate(player).model_dump()},
               request=request)
    db.delete(player)
    db.commit()
    return {"ok": True, "mode": "hard"}


# =========================================================================== MECIURI
@router.get("/matches", response_model=list[MatchOut])
def admin_list_matches(db: Session = Depends(get_db)):
    now = now_utc()
    matches = db.execute(
        select(Match)
        .options(
            selectinload(Match.home_team), selectinload(Match.away_team), selectinload(Match.group)
        )
        .order_by(Match.round_no, Match.bracket_position)
    ).scalars()
    return [build_match_out(m, now=now) for m in matches]


def _validate_team_ids(db: Session, *team_ids: int | None) -> None:
    ids = [t for t in team_ids if t is not None]
    if not ids:
        return
    found = {r[0] for r in db.execute(select(Team.id).where(Team.id.in_(ids))).all()}
    missing = [t for t in ids if t not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"Echipe inexistente: {missing}.")


@router.post("/matches", response_model=MatchOut, status_code=201)
def admin_create_match(
    payload: MatchCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _validate_team_ids(db, payload.home_team_id, payload.away_team_id)
    match = Match(status="SCHEDULED", is_settled=False, **payload.model_dump())
    db.add(match)
    db.flush()
    log_action(db, "admin.match.create", actor=admin, entity_type="match", entity_id=match.id,
               detail={"after": payload.model_dump()}, request=request)
    db.commit()
    db.refresh(match)
    return build_match_out(match)


@router.put("/matches/{match_id}", response_model=MatchOut)
def admin_update_match(
    match_id: int,
    payload: MatchUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    match = _get_or_404(db, Match, match_id, "Meciul")
    if match.is_settled:
        raise HTTPException(
            status_code=409,
            detail="Meciul e validat. Modifică scorul prin re-validare, nu de aici.",
        )
    data = payload.model_dump(exclude_unset=True)
    _validate_team_ids(db, data.get("home_team_id"), data.get("away_team_id"))

    before = {"scheduled_at": match.scheduled_at, "status": match.status,
              "home_team_id": match.home_team_id, "away_team_id": match.away_team_id}
    for key, value in data.items():
        setattr(match, key, value)
    db.flush()
    log_action(db, "admin.match.update", actor=admin, entity_type="match", entity_id=match.id,
               detail={"before": before, "after": data}, request=request)
    db.commit()
    db.refresh(match)
    return build_match_out(match)


@router.put("/matches/{match_id}/schedule", response_model=MatchOut)
def admin_schedule_match(
    match_id: int,
    payload: ScheduleIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    match = _get_or_404(db, Match, match_id, "Meciul")
    if match.is_settled:
        raise HTTPException(status_code=409, detail="Meciul e validat. Nu-i mai poți schimba ora.")
    before = match.scheduled_at
    match.scheduled_at = payload.scheduled_at
    db.flush()
    log_action(db, "admin.match.schedule", actor=admin, entity_type="match", entity_id=match.id,
               detail={"before": before, "after": payload.scheduled_at}, request=request)
    db.commit()
    db.refresh(match)
    return build_match_out(match)


@router.post("/matches/{match_id}/settle", response_model=SettleResult)
def admin_settle_match(
    match_id: int,
    payload: SettleIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Valideaza (sau re-valideaza) meciul: scor, penalty-uri, marcatori FEG.

    Re-validarea anuleaza complet efectul precedent inainte de recalcul.
    """
    match, tickets_settled, warning = settle_match(db, match_id, payload, actor=admin, request=request)
    fresh = db.execute(
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.scorers),
            selectinload(Match.group),
        )
        .where(Match.id == match.id)
    ).scalar_one()
    return SettleResult(
        match=build_match_out(fresh, with_scorers=True),
        tickets_settled=tickets_settled,
        warning=warning,
    )


@router.delete("/matches/{match_id}", status_code=200)
def admin_delete_match(
    match_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    match = _get_or_404(db, Match, match_id, "Meciul")
    if match.is_settled:
        raise HTTPException(status_code=409, detail="Meciul e validat. Nu se mai poate șterge.")
    if db.execute(select(Ticket.id).where(Ticket.match_id == match_id)).first() is not None:
        raise HTTPException(status_code=409, detail="Meciul are bilete. Nu se poate șterge.")

    # Rupe legaturile: meciurile care avansau in acesta raman fara destinatie.
    for predecessor in db.execute(
        select(Match).where(Match.next_match_id == match_id)
    ).scalars():
        predecessor.next_match_id = None
        predecessor.next_slot = None

    log_action(db, "admin.match.delete", actor=admin, entity_type="match", entity_id=match_id,
               detail={"round_no": match.round_no, "bracket_position": match.bracket_position},
               request=request)
    db.delete(match)
    db.commit()
    return {"ok": True}


# ============================================================================ BRACKET
@router.post("/bracket/generate", response_model=list[MatchOut], status_code=201)
def admin_generate_bracket(
    payload: BracketGenerateIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        matches = generate_bracket(db, payload.size, payload.team_ids)
    except BracketError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_action(db, "admin.bracket.generate", actor=admin, entity_type="bracket", entity_id=None,
               detail={"size": payload.size, "team_ids": payload.team_ids}, request=request)
    db.commit()
    now = now_utc()
    return [build_match_out(m, now=now) for m in matches]


# ============================================================================== STATS
@router.get("/stats")
def admin_stats(db: Session = Depends(get_db)):
    market_row = db.execute(
        select(TicketSelection.market, func.count(TicketSelection.id))
        .group_by(TicketSelection.market)
        .order_by(func.count(TicketSelection.id).desc())
        .limit(1)
    ).first()
    return {
        "users": db.scalar(select(func.count(User.id))),
        "teams": db.scalar(select(func.count(Team.id))),
        "players": db.scalar(select(func.count(Player.id))),
        "matches": db.scalar(select(func.count(Match.id))),
        "matches_settled": db.scalar(
            select(func.count(Match.id)).where(Match.is_settled.is_(True))
        ),
        "tickets": db.scalar(select(func.count(Ticket.id))),
        "top_market": market_row[0] if market_row else None,
    }


# =============================================================================== LOGURI
_LOG_PAGE_SIZE = 50


@router.get("/logs", response_model=LogPageOut)
def admin_logs(
    db: Session = Depends(get_db),
    user_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
):
    filters = []
    if user_id is not None:
        filters.append(ActivityLog.actor_user_id == user_id)
    if action:
        filters.append(ActivityLog.action == action)
    if from_ is not None:
        filters.append(ActivityLog.created_at >= from_)
    if to is not None:
        filters.append(ActivityLog.created_at <= to)
    if q:
        filters.append(ActivityLog.detail.ilike(f"%{q}%"))

    total = db.scalar(select(func.count(ActivityLog.id)).where(*filters)) or 0
    pages = max(1, ceil(total / _LOG_PAGE_SIZE))
    entries = db.execute(
        select(ActivityLog)
        .where(*filters)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(_LOG_PAGE_SIZE)
        .offset((page - 1) * _LOG_PAGE_SIZE)
    ).scalars().all()

    actor_ids = {e.actor_user_id for e in entries if e.actor_user_id}
    names = {
        uid: name
        for uid, name in db.execute(
            select(User.id, User.display_name).where(User.id.in_(actor_ids))
        ).all()
    }

    def _parse_detail(raw: str) -> object:
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw

    items = [
        LogItemOut(
            id=e.id,
            action=e.action,
            actor_user_id=e.actor_user_id,
            actor_name=names.get(e.actor_user_id) if e.actor_user_id else None,
            target_user_id=e.target_user_id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            detail=_parse_detail(e.detail),
            ip_address=e.ip_address,
            created_at=e.created_at,
        )
        for e in entries
    ]
    distinct_actions = [
        a for (a,) in db.execute(select(ActivityLog.action).distinct().order_by(ActivityLog.action)).all()
    ]
    return LogPageOut(items=items, total=total, page=page, pages=pages, actions=distinct_actions)


# =============================================================================== SETARI
@router.get("/settings", response_model=dict[str, int])
def admin_get_settings(db: Session = Depends(get_db)):
    stored = {
        s.key: s.value
        for s in db.execute(select(Setting).where(Setting.key.like("pts.%"))).scalars()
    }
    return {key: int(stored.get(key, default)) for key, default in DEFAULT_POINTS.items()}


@router.put("/settings", response_model=dict[str, int])
def admin_update_settings(
    payload: SettingsUpdateIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    unknown = [k for k in payload.values if k not in DEFAULT_POINTS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Chei de setare necunoscute: {unknown}.")

    before: dict[str, int] = {}
    for key, value in payload.values.items():
        setting = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
        before[key] = int(setting.value) if setting else DEFAULT_POINTS[key]
        if setting is None:
            db.add(Setting(key=key, value=str(value)))
        else:
            setting.value = str(value)

    log_action(
        db, "admin.settings.update", actor=admin, entity_type="settings", entity_id=None,
        detail={"before": before, "after": payload.values}, request=request,
    )
    db.commit()
    return admin_get_settings(db)


# ========================================================================= UTILIZATORI
def _require_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilizatorul nu există.")
    return user


@router.get("/users", response_model=list[AdminUserOut])
def admin_list_users(db: Session = Depends(get_db)):
    return list(db.execute(select(User).order_by(User.display_name)).scalars())


@router.put("/users/{user_id}/password", response_model=AdminUserOut)
def admin_set_password(
    user_id: int,
    payload: SetPasswordIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _require_user(db, user_id)
    user.password_hash = hash_password(payload.new_password)
    log_action(
        db, "admin.user.reset_password", actor=admin, target_user_id=user.id,
        entity_type="user", entity_id=user.id, request=request,
    )
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/role", response_model=AdminUserOut)
def admin_set_role(
    user_id: int,
    payload: SetRoleIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _require_user(db, user_id)
    if user.id == admin.id and not payload.is_admin:
        raise HTTPException(status_code=400, detail="Nu te poți auto-retrograda.")
    if not payload.is_admin and user.is_admin:
        other_admins = db.scalar(
            select(func.count(User.id)).where(User.is_admin.is_(True), User.id != user.id)
        )
        if not other_admins:
            raise HTTPException(
                status_code=400, detail="E ultimul admin. Trebuie să rămână cel puțin unul."
            )
    user.is_admin = payload.is_admin
    log_action(
        db, "admin.user.promote" if payload.is_admin else "admin.user.demote",
        actor=admin, target_user_id=user.id, entity_type="user", entity_id=user.id,
        request=request,
    )
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/active", response_model=AdminUserOut)
def admin_set_active(
    user_id: int,
    payload: SetActiveIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _require_user(db, user_id)
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="Nu te poți dezactiva singur.")
    user.is_active = payload.is_active
    log_action(
        db, "admin.user.deactivate" if not payload.is_active else "admin.user.activate",
        actor=admin, target_user_id=user.id, entity_type="user", entity_id=user.id,
        request=request,
    )
    db.commit()
    db.refresh(user)
    return user
