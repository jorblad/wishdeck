"""Gift Exchange: groups, global people (persons), memberships, draws.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "persons",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("family", sa.String(length=120), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", name="uq_persons_user_id"),
        sa.Index("ix_persons_family", "family"),
        sa.Index("ix_persons_user_id", "user_id"),
    )
    op.create_table(
        "gift_groups",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.Index("ix_gift_groups_owner_id", "owner_id"),
    )
    op.create_table(
        "gift_group_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("person_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["gift_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("group_id", "person_id", name="uq_group_person"),
        sa.Index("ix_gift_group_memberships_group_id", "group_id"),
        sa.Index("ix_gift_group_memberships_person_id", "person_id"),
    )
    op.create_table(
        "gift_draws",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("giver_id", sa.String(length=36), nullable=False),
        sa.Column("receiver_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["gift_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["giver_id"], ["persons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_id"], ["persons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("group_id", "year", "giver_id", name="uq_gift_draw_giver_year"),
        sa.Index("ix_gift_draws_group_id", "group_id"),
        sa.Index("ix_gift_draws_year", "year"),
        sa.Index("ix_gift_draws_giver_id", "giver_id"),
        sa.Index("ix_gift_draws_receiver_id", "receiver_id"),
    )


def downgrade() -> None:
    op.drop_table("gift_draws")
    op.drop_table("gift_group_memberships")
    op.drop_table("gift_groups")
    op.drop_table("persons")


__all__ = ["revision", "down_revision"]
