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
    with op.batch_alter_table("character_variants") as batch_op:
        batch_op.alter_column(
            "story_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )

    # Add new columns to character_variants
    with op.batch_alter_table("character_variants") as batch_op:
        batch_op.add_column(sa.Column("variant_name", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("image_style_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("story_style_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("traits", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("generated_image_ids", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"))

    # Add new columns to characters for Actor system
    with op.batch_alter_table("characters") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("default_story_style_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("default_image_style_id", sa.String(64), nullable=True))


def downgrade() -> None:
    # Remove character columns
    with op.batch_alter_table("characters") as batch_op:
        batch_op.drop_column("default_image_style_id")
        batch_op.drop_column("default_story_style_id")
        batch_op.drop_column("display_name")

    # Remove character_variants columns and restore story_id
    with op.batch_alter_table("character_variants") as batch_op:
        batch_op.drop_column("is_default")
        batch_op.drop_column("generated_image_ids")
        batch_op.drop_column("traits")
        batch_op.drop_column("story_style_id")
        batch_op.drop_column("image_style_id")
        batch_op.drop_column("variant_name")
        batch_op.alter_column(
            "story_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
