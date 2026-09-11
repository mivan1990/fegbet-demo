"""Public: grupe (clasament calculat) + pronosticuri de grupa (user).

Regulile de lock traiesc server-side in services/groups.py — frontend-ul doar
ascunde butoane, la fel ca la bilete (PLAN_GRUPE.md 5.4).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import Group, GroupPrediction, GroupPredictionPick, User
from schemas.groups import GroupOut, GroupPredictionIn, GroupPredictionOut, GroupPredictionUpdateIn
from services.audit import log_action
from services.groups import (
    assert_group_open_for_prediction,
    assert_valid_prediction_teams,
    build_group_out,
    build_group_prediction_out,
    group_lock_inputs,
)
from services.rate_limit import limiter
from services.security import get_current_user, get_optional_user

router = APIRouter(prefix="/api", tags=["groups"])


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


def _owned_prediction(db: Session, prediction_id: int, user: User) -> GroupPrediction:
    prediction = db.execute(
        select(GroupPrediction)
        .options(selectinload(GroupPrediction.picks))
        .where(GroupPrediction.id == prediction_id)
    ).scalar_one_or_none()
    # 404 (nu 403) daca nu e al userului — nu confirmam existenta pronosticurilor altora.
    if prediction is None or prediction.user_id != user.id:
        raise HTTPException(status_code=404, detail="Pronosticul nu există.")
    return prediction


def _picks_snapshot(prediction: GroupPrediction) -> list[int]:
    return sorted(p.team_id for p in prediction.picks)


@router.get("/groups", response_model=list[GroupOut])
def list_groups(
    db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
) -> list[GroupOut]:
    return [build_group_out(db, g, user) for g in _all_groups(db)]


@router.get("/groups/{group_id}", response_model=GroupOut)
def get_group(
    group_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
) -> GroupOut:
    group = _get_group_or_404(db, group_id)
    return build_group_out(db, group, user)


@router.get("/group-predictions/mine", response_model=list[GroupPredictionOut])
def my_group_predictions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[GroupPredictionOut]:
    predictions = db.execute(
        select(GroupPrediction)
        .options(selectinload(GroupPrediction.picks))
        .where(GroupPrediction.user_id == user.id)
    ).scalars()
    return [build_group_prediction_out(db, p) for p in predictions]


@router.post("/group-predictions", response_model=GroupPredictionOut, status_code=201)
@limiter.limit("30/minute")
def create_group_prediction(
    payload: GroupPredictionIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupPredictionOut:
    group = _get_group_or_404(db, payload.group_id)
    locks_at, has_settled_match, is_finalized = group_lock_inputs(db, group)
    assert_group_open_for_prediction(
        locks_at, has_settled_match=has_settled_match, is_finalized=is_finalized
    )
    assert_valid_prediction_teams(group, payload.team_ids)

    existing = db.execute(
        select(GroupPrediction).where(
            GroupPrediction.user_id == user.id, GroupPrediction.group_id == group.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ai deja un pronostic pe grupa asta.")

    prediction = GroupPrediction(user_id=user.id, group_id=group.id, status="OPEN")
    for team_id in payload.team_ids:
        prediction.picks.append(GroupPredictionPick(team_id=team_id))
    db.add(prediction)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Ai deja un pronostic pe grupa asta."
        ) from None

    log_action(
        db, "group_prediction.create", actor=user, entity_type="group_prediction",
        entity_id=prediction.id,
        detail={"group_id": group.id, "team_ids": payload.team_ids}, request=request,
    )
    db.commit()
    db.refresh(prediction)
    return build_group_prediction_out(db, prediction)


@router.put("/group-predictions/{prediction_id}", response_model=GroupPredictionOut)
@limiter.limit("30/minute")
def update_group_prediction(
    prediction_id: int,
    payload: GroupPredictionUpdateIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupPredictionOut:
    prediction = _owned_prediction(db, prediction_id, user)
    if prediction.status != "OPEN":
        raise HTTPException(status_code=400, detail="Pronosticul e deja decontat.")
    group = _get_group_or_404(db, prediction.group_id)
    locks_at, has_settled_match, is_finalized = group_lock_inputs(db, group)
    assert_group_open_for_prediction(
        locks_at, has_settled_match=has_settled_match, is_finalized=is_finalized
    )
    assert_valid_prediction_teams(group, payload.team_ids)

    before = _picks_snapshot(prediction)
    prediction.picks.clear()
    db.flush()
    for team_id in payload.team_ids:
        prediction.picks.append(GroupPredictionPick(team_id=team_id))
    db.flush()

    log_action(
        db, "group_prediction.update", actor=user, entity_type="group_prediction",
        entity_id=prediction.id,
        detail={"before": before, "after": sorted(payload.team_ids)}, request=request,
    )
    db.commit()
    db.refresh(prediction)
    return build_group_prediction_out(db, prediction)


@router.delete("/group-predictions/{prediction_id}", status_code=200)
@limiter.limit("30/minute")
def delete_group_prediction(
    prediction_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    prediction = _owned_prediction(db, prediction_id, user)
    if prediction.status != "OPEN":
        raise HTTPException(status_code=400, detail="Pronosticul e deja decontat.")
    group = _get_group_or_404(db, prediction.group_id)
    locks_at, has_settled_match, is_finalized = group_lock_inputs(db, group)
    assert_group_open_for_prediction(
        locks_at, has_settled_match=has_settled_match, is_finalized=is_finalized
    )

    log_action(
        db, "group_prediction.delete", actor=user, entity_type="group_prediction",
        entity_id=prediction.id,
        detail={"group_id": prediction.group_id, "team_ids": _picks_snapshot(prediction)},
        request=request,
    )
    db.delete(prediction)
    db.commit()
    return {"ok": True}
