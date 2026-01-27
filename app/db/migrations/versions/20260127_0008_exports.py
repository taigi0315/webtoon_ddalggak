"""exports

Revision ID: 20260127_0008
Revises: 20260127_0007
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0008"
down_revision = "20260127_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exports",
        sa.Column("export_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scenes.scene_id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("output_url", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_exports_scene_id", "exports", ["scene_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_exports_scene_id", table_name="exports")
    op.drop_table("exports")
