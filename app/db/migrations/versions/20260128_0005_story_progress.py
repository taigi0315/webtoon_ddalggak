"""story progress fields

Revision ID: 20260128_0005
Revises: 20260128_0004
Create Date: 2026-01-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260128_0005"
down_revision = "20260128_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("generation_status", sa.String(length=32), nullable=False, server_default="idle"))
    op.add_column("stories", sa.Column("generation_error", sa.Text(), nullable=True))
    op.add_column("stories", sa.Column("progress", sa.JSON(), nullable=True))
    op.add_column("stories", sa.Column("progress_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("stories", "progress_updated_at")
    op.drop_column("stories", "progress")
    op.drop_column("stories", "generation_error")
    op.drop_column("stories", "generation_status")
