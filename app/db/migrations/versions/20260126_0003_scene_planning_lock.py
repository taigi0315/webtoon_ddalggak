"""scene planning lock

Revision ID: 20260126_0003
Revises: 20260126_0002
Create Date: 2026-01-26

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260126_0003"
down_revision = "20260126_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenes",
        sa.Column("planning_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("scenes", "planning_locked")
