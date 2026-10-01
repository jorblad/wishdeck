"""Gift Exchange (Secret Santa) API.

Endpoints are gated behind the ``ENABLE_GIFT_EXCHANGE`` feature flag and require
authentication. The organizer (group owner) manages groups, participants and
runs the draw; account-holding participants may only read their own assignment.
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
from app.models.gift_exchange import GiftDraw, GiftGroup, GiftParticipant
from app.schemas import (
    GiftAssignmentOut,
    GiftDrawResult,
    GiftGroupCreate,
    GiftGroupOut,
    GiftGroupUpdate,
    GiftMyAssignment,
    GiftParticipantCreate,
    GiftParticipantOut,
    GiftParticipantUpdate,
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
            .options(selectinload(GiftGroup.participants))
        )
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


async def _access_role(session: AsyncSession, group: GiftGroup, user: User) -> Optional[str]:
    if group.owner_id == user.id:
        return "owner"
    participant = (
        await session.execute(
            select(GiftParticipant).where(
                GiftParticipant.group_id == group.id,
                GiftParticipant.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    return "participant" if participant else None


async def _require_owner(session: AsyncSession, group: GiftGroup, user: User) -> None:
    if group.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group organizer can do this",
        )


def _current_year() -> int:
    return datetime.now(timezone.utc).year


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
            .options(selectinload(GiftGroup.participants))
        )
    ).scalars().all()

    participated = (
        await session.execute(
            select(GiftGroup)
            .join(GiftParticipant)
            .where(GiftParticipant.user_id == user.id)
        )
    ).scalars().all()

    owned_ids = {g.id for g in owned}
    result: list[GiftGroupOut] = [GiftGroupOut.model_validate(g) for g in owned]
    for g in participated:
        if g.id in owned_ids:
            continue
        # Participants only see the group exists, not the member list.
        result.append(GiftGroupOut.model_validate(g, update={"participants": []}))
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
    await session.refresh(group, attribute_names=["participants"])
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
        await session.refresh(group, attribute_names=["participants"])
        return GiftGroupOut.model_validate(group)

    # Participant: only reveal their own assignment, never the member list.
    my = await _my_assignment(session, group, user)
    return GiftGroupOut.model_validate(
        group, update={"participants": [], "my_assignment": my}
    )


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
    await session.refresh(group)
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
# Participants
# ---------------------------------------------------------------------------
@router.post(
    "/groups/{group_id}/participants",
    response_model=GiftParticipantOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    group_id: str,
    payload: GiftParticipantCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GiftParticipant:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)
    participant = GiftParticipant(
        group_id=group.id, name=payload.name, family=payload.family
    )
    session.add(participant)
    await session.flush()
    await session.refresh(participant)
    return participant


@router.put(
    "/groups/{group_id}/participants/{participant_id}",
    response_model=GiftParticipantOut,
)
async def update_participant(
    group_id: str,
    participant_id: str,
    payload: GiftParticipantUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GiftParticipant:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)
    participant = (
        await session.execute(
            select(GiftParticipant).where(
                GiftParticipant.id == participant_id,
                GiftParticipant.group_id == group.id,
            )
        )
    ).scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    if payload.name is not None:
        participant.name = payload.name
    if payload.family is not None:
        participant.family = payload.family
    await session.flush()
    await session.refresh(participant)
    return participant


@router.delete("/groups/{group_id}/participants/{participant_id}")
async def remove_participant(
    group_id: str,
    participant_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    group = await _load_group(session, group_id)
    await _require_owner(session, group, user)
    participant = (
        await session.execute(
            select(GiftParticipant).where(
                GiftParticipant.id == participant_id,
                GiftParticipant.group_id == group.id,
            )
        )
    ).scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    await session.delete(participant)
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

    participants = (
        await session.execute(
            select(GiftParticipant).where(GiftParticipant.group_id == group.id)
        )
    ).scalars().all()
    if len(participants) < 2:
        return GiftDrawResult(
            year=_current_year(),
            assignments=[],
            unsolvable=True,
            message="Need at least two participants to draw.",
        )

    year = _current_year()
    previous = await _previous_year_pairs(session, group.id, year)

    mapping = compute_draw(
        [{"id": p.id, "family": p.family} for p in participants],
        previous_pairs=previous,
    )
    if mapping is None:
        return GiftDrawResult(
            year=year,
            assignments=[],
            unsolvable=True,
            message=(
                "No valid assignment exists with the current family and history "
                "constraints. Try relaxing a family, or add more participants."
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

    names = {p.id: p.name for p in participants}
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
            await session.execute(
                select(GiftParticipant).where(GiftParticipant.id.in_(ids))
            )
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


@router.get("/groups/{group_id}/assignment/me", response_model=GiftMyAssignment)
async def my_assignment(
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
async def _previous_year_pairs(
    session: AsyncSession, group_id: str, year: int
) -> list[tuple[str, str]]:
    prior_year = (
        await session.execute(
            select(GiftDraw.year)
            .where(GiftDraw.group_id == group_id, GiftDraw.year < year)
            .order_by(GiftDraw.year.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if prior_year is None:
        return []
    rows = (
        await session.execute(
            select(GiftDraw.giver_id, GiftDraw.receiver_id).where(
                GiftDraw.group_id == group_id, GiftDraw.year == prior_year
            )
        )
    ).all()
    return [(g, r) for g, r in rows]


async def _my_assignment(
    session: AsyncSession, group: GiftGroup, user: User
) -> Optional[GiftMyAssignment]:
    participant = (
        await session.execute(
            select(GiftParticipant).where(
                GiftParticipant.group_id == group.id,
                GiftParticipant.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if participant is None:
        return None
    year = _current_year()
    draw = (
        await session.execute(
            select(GiftDraw).where(
                GiftDraw.group_id == group.id,
                GiftDraw.year == year,
                GiftDraw.giver_id == participant.id,
            )
        )
    ).scalar_one_or_none()
    if draw is None:
        return None
    receiver = (
        await session.execute(
            select(GiftParticipant).where(GiftParticipant.id == draw.receiver_id)
        )
    ).scalar_one_or_none()
    return GiftMyAssignment(
        year=year, receiver_name=receiver.name if receiver else "?"
    )


__all__ = ["router"]
