"""character variant suggestions

Revision ID: 20260129_0008
Revises: 20260129_0007
Create Date: 2026-01-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260129_0008"
down_revision = "20260129_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_variant_suggestions",
        sa.Column("suggestion_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("story_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("character_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("variant_type", sa.String(length=32), nullable=False, server_default="outfit_change"),
        sa.Column("override_attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["story_id"], ["stories.story_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.character_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_variant_suggestions_story_character",
        "character_variant_suggestions",
        ["story_id", "character_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_variant_suggestions_story_character", table_name="character_variant_suggestions")
    op.drop_table("character_variant_suggestions")
