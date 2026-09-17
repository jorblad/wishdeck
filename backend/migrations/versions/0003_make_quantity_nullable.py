"""Make wish_items.quantity nullable.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch mode so this works on SQLite (which cannot ALTER COLUMN).
    with op.batch_alter_table("wish_items") as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Integer(),
            nullable=True,
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("wish_items") as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="1",
        )
