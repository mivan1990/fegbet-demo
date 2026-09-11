"""Scheme Pydantic pentru bilete."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from services.scoring import (
    MARKET_BTTS,
    MARKET_QUALIFY,
    MARKET_SCORER,
    MARKET_TOTAL_GOALS,
    MARKET_WINNER,
)

_GOAL_LINES = {0.5, 1.5, 2.5, 3.5}

# Ce `pick`-uri sunt valide pe fiecare piata (SCORER foloseste player_id, pick fix).
_VALID_PICKS: dict[str, set[str]] = {
    MARKET_WINNER: {"HOME", "DRAW", "AWAY"},
    MARKET_QUALIFY: {"HOME", "AWAY"},
    MARKET_TOTAL_GOALS: {"OVER", "UNDER"},
    MARKET_BTTS: {"YES", "NO"},
    MARKET_SCORER: {"SCORER"},
}


class SelectionIn(BaseModel):
    market: str
    pick: str
    line: float | None = None
    player_id: int | None = None

    @field_validator("market")
    @classmethod
    def _market(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in _VALID_PICKS:
            raise ValueError(f"Piata necunoscuta: {v}.")
        return v

    @field_validator("pick")
    @classmethod
    def _pick(cls, v: str) -> str:
        return v.strip().upper()


def _validate_selections(selections: list[SelectionIn]) -> list[SelectionIn]:
    if len(selections) < 1:
        raise ValueError("Biletul trebuie sa aiba cel putin o selectie.")
    markets = [s.market for s in selections]
    if len(set(markets)) != len(markets):
        raise ValueError("Ai doua selectii pe aceeasi piata.")
    for s in selections:
        if s.pick not in _VALID_PICKS[s.market]:
            raise ValueError(f"Optiune invalida pentru piata {s.market}.")
        if s.market == MARKET_TOTAL_GOALS and s.line not in _GOAL_LINES:
            raise ValueError("Total goluri are nevoie de linie: 0.5, 1.5, 2.5 sau 3.5.")
        if s.market == MARKET_SCORER and s.player_id is None:
            raise ValueError("Selectia de marcator are nevoie de un jucator.")
    return selections


class TicketIn(BaseModel):
    match_id: int
    selections: list[SelectionIn]

    @field_validator("selections")
    @classmethod
    def _selections(cls, v: list[SelectionIn]) -> list[SelectionIn]:
        return _validate_selections(v)


class TicketUpdateIn(BaseModel):
    selections: list[SelectionIn]

    @field_validator("selections")
    @classmethod
    def _selections(cls, v: list[SelectionIn]) -> list[SelectionIn]:
        return _validate_selections(v)


class SelectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market: str
    pick: str
    line: float | None
    player_id: int | None
    player_name: str | None = None
    points: int = 0  # cate puncte ar aduce daca e corecta
    is_correct: bool | None = None
    points_awarded: int | None = None


class MatchRef(BaseModel):
    id: int
    stage_label: str | None
    scheduled_at: datetime | None
    status: str
    is_settled: bool
    is_locked: bool
    home_name: str | None
    away_name: str | None
    home_score: int | None
    away_score: int | None


class TicketOut(BaseModel):
    id: int
    match_id: int
    status: str
    selections: list[SelectionOut]
    potential_points: int
    total_points: int | None
    created_at: datetime
    updated_at: datetime
    match: MatchRef | None = None
