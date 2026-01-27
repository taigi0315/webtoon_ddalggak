"""scene environment link

Revision ID: 20260127_0007
Revises: 20260127_0006
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0007"
down_revision = "20260127_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenes",
        sa.Column("environment_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_scenes_environment_id",
        "scenes",
        "environment_anchors",
        ["environment_id"],
        ["environment_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_scenes_environment_id", "scenes", type_="foreignkey")
    op.drop_column("scenes", "environment_id")
