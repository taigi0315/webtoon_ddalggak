"""dialogue layer

Revision ID: 20260127_0005
Revises: 20260127_0004
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0005"
down_revision = "20260127_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dialogue_layers",
        sa.Column("dialogue_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scenes.scene_id"), nullable=False, unique=True),
        sa.Column("bubbles", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("dialogue_layers")
