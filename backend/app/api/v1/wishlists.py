"""Wishlist CRUD + public/unlisted sharing + item claim/reserve controls."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_optional_user
from app.core.config import effective_value
from app.models.core import _uuid
from app.db.session import get_session
from app.models.core import User
from app.models.wishlist import (
    Category,
    ClaimStatus,
    Visibility,
    WishItem,
    Wishlist,
)
from app.schemas import (
    CategoryBase,
    CategoryOut,
    WishItemCreate,
    WishItemOut,
    WishlistBase,
    WishlistCreate,
    WishlistOut,
    WishlistUpdate,
)

router = APIRouter(prefix="/wishlists", tags=["wishlists"])


# --------------------------------------------------------------------------
# Owned wishlists
# --------------------------------------------------------------------------
@router.get("", response_model=list[WishlistOut])
async def list_my_wishlists(
    archived: bool = False,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[Wishlist]:
    rows = (await session.execute(
        select(Wishlist)
        .options(selectinload(Wishlist.categories), selectinload(Wishlist.items))
        .where(Wishlist.owner_id == user.id, Wishlist.archived == archived)
        .order_by(Wishlist.created_at.desc())
    )).scalars().all()
    for wl in rows:
        _exclude_archived_items(wl)
    return rows


@router.post("", response_model=WishlistOut, status_code=status.HTTP_201_CREATED)
async def create_wishlist(
    payload: WishlistCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Wishlist:
    visibility = payload.visibility
    if visibility not in [v.value for v in Visibility]:
        raise HTTPException(status_code=422, detail="Invalid visibility")
    wl = Wishlist(
        owner_id=user.id,
        slug=str(uuid.uuid4()),
        **{k: (Visibility(v) if k == "visibility" else v) for k, v in payload.model_dump().items()},
    )
    session.add(wl)
    await session.flush()
    await session.refresh(wl, attribute_names=["categories", "items"])
    return wl


@router.get("/{wishlist_id}", response_model=WishlistOut)
async def get_wishlist(
    wishlist_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Wishlist:
    wl = await _get_owned(session, wishlist_id, user)
    await session.refresh(wl, attribute_names=["categories", "items"])
    _exclude_archived_items(wl)
    return wl


@router.put("/{wishlist_id}", response_model=WishlistOut)
async def update_wishlist(
    wishlist_id: str,
    payload: WishlistUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Wishlist:
    wl = await _get_owned(session, wishlist_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(wl, k, Visibility(v) if k == "visibility" else v)
    await session.flush()
    await session.refresh(wl, attribute_names=["categories", "items"])
    return wl


@router.delete("/{wishlist_id}")
async def delete_wishlist(
    wishlist_id: str,
    response: Response,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    wl = await _get_owned(session, wishlist_id, user)
    await session.delete(wl)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


async def _get_owned(session: AsyncSession, wl_id: str, user: User) -> Wishlist:
    wl = (await session.execute(
        select(Wishlist).where(Wishlist.id == wl_id)
    )).scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if wl.owner_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return wl


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------
@router.post("/{wishlist_id}/categories", response_model=CategoryOut, status_code=201)
async def add_category(
    wishlist_id: str,
    payload: CategoryBase,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Category:
    await _get_owned(session, wishlist_id, user)
    cat = Category(wishlist_id=wishlist_id, **payload.model_dump())
    session.add(cat)
    await session.flush()
    return cat


# --------------------------------------------------------------------------
# Items
# --------------------------------------------------------------------------
@router.post("/{wishlist_id}/items", response_model=WishItemOut, status_code=201)
async def add_item(
    wishlist_id: str,
    payload: WishItemCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> WishItem:
    await _get_owned(session, wishlist_id, user)
    item = WishItem(wishlist_id=wishlist_id, **payload.model_dump())
    session.add(item)
    await session.flush()
    return item


@router.put("/items/{item_id}", response_model=WishItemOut)
async def update_item(
    item_id: str,
    payload: WishItemCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> WishItem:
    item = await _get_item_for_owner(session, item_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await session.flush()
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    item = await _get_item_for_owner(session, item_id, user)
    await session.delete(item)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/items/{item_id}/claim", response_model=WishItemOut)
async def claim_item(
    item_id: str,
    claimer_name: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
) -> WishItem:
    """Reserve/claim an item on a public or unlisted list (if permitted)."""
    item = (await session.execute(
        select(WishItem).where(WishItem.id == item_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    wl = (await session.execute(
        select(Wishlist).where(Wishlist.id == item.wishlist_id)
    )).scalar_one_or_none()

    public_claims = await effective_value("ALLOW_PUBLIC_CLAIMS", session)
    if not (wl.allow_claims and (user is not None or public_claims)):
        raise HTTPException(status_code=403, detail="Claiming not allowed")

    item.status = ClaimStatus.CLAIMED
    item.claimed_by = user.id if user else None
    item.claimed_by_name = user.full_name if user else (claimer_name or "Anonymous")
    item.claimed_at = _utcnow()
    await session.flush()
    return item


async def _get_item_for_owner(session: AsyncSession, item_id: str, user: User) -> WishItem:
    item = (await session.execute(
        select(WishItem).where(WishItem.id == item_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    wl = (await session.execute(
        select(Wishlist).where(Wishlist.id == item.wishlist_id)
    )).scalar_one_or_none()
    if wl.owner_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return item


# --------------------------------------------------------------------------
# Public / unlisted (shared) views
# --------------------------------------------------------------------------
@router.get("/public/{slug}", response_model=WishlistOut)
async def public_wishlist(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Wishlist:
    wl = (await session.execute(
        select(Wishlist)
        .options(selectinload(Wishlist.categories), selectinload(Wishlist.items))
        .where(Wishlist.slug == slug)
    )).scalar_one_or_none()
    if not wl or wl.archived:
        raise HTTPException(status_code=404, detail="Not found")
    if wl.visibility.value == Visibility.PRIVATE.value:
        raise HTTPException(status_code=403, detail="Private list")
    _exclude_archived_items(wl)
    return wl


def _exclude_archived_items(wl: Wishlist) -> None:
    """Filter archived items out of an eager-loaded wishlist.items collection."""
    wl.items = [item for item in wl.items if not item.archived]


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


__all__ = ["router"]
