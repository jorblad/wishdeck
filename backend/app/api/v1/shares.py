"""Collaborator (shared wishlist) management: owner/admin grant/edit/revoke access."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.wishlist_access import assert_manage, get_wishlist_or_404
from app.db.session import get_session
from app.models.core import User
from app.models.wishlist import WishlistShare
from app.schemas import WishlistShareCreate, WishlistShareOut, WishlistShareUpdate

router = APIRouter(prefix="/wishlists", tags=["shares"])


@router.get("/{wishlist_id}/shares", response_model=list[WishlistShareOut])
async def list_shares(
    wishlist_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[WishlistShare]:
    wl = await get_wishlist_or_404(session, wishlist_id)
    await assert_manage(session, wl, user)
    rows = (await session.execute(
        select(WishlistShare)
        .where(WishlistShare.wishlist_id == wishlist_id)
        .order_by(WishlistShare.created_at)
    )).scalars().all()
    return rows


@router.post("/{wishlist_id}/shares", response_model=WishlistShareOut, status_code=201)
async def add_share(
    wishlist_id: str,
    payload: WishlistShareCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> WishlistShare:
    wl = await get_wishlist_or_404(session, wishlist_id)
    await assert_manage(session, wl, user)

    if payload.user_id == wl.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share with the owner")

    target = (await session.execute(
        select(User).where(User.id == payload.user_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = (await session.execute(
        select(WishlistShare).where(
            WishlistShare.wishlist_id == wishlist_id,
            WishlistShare.user_id == payload.user_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already shared with this user")

    share = WishlistShare(
        wishlist_id=wishlist_id, user_id=payload.user_id, can_edit=payload.can_edit
    )
    session.add(share)
    await session.flush()
    await session.refresh(share, attribute_names=["user"])
    return share


@router.put("/{wishlist_id}/shares/{user_id}", response_model=WishlistShareOut)
async def update_share(
    wishlist_id: str,
    user_id: str,
    payload: WishlistShareUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> WishlistShare:
    wl = await get_wishlist_or_404(session, wishlist_id)
    await assert_manage(session, wl, user)
    share = (await session.execute(
        select(WishlistShare).where(
            WishlistShare.wishlist_id == wishlist_id,
            WishlistShare.user_id == user_id,
        )
    )).scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")
    share.can_edit = payload.can_edit
    await session.flush()
    await session.refresh(share, attribute_names=["user"])
    return share


@router.delete("/{wishlist_id}/shares/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_share(
    wishlist_id: str,
    user_id: str,
    response: Response,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    wl = await get_wishlist_or_404(session, wishlist_id)
    await assert_manage(session, wl, user)
    share = (await session.execute(
        select(WishlistShare).where(
            WishlistShare.wishlist_id == wishlist_id,
            WishlistShare.user_id == user_id,
        )
    )).scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")
    await session.delete(share)
    await session.flush()
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


__all__ = ["router"]
