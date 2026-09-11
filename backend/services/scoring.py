"""Motorul de punctaj — PLAN_SONNET.md sectiunea 6.

Functii PURE, fara acces la DB. Toata logica de „ce inseamna rezultatul unei
piete" si „cate puncte aduce" traieste aici, ca sa fie usor de testat izolat.
Decontarea (services/settlement.py, Faza 5) combina aceste functii cu DB-ul.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

# Piete
MARKET_WINNER = "WINNER"
MARKET_QUALIFY = "QUALIFY"
MARKET_TOTAL_GOALS = "TOTAL_GOALS"
MARKET_BTTS = "BTTS"
MARKET_SCORER = "SCORER"
ALL_MARKETS = frozenset(
    {MARKET_WINNER, MARKET_QUALIFY, MARKET_TOTAL_GOALS, MARKET_BTTS, MARKET_SCORER}
)

_GOAL_LINES: dict[float, str] = {0.5: "0.5", 1.5: "1.5", 2.5: "2.5", 3.5: "3.5"}
_TOTAL_GOALS_PICKS = frozenset({"OVER", "UNDER"})

# Valorile default din PLAN_SONNET.md sectiunea 6 (identice cu seed.py).
# `points_for` cade pe ele daca o cheie lipseste din `settings`.
DEFAULT_POINTS: dict[str, int] = {
    "pts.winner.side": 3,
    "pts.winner.draw": 4,
    "pts.qualify": 2,
    "pts.goals.over.0.5": 1,
    "pts.goals.over.1.5": 2,
    "pts.goals.over.2.5": 3,
    "pts.goals.over.3.5": 4,
    "pts.goals.under.3.5": 1,
    "pts.goals.under.2.5": 2,
    "pts.goals.under.1.5": 3,
    "pts.goals.under.0.5": 4,
    "pts.btts.yes": 2,
    "pts.btts.no": 2,
    "pts.scorer": 5,
    "pts.bonus.perfect": 0,
    # Faza 9 (PLAN_GRUPE.md sectiunea 4): pronosticul "cine merge mai departe" de grupa.
    "pts.group.qualify": 2,
    "pts.group.perfect": 0,
}


class ScoringError(ValueError):
    """Nu se poate calcula punctajul (date invalide sau meci egal fara penalty-uri)."""


@dataclass(frozen=True)
class Selection:
    market: str
    pick: str
    line: float | None = None
    player_id: int | None = None


@dataclass(frozen=True)
class MatchOutcome:
    home_score: int
    away_score: int
    penalties_home: int | None = None
    penalties_away: int | None = None
    # Perechi (player_id, goals) pentru marcatorii FEG ai meciului.
    scorers: tuple[tuple[int, int], ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------- guards
def _require_score(*values: object) -> None:
    for v in values:
        if v is None or not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise ScoringError("Scorul trebuie sa fie un intreg >= 0.")


def _setting_int(settings: Mapping[str, str], key: str) -> int:
    if key in settings:
        try:
            return int(settings[key])
        except (TypeError, ValueError) as exc:
            raise ScoringError(f"Setarea {key} nu e un numar valid.") from exc
    return DEFAULT_POINTS[key]


# ------------------------------------------------------------------ resolve_* (pure)
def resolve_winner(home_score: int, away_score: int) -> str:
    """Castigatorul in timp regulamentar. Penalty-urile NU conteaza."""
    _require_score(home_score, away_score)
    if home_score > away_score:
        return "HOME"
    if away_score > home_score:
        return "AWAY"
    return "DRAW"


def resolve_qualify(
    home_score: int,
    away_score: int,
    penalties_home: int | None,
    penalties_away: int | None,
) -> str:
    """Ce echipa merge mai departe: „HOME" sau „AWAY".

    La egalitate se decide din penalty-uri; daca lipsesc sau sunt egale,
    decontarea e blocata cu eroare clara.
    """
    _require_score(home_score, away_score)
    if home_score > away_score:
        return "HOME"
    if away_score > home_score:
        return "AWAY"

    if penalties_home is None or penalties_away is None:
        raise ScoringError("Meci egal — completează penalty-urile.")
    _require_score(penalties_home, penalties_away)
    if penalties_home > penalties_away:
        return "HOME"
    if penalties_away > penalties_home:
        return "AWAY"
    raise ScoringError("Penalty-urile sunt egale — nu se poate decide calificarea.")


def resolve_total_goals(home_score: int, away_score: int, pick: str, line: float) -> bool:
    """`pick` = OVER / UNDER, `line` in {0.5, 1.5, 2.5, 3.5}. Fara penalty-uri."""
    _require_score(home_score, away_score)
    if pick not in _TOTAL_GOALS_PICKS:
        raise ScoringError("Pariul de total goluri e OVER sau UNDER.")
    if line not in _GOAL_LINES:
        raise ScoringError("Linia de goluri trebuie sa fie 0.5, 1.5, 2.5 sau 3.5.")
    total = home_score + away_score
    return total > line if pick == "OVER" else total < line


def resolve_btts(home_score: int, away_score: int) -> str:
    """„YES" daca ambele echipe au marcat cel putin un gol, altfel „NO"."""
    _require_score(home_score, away_score)
    return "YES" if home_score >= 1 and away_score >= 1 else "NO"


def resolve_scorer(player_id: int, scorers: Iterable[tuple[int, int]]) -> bool:
    """Corect daca `player_id` apare printre marcatori cu cel putin un gol.

    Autogolurile / inregistrarile cu 0 goluri nu conteaza.
    """
    return any(pid == player_id and goals >= 1 for pid, goals in scorers)


# ---------------------------------------------------------------------- points_for
def points_for(selection: Selection, settings: Mapping[str, str]) -> int:
    """Cate puncte aduce o selectie CORECTA de acest tip. Nu verifica corectitudinea."""
    market = selection.market
    if market == MARKET_WINNER:
        key = "pts.winner.draw" if selection.pick == "DRAW" else "pts.winner.side"
        return _setting_int(settings, key)
    if market == MARKET_QUALIFY:
        return _setting_int(settings, "pts.qualify")
    if market == MARKET_TOTAL_GOALS:
        if selection.line not in _GOAL_LINES:
            raise ScoringError("Linia de goluri trebuie sa fie 0.5, 1.5, 2.5 sau 3.5.")
        if selection.pick not in _TOTAL_GOALS_PICKS:
            raise ScoringError("Pariul de total goluri e OVER sau UNDER.")
        key = f"pts.goals.{selection.pick.lower()}.{_GOAL_LINES[selection.line]}"
        return _setting_int(settings, key)
    if market == MARKET_BTTS:
        key = "pts.btts.yes" if selection.pick == "YES" else "pts.btts.no"
        return _setting_int(settings, key)
    if market == MARKET_SCORER:
        return _setting_int(settings, "pts.scorer")
    raise ScoringError(f"Piata necunoscuta: {market}.")


# ----------------------------------------------------------------- market_available
def market_available(
    market: str, *, has_feg: bool, both_teams_set: bool, is_group: bool = False
) -> bool:
    """Ce piete pot aparea pe un bilet, in functie de meci.

    `is_group` = meciul e de grupa (Match.phase == "GROUP"): piata QUALIFY dispare —
    pronosticul "cine merge mai departe" se muta la nivel de grupa (PLAN_GRUPE.md 5.1).
    """
    if market == MARKET_QUALIFY:
        return both_teams_set and not is_group
    if market == MARKET_WINNER:
        return both_teams_set
    if market == MARKET_SCORER:
        return has_feg
    if market in (MARKET_TOTAL_GOALS, MARKET_BTTS):
        return True
    return False


# --------------------------------------------------------------- grade_selection
def grade_selection(
    selection: Selection,
    outcome: MatchOutcome,
    settings: Mapping[str, str],
    *,
    has_feg: bool = True,
    both_teams_set: bool = True,
    is_group: bool = False,
) -> tuple[bool, int]:
    """Intoarce (is_correct, points_awarded) pentru o selectie, dat rezultatul meciului.

    Selectie gresita => (False, 0). Niciodata negativ.
    Ridica ScoringError daca piata nu e disponibila sau meciul e egal fara penalty-uri.
    """
    if not market_available(
        selection.market, has_feg=has_feg, both_teams_set=both_teams_set, is_group=is_group
    ):
        raise ScoringError(f"Piata {selection.market} nu e disponibila pe acest meci.")

    h, a = outcome.home_score, outcome.away_score
    market = selection.market

    # market_available a garantat deja ca `market` e una dintre cele 5 piete cunoscute.
    if market == MARKET_WINNER:
        correct = resolve_winner(h, a) == selection.pick
    elif market == MARKET_QUALIFY:
        correct = (
            resolve_qualify(h, a, outcome.penalties_home, outcome.penalties_away)
            == selection.pick
        )
    elif market == MARKET_TOTAL_GOALS:
        correct = resolve_total_goals(h, a, selection.pick, selection.line or 0.0)
    elif market == MARKET_BTTS:
        correct = resolve_btts(h, a) == selection.pick
    else:  # MARKET_SCORER
        if selection.player_id is None:
            raise ScoringError("Selectia de marcator nu are jucator.")
        correct = resolve_scorer(selection.player_id, outcome.scorers)

    return (correct, points_for(selection, settings) if correct else 0)


# ------------------------------------------------------------------ perfect_bonus
def perfect_bonus(*, correct: int, total: int, settings: Mapping[str, str]) -> int:
    """Bonus „bilet perfect": daca e activat (> 0) si biletul are >= 3 selectii
    TOATE corecte. Dezactivat din default.
    """
    bonus = _setting_int(settings, "pts.bonus.perfect")
    if bonus > 0 and total >= 3 and correct == total:
        return bonus
    return 0
