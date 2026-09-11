"""Hash parole, JWT, dependinte de rol.

Rolul de admin NU se citeste din token — se ia `user.is_admin` din DB la fiecare
cerere, ca retrogradarea sa aiba efect imediat (PLAN_SONNET.md sectiunea 8).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import JWT_ALGORITHM, JWT_EXPIRE_DAYS, settings
from database import get_db
from models import User

# 72 de octeti este limita bcrypt; parolele mai lungi se trunchiaza (documentat).
_BCRYPT_MAX_BYTES = 72

_bearer = HTTPBearer(auto_error=False)


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def create_access_token(email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "type": "user",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=JWT_EXPIRE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def email_from_token(token: str) -> str | None:
    """Fara verificarea expirarii — folosit doar pentru access log."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[JWT_ALGORITHM], options={"verify_exp": False}
        )
        sub = payload.get("sub")
        return str(sub) if sub else None
    except JWTError:
        return None


def _user_from_credentials(
    creds: HTTPAuthorizationCredentials | None, db: Session
) -> User | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "user":
        return None
    email = payload.get("sub")
    if not email:
        return None
    return db.execute(select(User).where(User.email == str(email).lower())).scalar_one_or_none()


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_credentials(creds, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Nu ești autentificat."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contul tău este dezactivat. Vorbește cu un admin.",
        )
    return user


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    user = _user_from_credentials(creds, db)
    if user is not None and not user.is_active:
        return None
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zona asta e doar pentru șefi.",
        )
    return user


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "-"
