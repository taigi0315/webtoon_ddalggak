"""initial

Revision ID: 20260126_0001
Revises: 
Create Date: 2026-01-26

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260126_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "stories",
        sa.Column("story_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "scenes",
        sa.Column("scene_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("story_id", sa.Uuid(as_uuid=True), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "characters",
        sa.Column("character_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("story_id", sa.Uuid(as_uuid=True), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "character_reference_images",
        sa.Column("reference_image_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "character_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("characters.character_id"),
            nullable=False,
        ),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "artifacts",
        sa.Column("artifact_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scenes.scene_id"), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Uuid(as_uuid=True), sa.ForeignKey("artifacts.artifact_id"), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "images",
        sa.Column("image_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("artifact_id", sa.Uuid(as_uuid=True), sa.ForeignKey("artifacts.artifact_id"), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index("ix_artifacts_scene_type_version", "artifacts", ["scene_id", "type", "version"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_artifacts_scene_type_version", table_name="artifacts")
    op.drop_table("images")
    op.drop_table("artifacts")
    op.drop_table("character_reference_images")
    op.drop_table("characters")
    op.drop_table("scenes")
    op.drop_table("stories")
    op.drop_table("projects")
