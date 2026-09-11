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
from services.security import hash_password

# Sămânța fixă: aceleași date la fiecare rulare, deci demo-ul arată la fel
# după fiecare resetare orară de pe server.
SEED = 20260911
DEMO_PASSWORD = "demo1234"

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
TODAY = datetime.now(timezone.utc).replace(hour=19, minute=0, second=0, microsecond=0)
GROUP_ROUND_DAYS = {1: -45, 2: -42, 3: -39}
KNOCKOUT_DAYS = {1: -32, 2: -25, 3: -18}  # sferturi / semifinale / finala


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

        # 5. meciurile de grupa: data, bilete, validare
        group_matches = list(
            db.execute(
                select(Match).where(Match.phase == "GROUP").order_by(Match.group_id, Match.round_no, Match.id)
            ).scalars()
        )
        for match in group_matches:
            match.scheduled_at = TODAY + timedelta(days=GROUP_ROUND_DAYS[match.round_no])
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
            for match in matches:
                match.scheduled_at = TODAY + timedelta(days=KNOCKOUT_DAYS[round_no])
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
