"""character consistency fields

Revision ID: 20260126_0002
Revises: 20260126_0001
Create Date: 2026-01-26

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260126_0002"
down_revision = "20260126_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("role", sa.String(length=32), nullable=False, server_default="secondary"),
    )
    op.add_column(
        "characters",
        sa.Column("identity_line", sa.Text(), nullable=True),
    )
    op.add_column(
        "characters",
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.add_column(
        "character_reference_images",
        sa.Column("ref_type", sa.String(length=32), nullable=False, server_default="face"),
    )
    op.add_column(
        "character_reference_images",
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "character_reference_images",
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("character_reference_images", "is_primary")
    op.drop_column("character_reference_images", "approved")
    op.drop_column("character_reference_images", "ref_type")

    op.drop_column("characters", "approved")
    op.drop_column("characters", "identity_line")
    op.drop_column("characters", "role")
