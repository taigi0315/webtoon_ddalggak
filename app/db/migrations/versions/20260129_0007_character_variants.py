"""character variants

Revision ID: 20260129_0007
Revises: 20260129_0006
Create Date: 2026-01-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260129_0007"
down_revision = "20260129_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_variants",
        sa.Column("variant_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("character_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("story_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("variant_type", sa.String(length=32), nullable=False, server_default="outfit_change"),
        sa.Column("override_attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reference_image_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_active_for_story", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["character_id"], ["characters.character_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_id"], ["stories.story_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reference_image_id"], ["character_reference_images.reference_image_id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_character_variants_story_character",
        "character_variants",
        ["story_id", "character_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_character_variants_story_character", table_name="character_variants")
    op.drop_table("character_variants")
