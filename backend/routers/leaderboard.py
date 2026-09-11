"""Public: clasamentul utilizatorilor."""
from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from database import get_db
from models import GroupPrediction, GroupPredictionPick, Ticket, TicketSelection, User
from schemas.leaderboard import LeaderboardRow

router = APIRouter(prefix="/api", tags=["leaderboard"])


@router.get("/leaderboard", response_model=list[LeaderboardRow])
def leaderboard(db: Session = Depends(get_db)) -> list[LeaderboardRow]:
    users = db.execute(select(User).where(User.is_active.is_(True))).scalars().all()

    ticket_rows = db.execute(
        select(
            Ticket.user_id,
            func.count(Ticket.id),
            func.sum(case((Ticket.status == "SETTLED", 1), else_=0)),
            func.sum(case(((Ticket.total_points.is_not(None)) & (Ticket.total_points > 0), 1), else_=0)),
        ).group_by(Ticket.user_id)
    ).all()
    tickets_by_user = {
        uid: (total, settled or 0, won or 0) for uid, total, settled, won in ticket_rows
    }

    sel_rows = db.execute(
        select(
            Ticket.user_id,
            func.count(TicketSelection.id),
            func.sum(case((TicketSelection.is_correct.is_(True), 1), else_=0)),
        )
        .join(TicketSelection, TicketSelection.ticket_id == Ticket.id)
        .where(Ticket.status == "SETTLED")
        .group_by(Ticket.user_id)
    ).all()
    selections_by_user = {uid: (total, correct or 0) for uid, total, correct in sel_rows}

    group_points_rows = db.execute(
        select(
            GroupPrediction.user_id,
            func.sum(case((GroupPrediction.status == "SETTLED", GroupPrediction.total_points), else_=0)),
        ).group_by(GroupPrediction.user_id)
    ).all()
    group_points_by_user = {uid: (points or 0) for uid, points in group_points_rows}

    qualifier_rows = db.execute(
        select(
            GroupPrediction.user_id,
            func.count(GroupPredictionPick.id),
            func.sum(case((GroupPredictionPick.is_correct.is_(True), 1), else_=0)),
        )
        .join(GroupPredictionPick, GroupPredictionPick.prediction_id == GroupPrediction.id)
        .where(GroupPrediction.status == "SETTLED")
        .group_by(GroupPrediction.user_id)
    ).all()
    qualifiers_by_user = {uid: (total, correct or 0) for uid, total, correct in qualifier_rows}

    rows: list[dict] = []
    for u in users:
        total, settled, won = tickets_by_user.get(u.id, (0, 0, 0))
        total_sel, correct_sel = selections_by_user.get(u.id, (0, 0))
        total_qual, correct_qual = qualifiers_by_user.get(u.id, (0, 0))
        rows.append(
            {
                "display_name": u.display_name,
                "points": u.points,
                "tickets": total,
                "settled_tickets": settled,
                "won_tickets": won,
                "correct_selections": correct_sel,
                "total_selections": total_sel,
                "group_points": group_points_by_user.get(u.id, 0),
                "correct_qualifiers": correct_qual,
                "total_qualifiers": total_qual,
            }
        )

    rows.sort(key=lambda r: (-r["points"], -r["won_tickets"], r["display_name"].lower()))
    return [LeaderboardRow(rank=i + 1, **r) for i, r in enumerate(rows)]
