"""Seed idempotent, rulat la fiecare pornire: setari, echipa FEG, lotul FEG, primul admin."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from models import Player, Setting, Team, User
from services.security import hash_password

logger = logging.getLogger("app.seed")

# Punctajele — PLAN_SONNET.md sectiunea 6. Adminul le poate schimba din UI.
DEFAULT_SETTINGS: dict[str, str] = {
    "pts.winner.side": "3",
    "pts.winner.draw": "4",
    "pts.qualify": "2",
    "pts.goals.over.0.5": "1",
    "pts.goals.over.1.5": "2",
    "pts.goals.over.2.5": "3",
    "pts.goals.over.3.5": "4",
    "pts.goals.under.3.5": "1",
    "pts.goals.under.2.5": "2",
    "pts.goals.under.1.5": "3",
    "pts.goals.under.0.5": "4",
    "pts.btts.yes": "2",
    "pts.btts.no": "2",
    "pts.scorer": "5",
    "pts.bonus.perfect": "0",  # dezactivat din default (alegere explicita a utilizatorului)
    # Faza 9 (PLAN_GRUPE.md sectiunea 4): pronosticul "cine merge mai departe" de grupa.
    "pts.group.qualify": "2",
    "pts.group.perfect": "0",  # dezactivat din default, la fel ca bonusul de bilet perfect
}

# Lot inventat. Asta e varianta publica de demo — niciun nume de aici nu
# apartine unei persoane reale.
FEG_PLAYERS: list[str] = [
    "Andrei Mocanu",
    "Cristian Albu",
    "Darius Neagu",
    "Emil Vâlcu",
    "Florin Barbu",
    "George Lupaș",
    "Horia Șerban",
    "Tudor Dobre",
    "Răzvan Tătaru",
    "Sorin Anghelache",
    "Vlad Petrescu",
]


def _seed_settings(db: Session) -> None:
    existing = {s.key for s in db.execute(select(Setting)).scalars()}
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            db.add(Setting(key=key, value=value))


def _seed_feg_team(db: Session) -> Team:
    team = db.execute(select(Team).where(Team.is_feg.is_(True))).scalar_one_or_none()
    if team is None:
        team = Team(name="FEG", short_name="FEG", is_feg=True, is_active=True)
        db.add(team)
        db.flush()
        logger.info("seed: echipa FEG creata (id=%s)", team.id)
    return team


def _seed_players(db: Session, feg_team: Team) -> None:
    existing = {
        p.name for p in db.execute(select(Player).where(Player.team_id == feg_team.id)).scalars()
    }
    for name in FEG_PLAYERS:
        if name not in existing:
            db.add(Player(team_id=feg_team.id, name=name, is_active=True))


# Nota (varianta de demo): aplicatia originala avea aici si dezactivarea unui
# cont de admin istoric, ramas din bazele vechi. Demo-ul porneste de fiecare
# data de la zero, deci n-are ce migra — mecanismul a fost scos.

# Nume afisate pentru adminii impliciti (clasament, UI) — nu exista niciun
# endpoint de schimbare a display_name in aplicatie, deci valoarea de aici
# ramane PERMANENT cea vazuta de utilizatori. Orice email care nu e in map
# foloseste fallback-ul vechi: prefixul emailului.
ADMIN_DISPLAY_NAMES: dict[str, str] = {
    "admin@mariusivan.ro": "Admin Demo",
}


def _seed_admin(db: Session) -> None:
    """Creeaza/promoveaza adminii din settings.admin_emails.

    Parola se seteaza DOAR la crearea contului — o repornire nu are voie sa
    resetize parola unui admin care si-a schimbat-o deja din aplicatie.
    """
    if not settings.admin_password:
        logger.warning("seed: ADMIN_PASSWORD lipseste — nu se creeaza/promoveaza niciun admin.")
        return

    any_new_admin_active = False
    for email in settings.admin_emails:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            db.add(
                User(
                    email=email,
                    password_hash=hash_password(settings.admin_password),
                    display_name=ADMIN_DISPLAY_NAMES.get(email, email.split("@", 1)[0]),
                    is_admin=True,
                    is_active=True,
                )
            )
            logger.info("seed: admin creat (%s)", email)
            any_new_admin_active = True
        else:
            if not user.is_admin:
                user.is_admin = True
                logger.info("seed: %s promovat la admin", email)
            if user.is_active:
                any_new_admin_active = True
            # parola NU se atinge la un cont deja existent.

    if not any_new_admin_active:
        logger.warning("seed: niciun admin activ dupa seed.")


def seed_all(db: Session) -> None:
    _seed_settings(db)
    feg_team = _seed_feg_team(db)
    _seed_players(db, feg_team)
    _seed_admin(db)
    db.commit()
