"""environment anchors

Revision ID: 20260127_0006
Revises: 20260127_0005
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0006"
down_revision = "20260127_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "environment_anchors",
        sa.Column("environment_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("anchor_type", sa.String(length=32), nullable=False, server_default="descriptive"),
        sa.Column("reference_images", sa.JSON(), nullable=False),
        sa.Column("locked_elements", sa.JSON(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("environment_anchors")
