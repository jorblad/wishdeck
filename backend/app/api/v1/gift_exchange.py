"""Gift Exchange (Secret Santa) API.

Endpoints are gated behind the ``ENABLE_GIFT_EXCHANGE`` feature flag and require
authentication. The organizer (group owner) manages groups, members and runs the
draw; account-holding members (a person linked to the user) may only read their
own assignment.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import effective_value
from app.db.session import get_session
from app.models.core import User
from app.models.gift_exchange import GiftDraw, GiftGroup, GiftGroupMembership, Person
from app.schemas import (
    GiftAssignmentOut,
    GiftDrawResult,
    GiftGroupAddMember,
    GiftGroupCreate,
    GiftGroupOut,
    GiftGroupUpdate,
    GiftHistoryIn,
    GiftMyAssignment,
    PersonOut,
)
from app.services.gift_exchange import compute_draw

router = APIRouter(
    prefix="/gift-exchange",
    tags=["gift-exchange"],
)


async def require_gift_exchange(session: AsyncSession = Depends(get_session)) -> None:
    if not await effective_value("ENABLE_GIFT_EXCHANGE", session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Gift exchange feature is disabled",
        )


# Router-level gate so every endpoint respects the feature flag.
router.dependencies.append(Depends(require_gift_exchange))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _load_group(session: AsyncSession, group_id: str) -> GiftGroup:
    group = (
        await session.execute(
            select(GiftGroup)
            .where(GiftGroup.id == group_id)
            .options(
                selectinload(GiftGroup.memberships).selectinload(GiftGroupMembership.person)
            )
        )
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


async def _access_role(session: AsyncSession, group: GiftGroup, user: User) -> Optional[str]:
    if group.owner_id == user.id:
        return "owner"
    linked = (
        await session.execute(
            select(GiftGroupMembership)
            .join(Person)
            .where(
                GiftGroupMembership.group_id == group.id,
                Person.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    return "participant" if linked else None


async def _require_owner(session: AsyncSession, group: GiftGroup, user: User) -> None:
    if group.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group organizer can do this",
        )


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _member_persons(group: GiftGroup) -> list[Person]:
    return [m.person for m in group.memberships]


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------
@router.get("/groups", response_model=list[GiftGroupOut])
async def list_groups(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GiftGroupOut]:
    owned = (
        await session.execute(
            select(GiftGroup)
            .where(GiftGroup.owner_id == user.id)
            .options(
                selectinload(GiftGroup.memberships).selectinload(GiftGroupMembership.person)
            )
        )
    ).scalars().all()

    participated = (
        await session.execute(
            select(GiftGroup)
            .join(GiftGroupMembership)
            .join(Person)
            .where(Person.user_id == user.id)
        )
    ).scalars().all()

    owned_ids = {g.id for g in owned}
    result: list[GiftGroupOut] = []
    for g in owned:
        out = GiftGroupOut.model_validate(g)
        out.members = [PersonOut.model_validate(p) for p in _member_persons(g)]
        result.append(out)
    for g in participated:
        if g.id in owned_ids:
            continue
        # Participants only see the group exists, never the member list.
        out = GiftGroupOut.model_validate(g)
        out.members = []
        out.my_assignment = await _my_assignment(session, g, user)
        result.append(out)
    return result


@router.post("/groups", response_model=GiftGroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GiftGroupCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GiftGroup:
    group = GiftGroup(name=payload.name, owner_id=user.id)
    session.add(group)
    await session.flush()
    await session.refresh(group, attribute_names=["memberships"])
    return group


@router.get("/groups/{group_id}", response_model=GiftGroupOut)
async def get_group(
    group_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GiftGroupOut:
    group = await _load_group(session, group_id)
    role = await _access_role(session, group, user)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if role == "owner":
        out = GiftGroupOut.model_validate(group)
        out.members = [PersonOut.model_validate(p) for p in _member_persons(group)]
        return out

    # Participant: only reveal their own assignment, never the member list.
    my = await _my_assignment(session, group, user)
    out = GiftGroupOut.model_validate(group)
    out.members = []
    out.my_assignment = my
    return out


@router.put("/groups/{group_id}", response_model=GiftGroupOut)
async def update_group(
    group_id: str,
    payload: GiftGroupUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GiftGroup:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)
    group.name = payload.name
    await session.flush()
    await session.refresh(group, attribute_names=["memberships"])
    return group


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)
    await session.delete(group)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Members (global people linked into a group)
# ---------------------------------------------------------------------------
@router.post("/groups/{group_id}/members", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    group_id: str,
    payload: GiftGroupAddMember,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Person:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)

    person: Optional[Person] = None
    if payload.person_id:
        person = await session.get(Person, payload.person_id)
        if person is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )
    elif payload.name:
        person = Person(name=payload.name, family=payload.family, user_id=payload.user_id)
        session.add(person)
        await session.flush()
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide person_id or name",
        )

    existing = (
        await session.execute(
            select(GiftGroupMembership).where(
                GiftGroupMembership.group_id == group.id,
                GiftGroupMembership.person_id == person.id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(GiftGroupMembership(group_id=group.id, person_id=person.id))
        await session.flush()

    await session.refresh(person)
    return person


@router.delete("/groups/{group_id}/members/{person_id}")
async def remove_member(
    group_id: str,
    person_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)
    membership = (
        await session.execute(
            select(GiftGroupMembership).where(
                GiftGroupMembership.group_id == group.id,
                GiftGroupMembership.person_id == person_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )
    await session.delete(membership)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Draw
# ---------------------------------------------------------------------------
@router.post("/groups/{group_id}/draw", response_model=GiftDrawResult)
async def run_draw(
    group_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GiftDrawResult:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)

    persons = _member_persons(group)
    if len(persons) < 2:
        return GiftDrawResult(
            year=_current_year(),
            assignments=[],
            unsolvable=True,
            message="Need at least two members to draw.",
        )

    year = _current_year()
    previous = await _historical_pairs(session, group.id, year)

    mapping = compute_draw(
        [{"id": p.id, "family": p.family} for p in persons],
        previous_pairs=previous,
    )
    if mapping is None:
        return GiftDrawResult(
            year=year,
            assignments=[],
            unsolvable=True,
            message=(
                "No valid assignment exists with the current family and history "
                "constraints. Try relaxing a family, or add more members."
            ),
        )

    # Replace any existing draw for this year.
    existing = (
        await session.execute(
            select(GiftDraw).where(
                GiftDraw.group_id == group.id, GiftDraw.year == year
            )
        )
    ).scalars().all()
    for row in existing:
        await session.delete(row)
    await session.flush()

    names = {p.id: p.name for p in persons}
    assignments = [
        GiftAssignmentOut(
            giver_id=giver,
            giver_name=names[giver],
            receiver_id=receiver,
            receiver_name=names[receiver],
        )
        for giver, receiver in mapping.items()
    ]
    for a in assignments:
        session.add(
            GiftDraw(
                group_id=group.id,
                year=year,
                giver_id=a.giver_id,
                receiver_id=a.receiver_id,
            )
        )
    await session.flush()
    return GiftDrawResult(year=year, assignments=assignments)


@router.get("/groups/{group_id}/assignments", response_model=list[GiftAssignmentOut])
async def get_assignments(
    group_id: str,
    year: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GiftAssignmentOut]:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)
    year = year or _current_year()
    rows = (
        await session.execute(
            select(GiftDraw).where(
                GiftDraw.group_id == group.id, GiftDraw.year == year
            )
        )
    ).scalars().all()
    if not rows:
        return []
    ids = {r.giver_id for r in rows} | {r.receiver_id for r in rows}
    names = {
        p.id: p.name
        for p in (
            await session.execute(select(Person).where(Person.id.in_(ids)))
        ).scalars().all()
    }
    return [
        GiftAssignmentOut(
            giver_id=r.giver_id,
            giver_name=names.get(r.giver_id, "?"),
            receiver_id=r.receiver_id,
            receiver_name=names.get(r.receiver_id, "?"),
        )
        for r in rows
    ]


@router.post(
    "/groups/{group_id}/assignments",
    response_model=list[GiftAssignmentOut],
    status_code=status.HTTP_201_CREATED,
)
async def set_assignments(
    group_id: str,
    payload: GiftHistoryIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[GiftAssignmentOut]:
    """Set the full set of pairings for a (usually past) year.

    Use this to record previous years' gifts so the first in-app draw avoids
    repeating them. Replaces any draws already stored for that year.
    """
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)

    member_ids = set(
        (
            await session.execute(
                select(GiftGroupMembership.person_id).where(
                    GiftGroupMembership.group_id == group.id
                )
            )
        ).scalars().all()
    )
    if not member_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group has no members.")

    seen_givers = set()
    for pair in payload.assignments:
        if pair.giver_id not in member_ids or pair.receiver_id not in member_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Pairing references a non-member.",
            )
        if pair.giver_id == pair.receiver_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A person cannot give to themselves.",
            )
        if pair.giver_id in seen_givers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate giver in history.",
            )
        seen_givers.add(pair.giver_id)

    existing = (
        await session.execute(
            select(GiftDraw).where(
                GiftDraw.group_id == group.id, GiftDraw.year == payload.year
            )
        )
    ).scalars().all()
    for row in existing:
        await session.delete(row)
    await session.flush()

    names = {
        p.id: p.name
        for p in (
            await session.execute(select(Person).where(Person.id.in_(member_ids)))
        ).scalars().all()
    }
    out: list[GiftAssignmentOut] = []
    for pair in payload.assignments:
        session.add(
            GiftDraw(
                group_id=group.id,
                year=payload.year,
                giver_id=pair.giver_id,
                receiver_id=pair.receiver_id,
            )
        )
        out.append(
            GiftAssignmentOut(
                giver_id=pair.giver_id,
                giver_name=names.get(pair.giver_id, "?"),
                receiver_id=pair.receiver_id,
                receiver_name=names.get(pair.receiver_id, "?"),
            )
        )
    await session.flush()
    return out


@router.get("/groups/{group_id}/history", response_model=list[int])
async def list_history_years(
    group_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[int]:
    """Distinct years that have recorded draws (past or current), newest first."""
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)
    rows = (
        await session.execute(
            select(GiftDraw.year)
            .where(GiftDraw.group_id == group.id)
            .distinct()
            .order_by(GiftDraw.year.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/groups/{group_id}/assignment/me", response_model=GiftMyAssignment)
async def my_assignment_endpoint(
    group_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GiftMyAssignment:
    group = await _load_group(session, group_id)
    role = await _access_role(session, group, user)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    my = await _my_assignment(session, group, user)
    if my is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No assignment yet — the organizer hasn't run the draw.",
        )
    return my


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
async def _historical_pairs(
    session: AsyncSession, group_id: str, year: int
) -> list[tuple[str, str]]:
    """All recorded giver/receiver pairs from years before ``year``.

    Manually-entered history (see ``set_assignments``) and prior in-app draws are
    both avoided so the first in-app draw can respect previous years' gifts.
    """
    rows = (
        await session.execute(
            select(GiftDraw.giver_id, GiftDraw.receiver_id).where(
                GiftDraw.group_id == group_id, GiftDraw.year < year
            )
        )
    ).all()
    return [(g, r) for g, r in rows]


async def _my_assignment(
    session: AsyncSession, group: GiftGroup, user: User
) -> Optional[GiftMyAssignment]:
    membership = (
        await session.execute(
            select(GiftGroupMembership)
            .join(Person)
            .where(
                GiftGroupMembership.group_id == group.id,
                Person.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        return None
    year = _current_year()
    draw = (
        await session.execute(
            select(GiftDraw).where(
                GiftDraw.group_id == group.id,
                GiftDraw.year == year,
                GiftDraw.giver_id == membership.person_id,
            )
        )
    ).scalar_one_or_none()
    if draw is None:
        return None
    receiver = (
        await session.execute(
            select(Person).where(Person.id == draw.receiver_id)
        )
    ).scalar_one_or_none()
    return GiftMyAssignment(
        year=year, receiver_name=receiver.name if receiver else "?"
    )


__all__ = ["router"]
