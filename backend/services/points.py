"""Recalculul complet al `User.points` — PLAN_GRUPE.md sectiunea 5.6.

Extras din `services/settlement.py` (pasul 4) ca sa poata fi apelat si din
finalizarea grupelor (`services/groups.finalize_group`), nu doar din decontarea
biletelor. Recalcul COMPLET (nu incremental) — mai lent, dar imposibil de
desincronizat, la fel ca varianta originala din settlement.py.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import GroupPrediction, Ticket, User


def recalc_all_user_points(db: Session) -> None:
    """User.points = SUM(tickets.total_points SETTLED) + SUM(group_predictions.total_points SETTLED)."""
    for user in db.execute(select(User)).scalars():
        ticket_points = db.execute(
            select(func.coalesce(func.sum(Ticket.total_points), 0)).where(
                Ticket.user_id == user.id, Ticket.status == "SETTLED"
            )
        ).scalar_one()
        group_points = db.execute(
            select(func.coalesce(func.sum(GroupPrediction.total_points), 0)).where(
                GroupPrediction.user_id == user.id, GroupPrediction.status == "SETTLED"
            )
        ).scalar_one()
        user.points = ticket_points + group_points


__all__ = ["recalc_all_user_points"]
