"""Security primitives: password hashing (Argon2) and JWT cookie helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ALGORITHM = settings.JWT_ALGORITHM


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------
def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "iat": now, "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def cookie_props() -> dict[str, Any]:
    """Return kwargs for `Response.set_cookie` for the auth cookie."""
    return {
        "key": "access_token",
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "max_age": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "path": "/",
    }


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "cookie_props",
]
