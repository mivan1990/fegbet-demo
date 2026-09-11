"""Public: lista jucatorilor FEG activi (pentru piata Marcator)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Player, Team
from schemas.players import PlayerOut

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("", response_model=list[PlayerOut])
def list_players(db: Session = Depends(get_db)) -> list[Player]:
    return list(
        db.execute(
            select(Player)
            .join(Team, Player.team_id == Team.id)
            .where(Team.is_feg.is_(True), Player.is_active.is_(True))
            .order_by(Player.name)
        ).scalars()
    )
