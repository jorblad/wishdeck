"""Link wishlists to a global Person (Gift Exchange).

Adds ``wishlists.person_id`` so a wishlist can be attached to a person, letting a
gift-exchange draw's "who gives what" list link straight to the receiver's
wishlist. One wishlist per person (unique).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("wishlists") as batch:
        batch.add_column(sa.Column("person_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_wishlists_person_id",
            "persons",
            ["person_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_unique_constraint("uq_wishlists_person_id", ["person_id"])


def downgrade() -> None:
    with op.batch_alter_table("wishlists") as batch:
        batch.drop_constraint("uq_wishlists_person_id", type_="unique")
        batch.drop_constraint("fk_wishlists_person_id", type_="foreignkey")
        batch.drop_column("person_id")


__all__ = ["revision", "down_revision"]
