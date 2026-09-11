"""Rute de administrare pentru grupe — PLAN_GRUPE.md sectiunea 6.2.

Fisier separat de routers/admin.py (care e deja mare) — acelasi tipar ca separarea
routers/matches.py (public) / partea de meciuri din routers/admin.py (admin).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import Group, User
from schemas.groups import GroupFinalizeIn, GroupOut, GroupSpecIn, GroupsGenerateIn, GroupUpdateIn
from schemas.matches import MatchOut
from services.audit import log_action
from services.groups import (
    GroupError,
    build_group_out,
    create_group,
    delete_group,
    finalize_group,
    generate_bracket_from_groups,
    generate_groups,
    update_group,
)
from services.match_state import build_match_out, now_utc
from services.security import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin-groups"], dependencies=[Depends(require_admin)])


def _all_groups(db: Session) -> list[Group]:
    return list(
        db.execute(
            select(Group)
            .options(selectinload(Group.teams), selectinload(Group.matches))
            .order_by(Group.sort_order)
        ).scalars()
    )


def _get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.execute(
        select(Group)
        .options(selectinload(Group.teams), selectinload(Group.matches))
        .where(Group.id == group_id)
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="Grupa nu există.")
    return group


@router.get("/groups", response_model=list[GroupOut])
def admin_list_groups(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [build_group_out(db, g, admin) for g in _all_groups(db)]


@router.get("/groups/{group_id}", response_model=GroupOut)
def admin_get_group(
    group_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    return build_group_out(db, _get_group_or_404(db, group_id), admin)


@router.post("/groups/generate", response_model=list[GroupOut], status_code=201)
def admin_generate_groups(
    payload: GroupsGenerateIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        generate_groups(db, [(g.name, g.team_ids) for g in payload.groups])
    except GroupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_action(
        db, "admin.group.generate", actor=admin, entity_type="group", entity_id=None,
        detail={"groups": [{"name": g.name, "team_ids": g.team_ids} for g in payload.groups]},
        request=request,
    )
    db.commit()
    return [build_group_out(db, g, admin) for g in _all_groups(db)]


@router.post("/groups", response_model=GroupOut, status_code=201)
def admin_create_group(
    payload: GroupSpecIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Adaugă O grupă, fără să atingă grupele existente — spre deosebire de
    `/groups/generate` (reset global), asta e aditivă (services.groups.create_group)."""
    group = create_group(db, payload.name, payload.team_ids, actor=admin, request=request)
    return build_group_out(db, _get_group_or_404(db, group.id), admin)


@router.put("/groups/{group_id}", response_model=GroupOut)
def admin_update_group(
    group_id: int,
    payload: GroupUpdateIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    group = _get_group_or_404(db, group_id)
    update_group(
        db, group,
        name=payload.name, qualifiers_count=payload.qualifiers_count, team_ids=payload.team_ids,
        actor=admin, request=request,
    )
    return build_group_out(db, _get_group_or_404(db, group_id), admin)


@router.delete("/groups/{group_id}", status_code=200)
def admin_delete_group(
    group_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    group = _get_group_or_404(db, group_id)
    delete_group(db, group, actor=admin, request=request)
    return {"ok": True}


@router.post("/groups/{group_id}/finalize", response_model=GroupOut)
def admin_finalize_group(
    group_id: int,
    payload: GroupFinalizeIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    group = _get_group_or_404(db, group_id)
    finalize_group(db, group, payload.team_ids, actor=admin, request=request)
    return build_group_out(db, _get_group_or_404(db, group_id), admin)


@router.post("/bracket/generate-from-groups", response_model=list[MatchOut], status_code=201)
def admin_generate_bracket_from_groups(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    matches = generate_bracket_from_groups(db, actor=admin, request=request)
    now = now_utc()
    return [build_match_out(m, now=now) for m in matches]
