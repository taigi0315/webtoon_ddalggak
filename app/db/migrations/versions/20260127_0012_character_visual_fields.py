"""character_visual_fields - add gender, age_range, appearance for age-based character styling

Revision ID: 20260127_0012
Revises: 20260127_0011
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0012"
down_revision = "20260127_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add gender field for age-based character style prompts
    op.add_column("characters", sa.Column("gender", sa.String(length=16), nullable=True))
    # Add age_range field for age-based character style prompts
    op.add_column("characters", sa.Column("age_range", sa.String(length=32), nullable=True))
    # Add appearance JSON field for detailed visual attributes
    op.add_column("characters", sa.Column("appearance", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("characters", "appearance")
    op.drop_column("characters", "age_range")
    op.drop_column("characters", "gender")
