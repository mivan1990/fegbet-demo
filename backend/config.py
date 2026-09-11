"""Configurare din mediu (.env). Fara secrete in cod."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30

# Adminii impliciti. Parola vine STRICT din mediu (ADMIN_PASSWORD), ca sa nu
# ajunga niciodata in istoricul git. Suprascriibil din mediu (ADMIN_EMAILS,
# separate prin virgula).
#
# In varianta asta publica de demo, contul de admin e cel pe care il foloseste
# butonul „Vezi ca admin" din interfata — vezi README.
DEFAULT_ADMIN_EMAILS = ("admin@mariusivan.ro",)


class Settings:
    def __init__(self) -> None:
        self.jwt_secret: str = os.getenv("JWT_SECRET", "")
        self.allowed_email_domain: str = (
            os.getenv("ALLOWED_EMAIL_DOMAIN", "@mariusivan.ro").strip().lower()
        )
        self.admin_emails: list[str] = [
            e.strip().lower()
            for e in os.getenv("ADMIN_EMAILS", ",".join(DEFAULT_ADMIN_EMAILS)).split(",")
            if e.strip()
        ]
        self.admin_password: str = os.getenv("ADMIN_PASSWORD", "")
        self.app_name: str = os.getenv("APP_NAME", "FEG BET").strip() or "FEG BET"
        self.cors_origins: list[str] = [
            o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
        ]
        self.database_url: str = os.getenv(
            "DATABASE_URL", f"sqlite:///{BASE_DIR / 'fegbet.db'}"
        )
        # Ruta de test /api/e2e/reset-groups (routers/e2e.py) exista in aplicatie
        # DOAR daca variabila asta e "1" — vezi main.py. NU o seta niciodata pe
        # serverul de productie (INSTALARE_SERVER.md); nu apare in .env.example
        # intentionat, ca sa nu ajunga copiata acolo dintr-o greseala.
        self.e2e_test_mode: bool = os.getenv("E2E_TEST_MODE", "").strip() == "1"

    def validate(self) -> None:
        """Cerinta de securitate: fara JWT_SECRET valid, aplicatia NU porneste."""
        if len(self.jwt_secret) < 32:
            raise RuntimeError(
                "JWT_SECRET lipseste sau are sub 32 de caractere. "
                "Completeaza-l in backend/.env inainte de pornire "
                "(python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
            )


settings = Settings()
