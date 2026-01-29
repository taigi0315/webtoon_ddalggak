"""project-level characters and story links

Revision ID: 20260129_0006
Revises: 20260128_0005
Create Date: 2026-01-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260129_0006"
down_revision = "20260128_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE characters
        SET project_id = stories.project_id
        FROM stories
        WHERE characters.story_id = stories.story_id
        """
    )

    op.create_table(
        "story_characters",
        sa.Column("story_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("character_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["story_id"], ["stories.story_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.character_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("story_id", "character_id"),
    )

    op.execute(
        """
        INSERT INTO story_characters (story_id, character_id)
        SELECT story_id, character_id FROM characters
        """
    )

    op.alter_column("characters", "project_id", nullable=False)

    op.execute("ALTER TABLE characters DROP CONSTRAINT IF EXISTS characters_story_id_fkey")
    op.drop_column("characters", "story_id")
    op.create_foreign_key(
        "characters_project_id_fkey",
        "characters",
        "projects",
        ["project_id"],
        ["project_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.add_column("characters", sa.Column("story_id", sa.Uuid(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE characters
        SET story_id = story_characters.story_id
        FROM story_characters
        WHERE characters.character_id = story_characters.character_id
        """
    )
    op.execute("ALTER TABLE characters DROP CONSTRAINT IF EXISTS characters_project_id_fkey")
    op.drop_column("characters", "project_id")
    op.create_foreign_key(
        "characters_story_id_fkey",
        "characters",
        "stories",
        ["story_id"],
        ["story_id"],
        ondelete="CASCADE",
    )
    op.drop_table("story_characters")
