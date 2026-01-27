"""episodes

Revision ID: 20260127_0009
Revises: 20260127_0008
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260127_0009"
down_revision = "20260127_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "episodes",
        sa.Column("episode_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("story_id", sa.Uuid(as_uuid=True), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("default_story_style", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("default_image_style", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "episode_scenes",
        sa.Column("episode_scene_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("episode_id", sa.Uuid(as_uuid=True), sa.ForeignKey("episodes.episode_id"), nullable=False),
        sa.Column("scene_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scenes.scene_id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
    )
    op.create_table(
        "episode_assets",
        sa.Column("episode_asset_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("episode_id", sa.Uuid(as_uuid=True), sa.ForeignKey("episodes.episode_id"), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.Uuid(as_uuid=True), nullable=False),
    )
    op.create_index("ix_episode_scenes_episode_id", "episode_scenes", ["episode_id"], unique=False)
    op.create_index("ix_episode_scenes_scene_id", "episode_scenes", ["scene_id"], unique=False)
    op.create_index("ix_episode_assets_episode_id", "episode_assets", ["episode_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_episode_assets_episode_id", table_name="episode_assets")
    op.drop_index("ix_episode_scenes_scene_id", table_name="episode_scenes")
    op.drop_index("ix_episode_scenes_episode_id", table_name="episode_scenes")
    op.drop_table("episode_assets")
    op.drop_table("episode_scenes")
    op.drop_table("episodes")
