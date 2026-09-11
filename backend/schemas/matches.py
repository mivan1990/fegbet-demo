"""Scheme Pydantic pentru meciuri si bracket."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

MATCH_STATUSES = {"SCHEDULED", "LIVE", "FINISHED", "CANCELLED"}
BRACKET_SIZES = {4, 8, 16}


# --------------------------------------------------------------------------- admin
class MatchCreate(BaseModel):
    round_no: int
    bracket_position: int
    stage_label: str | None = None
    home_team_id: int | None = None
    away_team_id: int | None = None
    scheduled_at: datetime | None = None
    next_match_id: int | None = None
    next_slot: str | None = None

    @field_validator("next_slot")
    @classmethod
    def _slot(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        if v not in {"home", "away"}:
            raise ValueError("next_slot trebuie sa fie 'home' sau 'away'.")
        return v


class MatchUpdate(BaseModel):
    round_no: int | None = None
    bracket_position: int | None = None
    stage_label: str | None = None
    home_team_id: int | None = None
    away_team_id: int | None = None
    scheduled_at: datetime | None = None
    status: str | None = None
    next_match_id: int | None = None
    next_slot: str | None = None

    @field_validator("status")
    @classmethod
    def _status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        if v not in MATCH_STATUSES:
            raise ValueError(f"Status invalid. Permise: {', '.join(sorted(MATCH_STATUSES))}.")
        return v


class ScheduleIn(BaseModel):
    scheduled_at: datetime | None


class ScorerIn(BaseModel):
    player_id: int
    goals: int = Field(default=1, ge=1, le=20)


class SettleIn(BaseModel):
    home_score: int = Field(ge=0, le=99)
    away_score: int = Field(ge=0, le=99)
    penalties_home: int | None = Field(default=None, ge=0, le=99)
    penalties_away: int | None = Field(default=None, ge=0, le=99)
    scorers: list[ScorerIn] = []


class BracketGenerateIn(BaseModel):
    size: int
    team_ids: list[int]

    @field_validator("size")
    @classmethod
    def _size(cls, v: int) -> int:
        if v not in BRACKET_SIZES:
            raise ValueError("Marimea bracket-ului trebuie sa fie 4, 8 sau 16.")
        return v

    @field_validator("team_ids")
    @classmethod
    def _teams(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("Ai pus aceeasi echipa de doua ori.")
        return v


# -------------------------------------------------------------------------- output
class TeamRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str | None
    is_feg: bool


class ScorerOut(BaseModel):
    player_id: int
    name: str
    goals: int


class MyTicketSummary(BaseModel):
    ticket_id: int
    selection_count: int
    potential_points: int
    status: str
    total_points: int | None


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    round_no: int
    bracket_position: int
    stage_label: str | None
    status: str
    scheduled_at: datetime | None

    # Faza 9: faza meciului (GROUP/KNOCKOUT) si grupa lui, daca e cazul.
    phase: str = "KNOCKOUT"
    group_id: int | None = None
    group_name: str | None = None

    home_team: TeamRef | None
    away_team: TeamRef | None

    home_score: int | None
    away_score: int | None
    penalties_home: int | None
    penalties_away: int | None
    winner_team_id: int | None

    is_settled: bool
    next_match_id: int | None
    next_slot: str | None

    # calculate server-side (PLAN_SONNET.md sectiunea 8)
    is_locked: bool = False
    is_bettable: bool = False
    has_feg: bool = False

    # doar daca cererea e autentificata si userul are bilet pe acest meci
    my_ticket: MyTicketSummary | None = None


class MatchDetailOut(MatchOut):
    scorers: list[ScorerOut] = []


class BracketRoundOut(BaseModel):
    round_no: int
    stage_label: str | None
    matches: list[MatchOut]


class SettleResult(BaseModel):
    match: MatchDetailOut
    tickets_settled: int
    warning: str | None = None
