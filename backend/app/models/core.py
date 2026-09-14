from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


def _uuid() -> str:
    return str(uuid.uuid4())


class AuthProvider(str, enum.Enum):
    LOCAL = "local"
    OIDC = "oidc"


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(150), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider), default=AuthProvider.LOCAL, nullable=False
    )
    oidc_subject: Mapped[str | None] = mapped_column(String(255), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    wishlists: Mapped[list["Wishlist"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class SystemSetting(Base, TimestampMixin):
    """Layer 1 of the hierarchical settings engine (UI-editable key/value)."""

    __tablename__ = "system_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_system_settings_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(16), default="str", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


__all__ = ["User", "SystemSetting", "AuthProvider", "UserRole", "_uuid"]
