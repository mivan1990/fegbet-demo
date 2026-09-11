"""Grupe: clasament (functii PURE, fara DB) + orchestrare admin — PLAN_GRUPE.md sectiunile 5, 6.

Sectiunea 5.3 a planului cere ca `standings` / `qualified_team_ids` sa fie pure (fara
acces la DB), ca sa fie usor de testat izolat — la fel ca `services/scoring.py`.
Restul fisierului (generare/editare/finalizare grupe) e orchestrare DB, la fel ca
`services/bracket.py` care combina o functie pura (`stage_label`) cu una care
atinge baza de date (`generate_bracket`).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from models import (
    Group,
    GroupPrediction,
    GroupPredictionPick,
    GroupQualifier,
    Match,
    MatchScorer,
    Setting,
    Team,
    User,
)
from services.audit import log_action
from services.bracket import BracketError, generate_bracket
from services.points import recalc_all_user_points
from services.scoring import DEFAULT_POINTS


class GroupError(ValueError):
    """Eroare de validare pe domeniul grupelor (mesaj in romana)."""


# ============================================================================ PURE
@dataclass(frozen=True)
class GroupResult:
    """Un meci de grupa deja validat (is_settled), gata de intrat in clasament."""

    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int


@dataclass(frozen=True)
class StandingRow:
    team_id: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    rank: int
    tied_with: tuple[int, ...] = field(default_factory=tuple)


def _base_stats() -> dict[str, int]:
    return {"played": 0, "won": 0, "drawn": 0, "lost": 0, "goals_for": 0, "goals_against": 0}


def _apply_result(stats: dict[int, dict[str, int]], team_id: int, own: int, opp: int) -> None:
    s = stats[team_id]
    s["played"] += 1
    s["goals_for"] += own
    s["goals_against"] += opp
    if own > opp:
        s["won"] += 1
    elif own < opp:
        s["lost"] += 1
    else:
        s["drawn"] += 1


def _points(s: Mapping[str, int]) -> int:
    return s["won"] * 3 + s["drawn"]


def _goal_diff(s: Mapping[str, int]) -> int:
    return s["goals_for"] - s["goals_against"]


def standings(team_ids: Sequence[int], results: Sequence[GroupResult]) -> list[StandingRow]:
    """Clasamentul unei grupe — PLAN_GRUPE.md 5.3.

    Punctaj 3/1/0. Departajare: puncte -> golaveraj -> goluri marcate -> rezultatul
    direct (mini-clasament doar intre echipele ramase egale). Echipele complet egale
    (inclusiv dupa mini-clasament) primesc acelasi rank si apar reciproc in `tied_with`.
    Presupune ca `results` contine doar meciuri intre echipe din `team_ids`.
    """
    ids = list(team_ids)
    stats: dict[int, dict[str, int]] = {tid: _base_stats() for tid in ids}
    for r in results:
        _apply_result(stats, r.home_team_id, r.home_score, r.away_score)
        _apply_result(stats, r.away_team_id, r.away_score, r.home_score)

    def overall_key(tid: int) -> tuple[int, int, int]:
        s = stats[tid]
        return (-_points(s), -_goal_diff(s), -s["goals_for"])

    ids_sorted = sorted(ids, key=overall_key)

    groups: list[list[int]] = []
    for tid in ids_sorted:
        if groups and overall_key(groups[-1][0]) == overall_key(tid):
            groups[-1].append(tid)
        else:
            groups.append([tid])

    final_order: list[int] = []
    tied_with_map: dict[int, tuple[int, ...]] = {}

    for group in groups:
        if len(group) == 1:
            final_order.extend(group)
            tied_with_map[group[0]] = ()
            continue

        gset = set(group)
        mini_stats: dict[int, dict[str, int]] = {tid: _base_stats() for tid in group}
        for r in results:
            if r.home_team_id in gset and r.away_team_id in gset:
                _apply_result(mini_stats, r.home_team_id, r.home_score, r.away_score)
                _apply_result(mini_stats, r.away_team_id, r.away_score, r.home_score)

        def mini_key(tid: int, _mini: dict[int, dict[str, int]] = mini_stats) -> tuple[int, int, int]:
            s = _mini[tid]
            return (-_points(s), -_goal_diff(s), -s["goals_for"])

        group_sorted = sorted(group, key=mini_key)
        subgroups: list[list[int]] = []
        for tid in group_sorted:
            if subgroups and mini_key(subgroups[-1][0]) == mini_key(tid):
                subgroups[-1].append(tid)
            else:
                subgroups.append([tid])

        for sub in subgroups:
            final_order.extend(sub)
            if len(sub) > 1:
                for tid in sub:
                    tied_with_map[tid] = tuple(sorted(t for t in sub if t != tid))
            else:
                tied_with_map[sub[0]] = ()

    rows: list[StandingRow] = []
    rank = 1
    i = 0
    while i < len(final_order):
        tid = final_order[i]
        group_size = len(tied_with_map[tid]) + 1
        for j in range(group_size):
            member = final_order[i + j]
            s = stats[member]
            rows.append(
                StandingRow(
                    team_id=member,
                    played=s["played"],
                    won=s["won"],
                    drawn=s["drawn"],
                    lost=s["lost"],
                    goals_for=s["goals_for"],
                    goals_against=s["goals_against"],
                    goal_diff=_goal_diff(s),
                    points=_points(s),
                    rank=rank,
                    tied_with=tied_with_map[member],
                )
            )
        rank += group_size
        i += group_size
    return rows


def _format_team_ids(ids: Sequence[int]) -> str:
    labels = [f"echipa {tid}" for tid in ids]
    return f"{', '.join(labels[:-1])} și {labels[-1]}"


def qualified_team_ids(rows: Sequence[StandingRow], count: int) -> list[int]:
    """Primele `count` echipe din clasament. GroupError daca taietura e ambigua."""
    if count <= 0:
        raise GroupError("Numărul de calificați trebuie să fie cel puțin 1.")
    if count > len(rows):
        raise GroupError("Numărul de calificați e mai mare decât numărul de echipe din grupă.")

    ordered = sorted(rows, key=lambda r: r.rank)
    selected = [r for r in ordered if r.rank <= count]
    if len(selected) == count:
        return [r.team_id for r in selected]

    boundary = next(r for r in ordered if r.rank <= count < r.rank + len(r.tied_with))
    ids = sorted({boundary.team_id, *boundary.tied_with})
    raise GroupError(
        f"Nu pot departaja {_format_team_ids(ids)} pentru ultimul loc — "
        "alege manual echipele calificate."
    )


def round_robin_pairs(team_ids: Sequence[int]) -> list[tuple[int, int, int]]:
    """Cele 6 meciuri ale unei grupe de 4, metoda cercului — PLAN_GRUPE.md 6.2.

    Intoarce (etapa, home_team_id, away_team_id); fiecare pereche apare o singura data.
    """
    if len(team_ids) != 4:
        raise GroupError("O grupă are nevoie de exact 4 echipe.")
    t1, t2, t3, t4 = team_ids
    return [
        (1, t1, t4),
        (1, t2, t3),
        (2, t4, t3),
        (2, t1, t2),
        (3, t2, t4),
        (3, t3, t1),
    ]


def group_locks_at(scheduled_ats: Iterable[datetime | None]) -> datetime | None:
    """min(scheduled_at) dintre meciurile grupei, sau None daca niciunul nu are ora."""
    values = [s for s in scheduled_ats if s is not None]
    return min(values) if values else None


def group_lock_inputs(db: Session, group: Group) -> tuple[datetime | None, bool, bool]:
    """(locks_at, has_settled_match, is_finalized) pentru `group_lock_reason` / assert.

    Presupune ca `group.matches` e deja incarcat (selectinload) — nu declanseaza un query
    suplimentar pentru meciuri, doar pentru existenta unui `GroupQualifier`.
    """
    matches = list(group.matches)
    locks_at = group_locks_at(m.scheduled_at for m in matches)
    has_settled_match = any(m.is_settled for m in matches)
    is_finalized = (
        db.execute(select(GroupQualifier.id).where(GroupQualifier.group_id == group.id).limit(1))
        .scalar_one_or_none()
        is not None
    )
    return locks_at, has_settled_match, is_finalized


def group_lock_reason(
    *,
    locks_at: datetime | None,
    has_settled_match: bool,
    is_finalized: bool,
    now: datetime | None = None,
) -> str | None:
    """Sursa unica de adevar pentru "de ce e blocata grupa la pronostic" (PLAN_GRUPE.md 5.4).

    Intoarce mesajul in romana daca grupa e blocata, sau None daca pronosticul se poate
    inca plasa/edita. "Blocat" = grupa a inceput SAU s-a jucat deja, nu doar "a trecut ora
    programata":
      - grupa e deja finalizata (exista GroupQualifier) -> mesajul cel mai specific;
      - cel putin un meci al grupei e deja validat (`Match.is_settled`), indiferent de ora
        programata (admin poate valida devreme, sau ora poate fi gresita) -> a doua prioritate;
      - a trecut ora programata (`locks_at <= now`) -> regula de baza, ramasa neschimbata.

    Folosita atat de `assert_group_open_for_prediction` (ridica HTTPException) cat si de
    `build_group_out` (calculeaza `GroupOut.is_locked`) — ca sa nu poata diverge intre ele.
    """
    now = now or datetime.now(timezone.utc)
    if is_finalized:
        return "Grupa s-a încheiat — pronosticurile s-au închis."
    if has_settled_match:
        return (
            "Grupa a început — cel puțin un meci a fost deja validat, "
            "nu mai poți schimba pronosticul."
        )
    if locks_at is not None and locks_at <= now:
        return "Grupa a început — nu mai poți schimba pronosticul."
    return None


def group_missed_prediction_reason(
    *,
    locks_at: datetime | None,
    has_settled_match: bool,
    is_finalized: bool,
    now: datetime | None = None,
) -> str | None:
    """Ca `group_lock_reason`, dar formulat pentru un user care N-A PUS deloc
    pronostic — empty state-ul din `GroupCard.tsx`, nu un răspuns de eroare la o
    acțiune. Mesajele lui `group_lock_reason` sunt gândite pentru cineva care
    încearcă să *schimbe* un pronostic existent ("nu mai poți SCHIMBA
    pronosticul"); aici userul n-a apucat să pună niciunul, deci „schimbă" ar suna
    greșit în context. Aceeași sursă de adevăr pentru CÂND grupa e blocată — doar
    formularea textului diferă.
    """
    now = now or datetime.now(timezone.utc)
    if is_finalized:
        return "Grupa s-a încheiat — pronosticurile s-au închis."
    if has_settled_match:
        return (
            "Grupa a început — cel puțin un meci a fost deja validat, "
            "nu mai poți pune pronostic."
        )
    if locks_at is not None and locks_at <= now:
        return "Grupa a început — nu mai poți pune pronostic."
    return None


def assert_group_open_for_prediction(
    locks_at: datetime | None,
    *,
    has_settled_match: bool,
    is_finalized: bool,
    now: datetime | None = None,
) -> None:
    """Sursa unica server-side pentru blocarea pronosticurilor de grupa (PLAN_GRUPE.md 5.4).

    Frontend-ul doar ascunde butoane — nicio regula nu se bazeaza pe el.
    """
    reason = group_lock_reason(
        locks_at=locks_at, has_settled_match=has_settled_match, is_finalized=is_finalized, now=now
    )
    if reason is not None:
        raise HTTPException(status_code=400, detail=reason)
    if locks_at is None:
        raise HTTPException(status_code=400, detail="Grupa n-are încă program.")


def assert_valid_prediction_teams(group: Group, team_ids: Sequence[int]) -> None:
    """Exact `group.qualifiers_count` echipe, fara duplicate, toate din grupa asta."""
    if len(set(team_ids)) != len(team_ids):
        raise HTTPException(status_code=400, detail="Ai ales aceeași echipă de două ori.")
    if len(team_ids) != group.qualifiers_count:
        raise HTTPException(
            status_code=400, detail=f"Trebuie să alegi exact {group.qualifiers_count} echipe."
        )
    valid_ids = {t.id for t in group.teams}
    if not set(team_ids) <= valid_ids:
        raise HTTPException(status_code=400, detail="Poți alege doar echipe din grupa asta.")


# ============================================================================ helpers DB
def _results_for(matches: Sequence[Match]) -> list[GroupResult]:
    return [
        GroupResult(
            home_team_id=m.home_team_id,
            away_team_id=m.away_team_id,
            home_score=m.home_score,
            away_score=m.away_score,
        )
        for m in matches
        if m.is_settled
        and m.home_team_id is not None
        and m.away_team_id is not None
        and m.home_score is not None
        and m.away_score is not None
    ]


def _group_points_settings(db: Session) -> dict[str, str]:
    return {
        s.key: s.value
        for s in db.execute(select(Setting).where(Setting.key.like("pts.group.%"))).scalars()
    }


def _group_setting_int(settings: Mapping[str, str], key: str) -> int:
    if key in settings:
        return int(settings[key])
    return DEFAULT_POINTS[key]


def _create_group_matches(db: Session, group: Group, team_ids: Sequence[int]) -> None:
    for idx, (round_no, home_id, away_id) in enumerate(round_robin_pairs(team_ids)):
        db.add(
            Match(
                round_no=round_no,
                bracket_position=idx % 2,
                stage_label=f"Grupa {group.name} · etapa {round_no}",
                phase="GROUP",
                group_id=group.id,
                home_team_id=home_id,
                away_team_id=away_id,
                status="SCHEDULED",
                is_settled=False,
            )
        )
    db.flush()


def build_group_prediction_out(db: Session, prediction: GroupPrediction):
    from schemas.groups import GroupPickOut, GroupPredictionOut

    team_ids = [p.team_id for p in prediction.picks]
    names = (
        {t.id: t.name for t in db.execute(select(Team).where(Team.id.in_(team_ids))).scalars()}
        if team_ids
        else {}
    )

    settings = _group_points_settings(db)
    qualify_pts = _group_setting_int(settings, "pts.group.qualify")
    perfect_pts = _group_setting_int(settings, "pts.group.perfect")
    potential = len(prediction.picks) * qualify_pts
    if perfect_pts > 0:
        potential += perfect_pts

    picks_out = [
        GroupPickOut(
            team_id=p.team_id,
            team_name=names.get(p.team_id, ""),
            is_correct=p.is_correct,
            points_awarded=p.points_awarded,
        )
        for p in sorted(prediction.picks, key=lambda p: p.team_id)
    ]
    return GroupPredictionOut(
        id=prediction.id,
        group_id=prediction.group_id,
        status=prediction.status,
        total_points=prediction.total_points,
        picks=picks_out,
        potential_points=potential,
        created_at=prediction.created_at,
        updated_at=prediction.updated_at,
    )


def build_group_out(db: Session, group: Group, user: User | None = None):
    from schemas.groups import GroupOut, StandingOut
    from schemas.matches import TeamRef
    from services.match_state import build_match_out, now_utc

    now = now_utc()
    team_by_id = {t.id: t for t in group.teams}
    team_ids = list(team_by_id.keys())
    matches = sorted(group.matches, key=lambda m: (m.round_no, m.bracket_position))
    results = _results_for(matches)
    rows = standings(team_ids, results)

    standings_out = [
        StandingOut(
            team_id=r.team_id,
            team=TeamRef.model_validate(team_by_id[r.team_id]),
            played=r.played,
            won=r.won,
            drawn=r.drawn,
            lost=r.lost,
            goals_for=r.goals_for,
            goals_against=r.goals_against,
            goal_diff=r.goal_diff,
            points=r.points,
            rank=r.rank,
            tied_with=list(r.tied_with),
        )
        for r in rows
    ]

    is_complete = len(matches) > 0 and all(m.is_settled for m in matches)
    has_settled_match = any(m.is_settled for m in matches)
    locks_at = group_locks_at(m.scheduled_at for m in matches)

    qualifiers = list(
        db.execute(
            select(GroupQualifier).where(GroupQualifier.group_id == group.id).order_by(GroupQualifier.rank)
        ).scalars()
    )
    qualified = [TeamRef.model_validate(team_by_id[q.team_id]) for q in qualifiers]
    is_finalized = len(qualifiers) > 0

    # Aceeasi sursa de adevar ca `assert_group_open_for_prediction` — nu doua implementari
    # paralele care pot diverge (vezi bug-ul din PLAN_GRUPE.md: grupa finalizata sau cu un
    # meci validat devreme tot trebuia sa apara blocata, nu doar dupa `locks_at`).
    lock_reason = group_lock_reason(
        locks_at=locks_at, has_settled_match=has_settled_match, is_finalized=is_finalized, now=now,
    )
    is_locked = lock_reason is not None
    missed_prediction_reason = group_missed_prediction_reason(
        locks_at=locks_at, has_settled_match=has_settled_match, is_finalized=is_finalized, now=now,
    )

    my_prediction_out = None
    if user is not None:
        pred = db.execute(
            select(GroupPrediction)
            .options(selectinload(GroupPrediction.picks))
            .where(GroupPrediction.user_id == user.id, GroupPrediction.group_id == group.id)
        ).scalar_one_or_none()
        if pred is not None:
            my_prediction_out = build_group_prediction_out(db, pred)

    return GroupOut(
        id=group.id,
        name=group.name,
        sort_order=group.sort_order,
        qualifiers_count=group.qualifiers_count,
        teams=[TeamRef.model_validate(t) for t in sorted(group.teams, key=lambda t: t.name)],
        standings=standings_out,
        matches=[build_match_out(m, now=now) for m in matches],
        is_complete=is_complete,
        is_finalized=is_finalized,
        is_locked=is_locked,
        lock_reason=lock_reason,
        missed_prediction_reason=missed_prediction_reason,
        locks_at=locks_at,
        qualified=qualified,
        my_prediction=my_prediction_out,
    )


# ============================================================================ admin: generare
def generate_groups(db: Session, groups: Sequence[tuple[str, list[int]]]) -> list[Group]:
    """Creeaza grupele + meciurile round-robin. Sterge si regenereaza daca e curat.

    `groups` = [(name, team_ids), ...], fiecare team_ids cu exact 4 id-uri unice.
    Refuza (GroupError) daca exista meciuri de grupa VALIDATE sau pronosticuri PLASATE.
    """
    if not groups:
        raise GroupError("Trimite cel puțin o grupă.")

    names = [name.strip().upper() for name, _ in groups]
    if len(set(names)) != len(names):
        raise GroupError("Numele grupelor trebuie să fie unice.")

    all_team_ids: list[int] = []
    for name, team_ids in groups:
        if len(team_ids) != 4:
            raise GroupError(f"Grupa {name} are nevoie de exact 4 echipe, ai dat {len(team_ids)}.")
        if len(set(team_ids)) != 4:
            raise GroupError(f"Grupa {name} are echipe duplicate.")
        all_team_ids.extend(team_ids)

    if len(set(all_team_ids)) != len(all_team_ids):
        raise GroupError("O echipă nu poate fi în două grupe.")

    teams = db.execute(select(Team).where(Team.id.in_(all_team_ids))).scalars().all()
    by_id = {t.id: t for t in teams}
    missing = [tid for tid in all_team_ids if tid not in by_id]
    if missing:
        raise GroupError(f"Echipe inexistente: {missing}.")
    inactive = [by_id[tid].name for tid in all_team_ids if not by_id[tid].is_active]
    if inactive:
        raise GroupError(f"Echipe dezactivate: {', '.join(inactive)}.")

    if db.execute(
        select(Match.id).where(Match.phase == "GROUP", Match.is_settled.is_(True)).limit(1)
    ).scalar_one_or_none() is not None:
        raise GroupError("Există meciuri de grupă deja validate. Nu pot regenera grupele.")
    if db.execute(select(GroupPrediction.id).limit(1)).scalar_one_or_none() is not None:
        raise GroupError("Există pronosticuri plasate pe grupe. Nu pot regenera grupele.")

    old_groups = db.execute(select(Group)).scalars().all()
    if old_groups:
        old_group_ids = [g.id for g in old_groups]
        for team in db.execute(select(Team).where(Team.group_id.in_(old_group_ids))).scalars():
            team.group_id = None
        old_matches = db.execute(select(Match).where(Match.phase == "GROUP")).scalars().all()
        for m in old_matches:
            db.execute(MatchScorer.__table__.delete().where(MatchScorer.match_id == m.id))
        for m in old_matches:
            db.delete(m)
        db.flush()
        for g in old_groups:
            db.execute(GroupQualifier.__table__.delete().where(GroupQualifier.group_id == g.id))
            db.delete(g)
        db.flush()

    created: list[Group] = []
    for sort_order, (name, team_ids) in enumerate(groups, start=1):
        group = Group(name=name.strip().upper(), sort_order=sort_order, qualifiers_count=2)
        db.add(group)
        db.flush()
        for tid in team_ids:
            by_id[tid].group_id = group.id
        _create_group_matches(db, group, team_ids)
        created.append(group)

    db.flush()
    return created


def create_group(db: Session, name: str, team_ids: Sequence[int], *, actor: User, request) -> Group:
    """Adaugă O SINGURĂ grupă nouă, fără să atingă vreo grupă existentă.

    Spre deosebire de `generate_groups` (reset global, o singură dată per turneu),
    asta e ADITIVĂ: nu șterge nimic, deci nu se lovește de refuzul global al lui
    `generate_groups` cât timp există undeva meciuri de grupă validate sau
    pronosticuri plasate. Utilă și pentru admin în timpul turneului — de ex. dacă a
    uitat o echipă la generarea inițială, poate adăuga o grupă în plus fără să
    repornească totul — deci nu e cod scris doar pentru teste (vezi PLAN_GRUPE.md
    6.2, care lasă generarea inițială neschimbată).

    Reguli: nume unic (validat și de `GroupSpecIn`: 1-2 caractere), exact 4 echipe
    active, niciuna deja alocată altei grupe. `sort_order` = următorul liber.
    """
    name = name.strip().upper()
    if db.execute(select(Group.id).where(Group.name == name)).first():
        raise HTTPException(status_code=409, detail="Există deja o grupă cu numele ăsta.")

    if len(team_ids) != 4 or len(set(team_ids)) != 4:
        raise HTTPException(status_code=400, detail="O grupă are nevoie de exact 4 echipe distincte.")

    teams = db.execute(select(Team).where(Team.id.in_(team_ids))).scalars().all()
    by_id = {t.id: t for t in teams}
    missing = [tid for tid in team_ids if tid not in by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Echipe inexistente: {missing}.")
    inactive = [by_id[tid].name for tid in team_ids if not by_id[tid].is_active]
    if inactive:
        raise HTTPException(status_code=400, detail=f"Echipe dezactivate: {', '.join(inactive)}.")
    taken = [by_id[tid].name for tid in team_ids if by_id[tid].group_id is not None]
    if taken:
        raise HTTPException(status_code=400, detail=f"Deja în altă grupă: {', '.join(taken)}.")

    next_sort_order = (db.execute(select(func.max(Group.sort_order))).scalar_one_or_none() or 0) + 1
    group = Group(name=name, sort_order=next_sort_order, qualifiers_count=2)
    db.add(group)
    db.flush()
    for tid in team_ids:
        by_id[tid].group_id = group.id
    _create_group_matches(db, group, list(team_ids))

    log_action(
        db, "admin.group.create", actor=actor, entity_type="group", entity_id=group.id,
        detail={"name": name, "team_ids": list(team_ids)}, request=request,
    )
    db.commit()
    db.refresh(group)
    return group


def update_group(
    db: Session,
    group: Group,
    *,
    name: str | None,
    qualifiers_count: int | None,
    team_ids: list[int] | None,
    actor: User,
    request,
) -> Group:
    matches = list(db.execute(select(Match).where(Match.group_id == group.id)).scalars())
    if any(m.is_settled for m in matches):
        raise HTTPException(status_code=400, detail="Grupa are meciuri validate. Nu mai poate fi editată.")

    before = {"name": group.name, "qualifiers_count": group.qualifiers_count}
    after: dict = {}

    if name is not None:
        name = name.strip().upper()
        if name != group.name:
            if db.execute(
                select(Group.id).where(Group.name == name, Group.id != group.id)
            ).first():
                raise HTTPException(status_code=409, detail="Există deja o grupă cu numele ăsta.")
            group.name = name
            after["name"] = name

    if qualifiers_count is not None and qualifiers_count != group.qualifiers_count:
        if qualifiers_count < 1 or qualifiers_count > 4:
            raise HTTPException(status_code=400, detail="Numărul de calificați trebuie să fie între 1 și 4.")
        group.qualifiers_count = qualifiers_count
        after["qualifiers_count"] = qualifiers_count

    if team_ids is not None:
        if db.execute(
            select(GroupPrediction.id).where(GroupPrediction.group_id == group.id)
        ).first():
            raise HTTPException(
                status_code=400,
                detail="Există deja pronosticuri pe grupa asta. Nu-i poți schimba echipele.",
            )
        if len(team_ids) != 4 or len(set(team_ids)) != 4:
            raise HTTPException(status_code=400, detail="O grupă are nevoie de exact 4 echipe distincte.")
        teams = db.execute(select(Team).where(Team.id.in_(team_ids))).scalars().all()
        by_id = {t.id: t for t in teams}
        missing = [tid for tid in team_ids if tid not in by_id]
        if missing:
            raise HTTPException(status_code=400, detail=f"Echipe inexistente: {missing}.")
        others_taken = [
            tid for tid in team_ids if by_id[tid].group_id is not None and by_id[tid].group_id != group.id
        ]
        if others_taken:
            raise HTTPException(status_code=400, detail="Una dintre echipe e deja în altă grupă.")

        for m in matches:
            db.execute(MatchScorer.__table__.delete().where(MatchScorer.match_id == m.id))
        for m in matches:
            db.delete(m)
        db.flush()
        for t in db.execute(select(Team).where(Team.group_id == group.id)).scalars():
            t.group_id = None
        for tid in team_ids:
            by_id[tid].group_id = group.id
        db.flush()
        _create_group_matches(db, group, team_ids)
        after["team_ids"] = team_ids

    log_action(
        db, "admin.group.update", actor=actor, entity_type="group", entity_id=group.id,
        detail={"before": before, "after": after}, request=request,
    )
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group: Group, *, actor: User, request) -> None:
    matches = list(db.execute(select(Match).where(Match.group_id == group.id)).scalars())
    if any(m.is_settled for m in matches):
        raise HTTPException(status_code=400, detail="Grupa are meciuri validate. Nu poate fi ștearsă.")
    if db.execute(select(GroupPrediction.id).where(GroupPrediction.group_id == group.id)).first():
        raise HTTPException(status_code=400, detail="Grupa are pronosticuri. Nu poate fi ștearsă.")

    for m in matches:
        db.execute(MatchScorer.__table__.delete().where(MatchScorer.match_id == m.id))
    for m in matches:
        db.delete(m)
    db.flush()
    for t in db.execute(select(Team).where(Team.group_id == group.id)).scalars():
        t.group_id = None
    db.execute(GroupQualifier.__table__.delete().where(GroupQualifier.group_id == group.id))

    log_action(
        db, "admin.group.delete", actor=actor, entity_type="group", entity_id=group.id,
        detail={"name": group.name}, request=request,
    )
    db.delete(group)
    db.commit()


# ============================================================================ admin: finalizare
def finalize_group(
    db: Session, group: Group, team_ids_override: list[int] | None, *, actor: User, request
) -> tuple[Group, list[int], int, bool]:
    """PLAN_GRUPE.md 5.5. Intoarce (grupa, id-uri calificate, nr. pronosticuri decontate, manual)."""
    matches = list(db.execute(select(Match).where(Match.group_id == group.id)).scalars())
    unsettled = [m for m in matches if not m.is_settled]
    if unsettled:
        raise HTTPException(
            status_code=400,
            detail=f"Mai sunt {len(unsettled)} meciuri nevalidate în grupa {group.name}.",
        )

    team_rows = db.execute(select(Team).where(Team.group_id == group.id)).scalars().all()
    team_ids_in_group = {t.id for t in team_rows}

    manual = team_ids_override is not None
    if not manual:
        results = _results_for(matches)
        rows = standings(list(team_ids_in_group), results)
        try:
            qualified_ids = qualified_team_ids(rows, group.qualifiers_count)
        except GroupError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        assert team_ids_override is not None
        if len(set(team_ids_override)) != len(team_ids_override):
            raise HTTPException(status_code=400, detail="Ai pus aceeași echipă de două ori.")
        if len(team_ids_override) != group.qualifiers_count:
            raise HTTPException(
                status_code=400, detail=f"Trebuie să alegi exact {group.qualifiers_count} echipe."
            )
        if not set(team_ids_override) <= team_ids_in_group:
            raise HTTPException(status_code=400, detail="Poți alege doar echipe din grupa asta.")
        qualified_ids = list(team_ids_override)

    before_qualifiers = [
        {"team_id": q.team_id, "rank": q.rank}
        for q in db.execute(
            select(GroupQualifier).where(GroupQualifier.group_id == group.id).order_by(GroupQualifier.rank)
        ).scalars()
    ]

    db.execute(GroupQualifier.__table__.delete().where(GroupQualifier.group_id == group.id))
    db.flush()
    for rank, team_id in enumerate(qualified_ids, start=1):
        db.add(GroupQualifier(group_id=group.id, team_id=team_id, rank=rank))
    db.flush()

    predictions = list(
        db.execute(
            select(GroupPrediction)
            .options(selectinload(GroupPrediction.picks))
            .where(GroupPrediction.group_id == group.id)
        ).scalars()
    )
    settings = _group_points_settings(db)
    qualify_pts = _group_setting_int(settings, "pts.group.qualify")
    perfect_pts = _group_setting_int(settings, "pts.group.perfect")
    qualified_set = set(qualified_ids)

    # 5. anuleaza COMPLET efectul precedent inainte de a recalcula (acelasi tipar ca settlement.py).
    for pred in predictions:
        for pick in pred.picks:
            pick.is_correct = None
            pick.points_awarded = None
        pred.total_points = None
        pred.status = "OPEN"
    db.flush()

    for pred in predictions:
        total = 0
        correct = 0
        for pick in pred.picks:
            is_correct = pick.team_id in qualified_set
            points = qualify_pts if is_correct else 0
            pick.is_correct = is_correct
            pick.points_awarded = points
            total += points
            correct += 1 if is_correct else 0
        if perfect_pts > 0 and pred.picks and correct == len(pred.picks):
            total += perfect_pts
        pred.total_points = total
        pred.status = "SETTLED"
    db.flush()

    recalc_all_user_points(db)

    log_action(
        db, "admin.group.finalize", actor=actor, entity_type="group", entity_id=group.id,
        detail={
            "before": before_qualifiers,
            "after": [{"team_id": tid, "rank": r} for r, tid in enumerate(qualified_ids, start=1)],
            "predictions_settled": len(predictions),
            "manual": manual,
        },
        request=request,
    )
    db.commit()
    db.refresh(group)
    return group, qualified_ids, len(predictions), manual


# ============================================================================ admin: bracket
def _bracket_seed_order(groups_with_qualifiers: list[tuple[Group, list[GroupQualifier]]]) -> list[int]:
    """Ordinea echipelor pentru `generate_bracket`, dupa calificarea din grupe (6.2).

    Cazul canonic (4 grupe x 2 calificati): imperechere incrucisata
    1G1,2G2,1G3,2G4,1G2,2G1,1G4,2G3 — nicio echipa nu intalneste in sferturi o echipa
    din propria grupa. Pentru orice alta configuratie, ordinea e simpla: grupele in
    ordinea sort_order, calificatii in ordinea rank-ului.
    """
    ordered = sorted(groups_with_qualifiers, key=lambda gq: gq[0].sort_order)
    if len(ordered) == 4 and all(len(q) == 2 for _, q in ordered):
        by_rank = [{r.rank: r.team_id for r in q} for _, q in ordered]
        g1, g2, g3, g4 = by_rank
        return [g1[1], g2[2], g3[1], g4[2], g2[1], g1[2], g4[1], g3[2]]

    team_ids: list[int] = []
    for _, quals in ordered:
        for q in sorted(quals, key=lambda r: r.rank):
            team_ids.append(q.team_id)
    return team_ids


def generate_bracket_from_groups(db: Session, *, actor: User, request) -> list[Match]:
    groups = list(db.execute(select(Group).order_by(Group.sort_order)).scalars())
    if not groups:
        raise HTTPException(status_code=400, detail="Nu există nicio grupă.")

    groups_with_qualifiers: list[tuple[Group, list[GroupQualifier]]] = []
    for g in groups:
        quals = list(
            db.execute(select(GroupQualifier).where(GroupQualifier.group_id == g.id)).scalars()
        )
        if not quals:
            raise HTTPException(status_code=400, detail=f"Grupa {g.name} nu este finalizată încă.")
        groups_with_qualifiers.append((g, quals))

    total = sum(len(q) for _, q in groups_with_qualifiers)
    if total not in (4, 8, 16):
        raise HTTPException(
            status_code=400,
            detail=f"Din grupe ies {total} echipe, iar bracket-ul acceptă doar 4, 8 sau 16.",
        )

    team_ids = _bracket_seed_order(groups_with_qualifiers)

    try:
        matches = generate_bracket(db, total, team_ids)
    except BracketError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_action(
        db, "admin.bracket.generate_from_groups", actor=actor, entity_type="bracket", entity_id=None,
        detail={"team_ids": team_ids, "size": total}, request=request,
    )
    db.commit()
    return matches


# ============================================================================ test-only
def reset_all_groups(db: Session) -> None:
    """Șterge NECONDIȚIONAT tot domeniul grupelor: pronosticuri, calificați, meciuri
    de grupă, grupele însele; degrupează echipele.

    ATENȚIE — spre deosebire de `generate_groups` (care refuză dacă există progres
    real: meciuri validate sau pronosticuri plasate), asta nu verifică nimic, șterge
    tot necondiționat, inclusiv pronosticuri deja decontate. Există STRICT pentru
    ruta de test `routers/e2e.py` — înregistrată în aplicație doar cu
    `E2E_TEST_MODE=1` (vezi main.py) — ca suita Playwright să poată da specurilor de
    grupe o bază curată între încercări care împart aceeași bază SQLite de test în
    cadrul unei singure rulări `npx playwright test` (vezi
    frontend/e2e/admin-groups-flow.spec.ts). NU o apela din alt cod de producție.
    """
    db.execute(GroupPredictionPick.__table__.delete())
    db.execute(GroupPrediction.__table__.delete())
    db.execute(GroupQualifier.__table__.delete())

    group_match_ids = list(db.execute(select(Match.id).where(Match.phase == "GROUP")).scalars())
    if group_match_ids:
        db.execute(MatchScorer.__table__.delete().where(MatchScorer.match_id.in_(group_match_ids)))
        db.execute(Match.__table__.delete().where(Match.id.in_(group_match_ids)))

    db.execute(Team.__table__.update().where(Team.group_id.is_not(None)).values(group_id=None))
    db.execute(Group.__table__.delete())
    db.commit()


__all__ = [
    "GroupError",
    "GroupResult",
    "StandingRow",
    "standings",
    "qualified_team_ids",
    "round_robin_pairs",
    "group_locks_at",
    "group_lock_inputs",
    "group_lock_reason",
    "group_missed_prediction_reason",
    "assert_group_open_for_prediction",
    "assert_valid_prediction_teams",
    "build_group_out",
    "build_group_prediction_out",
    "generate_groups",
    "create_group",
    "update_group",
    "delete_group",
    "finalize_group",
    "generate_bracket_from_groups",
    "reset_all_groups",
]
