"""Add can_manage flag to wishlist_shares (managers vs editors).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-25 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("wishlist_shares") as batch_op:
        batch_op.add_column(
            sa.Column("can_manage", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("wishlist_shares") as batch_op:
        batch_op.drop_column("can_manage")


__all__ = ["revision", "down_revision"]
