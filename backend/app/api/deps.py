"""Shared FastAPI dependencies (current user from JWT cookie, etc.)."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_session
from app.models.core import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    token = None
    if creds:
        token = creds.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return user


async def get_optional_user(
    request: Request, session: AsyncSession = Depends(get_session)
) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token)
        return (await session.execute(
            select(User).where(User.id == payload.get("sub"))
        )).scalar_one_or_none()
    except Exception:  # noqa: BLE001
        return None


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


__all__ = ["get_current_user", "get_optional_user", "require_admin"]
