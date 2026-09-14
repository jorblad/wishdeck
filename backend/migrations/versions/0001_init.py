"""Initial schema: users, system_settings, wishlists, categories, wish_items.

Revision ID: 0001_init
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Native enums are disabled so the same migration applies on SQLite (WAL) and
# PostgreSQL. SQLAlchemy stores the enum name string in a VARCHAR column.
_ENUM_KW = dict(native_enum=False, create_type=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("username", sa.String(150), unique=True),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.Enum("user", "admin", name="userrole", **_ENUM_KW), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "auth_provider",
            sa.Enum("local", "oidc", name="authprovider", **_ENUM_KW),
            nullable=False,
            server_default="local",
        ),
        sa.Column("oidc_subject", sa.String(255), index=True),
        sa.Column("avatar_url", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(128), nullable=False, unique=True),
        sa.Column("value", sa.Text()),
        sa.Column("value_type", sa.String(16), nullable=False, server_default="str"),
        sa.Column("description", sa.String(255)),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "wishlists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "visibility",
            sa.Enum("private", "unlisted", "public", name="visibility", **_ENUM_KW),
            nullable=False,
            server_default="private",
            index=True,
        ),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column("allow_claims", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cover_image", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "wishlist_id",
            sa.String(36),
            sa.ForeignKey("wishlists.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#1976d2"),
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "wish_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "wishlist_id",
            sa.String(36),
            sa.ForeignKey("wishlists.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("url", sa.String(2048)),
        sa.Column("image_url", sa.String(2048)),
        sa.Column("price", sa.Float()),
        sa.Column("currency", sa.String(8)),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum("open", "claimed", "purchased", name="claimstatus", **_ENUM_KW),
            nullable=False,
            server_default="open",
        ),
        sa.Column("claimed_by", sa.String(255)),
        sa.Column("claimed_by_name", sa.String(255)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("wish_items")
    op.drop_table("categories")
    op.drop_table("wishlists")
    op.drop_table("system_settings")
    op.drop_table("users")
    bind = op.get_bind()
    sa.Enum(name="claimstatus").drop(bind=bind)
    sa.Enum(name="visibility").drop(bind=bind)
    sa.Enum(name="authprovider").drop(bind=bind)
    sa.Enum(name="userrole").drop(bind=bind)
