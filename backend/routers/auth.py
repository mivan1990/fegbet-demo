"""Rute de autentificare: register, login, me, logout, schimbare parola."""
# Fara `from __future__ import annotations`: FastAPI are nevoie de tipurile reale
# in semnatura rutelor ca sa distinga corpul (RegisterIn) de parametrii de query.

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User, utcnow
from schemas.auth import LoginIn, PasswordChangeIn, RegisterIn, TokenOut, UserOut
from services.audit import log_action
from services.rate_limit import limiter
from services.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Acelasi mesaj pentru domeniu gresit SI pentru email deja folosit, ca sa nu se
# poata deduce domeniul permis prin comparatie de mesaje (PLAN_SONNET.md sectiunea 7).
_GENERIC_REGISTER_ERROR = "Nu am putut crea contul cu acest email."
_GENERIC_LOGIN_ERROR = "Email sau parolă greșite."


def _token_response(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.email), user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    email = payload.email

    # Hash-uim intai (operatia costisitoare), ca ambele cai de respingere sa dureze la fel.
    password_hash = hash_password(payload.password)

    domain_ok = email.endswith(settings.allowed_email_domain)
    already_exists = (
        db.execute(select(User.id).where(User.email == email)).scalar_one_or_none() is not None
    )

    if not domain_ok or already_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_GENERIC_REGISTER_ERROR)

    display_name = payload.display_name or email.split("@", 1)[0]
    user = User(
        email=email,
        password_hash=password_hash,
        display_name=display_name,
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    db.flush()

    log_action(
        db,
        "auth.register",
        actor=user,
        target_user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        detail={"email": email, "display_name": display_name},
        request=request,
    )
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        log_action(
            db,
            "auth.login_failed",
            actor_user_id=user.id if user else None,
            detail={
                "email": payload.email,
                "reason": "unknown_user" if user is None else "bad_credentials",
            },
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_GENERIC_LOGIN_ERROR)

    if not user.is_active:
        log_action(
            db,
            "auth.login_failed",
            actor_user_id=user.id,
            detail={"email": payload.email, "reason": "inactive"},
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contul tău este dezactivat. Vorbește cu un admin.",
        )

    user.last_login_at = utcnow()
    log_action(
        db,
        "auth.login",
        actor=user,
        target_user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, bool]:
    log_action(db, "auth.logout", actor=user, target_user_id=user.id, request=request)
    db.commit()
    return {"ok": True}


@router.put("/password", response_model=UserOut)
def change_password(
    payload: PasswordChangeIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Parola veche nu e corectă."
        )
    user.password_hash = hash_password(payload.new_password)
    log_action(
        db,
        "auth.password_change",
        actor=user,
        target_user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
