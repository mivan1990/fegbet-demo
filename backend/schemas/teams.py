"""Scheme Pydantic pentru echipe."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class TeamBase(BaseModel):
    name: str
    short_name: str | None = None
    logo_url: str | None = None
    is_feg: bool = False
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Numele echipei e obligatoriu.")
        return v

    @field_validator("short_name")
    @classmethod
    def _short(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        if not v:
            return None
        if len(v) > 4:
            raise ValueError("Prescurtarea are maxim 4 caractere.")
        return v


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str | None = None
    short_name: str | None = None
    logo_url: str | None = None
    is_feg: bool | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Numele echipei nu poate fi gol.")
        return v


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str | None
    logo_url: str | None
    is_feg: bool
    is_active: bool


class TeamAdminOut(TeamOut):
    player_count: int = 0
    match_count: int = 0
