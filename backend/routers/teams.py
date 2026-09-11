"""Public: lista echipelor active."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Team
from schemas.teams import TeamOut

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)) -> list[Team]:
    return list(
        db.execute(select(Team).where(Team.is_active.is_(True)).order_by(Team.name)).scalars()
    )
