"""Seed de demo: un turneu complet, jucat si validat de la un capat la altul.

Ruleaza pe o baza goala si produce exact ce vede un vizitator pe
fegbet.mariusivan.ro: 4 grupe jucate, bracket de 8, campion decis, 15 utilizatori
cu bilete decontate si un clasament final.

    python seed_demo.py            # refuza daca baza are deja date
    python seed_demo.py --force    # sterge tot si reconstruieste

Nimic din datele de aici nu apartine unei persoane reale: echipele, jucatorii si
utilizatorii sunt inventati.

De ce nu sunt punctele scrise direct in baza: scorurile trec prin `settle_match`,
adica prin acelasi motor pe care il foloseste adminul cand valideaza un meci in
aplicatie. Asa clasamentul e garantat coerent cu regulile din `services/scoring.py`
— daca cineva apasa „recalculeaza" in admin, nu se schimba nimic.
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database import Base, SessionLocal, engine
from models import (
    Group,
    GroupPrediction,
    GroupPredictionPick,
    Match,
    Player,
    Team,
    Ticket,
    TicketSelection,
    User,
)
from schemas.matches import ScorerIn, SettleIn
from seed import seed_all
from services.groups import (
    finalize_group,
    generate_bracket_from_groups,
    generate_groups,
    qualified_team_ids,
    standings,
)
from services.groups import GroupResult
from services.points import recalc_all_user_points
from services.scoring import DEFAULT_POINTS
from services.security import hash_password

# Sămânța fixă: aceleași date la fiecare rulare, deci demo-ul arată la fel
# după fiecare resetare orară de pe server.
SEED = 20260911
DEMO_PASSWORD = "demo1234"

# Contul cu care intra automat orice vizitator al demo-ului. Biletele lui NU
# sunt aleatoare (vezi _place_tickets si sectiunea "bilete de vitrina" de mai
# jos) — sunt alese pe rand, ca pagina „Biletele mele" sa arate din prima un
# bilet castigat, unul pierdut, cateva partiale si toate cele cinci piete.
VIZITATOR_EMAIL = "test@mariusivan.ro"

# --------------------------------------------------------------------- echipe
# (nume, short_name) — short_name are maximum 4 caractere in model.
GROUPS: dict[str, list[tuple[str, str]]] = {
    "A": [("FEG", "FEG"), ("Dinamo Birou", "DBIR"), ("AS Cafeaua", "ASC"), ("Real Depozit", "RDEP")],
    "B": [
        ("Atletic Contabili", "ATCO"),
        ("FC Serverul", "FCSV"),
        ("Sporting Pauza", "SPPA"),
        ("Juventus Etaj 3", "JUE3"),
    ],
    "C": [
        ("Dynamo Logistică", "DYLO"),
        ("AC Recepția", "ACRE"),
        ("Steaua Parcării", "STPA"),
        ("FC Overtime", "FCOV"),
    ],
    "D": [
        ("Rapid Livrare", "RALI"),
        ("Inter Ședința", "INSE"),
        ("Barcelona Backoffice", "BABO"),
        ("FC Deadline", "FCDE"),
    ],
}

# Cat de des marcheaza fiecare echipa — doar pentru ca scorurile sa nu fie
# uniforme. FEG are oricum rezultatele fortate (vezi _result).
STRENGTH: dict[str, float] = {
    "FEG": 2.2,
    "Atletic Contabili": 1.9,
    "Dynamo Logistică": 1.8,
    "Rapid Livrare": 1.8,
    "FC Serverul": 1.5,
    "Inter Ședința": 1.5,
    "AC Recepția": 1.4,
    "Dinamo Birou": 1.3,
    "Steaua Parcării": 1.2,
    "Barcelona Backoffice": 1.2,
    "Sporting Pauza": 1.1,
    "AS Cafeaua": 1.0,
    "FC Overtime": 1.0,
    "Juventus Etaj 3": 0.9,
    "Real Depozit": 0.9,
    "FC Deadline": 0.8,
}

# --------------------------------------------------------------- utilizatori
# `test@mariusivan.ro` e contul cu care intra vizitatorul (auto-login).
# `accuracy` = cat de des nimereste — de aici iese un clasament cu diferente.
DEMO_USERS: list[tuple[str, str, float]] = [
    ("test@mariusivan.ro", "Vizitator Demo", 0.62),
    ("ana.dumitrache@mariusivan.ro", "Ana Dumitrache", 0.74),
    ("bogdan.ilie@mariusivan.ro", "Bogdan Ilie", 0.70),
    ("carmen.stoica@mariusivan.ro", "Carmen Stoica", 0.66),
    ("dan.marinescu@mariusivan.ro", "Dan Marinescu", 0.64),
    ("elena.vasile@mariusivan.ro", "Elena Vasile", 0.60),
    ("gabriel.toma@mariusivan.ro", "Gabriel Toma", 0.58),
    ("ioana.radu@mariusivan.ro", "Ioana Radu", 0.55),
    ("lucian.enache@mariusivan.ro", "Lucian Enache", 0.52),
    ("maria.ionescu@mariusivan.ro", "Maria Ionescu", 0.49),
    ("nicolae.badea@mariusivan.ro", "Nicolae Badea", 0.46),
    ("oana.craciun@mariusivan.ro", "Oana Crăciun", 0.43),
    ("paul.georgescu@mariusivan.ro", "Paul Georgescu", 0.40),
    ("silvia.munteanu@mariusivan.ro", "Silvia Munteanu", 0.36),
]

# Cand s-a jucat turneul — tot in trecut, ca sa fie limpede ca s-a incheiat.
TODAY = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
GROUP_ROUND_DAYS = {1: -45, 2: -42, 3: -39}
KNOCKOUT_DAYS = {1: -32, 2: -25, 3: -18}  # sferturi / semifinale / finala

# Orele de start. Turneul e unul de birou, deci se joaca seara, dupa program:
# orele de mai jos sunt UTC, iar Romania e pe UTC+3 vara (iulie-august), deci
# 15:00 UTC = 18:00 ora locala.
#
# Meciurile nu incep toate in aceeasi clipa. O etapa de grupe are 8 meciuri, si
# se joaca cate doua odata — doua terenuri in paralel — la fiecare ora. In
# eliminatorii se joaca pe rand, cu pauza intre ele.
GROUP_FIRST_KICKOFF_UTC = 15  # 18:00 local; etapa tine pana la 21:00
GROUP_MATCHES_PER_SLOT = 2
GROUP_SLOT_MINUTES = 60

# round_no -> (ora UTC a primului meci, minute intre meciuri succesive)
KNOCKOUT_KICKOFF = {
    1: (14, 90),   # sferturi: 17:00, 18:30, 20:00, 21:30 local
    2: (16, 120),  # semifinale: 19:00 si 21:00 local
    3: (17, 0),    # finala, singura: 20:00 local
}


# ====================================================================== scoruri
def _goals(rng: random.Random, strength: float) -> int:
    """Goluri marcate de o echipa intr-un meci — distributie simpla, ponderata."""
    weights = [max(0.05, 1.6 - strength), 1.4, strength, strength * 0.55, strength * 0.2]
    return rng.choices([0, 1, 2, 3, 4], weights=weights)[0]


def _result(
    rng: random.Random,
    home: str,
    away: str,
    *,
    allow_draw: bool,
    force_winner: str | None = None,
) -> dict:
    """Un rezultat de meci. `force_winner` e numele echipei care trebuie sa castige."""
    for _ in range(200):
        h = _goals(rng, STRENGTH[home])
        a = _goals(rng, STRENGTH[away])
        if force_winner == home and h <= a:
            continue
        if force_winner == away and a <= h:
            continue
        if not allow_draw and force_winner is None and h == a:
            continue
        return {"home_score": h, "away_score": a, "pen_home": None, "pen_away": None}
    # Fallback determinist, ca sa nu depinda de noroc.
    if force_winner == home:
        return {"home_score": 2, "away_score": 1, "pen_home": None, "pen_away": None}
    if force_winner == away:
        return {"home_score": 1, "away_score": 2, "pen_home": None, "pen_away": None}
    return {"home_score": 1, "away_score": 0, "pen_home": None, "pen_away": None}


def _penalty_result(rng: random.Random) -> dict:
    """Egal in bracket, decis la penalty-uri — exista ca sa se vada si cazul asta."""
    h = rng.choice([1, 2])
    ph, pa = rng.choice([(5, 4), (4, 3), (5, 3), (3, 4), (4, 5)])
    return {"home_score": h, "away_score": h, "pen_home": ph, "pen_away": pa}


def _scorers_for(rng: random.Random, feg_goals: int, feg_players: list[Player]) -> list[tuple[int, int]]:
    """Cine a marcat pentru FEG. Suma golurilor nu are voie sa depaseasca scorul."""
    if feg_goals <= 0:
        return []
    chosen = rng.sample(feg_players, k=min(feg_goals, len(feg_players)))
    out = [(p.id, 1) for p in chosen]
    rest = feg_goals - len(out)
    if rest > 0 and out:
        pid, goals = out[0]
        out[0] = (pid, goals + rest)
    return out


# ====================================================================== bilete
def _winner_pick(h: int, a: int) -> str:
    return "HOME" if h > a else ("AWAY" if a > h else "DRAW")


def _qualify_pick(res: dict) -> str:
    h, a = res["home_score"], res["away_score"]
    if h != a:
        return "HOME" if h > a else "AWAY"
    return "HOME" if (res["pen_home"] or 0) > (res["pen_away"] or 0) else "AWAY"


def _place_tickets(
    db,
    rng: random.Random,
    users: list[tuple[User, float]],
    match: Match,
    res: dict,
    *,
    is_group: bool,
    feg_players: list[Player],
    scorer_ids: set[int],
    visitor: User,
    showcase_state: dict,
) -> None:
    """Bilete pe un meci, inainte de validarea lui — exact ordinea din realitate."""
    h, a = res["home_score"], res["away_score"]
    has_feg = bool(
        (match.home_team and match.home_team.is_feg) or (match.away_team and match.away_team.is_feg)
    )

    markets = ["WINNER", "TOTAL_GOALS", "BTTS"]
    if not is_group:
        markets.append("QUALIFY")
    if has_feg:
        markets.append("SCORER")

    # Vizitatorul (VIZITATOR_EMAIL) ramane in aceasta bucla la fel ca oricare
    # alt utilizator — inclusiv el consuma rng.random()/rng.sample() mai jos —
    # ca sa nu se schimbe deloc secventa de numere aleatoare pentru ceilalti
    # 13 utilizatori. Biletul lui "aleator" rezultat e insa sters imediat dupa
    # bucla (mai jos) si inlocuit, pe unele meciuri alese, cu un bilet de
    # vitrina construit deliberat — vezi _maybe_place_showcase_ticket.
    for user, accuracy in users:
        if rng.random() > 0.72:  # nu toata lumea joaca fiecare meci
            continue
        picked = rng.sample(markets, k=rng.randint(2, min(4, len(markets))))
        ticket = Ticket(user_id=user.id, match_id=match.id, status="OPEN")
        db.add(ticket)
        db.flush()

        for market in picked:
            hit = rng.random() < accuracy
            line = None
            player_id = None

            if market == "WINNER":
                right = _winner_pick(h, a)
                pick = right if hit else rng.choice([p for p in ("HOME", "AWAY", "DRAW") if p != right])
            elif market == "QUALIFY":
                right = _qualify_pick(res)
                pick = right if hit else ("AWAY" if right == "HOME" else "HOME")
            elif market == "TOTAL_GOALS":
                line = rng.choice([0.5, 1.5, 2.5, 3.5])
                right = "OVER" if (h + a) > line else "UNDER"
                pick = right if hit else ("UNDER" if right == "OVER" else "OVER")
            elif market == "BTTS":
                right = "YES" if h >= 1 and a >= 1 else "NO"
                pick = right if hit else ("NO" if right == "YES" else "YES")
            else:  # SCORER
                pick = "SCORED"
                if hit and scorer_ids:
                    player_id = rng.choice(sorted(scorer_ids))
                else:
                    missed = [p.id for p in feg_players if p.id not in scorer_ids]
                    if not missed:
                        continue
                    player_id = rng.choice(missed)

            db.add(
                TicketSelection(
                    ticket_id=ticket.id,
                    market=market,
                    pick=pick,
                    line=line,
                    player_id=player_id,
                )
            )
    db.flush()

    _maybe_place_showcase_ticket(
        db,
        visitor,
        match,
        res,
        is_group=is_group,
        has_feg=has_feg,
        feg_players=feg_players,
        scorer_ids=scorer_ids,
        state=showcase_state,
    )


# ============================================================ bilete de vitrina
# Vizitatorul (VIZITATOR_EMAIL) nu primeste bilete aleatoare (vezi _place_tickets
# mai sus) — primeste un set fix, ales pe rand, ca "Biletele mele" sa arate din
# prima toate cazurile: un bilet castigat integral (cel mai mare punctaj),
# unul pierdut integral, mai multe partiale cu proportii diferite, un bilet
# cu o singura selectie castigata, si toate cele cinci piete — fiecare aparuta
# de mai multe ori, macar o data corecta si macar o data gresita.
#
# Nu foloseste deloc `rng`: alegerea corecta/gresita e facuta direct din
# rezultatul deja calculat al meciului (`res`), deci nu consuma numere din
# fluxul aleator si nu afecteaza biletele celorlalti 13 utilizatori.
#
# Meciurile sunt alese dupa pozitia lor in ordinea de procesare (a N-a oara
# cand apare un meci de tipul cerut), nu dupa ID fix, ca sa ramana valabil
# indiferent de mici schimbari in generarea grupelor/bracket-ului.
def _max_points_total_goals_line(h: int, a: int) -> float:
    """Linia (din {0.5,1.5,2.5,3.5}) care aduce cele mai multe puncte pentru un
    pariu CORECT de total goluri, dat scorul real — folosita doar la biletul
    de vitrina "castigat integral", ca sa fie chiar cel mai gras bilet al lui."""
    total = h + a
    best_line, best_points = 0.5, -1
    for line in (0.5, 1.5, 2.5, 3.5):
        key = f"pts.goals.over.{line}" if total > line else f"pts.goals.under.{line}"
        points = DEFAULT_POINTS[key]
        if points > best_points:
            best_points, best_line = points, line
    return best_line


def _showcase_pick(
    market: str,
    h: int,
    a: int,
    res: dict,
    *,
    correct: bool,
    scorer_ids: set[int],
    feg_players: list[Player],
    total_goals_line: float,
) -> tuple[str, float | None, int | None]:
    """(pick, line, player_id) alese deliberat corect/gresit pentru piata data."""
    if market == "WINNER":
        right = _winner_pick(h, a)
        pick = right if correct else next(p for p in ("HOME", "AWAY", "DRAW") if p != right)
        return pick, None, None
    if market == "QUALIFY":
        right = _qualify_pick(res)
        pick = right if correct else ("AWAY" if right == "HOME" else "HOME")
        return pick, None, None
    if market == "BTTS":
        right = "YES" if h >= 1 and a >= 1 else "NO"
        pick = right if correct else ("NO" if right == "YES" else "YES")
        return pick, None, None
    if market == "TOTAL_GOALS":
        right = "OVER" if (h + a) > total_goals_line else "UNDER"
        pick = right if correct else ("UNDER" if right == "OVER" else "OVER")
        return pick, total_goals_line, None
    if market == "SCORER":
        if correct:
            player_id = sorted(scorer_ids)[0]
        else:
            missed = sorted(p.id for p in feg_players if p.id not in scorer_ids)
            player_id = missed[0]
        return "SCORED", None, player_id
    raise ValueError(f"piata necunoscuta pentru bilet de vitrina: {market}")


def _build_showcase_ticket(
    db,
    visitor: User,
    match: Match,
    res: dict,
    *,
    feg_players: list[Player],
    scorer_ids: set[int],
    picks: list[tuple[str, bool]],
    total_goals_line: float = 1.5,
) -> None:
    h, a = res["home_score"], res["away_score"]

    # Pe meciul asta vizitatorul primeste biletul de vitrina in locul celui
    # aleator, daca bucla din _place_tickets i-a facut unul — uq_ticket_user_match
    # nu permite doua. Se sterge DOAR aici, adica doar pe cele 8 meciuri de
    # vitrina; pe restul isi pastreaza biletele obisnuite, ca sa aiba un istoric
    # credibil si un loc decent in clasament, nu doar opt exemple.
    stray = db.execute(
        select(Ticket).where(Ticket.user_id == visitor.id, Ticket.match_id == match.id)
    ).scalar_one_or_none()
    if stray is not None:
        db.delete(stray)
        db.flush()

    ticket = Ticket(user_id=visitor.id, match_id=match.id, status="OPEN")
    db.add(ticket)
    db.flush()
    for market, correct in picks:
        pick, line, player_id = _showcase_pick(
            market, h, a, res,
            correct=correct,
            scorer_ids=scorer_ids,
            feg_players=feg_players,
            total_goals_line=total_goals_line,
        )
        db.add(
            TicketSelection(
                ticket_id=ticket.id, market=market, pick=pick, line=line, player_id=player_id
            )
        )
    db.flush()


def _maybe_place_showcase_ticket(
    db,
    visitor: User,
    match: Match,
    res: dict,
    *,
    is_group: bool,
    has_feg: bool,
    feg_players: list[Player],
    scorer_ids: set[int],
    state: dict,
) -> None:
    """Alege, pe baza contorului din `state`, daca meciul curent e unul dintre
    meciurile de vitrina si — daca da — construieste biletul potrivit.

    Contoare separate pentru fiecare categorie de meci (grupa+FEG, grupa fara
    FEG, eliminatorii+FEG); "a N-a aparitie" identifica meciul, nu ID-ul lui.
    """
    if is_group:
        if has_feg:
            state["feg_group"] = state.get("feg_group", 0) + 1
            slot = state["feg_group"]
            if slot == 1:
                # T1 — biletul castigat integral, cel mai gras: toate cele 4
                # piete disponibile pe un meci de grupa cu FEG, toate corecte.
                _build_showcase_ticket(
                    db, visitor, match, res,
                    feg_players=feg_players, scorer_ids=scorer_ids,
                    picks=[("WINNER", True), ("TOTAL_GOALS", True), ("BTTS", True), ("SCORER", True)],
                    total_goals_line=_max_points_total_goals_line(res["home_score"], res["away_score"]),
                )
        else:
            state["plain_group"] = state.get("plain_group", 0) + 1
            slot = state["plain_group"]
            if slot == 1:
                # T2 — pierdut integral: toate cele 3 piete disponibile, toate gresite.
                _build_showcase_ticket(
                    db, visitor, match, res,
                    feg_players=feg_players, scorer_ids=scorer_ids,
                    picks=[("WINNER", False), ("TOTAL_GOALS", False), ("BTTS", False)],
                )
            elif slot == 2:
                # T3 — o singura selectie, castigata.
                _build_showcase_ticket(
                    db, visitor, match, res,
                    feg_players=feg_players, scorer_ids=scorer_ids,
                    picks=[("WINNER", True)],
                )
            elif slot == 3:
                # T4 — partial, 1 din 3.
                _build_showcase_ticket(
                    db, visitor, match, res,
                    feg_players=feg_players, scorer_ids=scorer_ids,
                    picks=[("WINNER", True), ("TOTAL_GOALS", False), ("BTTS", False)],
                )
            elif slot == 4:
                # T5 — partial, 2 din 3.
                _build_showcase_ticket(
                    db, visitor, match, res,
                    feg_players=feg_players, scorer_ids=scorer_ids,
                    picks=[("WINNER", False), ("TOTAL_GOALS", True), ("BTTS", True)],
                )
    else:
        if has_feg:
            state["feg_ko"] = state.get("feg_ko", 0) + 1
            slot = state["feg_ko"]
            if slot == 1:
                # T6 — sferturi: partial, 3 din 4 (SCORER gresit).
                _build_showcase_ticket(
                    db, visitor, match, res,
                    feg_players=feg_players, scorer_ids=scorer_ids,
                    picks=[("WINNER", True), ("QUALIFY", True), ("BTTS", True), ("SCORER", False)],
                )
            elif slot == 2:
                # T7 — semifinala: partial, 1 din 2 (QUALIFY gresit de data asta).
                _build_showcase_ticket(
                    db, visitor, match, res,
                    feg_players=feg_players, scorer_ids=scorer_ids,
                    picks=[("QUALIFY", False), ("TOTAL_GOALS", True)],
                )
            elif slot == 3:
                # T8 — finala: partial, 2 din 3.
                _build_showcase_ticket(
                    db, visitor, match, res,
                    feg_players=feg_players, scorer_ids=scorer_ids,
                    picks=[("WINNER", True), ("QUALIFY", True), ("BTTS", False)],
                )


# ====================================================================== rulare
def _wipe(db) -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def build(force: bool) -> None:
    Base.metadata.create_all(engine)
    rng = random.Random(SEED)

    with SessionLocal() as db:
        existing = db.execute(select(Match)).first()
        if existing and not force:
            sys.exit("Baza are deja meciuri. Ruleaza cu --force ca sa o reconstruiesti.")

    if force:
        with SessionLocal() as db:
            _wipe(db)

    with SessionLocal() as db:
        # 1. seed-ul normal al aplicatiei: setari, echipa FEG, lotul ei, adminul
        seed_all(db)
        admin = db.execute(select(User).where(User.is_admin.is_(True))).scalars().first()
        if admin is None:
            sys.exit("Nu s-a creat niciun admin — verifica ADMIN_PASSWORD in .env.")
        feg = db.execute(select(Team).where(Team.is_feg.is_(True))).scalar_one()
        feg_players = list(db.execute(select(Player).where(Player.team_id == feg.id)).scalars())

        # 2. restul echipelor
        by_name: dict[str, Team] = {"FEG": feg}
        for _, teams in GROUPS.items():
            for name, short in teams:
                if name == "FEG":
                    continue
                team = Team(name=name, short_name=short, is_feg=False, is_active=True)
                db.add(team)
                db.flush()
                by_name[name] = team
        db.commit()

        # 3. grupele + meciurile round-robin
        generate_groups(db, [(g, [by_name[n].id for n, _ in teams]) for g, teams in GROUPS.items()])
        db.commit()

        # 4. utilizatorii
        users: list[tuple[User, float]] = []
        for email, display, accuracy in DEMO_USERS:
            user = User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=display,
                is_admin=False,
                is_active=True,
            )
            db.add(user)
            db.flush()
            users.append((user, accuracy))
        db.commit()

        visitor = next(u for u, _ in users if u.email == VIZITATOR_EMAIL)
        showcase_state: dict = {}

        # 5. meciurile de grupa: data, bilete, validare
        group_matches = list(
            db.execute(
                select(Match).where(Match.phase == "GROUP").order_by(Match.group_id, Match.round_no, Match.id)
            ).scalars()
        )
        # Orele: cele 8 meciuri ale unei etape se esaloneaza cate doua pe ora.
        # Ordinea in cadrul etapei e cea de mai sus (grupa, apoi id), deci e
        # stabila intre rulari — conteaza, fiindcă baza se reconstruieste orar.
        by_round: dict[int, list[Match]] = {}
        for match in group_matches:
            by_round.setdefault(match.round_no, []).append(match)
        for round_no, round_matches in by_round.items():
            day = TODAY + timedelta(days=GROUP_ROUND_DAYS[round_no], hours=GROUP_FIRST_KICKOFF_UTC)
            for i, match in enumerate(round_matches):
                slot = i // GROUP_MATCHES_PER_SLOT
                match.scheduled_at = day + timedelta(minutes=slot * GROUP_SLOT_MINUTES)
        db.commit()

        for match in group_matches:
            home = db.get(Team, match.home_team_id)
            away = db.get(Team, match.away_team_id)
            force_winner = feg.name if feg.id in (match.home_team_id, match.away_team_id) else None
            res = _result(rng, home.name, away.name, allow_draw=True, force_winner=force_winner)

            feg_is_home = match.home_team_id == feg.id
            feg_goals = res["home_score"] if feg_is_home else res["away_score"]
            scorers = (
                _scorers_for(rng, feg_goals, feg_players) if force_winner is not None else []
            )
            scorer_ids = {pid for pid, _ in scorers}

            _place_tickets(
                db, rng, users, match, res,
                is_group=True, feg_players=feg_players, scorer_ids=scorer_ids,
                visitor=visitor, showcase_state=showcase_state,
            )
            db.commit()

            settle_one(db, match.id, res, scorers, admin)

        # 6. pronosticurile de grupa — dupa ce s-au jucat meciurile, inainte de
        #    finalizare (asta e momentul in care se pot deconta)
        for group in db.execute(select(Group).order_by(Group.sort_order)).scalars():
            team_ids = [t.id for t in db.execute(select(Team).where(Team.group_id == group.id)).scalars()]
            matches = list(db.execute(select(Match).where(Match.group_id == group.id)).scalars())
            rows = standings(
                team_ids,
                [
                    GroupResult(
                        home_team_id=m.home_team_id,
                        away_team_id=m.away_team_id,
                        home_score=m.home_score,
                        away_score=m.away_score,
                    )
                    for m in matches
                ],
            )
            truth = set(qualified_team_ids(rows, group.qualifiers_count))

            for user, accuracy in users:
                if rng.random() > 0.8:
                    continue
                if rng.random() < accuracy:
                    picks = sorted(truth)
                else:
                    wrong = [t for t in team_ids if t not in truth]
                    picks = [sorted(truth)[0], rng.choice(wrong)] if wrong else sorted(truth)
                prediction = GroupPrediction(user_id=user.id, group_id=group.id, status="OPEN")
                db.add(prediction)
                db.flush()
                for team_id in picks[: group.qualifiers_count]:
                    db.add(GroupPredictionPick(prediction_id=prediction.id, team_id=team_id))
            db.commit()

            finalize_group(db, group, None, actor=admin, request=None)

        # 7. bracket-ul din grupe
        generate_bracket_from_groups(db, actor=admin, request=None)
        db.commit()

        # 8. fazele eliminatorii, runda cu runda: echipele se stiu abia dupa ce
        #    s-a jucat runda precedenta, deci si biletele se pun abia atunci
        rounds = sorted({m.round_no for m in db.execute(select(Match).where(Match.phase == "KNOCKOUT")).scalars()})
        penalty_used = False
        for round_no in rounds:
            matches = list(
                db.execute(
                    select(Match)
                    .where(Match.phase == "KNOCKOUT", Match.round_no == round_no)
                    .order_by(Match.bracket_position)
                ).scalars()
            )
            first_hour, gap_minutes = KNOCKOUT_KICKOFF[round_no]
            for slot, match in enumerate(matches):
                match.scheduled_at = TODAY + timedelta(
                    days=KNOCKOUT_DAYS[round_no],
                    hours=first_hour,
                    minutes=slot * gap_minutes,
                )
                home = db.get(Team, match.home_team_id)
                away = db.get(Team, match.away_team_id)
                feg_in = feg.id in (match.home_team_id, match.away_team_id)

                if not feg_in and not penalty_used and round_no == rounds[0]:
                    res = _penalty_result(rng)
                    penalty_used = True
                else:
                    res = _result(
                        rng, home.name, away.name,
                        allow_draw=False,
                        force_winner=feg.name if feg_in else None,
                    )

                feg_is_home = match.home_team_id == feg.id
                feg_goals = res["home_score"] if feg_is_home else res["away_score"]
                scorers = _scorers_for(rng, feg_goals, feg_players) if feg_in else []
                scorer_ids = {pid for pid, _ in scorers}

                _place_tickets(
                    db, rng, users, match, res,
                    is_group=False, feg_players=feg_players, scorer_ids=scorer_ids,
                    visitor=visitor, showcase_state=showcase_state,
                )
                db.commit()

                settle_one(db, match.id, res, scorers, admin)

        recalc_all_user_points(db)
        db.commit()
        _report(db)


def settle_one(db, match_id: int, res: dict, scorers: list[tuple[int, int]], admin: User) -> None:
    from services.settlement import settle_match

    payload = SettleIn(
        home_score=res["home_score"],
        away_score=res["away_score"],
        penalties_home=res["pen_home"],
        penalties_away=res["pen_away"],
        scorers=[ScorerIn(player_id=pid, goals=goals) for pid, goals in scorers],
    )
    settle_match(db, match_id, payload, actor=admin, request=None)
    db.commit()


def _report(db) -> None:
    final = db.execute(
        select(Match).where(Match.phase == "KNOCKOUT").order_by(Match.round_no.desc())
    ).scalars().first()
    champion = db.get(Team, final.winner_team_id) if final and final.winner_team_id else None

    print("\n--- demo construit ---")
    print(f"meciuri      : {db.execute(select(Match)).scalars().all().__len__()}")
    print(f"bilete       : {db.execute(select(Ticket)).scalars().all().__len__()}")
    print(f"pronosticuri : {db.execute(select(GroupPrediction)).scalars().all().__len__()}")
    print(f"campion      : {champion.name if champion else '—'}")
    print("\nclasament:")
    for i, user in enumerate(
        db.execute(select(User).where(User.is_admin.is_(False)).order_by(User.points.desc())).scalars(), 1
    ):
        print(f"  {i:2}. {user.display_name:22} {user.points:4} p   {user.email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Construieste datele de demo.")
    parser.add_argument("--force", action="store_true", help="sterge tot si reconstruieste")
    build(parser.parse_args().force)
