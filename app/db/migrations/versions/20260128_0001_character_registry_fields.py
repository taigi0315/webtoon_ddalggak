"""character registry fields

Revision ID: 20260128_0001
Revises: 20260127_0012
Create Date: 2026-01-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260128_0001"
down_revision = "20260127_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("canonical_code", sa.String(length=16), nullable=True))
    op.add_column("characters", sa.Column("hair_description", sa.String(length=128), nullable=True))
    op.add_column("characters", sa.Column("base_outfit", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("characters", "base_outfit")
    op.drop_column("characters", "hair_description")
    op.drop_column("characters", "canonical_code")
