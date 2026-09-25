"""Authenticated user directory search (for picking wishlist collaborators)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.core import User
from app.schemas import UserSearchOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserSearchOut])
async def search_users(
    q: str | None = Query(None, description="Filter by email/username/full name"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[User]:
    """List users so a wishlist owner/admin can share a list with them.

    Any authenticated user may search the directory (needed to pick
    collaborators); it never exposes sensitive fields like password/hash.
    """
    stmt = select(User).where(User.is_active.is_(True))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            User.email.ilike(like)
            | User.username.ilike(like)
            | User.full_name.ilike(like)
        )
    stmt = stmt.order_by(User.full_name.is_(None), User.full_name, User.email).limit(limit)
    return (await session.execute(stmt)).scalars().all()


__all__ = ["router"]
