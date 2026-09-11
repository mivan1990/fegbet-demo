"""Scheme Pydantic pentru jucatorii FEG."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

POSITIONS = {"GK", "DEF", "MID", "ATT"}


def _validate_position(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip().upper()
    if not v:
        return None
    if v not in POSITIONS:
        raise ValueError("Pozitia trebuie sa fie GK, DEF, MID sau ATT.")
    return v


class PlayerCreate(BaseModel):
    name: str
    shirt_number: int | None = None
    position: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Numele jucatorului e obligatoriu.")
        return v

    @field_validator("position")
    @classmethod
    def _pos(cls, v: str | None) -> str | None:
        return _validate_position(v)

    @field_validator("shirt_number")
    @classmethod
    def _shirt(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 99):
            raise ValueError("Numarul de tricou e intre 0 si 99.")
        return v


class PlayerUpdate(BaseModel):
    name: str | None = None
    shirt_number: int | None = None
    position: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Numele jucatorului nu poate fi gol.")
        return v

    @field_validator("position")
    @classmethod
    def _pos(cls, v: str | None) -> str | None:
        return _validate_position(v)


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    name: str
    shirt_number: int | None
    position: str | None
    is_active: bool
