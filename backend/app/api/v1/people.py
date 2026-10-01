"""Global People directory (used by Gift Exchange).

People are shared across groups and can be linked to a WishDeck user so they
can view their own assignment. Gated by the ``ENABLE_GIFT_EXCHANGE`` flag.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.gift_exchange import require_gift_exchange
from app.db.session import get_session
from app.models.core import User
from app.models.gift_exchange import Person
from app.schemas import PersonCreate, PersonOut, PersonUpdate

router = APIRouter(
    prefix="/people",
    tags=["people"],
    dependencies=[Depends(require_gift_exchange)],
)


@router.get("", response_model=list[PersonOut])
async def list_people(
    q: str | None = Query(None, description="Filter by name"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[Person]:
    stmt = select(Person)
    if q:
        stmt = stmt.where(Person.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Person.name).limit(limit)
    return (await session.execute(stmt)).scalars().all()


@router.post("", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
async def create_person(
    payload: PersonCreate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Person:
    person = Person(name=payload.name, family=payload.family, user_id=payload.user_id)
    session.add(person)
    await session.flush()
    await session.refresh(person)
    return person


@router.get("/{person_id}", response_model=PersonOut)
async def get_person(
    person_id: str,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Person:
    person = await session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


@router.put("/{person_id}", response_model=PersonOut)
async def update_person(
    person_id: str,
    payload: PersonUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Person:
    person = await session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    if payload.name is not None:
        person.name = payload.name
    if payload.family is not None:
        person.family = payload.family
    if payload.user_id is not None:
        person.user_id = payload.user_id
    await session.flush()
    await session.refresh(person)
    return person


__all__ = ["router"]
