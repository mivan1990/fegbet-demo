"""Decontarea unui meci: validare -> puncte -> avansare in bracket -> re-validare.

PLAN_SONNET.md sectiunea 7. Totul intr-o singura tranzactie. Re-validarea
ANULEAZA complet efectul precedent inainte de a recalcula (punctele vechi nu se
aduna peste cele noi).
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Match, MatchScorer, Player, Setting, Team, Ticket, User
from schemas.matches import SettleIn
from services.audit import log_action
from services.match_state import match_has_feg, now_utc
from services.points import recalc_all_user_points
from services.scoring import (
    MatchOutcome,
    ScoringError,
    Selection,
    grade_selection,
    perfect_bonus,
)


def _points_settings(db: Session) -> dict[str, str]:
    return {
        s.key: s.value
        for s in db.execute(select(Setting).where(Setting.key.like("pts.%"))).scalars()
    }


def _validate_input(db: Session, match: Match, payload: SettleIn) -> None:
    if match.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Meciul e anulat. Nu se poate valida.")
    if match.home_team_id is None or match.away_team_id is None:
        raise HTTPException(status_code=400, detail="Meciul n-are încă ambele echipe stabilite.")

    is_draw = payload.home_score == payload.away_score
    # La meciurile de grupa, egalul e valid fara penalty-uri (PLAN_GRUPE.md 5.2).
    if is_draw and match.phase != "GROUP":
        if payload.penalties_home is None or payload.penalties_away is None:
            raise HTTPException(status_code=400, detail="Meci egal — completează penalty-urile.")
        if payload.penalties_home == payload.penalties_away:
            raise HTTPException(
                status_code=400,
                detail="Penalty-urile sunt egale — nu se poate decide calificarea.",
            )

    has_feg = match_has_feg(match)
    if payload.scorers and not has_feg:
        raise HTTPException(
            status_code=400, detail="Meci fără FEG — n-ai marcatori de completat."
        )

    if payload.scorers:
        feg_team = db.execute(select(Team).where(Team.is_feg.is_(True))).scalar_one_or_none()
        feg_team_id = feg_team.id if feg_team else None
        seen: set[int] = set()
        for s in payload.scorers:
            if s.player_id in seen:
                raise HTTPException(
                    status_code=400, detail="Ai pus același jucător de două ori la marcatori."
                )
            seen.add(s.player_id)
            player = db.get(Player, s.player_id)
            if player is None or player.team_id != feg_team_id:
                raise HTTPException(
                    status_code=400, detail="Marcatorii pot fi doar jucători din lotul FEG."
                )
        feg_is_home = bool(match.home_team and match.home_team.is_feg)
        feg_goals = payload.home_score if feg_is_home else payload.away_score
        total_scorer_goals = sum(s.goals for s in payload.scorers)
        if total_scorer_goals > feg_goals:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Suma golurilor marcatorilor ({total_scorer_goals}) depășește "
                    f"golurile echipei FEG din meci ({feg_goals})."
                ),
            )


def _winner_team_id(match: Match, payload: SettleIn) -> int | None:
    if payload.home_score > payload.away_score:
        return match.home_team_id  # type: ignore[return-value]
    if payload.away_score > payload.home_score:
        return match.away_team_id  # type: ignore[return-value]
    # egal la un meci de grupa -> fara castigator, fara penalty-uri (PLAN_GRUPE.md 3.5/5.2)
    if match.phase == "GROUP":
        return None
    # egal la knockout -> penalty-uri (deja validate ca exista si nu-s egale)
    assert payload.penalties_home is not None and payload.penalties_away is not None
    return (
        match.home_team_id  # type: ignore[return-value]
        if payload.penalties_home > payload.penalties_away
        else match.away_team_id
    )


def _snapshot(match: Match) -> dict:
    return {
        "home_score": match.home_score,
        "away_score": match.away_score,
        "penalties_home": match.penalties_home,
        "penalties_away": match.penalties_away,
        "winner_team_id": match.winner_team_id,
        "scorers": [{"player_id": s.player_id, "goals": s.goals} for s in match.scorers],
    }


def settle_match(
    db: Session, match_id: int, payload: SettleIn, *, actor: User, request
) -> tuple[Match, int, str | None]:
    match = db.execute(
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.scorers),
            selectinload(Match.tickets).selectinload(Ticket.selections),
        )
        .where(Match.id == match_id)
    ).scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Meciul nu există.")

    is_revalidation = match.is_settled
    old_winner_id = match.winner_team_id
    before = _snapshot(match) if is_revalidation else None

    _validate_input(db, match, payload)

    # --- 1. anuleaza efectul precedent (re-validare) ---------------------------
    for ticket in match.tickets:
        for sel in ticket.selections:
            sel.is_correct = None
            sel.points_awarded = None
        ticket.total_points = None
        ticket.status = "OPEN"
    for old_scorer in list(match.scorers):
        db.delete(old_scorer)
    db.flush()

    match.scorers = [
        MatchScorer(match_id=match.id, player_id=s.player_id, goals=s.goals)
        for s in payload.scorers
    ]

    # --- 2. rezultat + castigator --------------------------------------------
    is_draw = payload.home_score == payload.away_score
    is_group = match.phase == "GROUP"
    winner_id = _winner_team_id(match, payload)

    match.home_score = payload.home_score
    match.away_score = payload.away_score
    # Meciurile de grupa nu au niciodata penalty-uri, chiar daca adminul le trimite.
    match.penalties_home = None if is_group else (payload.penalties_home if is_draw else None)
    match.penalties_away = None if is_group else (payload.penalties_away if is_draw else None)
    match.winner_team_id = winner_id
    match.status = "FINISHED"
    db.flush()

    settings = _points_settings(db)
    has_feg = match_has_feg(match)
    outcome = MatchOutcome(
        home_score=payload.home_score,
        away_score=payload.away_score,
        penalties_home=match.penalties_home,
        penalties_away=match.penalties_away,
        scorers=tuple((s.player_id, s.goals) for s in payload.scorers),
    )

    # --- 3. decontarea tuturor biletelor ------------------------------------
    for ticket in match.tickets:
        total = 0
        correct = 0
        for sel in ticket.selections:
            scoring_sel = Selection(
                market=sel.market, pick=sel.pick, line=sel.line, player_id=sel.player_id
            )
            try:
                is_correct, points = grade_selection(
                    scoring_sel,
                    outcome,
                    settings,
                    has_feg=has_feg,
                    both_teams_set=True,
                    is_group=is_group,
                )
            except ScoringError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            sel.is_correct = is_correct
            sel.points_awarded = points
            total += points
            correct += 1 if is_correct else 0
        total += perfect_bonus(correct=correct, total=len(ticket.selections), settings=settings)
        ticket.total_points = total
        ticket.status = "SETTLED"
    db.flush()

    # --- 4. recalcul COMPLET al punctelor tuturor userilor -----------------
    # Extras in services/points.py — aduna si biletele si pronosticurile de grupa
    # (PLAN_GRUPE.md 5.6), ca sa fie folosit si de finalize_group.
    recalc_all_user_points(db)

    # --- 5. avanseaza castigatorul in meciul urmator ----------------------
    warning: str | None = None
    if match.next_match_id and match.next_slot in ("home", "away"):
        next_match = db.get(Match, match.next_match_id)
        if next_match is not None:
            setattr(next_match, f"{match.next_slot}_team_id", winner_id)
            if is_revalidation and old_winner_id != winner_id and next_match.is_settled:
                label = next_match.stage_label or f"runda {next_match.round_no}"
                warning = (
                    f"Meciul următor ({label}) e deja validat, dar acum se califică altă "
                    "echipă. Trebuie să-l revalidezi și pe el manual — nu am făcut-o automat."
                )

    # --- 6. marcheaza decontat -------------------------------------------
    match.is_settled = True
    match.settled_at = now_utc()

    # --- 7. audit ------------------------------------------------------
    tickets_count = len(match.tickets)
    after = {**_snapshot(match), "tickets_settled": tickets_count}
    detail: dict = {"after": after}
    if before is not None:
        detail["before"] = before
    if warning:
        detail["warning"] = warning
    log_action(
        db,
        "admin.match.resettle" if is_revalidation else "admin.match.settle",
        actor=actor,
        entity_type="match",
        entity_id=match.id,
        detail=detail,
        request=request,
    )

    db.commit()
    return match, tickets_count, warning
