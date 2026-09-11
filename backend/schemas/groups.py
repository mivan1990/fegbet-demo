"""Scheme Pydantic pentru grupe si pronosticuri de grupa — PLAN_GRUPE.md sectiunea 6."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from schemas.matches import MatchOut, TeamRef


# -------------------------------------------------------------------------- admin: input
class GroupSpecIn(BaseModel):
    name: str
    team_ids: list[int]

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip().upper()
        if not v or len(v) > 2:
            raise ValueError("Numele grupei trebuie să aibă 1-2 caractere.")
        return v

    @field_validator("team_ids")
    @classmethod
    def _team_ids(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("Ai pus aceeași echipă de două ori.")
        return v


class GroupsGenerateIn(BaseModel):
    groups: list[GroupSpecIn]

    @field_validator("groups")
    @classmethod
    def _groups(cls, v: list[GroupSpecIn]) -> list[GroupSpecIn]:
        if not v:
            raise ValueError("Trimite cel puțin o grupă.")
        return v


class GroupUpdateIn(BaseModel):
    name: str | None = None
    qualifiers_count: int | None = Field(default=None, ge=1, le=4)
    team_ids: list[int] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        if not v or len(v) > 2:
            raise ValueError("Numele grupei trebuie să aibă 1-2 caractere.")
        return v

    @field_validator("team_ids")
    @classmethod
    def _team_ids(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        if len(set(v)) != len(v):
            raise ValueError("Ai pus aceeași echipă de două ori.")
        return v


class GroupFinalizeIn(BaseModel):
    team_ids: list[int] | None = None

    @field_validator("team_ids")
    @classmethod
    def _team_ids(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        if len(set(v)) != len(v):
            raise ValueError("Ai pus aceeași echipă de două ori.")
        return v


# ---------------------------------------------------------------- pronosticuri: input
class GroupPredictionIn(BaseModel):
    group_id: int
    team_ids: list[int]

    @field_validator("team_ids")
    @classmethod
    def _team_ids(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("Alege cel puțin o echipă.")
        if len(set(v)) != len(v):
            raise ValueError("Ai ales aceeași echipă de două ori.")
        return v


class GroupPredictionUpdateIn(BaseModel):
    team_ids: list[int]

    @field_validator("team_ids")
    @classmethod
    def _team_ids(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("Alege cel puțin o echipă.")
        if len(set(v)) != len(v):
            raise ValueError("Ai ales aceeași echipă de două ori.")
        return v


# -------------------------------------------------------------------------- output
class StandingOut(BaseModel):
    team_id: int
    team: TeamRef
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    rank: int
    tied_with: list[int]


class GroupPickOut(BaseModel):
    team_id: int
    team_name: str
    is_correct: bool | None
    points_awarded: int | None


class GroupPredictionOut(BaseModel):
    id: int
    group_id: int
    status: str
    total_points: int | None
    picks: list[GroupPickOut]
    potential_points: int
    created_at: datetime
    updated_at: datetime


class GroupOut(BaseModel):
    id: int
    name: str
    sort_order: int
    qualifiers_count: int
    teams: list[TeamRef]
    standings: list[StandingOut]
    matches: list[MatchOut]
    is_complete: bool
    is_finalized: bool
    is_locked: bool
    # Exact ce intoarce `services.groups.group_lock_reason` — None cand grupa e
    # deschisa. Gandit pentru un raspuns de eroare la o actiune ("nu mai poti
    # SCHIMBA pronosticul"). Pentru un user care n-a pus deloc pronostic, vezi
    # `missed_prediction_reason` mai jos — nu forta acelasi text in ambele contexte.
    lock_reason: str | None = None
    # Ca `lock_reason`, dar formulat pentru empty state-ul unui user fara pronostic
    # (`services.groups.group_missed_prediction_reason`) — PLAN_GRUPE.md 7.2 /
    # Sarcina 2 din curatenie: GroupCard.tsx afisa mereu acelasi text generic,
    # imprecis pentru o grupa deja incheiata.
    missed_prediction_reason: str | None = None
    locks_at: datetime | None
    qualified: list[TeamRef]
    my_prediction: GroupPredictionOut | None = None
