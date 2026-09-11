"""Public: valorile de punctaj, ca biletul sa poata afisa „+3p" si „poti castiga N"."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.scoring import DEFAULT_POINTS
from services.tickets import load_points_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/points", response_model=dict[str, int])
def get_points(db: Session = Depends(get_db)) -> dict[str, int]:
    stored = load_points_settings(db)
    return {
        key: int(stored.get(key, default))
        for key, default in DEFAULT_POINTS.items()
    }
