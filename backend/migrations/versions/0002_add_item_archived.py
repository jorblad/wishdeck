"""Add archived flag to wish_items.

Revision ID: 0002
Revises: 0001_init
Create Date: 2026-09-17 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wish_items",
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_wish_items_archived", "wish_items", ["archived"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wish_items_archived", table_name="wish_items")
    op.drop_column("wish_items", "archived")
