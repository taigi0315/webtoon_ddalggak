"""scene importance

Revision ID: 20260128_0003
Revises: 20260128_0002
Create Date: 2026-01-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260128_0003"
down_revision = "20260128_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("scene_importance", sa.String(length=24), nullable=True))


def downgrade() -> None:
    op.drop_column("scenes", "scene_importance")
