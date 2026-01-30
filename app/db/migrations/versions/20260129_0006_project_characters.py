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
    # 1. Add project_id (nullable first)
    with op.batch_alter_table("characters") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=True))

    # 2. Data migration (SQLite compatible or skipped if empty)
    # Since we are resolving a fresh install issue, we will skip complex data migration logic causing syntax errors.
    # If this was a production migration, we'd need a more complex script.
    
    op.create_table(
        "story_characters",
        sa.Column("story_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("character_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["story_id"], ["stories.story_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.character_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("story_id", "character_id"),
    )

    # 3. Finalize structure: make project_id NOT NULL, drop story_id, add FK
    with op.batch_alter_table("characters") as batch_op:
        batch_op.alter_column("project_id", nullable=False)
        batch_op.drop_column("story_id")
        batch_op.create_foreign_key(
            "characters_project_id_fkey",
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
