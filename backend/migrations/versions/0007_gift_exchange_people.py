"""Migrate gift exchange to global people (persons + memberships).

Replaces per-group participants with a global ``persons`` table and a
``gift_group_memberships`` join table. Existing per-group participants are
promoted to global people (keeping their id, name, family and user link) and a
membership is created for each, so groups and their members survive the move.
Draws are re-pointed at persons (the participant id is reused as the person id).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Guard: only migrate if the old per-group participants table still exists.
    # On a fresh install (0006 already creates persons) or a database that was
    # already migrated, gift_participants is absent and there is nothing to do.
    # Use the SQLAlchemy inspector so the check is database-agnostic (works on
    # both SQLite and PostgreSQL — sqlite_master does not exist on Postgres).
    if not sa.inspect(bind).has_table("gift_participants"):
        return

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

    bind = op.get_bind()

    # Promote existing participants to global people (reusing their id).
    participants = bind.execute(
        sa.text(
            "SELECT id, group_id, name, family, user_id, created_at, updated_at "
            "FROM gift_participants"
        )
    ).fetchall()
    for pid, gid, name, family, uid, ca, ua in participants:
        bind.execute(
            sa.text(
                "INSERT INTO persons (id, name, family, user_id, created_at, updated_at) "
                "VALUES (:id, :name, :family, :uid, :ca, :ua)"
            ),
            {"id": pid, "name": name, "family": family, "uid": uid, "ca": ca, "ua": ua},
        )
        bind.execute(
            sa.text(
                "INSERT INTO gift_group_memberships (id, group_id, person_id, created_at, updated_at) "
                "VALUES (:id, :gid, :pid, :ca, :ua)"
            ),
            {"id": str(__import__("uuid").uuid4()), "gid": gid, "pid": pid, "ca": ca, "ua": ua},
        )

    # Re-point draws at persons (participant ids are reused as person ids, so the
    # existing links stay valid). Copy rows, then swap the table.
    old_draws = bind.execute(
        sa.text(
            "SELECT id, group_id, year, giver_id, receiver_id, created_at, updated_at "
            "FROM gift_draws"
        )
    ).fetchall()
    op.drop_table("gift_draws")
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
    for did, gid, year, giver, receiver, ca, ua in old_draws:
        bind.execute(
            sa.text(
                "INSERT INTO gift_draws (id, group_id, year, giver_id, receiver_id, created_at, updated_at) "
                "VALUES (:id, :gid, :year, :g, :r, :ca, :ua)"
            ),
            {"id": did, "gid": gid, "year": year, "g": giver, "r": receiver, "ca": ca, "ua": ua},
        )

    op.drop_table("gift_participants")


def downgrade() -> None:
    # Reverse: collapse memberships back into per-group participants. Data from
    # people created after the migration is lost on downgrade.
    op.drop_table("gift_draws")
    op.create_table(
        "gift_participants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("family", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["gift_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.Index("ix_gift_participants_group_id", "group_id"),
        sa.Index("ix_gift_participants_user_id", "user_id"),
        sa.Index("ix_gift_participants_family", "family"),
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
        sa.ForeignKeyConstraint(["giver_id"], ["gift_participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_id"], ["gift_participants.id"], ondelete="CASCADE"),
        sa.Index("ix_gift_draws_group_id", "group_id"),
        sa.Index("ix_gift_draws_year", "year"),
        sa.Index("ix_gift_draws_giver_id", "giver_id"),
        sa.Index("ix_gift_draws_receiver_id", "receiver_id"),
        sa.UniqueConstraint("group_id", "year", "giver_id", name="uq_gift_draw_giver_year"),
    )
    op.drop_table("gift_group_memberships")
    op.drop_table("persons")


__all__ = ["revision", "down_revision"]
