"""style system

Revision ID: 20260127_0004
Revises: 20260126_0003
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0004"
down_revision = "20260126_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column("default_story_style", sa.String(length=64), nullable=False, server_default="default"),
    )
    op.add_column(
        "stories",
        sa.Column("default_image_style", sa.String(length=64), nullable=False, server_default="default"),
    )
    op.add_column(
        "scenes",
        sa.Column("story_style_override", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "scenes",
        sa.Column("image_style_override", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scenes", "image_style_override")
    op.drop_column("scenes", "story_style_override")
    op.drop_column("stories", "default_image_style")
    op.drop_column("stories", "default_story_style")
