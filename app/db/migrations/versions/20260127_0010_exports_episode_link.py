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
    op.add_column(
        "exports",
        sa.Column("episode_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_exports_episode_id",
        "exports",
        "episodes",
        ["episode_id"],
        ["episode_id"],
    )
    op.alter_column("exports", "scene_id", existing_type=sa.Uuid(as_uuid=True), nullable=True)
    op.create_index("ix_exports_episode_id", "exports", ["episode_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_exports_episode_id", table_name="exports")
    op.alter_column("exports", "scene_id", existing_type=sa.Uuid(as_uuid=True), nullable=False)
    op.drop_constraint("fk_exports_episode_id", "exports", type_="foreignkey")
    op.drop_column("exports", "episode_id")
