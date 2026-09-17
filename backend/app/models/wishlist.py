from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.core import _uuid


class Visibility(str, enum.Enum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class Wishlist(Base, TimestampMixin):
    __tablename__ = "wishlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility), default=Visibility.PRIVATE, nullable=False, index=True
    )
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    allow_claims: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cover_image: Mapped[str | None] = mapped_column(String(512))

    owner: Mapped["User"] = relationship(back_populates="wishlists")  # noqa: F821
    items: Mapped[list["WishItem"]] = relationship(
        back_populates="wishlist", cascade="all, delete-orphan",
        order_by="WishItem.priority",
    )
    categories: Mapped[list["Category"]] = relationship(
        back_populates="wishlist", cascade="all, delete-orphan"
    )


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    wishlist_id: Mapped[str | None] = mapped_column(
        ForeignKey("wishlists.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#1976d2", nullable=False)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    wishlist: Mapped["Wishlist"] = relationship(back_populates="categories")  # noqa: F821


class ClaimStatus(str, enum.Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    PURCHASED = "purchased"


class WishItem(Base, TimestampMixin):
    __tablename__ = "wish_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    wishlist_id: Mapped[str] = mapped_column(
        ForeignKey("wishlists.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    price: Mapped[float | None] = mapped_column()
    currency: Mapped[str | None] = mapped_column(String(8))
    priority: Mapped[int] = mapped_column(default=0, nullable=False, index=True)
    quantity: Mapped[int | None] = mapped_column(default=None, nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus), default=ClaimStatus.OPEN, nullable=False
    )
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    claimed_by: Mapped[str | None] = mapped_column(String(255))
    claimed_by_name: Mapped[str | None] = mapped_column(String(255))
    claimed_at: Mapped[datetime | None] = mapped_column()

    wishlist: Mapped["Wishlist"] = relationship(back_populates="items")  # noqa: F821
    category: Mapped["Category | None"] = relationship(back_populates=None)  # noqa: F821


__all__ = ["Wishlist", "Category", "WishItem", "Visibility", "ClaimStatus"]
