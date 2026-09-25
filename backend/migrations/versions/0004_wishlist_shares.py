"""Add wishlist_shares (collaborators) table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-25 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wishlist_shares",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "wishlist_id",
            sa.String(36),
            sa.ForeignKey("wishlists.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("can_edit", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("wishlist_id", "user_id", name="uq_wishlist_user"),
    )


def downgrade() -> None:
    op.drop_table("wishlist_shares")


__all__ = ["revision", "down_revision"]
