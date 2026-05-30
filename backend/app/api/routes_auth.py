from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import assert_refresh_not_expired, get_current_user
from app.api.utils import envelope
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import RefreshToken, Settings, User, UserProfile, UserStats
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
    UserPublic,
)
from app.services.audit import record_audit, record_event

router = APIRouter(prefix="/auth", tags=["auth"])


def _public_user(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        display_name=user.profile.display_name if user.profile else None,
    )


def _issue_tokens(db: Session, user: User) -> TokenPair:
    settings = get_settings()
    access, _, _ = create_token(
        user.id, "access", timedelta(minutes=settings.access_token_minutes)
    )
    refresh, token_id, expires_at = create_token(
        user.id, "refresh", timedelta(days=settings.refresh_token_days)
    )
    db.add(RefreshToken(user_id=user.id, token_id=token_id, expires_at=expires_at))
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/register")
def register(
    payload: RegisterRequest,
    request: Request,
    _: None = Depends(rate_limit("auth_register")),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот email уже зарегистрирован")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add_all(
        [
            UserProfile(user_id=user.id, display_name=payload.display_name),
            UserStats(user_id=user.id),
            Settings(user_id=user.id),
        ]
    )
    tokens = _issue_tokens(db, user)
    record_event(db, "auth.registered", user.id, {})
    record_audit(db, request, "auth.register", user.id)
    db.commit()
    db.refresh(user)
    return envelope(request, {"user": _public_user(user), "tokens": tokens})


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    _: None = Depends(rate_limit("auth_login")),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        record_audit(db, request, "auth.login_failed", None, {"email": payload.email.lower()})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    tokens = _issue_tokens(db, user)
    record_event(db, "auth.login", user.id, {})
    record_audit(db, request, "auth.login", user.id)
    db.commit()
    return envelope(request, {"user": _public_user(user), "tokens": tokens})


@router.post("/refresh")
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный refresh-токен") from exc
    if decoded.get("typ") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный тип токена")
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_id == decoded.get("jti")))
    if not token or token.revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh-токен отозван")
    assert_refresh_not_expired(token.expires_at)
    user = db.get(User, decoded.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь неактивен")
    token.revoked = True
    tokens = _issue_tokens(db, user)
    record_audit(db, request, "auth.refresh", user.id)
    db.commit()
    return envelope(request, {"tokens": tokens})


@router.post("/logout")
def logout(
    payload: RefreshRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        decoded = {}
    if decoded.get("jti"):
        token = db.scalar(select(RefreshToken).where(RefreshToken.token_id == decoded["jti"]))
        if token and token.user_id == user.id:
            token.revoked = True
    record_audit(db, request, "auth.logout", user.id)
    db.commit()
    return envelope(request, {"ok": True})


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    _: None = Depends(rate_limit("reset_password")),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    record_audit(db, request, "auth.reset_password_requested", user.id if user else None)
    if user:
        record_event(db, "auth.reset_password_requested", user.id, {})
    db.commit()
    return envelope(request, {"message": "Если аккаунт существует, инструкции по восстановлению будут отправлены."})
