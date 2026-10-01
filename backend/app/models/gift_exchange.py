from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.core import _uuid


class GiftGroup(Base, TimestampMixin):
    """A gift-exchange group (e.g. a family's Secret Santa). Owned by the organizer."""

    __tablename__ = "gift_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    participants: Mapped[list["GiftParticipant"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    draws: Mapped[list["GiftDraw"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GiftParticipant(Base, TimestampMixin):
    """A person in a gift group. May or may not have a WishDeck account."""

    __tablename__ = "gift_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("gift_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Linked WishDeck account (so the participant can log in and see their draw).
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # Family label: participants that share a non-null family are never paired
    # with each other (e.g. siblings), but may be paired with other families
    # (e.g. cousins in a different family).
    family: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)

    group: Mapped["GiftGroup"] = relationship(back_populates="participants")


class GiftDraw(Base, TimestampMixin):
    """One assigned giver→receiver pair for a given year. The full set of rows
    for a (group, year) is the draw; prior years' rows are the history used to
    avoid repeating pairs."""

    __tablename__ = "gift_draws"
    __table_args__ = (
        UniqueConstraint("group_id", "year", "giver_id", name="uq_gift_draw_giver_year"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("gift_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    year: Mapped[int] = mapped_column(index=True, nullable=False)
    giver_id: Mapped[str] = mapped_column(
        ForeignKey("gift_participants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    receiver_id: Mapped[str] = mapped_column(
        ForeignKey("gift_participants.id", ondelete="CASCADE"), index=True, nullable=False
    )

    group: Mapped["GiftGroup"] = relationship(back_populates="draws")


__all__ = ["GiftGroup", "GiftParticipant", "GiftDraw"]
