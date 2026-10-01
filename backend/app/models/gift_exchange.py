from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.core import _uuid


class Person(Base, TimestampMixin):
    """A global person. May be linked to a WishDeck user and belong to many groups."""

    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Family label used for the "no intra-family pairing" rule. Global to the
    # person so it stays consistent across every group they join.
    family: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    # Optional link to a WishDeck account (1:1). Lets a participant view their
    # own assignment after the organizer runs the draw.
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, index=True, nullable=True
    )

    memberships: Mapped[list["GiftGroupMembership"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class GiftGroup(Base, TimestampMixin):
    """A gift-exchange group (e.g. a family's Secret Santa). Owned by the organizer."""

    __tablename__ = "gift_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    memberships: Mapped[list["GiftGroupMembership"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    draws: Mapped[list["GiftDraw"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GiftGroupMembership(Base, TimestampMixin):
    """Join table: a person belongs to a group. A person can be in many groups."""

    __tablename__ = "gift_group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "person_id", name="uq_group_person"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("gift_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    person_id: Mapped[str] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), index=True, nullable=False
    )

    group: Mapped["GiftGroup"] = relationship(back_populates="memberships")
    person: Mapped["Person"] = relationship(back_populates="memberships")


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
        ForeignKey("persons.id", ondelete="CASCADE"), index=True, nullable=False
    )
    receiver_id: Mapped[str] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), index=True, nullable=False
    )

    group: Mapped["GiftGroup"] = relationship(back_populates="draws")
    giver: Mapped["Person"] = relationship(foreign_keys=[giver_id])
    receiver: Mapped["Person"] = relationship(foreign_keys=[receiver_id])


__all__ = ["Person", "GiftGroup", "GiftGroupMembership", "GiftDraw"]
