"""layers

Revision ID: 20260127_0011
Revises: 20260127_0010
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0011"
down_revision = "20260127_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "layers",
        sa.Column("layer_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scenes.scene_id"), nullable=False),
        sa.Column("layer_type", sa.String(length=32), nullable=False),
        sa.Column("objects", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_layers_scene_id", "layers", ["scene_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_layers_scene_id", table_name="layers")
    op.drop_table("layers")
