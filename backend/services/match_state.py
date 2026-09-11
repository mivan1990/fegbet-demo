"""Stare calculata server-side pentru un meci: blocat? se poate paria? are FEG?

Sursa unica de adevar pentru regulile de lock (PLAN_SONNET.md sectiunile 7-8).
Frontend-ul doar ascunde butoane — nicio regula nu se bazeaza pe el.
"""
from __future__ import annotations

from datetime import datetime, timezone

from models import Match


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def match_has_feg(match: Match) -> bool:
    return bool(
        (match.home_team is not None and match.home_team.is_feg)
        or (match.away_team is not None and match.away_team.is_feg)
    )


def is_bettable(match: Match, now: datetime | None = None) -> bool:
    """Se poate plasa/edita un bilet DOAR daca:
    ambele echipe stabilite ȘI scheduled_at setat ȘI scheduled_at > now ȘI status == SCHEDULED.
    """
    now = now or now_utc()
    return bool(
        match.home_team_id is not None
        and match.away_team_id is not None
        and match.scheduled_at is not None
        and match.scheduled_at > now
        and match.status == "SCHEDULED"
        and not match.is_settled
    )


def is_locked(match: Match, now: datetime | None = None) -> bool:
    """Meciul a inceput / s-a terminat / a fost anulat -> biletul e batut in cuie."""
    now = now or now_utc()
    if match.is_settled or match.status in {"LIVE", "FINISHED", "CANCELLED"}:
        return True
    if match.scheduled_at is not None and match.scheduled_at <= now:
        return True
    return False


def build_match_out(
    match: Match,
    *,
    now: datetime | None = None,
    with_scorers: bool = False,
    my_ticket=None,
):
    """Construieste MatchOut / MatchDetailOut cu campurile calculate server-side."""
    from schemas.matches import MatchDetailOut, MatchOut, ScorerOut, TeamRef

    now = now or now_utc()
    base = {
        "id": match.id,
        "round_no": match.round_no,
        "bracket_position": match.bracket_position,
        "stage_label": match.stage_label,
        "status": match.status,
        "scheduled_at": match.scheduled_at,
        "phase": match.phase,
        "group_id": match.group_id,
        "group_name": match.group.name if match.group is not None else None,
        "home_team": TeamRef.model_validate(match.home_team) if match.home_team else None,
        "away_team": TeamRef.model_validate(match.away_team) if match.away_team else None,
        "home_score": match.home_score,
        "away_score": match.away_score,
        "penalties_home": match.penalties_home,
        "penalties_away": match.penalties_away,
        "winner_team_id": match.winner_team_id,
        "is_settled": match.is_settled,
        "next_match_id": match.next_match_id,
        "next_slot": match.next_slot,
        "is_locked": is_locked(match, now),
        "is_bettable": is_bettable(match, now),
        "has_feg": match_has_feg(match),
        "my_ticket": my_ticket,
    }
    if with_scorers:
        scorers = [
            ScorerOut(player_id=s.player_id, name=s.player.name, goals=s.goals)
            for s in match.scorers
        ]
        return MatchDetailOut(**base, scorers=scorers)
    return MatchOut(**base)
