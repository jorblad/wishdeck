"""Shared authorization helpers for wishlist access (owner / admin / collaborators)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import User
from app.models.wishlist import Wishlist, WishlistShare


async def get_wishlist_or_404(session: AsyncSession, wl_id: str) -> Wishlist:
    wl = (await session.execute(
        select(Wishlist).where(Wishlist.id == wl_id)
    )).scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return wl


def _is_manager(wl: Wishlist, user: User) -> bool:
    return wl.owner_id == user.id or user.role.value == "admin"


def _share_for(wl: Wishlist, user: User) -> WishlistShare | None:
    for s in wl.shares:
        if s.user_id == user.id:
            return s
    return None


async def assert_manage(session: AsyncSession, wl: Wishlist, user: User) -> None:
    """Only the owner or an admin may add/remove collaborators or delete the list."""
    if not _is_manager(wl, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def assert_edit(session: AsyncSession, wl: Wishlist, user: User) -> None:
    """Owner, admin, or a collaborator with can_edit may modify the list."""
    if _is_manager(wl, user):
        return
    share = _share_for(wl, user)
    if share is None or not share.can_edit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def assert_read(session: AsyncSession, wl: Wishlist, user: User) -> None:
    """Owner, admin, or any collaborator (view or edit) may read the list."""
    if _is_manager(wl, user):
        return
    if _share_for(wl, user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


__all__ = [
    "get_wishlist_or_404",
    "assert_manage",
    "assert_edit",
    "assert_read",
]
