"""Scheme Pydantic pentru zonele de admin: loguri, setari, utilizatori."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from schemas.auth import MIN_PASSWORD_LEN

# --------------------------------------------------------------------------- loguri
class LogItemOut(BaseModel):
    id: int
    action: str
    actor_user_id: int | None
    actor_name: str | None
    target_user_id: int | None
    entity_type: str | None
    entity_id: int | None
    detail: object
    ip_address: str | None
    created_at: datetime


class LogPageOut(BaseModel):
    items: list[LogItemOut]
    total: int
    page: int
    pages: int
    actions: list[str]  # actiunile distincte prezente in DB, pentru filtru


# --------------------------------------------------------------------------- setari
class SettingsUpdateIn(BaseModel):
    """Actualizare partiala: doar cheile trimise. Toate valorile sunt intregi."""

    values: dict[str, int]

    @field_validator("values")
    @classmethod
    def _values(cls, v: dict[str, int]) -> dict[str, int]:
        if not v:
            raise ValueError("Nu ai trimis nicio setare.")
        for key, value in v.items():
            if not key.startswith("pts."):
                raise ValueError(f"Cheie de setare necunoscuta: {key}.")
            if value < 0:
                raise ValueError(f"Punctajul pentru {key} nu poate fi negativ.")
        return v


# --------------------------------------------------------------------- utilizatori
class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    points: int
    is_admin: bool
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class SetPasswordIn(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LEN:
            raise ValueError(f"Parola trebuie sa aiba minim {MIN_PASSWORD_LEN} caractere.")
        return v


class SetRoleIn(BaseModel):
    is_admin: bool


class SetActiveIn(BaseModel):
    is_active: bool
