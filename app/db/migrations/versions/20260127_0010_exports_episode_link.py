"""exports episode link

Revision ID: 20260127_0010
Revises: 20260127_0009
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0010"
down_revision = "20260127_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exports") as batch_op:
        batch_op.add_column(sa.Column("episode_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_exports_episode_id",
            "episodes",
            ["episode_id"],
            ["episode_id"],
        )
        batch_op.alter_column("scene_id", existing_type=sa.Uuid(as_uuid=True), nullable=True)
        batch_op.create_index("ix_exports_episode_id", ["episode_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("exports") as batch_op:
        batch_op.drop_index("ix_exports_episode_id")
        batch_op.alter_column("scene_id", existing_type=sa.Uuid(as_uuid=True), nullable=False)
        batch_op.drop_constraint("fk_exports_episode_id", type_="foreignkey")
        batch_op.drop_column("episode_id")
