"""character registry text fields

Revision ID: 20260128_0002
Revises: 20260128_0001
Create Date: 2026-01-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260128_0002"
down_revision = "20260128_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("characters", "hair_description", existing_type=sa.String(length=128), type_=sa.Text())
    op.alter_column("characters", "base_outfit", existing_type=sa.String(length=255), type_=sa.Text())


def downgrade() -> None:
    op.alter_column("characters", "base_outfit", existing_type=sa.Text(), type_=sa.String(length=255))
    op.alter_column("characters", "hair_description", existing_type=sa.Text(), type_=sa.String(length=128))
