"""Modele SQLAlchemy — PLAN_SONNET.md sectiunea 5.

Reguli:
- toate tabelele au `created_at`; cele mutabile au si `updated_at`;
- datele se stocheaza UTC timezone-aware (vezi `UtcDateTime`).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UtcDateTime(TypeDecorator):
    """DateTime care garanteaza UTC timezone-aware la intrare si la iesire.

    SQLite nu pastreaza fusul orar; fara asta, valorile citite ar fi naive si
    comparatia cu `datetime.now(timezone.utc)` ar arunca — sursa clasica de
    bug-uri la blocarea biletelor.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


# --------------------------------------------------------------------------- users
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# --------------------------------------------------------------------------- groups
class Group(TimestampMixin, Base):
    """O grupa a turneului (A/B/C/D) — PLAN_GRUPE.md sectiunea 3.1."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)  # "A".."D"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    qualifiers_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    teams: Mapped[list["Team"]] = relationship(back_populates="group")
    matches: Mapped[list["Match"]] = relationship(back_populates="group")


class GroupQualifier(Base):
    """Sursa de adevar pentru „cine a iesit din grupa" — scrisa la finalizare (3.2)."""

    __tablename__ = "group_qualifiers"
    __table_args__ = (
        UniqueConstraint("group_id", "rank", name="uq_group_qualifier_group_rank"),
        UniqueConstraint("group_id", "team_id", name="uq_group_qualifier_group_team"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..qualifiers_count
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, nullable=False)

    group: Mapped["Group"] = relationship()
    team: Mapped["Team"] = relationship()


# --------------------------------------------------------------------------- teams
class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(4), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_feg: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Faza 9: grupa din care face parte echipa (nullable — coloana noua pe tabel existent).
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True, index=True)

    players: Mapped[list["Player"]] = relationship(back_populates="team")
    group: Mapped["Group | None"] = relationship(back_populates="teams", foreign_keys=[group_id])


# ------------------------------------------------------------------------- players
class Player(TimestampMixin, Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[str | None] = mapped_column(String(3), nullable=True)  # GK / DEF / MID / ATT
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    team: Mapped["Team"] = relationship(back_populates="players")


# ------------------------------------------------------------------------- matches
class Match(TimestampMixin, Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    bracket_position: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Faza 9: "GROUP" / "KNOCKOUT". Coloana noua -> server_default ca sa mearga ALTER TABLE
    # pe SQLite; meciurile existente devin KNOCKOUT automat (comportament neschimbat).
    phase: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="KNOCKOUT", index=True
    )
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True, index=True)

    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="SCHEDULED", nullable=False)

    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    penalties_home: Mapped[int | None] = mapped_column(Integer, nullable=True)
    penalties_away: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    is_settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)

    next_match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    next_slot: Mapped[str | None] = mapped_column(String(4), nullable=True)  # home / away

    home_team: Mapped["Team | None"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team | None"] = relationship(foreign_keys=[away_team_id])
    winner_team: Mapped["Team | None"] = relationship(foreign_keys=[winner_team_id])
    group: Mapped["Group | None"] = relationship(back_populates="matches", foreign_keys=[group_id])
    scorers: Mapped[list["MatchScorer"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="match")


class MatchScorer(Base):
    __tablename__ = "match_scorers"
    __table_args__ = (UniqueConstraint("match_id", "player_id", name="uq_scorer_match_player"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    goals: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, nullable=False)

    match: Mapped["Match"] = relationship(back_populates="scorers")
    player: Mapped["Player"] = relationship()


# ------------------------------------------------------------------------- tickets
class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (UniqueConstraint("user_id", "match_id", name="uq_ticket_user_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(8), default="OPEN", nullable=False)  # OPEN/SETTLED/VOID
    total_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="tickets")
    match: Mapped["Match"] = relationship(back_populates="tickets")
    selections: Mapped[list["TicketSelection"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class TicketSelection(Base):
    __tablename__ = "ticket_selections"
    __table_args__ = (UniqueConstraint("ticket_id", "market", name="uq_selection_ticket_market"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    market: Mapped[str] = mapped_column(String(16), nullable=False)  # WINNER/QUALIFY/TOTAL_GOALS/BTTS/SCORER
    pick: Mapped[str] = mapped_column(String(16), nullable=False)
    line: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.5 / 1.5 / 2.5 / 3.5
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    points_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, nullable=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="selections")
    player: Mapped["Player | None"] = relationship()


# --------------------------------------------------------------- group_predictions
class GroupPrediction(TimestampMixin, Base):
    """Pronosticul „ce echipe ies din grupa X" al unui user — PLAN_GRUPE.md 3.3."""

    __tablename__ = "group_predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_group_prediction_user_group"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(8), default="OPEN", nullable=False)  # OPEN/SETTLED/VOID
    total_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship()
    group: Mapped["Group"] = relationship()
    picks: Mapped[list["GroupPredictionPick"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )


class GroupPredictionPick(Base):
    __tablename__ = "group_prediction_picks"
    __table_args__ = (
        UniqueConstraint("prediction_id", "team_id", name="uq_group_pick_prediction_team"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("group_predictions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    points_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, nullable=False)

    prediction: Mapped["GroupPrediction"] = relationship(back_populates="picks")
    team: Mapped["Team"] = relationship()


# ------------------------------------------------------------------------ settings
class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


# -------------------------------------------------------------------- activity_logs
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON serializat
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=utcnow, nullable=False, index=True
    )

    actor: Mapped["User | None"] = relationship(foreign_keys=[actor_user_id])


__all__ = [
    "Base",
    "utcnow",
    "UtcDateTime",
    "User",
    "Group",
    "GroupQualifier",
    "Team",
    "Player",
    "Match",
    "MatchScorer",
    "Ticket",
    "TicketSelection",
    "GroupPrediction",
    "GroupPredictionPick",
    "Setting",
    "ActivityLog",
]
