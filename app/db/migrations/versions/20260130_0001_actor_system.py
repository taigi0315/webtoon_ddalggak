"""Actor system - extend CharacterVariant for global variants.

Revision ID: 20260130_0001
Revises: 20260129_0009
Create Date: 2026-01-30

Adds:
- Nullable story_id on character_variants (for global/library variants)
- New fields on character_variants: variant_name, image_style_id, story_style_id, traits, generated_image_ids, is_default
- New fields on characters: display_name, default_story_style_id, default_image_style_id
"""

import sqlalchemy as sa
from alembic import op


revision = "20260130_0001"
down_revision = "20260129_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make story_id nullable on character_variants for global/library variants
    op.alter_column(
        "character_variants",
        "story_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # Add new columns to character_variants
    op.add_column(
        "character_variants",
        sa.Column("variant_name", sa.String(128), nullable=True),
    )
    op.add_column(
        "character_variants",
        sa.Column("image_style_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "character_variants",
        sa.Column("story_style_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "character_variants",
        sa.Column("traits", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "character_variants",
        sa.Column("generated_image_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "character_variants",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add new columns to characters for Actor system
    op.add_column(
        "characters",
        sa.Column("display_name", sa.String(128), nullable=True),
    )
    op.add_column(
        "characters",
        sa.Column("default_story_style_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "characters",
        sa.Column("default_image_style_id", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    # Remove character columns
    op.drop_column("characters", "default_image_style_id")
    op.drop_column("characters", "default_story_style_id")
    op.drop_column("characters", "display_name")

    # Remove character_variants columns
    op.drop_column("character_variants", "is_default")
    op.drop_column("character_variants", "generated_image_ids")
    op.drop_column("character_variants", "traits")
    op.drop_column("character_variants", "story_style_id")
    op.drop_column("character_variants", "image_style_id")
    op.drop_column("character_variants", "variant_name")

    # Make story_id required again
    # Note: This may fail if NULL values exist - manual cleanup required
    op.alter_column(
        "character_variants",
        "story_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
