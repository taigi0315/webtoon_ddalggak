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
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.add_column(sa.Column("environment_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_scenes_environment_id",
            "environment_anchors",
            ["environment_id"],
            ["environment_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.drop_constraint("fk_scenes_environment_id", type_="foreignkey")
        batch_op.drop_column("environment_id")
