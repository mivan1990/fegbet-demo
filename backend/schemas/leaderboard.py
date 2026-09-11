"""Scheme Pydantic pentru clasament."""
from __future__ import annotations

from pydantic import BaseModel


class LeaderboardRow(BaseModel):
    rank: int
    display_name: str
    points: int
    tickets: int
    settled_tickets: int
    won_tickets: int
    correct_selections: int
    total_selections: int
    # Faza 9 (PLAN_GRUPE.md 5.6): punctele din pronosticuri de grupa, separat de bilete.
    group_points: int = 0
    correct_qualifiers: int = 0
    total_qualifiers: int = 0
