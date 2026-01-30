"""cascade foreign keys for deletes

Revision ID: 20260128_0004
Revises: 20260128_0003
Create Date: 2026-01-28

"""

from __future__ import annotations

from alembic import op


revision = "20260128_0004"
down_revision = "20260128_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # projects -> stories
    with op.batch_alter_table("stories") as batch_op:
        # Note: In SQLite batch mode, we rely on table recreation to replace constraints.
        # We define the new FK configuration here.
        batch_op.create_foreign_key(
            "stories_project_id_fkey", "projects", ["project_id"], ["project_id"], ondelete="CASCADE"
        )

    # stories -> scenes/characters/episodes
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.create_foreign_key(
            "scenes_story_id_fkey", "stories", ["story_id"], ["story_id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("characters") as batch_op:
        batch_op.create_foreign_key(
            "characters_story_id_fkey", "stories", ["story_id"], ["story_id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("episodes") as batch_op:
        batch_op.create_foreign_key(
            "episodes_story_id_fkey", "stories", ["story_id"], ["story_id"], ondelete="CASCADE"
        )

    # scenes -> environment anchors
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.create_foreign_key(
            "scenes_environment_id_fkey",
            "environment_anchors",
            ["environment_id"],
            ["environment_id"],
            ondelete="SET NULL",
        )

    # characters -> reference images
    with op.batch_alter_table("character_reference_images") as batch_op:
        batch_op.create_foreign_key(
            "character_reference_images_character_id_fkey",
            "characters",
            ["character_id"],
            ["character_id"],
            ondelete="CASCADE",
        )

    # scenes -> artifacts/dialogue/layers/exports/episode_scenes
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.create_foreign_key(
            "artifacts_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("dialogue_layers") as batch_op:
        batch_op.create_foreign_key(
            "dialogue_layers_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("layers") as batch_op:
        batch_op.create_foreign_key(
            "layers_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("exports") as batch_op:
        batch_op.create_foreign_key(
            "exports_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("episode_scenes") as batch_op:
        batch_op.create_foreign_key(
            "episode_scenes_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"], ondelete="CASCADE"
        )

    # artifacts -> images (nullable)
    with op.batch_alter_table("images") as batch_op:
        batch_op.create_foreign_key(
            "images_artifact_id_fkey",
            "artifacts",
            ["artifact_id"],
            ["artifact_id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.create_foreign_key(
            "artifacts_parent_id_fkey",
            "artifacts",
            ["parent_id"],
            ["artifact_id"],
            ondelete="SET NULL",
        )

    # episodes -> episode_scenes/assets/exports
    with op.batch_alter_table("episode_scenes") as batch_op:
        batch_op.create_foreign_key(
            "episode_scenes_episode_id_fkey", "episodes", ["episode_id"], ["episode_id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("episode_assets") as batch_op:
        batch_op.create_foreign_key(
            "episode_assets_episode_id_fkey", "episodes", ["episode_id"], ["episode_id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("exports") as batch_op:
        batch_op.create_foreign_key(
            "exports_episode_id_fkey", "episodes", ["episode_id"], ["episode_id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    # Keep downgrade minimal; restore to NO ACTION by dropping/recreating without ON DELETE.
    # Note: drop_constraint removed for SQLite compatibility; we just overwrite.
    with op.batch_alter_table("exports") as batch_op:
        batch_op.create_foreign_key(
            "exports_episode_id_fkey", "episodes", ["episode_id"], ["episode_id"]
        )

    with op.batch_alter_table("episode_assets") as batch_op:
        batch_op.create_foreign_key(
            "episode_assets_episode_id_fkey", "episodes", ["episode_id"], ["episode_id"]
        )

    with op.batch_alter_table("episode_scenes") as batch_op:
        batch_op.create_foreign_key(
            "episode_scenes_episode_id_fkey", "episodes", ["episode_id"], ["episode_id"]
        )
        batch_op.create_foreign_key(
            "episode_scenes_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"]
        )

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.create_foreign_key(
            "artifacts_parent_id_fkey", "artifacts", ["parent_id"], ["artifact_id"]
        )
        batch_op.create_foreign_key(
            "artifacts_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"]
        )

    with op.batch_alter_table("images") as batch_op:
        batch_op.create_foreign_key(
            "images_artifact_id_fkey", "artifacts", ["artifact_id"], ["artifact_id"]
        )

    with op.batch_alter_table("exports") as batch_op:
        batch_op.create_foreign_key(
            "exports_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"]
        )

    with op.batch_alter_table("layers") as batch_op:
        batch_op.create_foreign_key(
            "layers_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"]
        )

    with op.batch_alter_table("dialogue_layers") as batch_op:
        batch_op.create_foreign_key(
            "dialogue_layers_scene_id_fkey", "scenes", ["scene_id"], ["scene_id"]
        )

    with op.batch_alter_table("character_reference_images") as batch_op:
        batch_op.create_foreign_key(
            "character_reference_images_character_id_fkey", "characters", ["character_id"], ["character_id"]
        )

    with op.batch_alter_table("scenes") as batch_op:
        batch_op.create_foreign_key(
            "scenes_environment_id_fkey", "environment_anchors", ["environment_id"], ["environment_id"]
        )
        batch_op.create_foreign_key(
            "scenes_story_id_fkey", "stories", ["story_id"], ["story_id"]
        )

    with op.batch_alter_table("episodes") as batch_op:
        batch_op.create_foreign_key(
            "episodes_story_id_fkey", "stories", ["story_id"], ["story_id"]
        )

    with op.batch_alter_table("characters") as batch_op:
        batch_op.create_foreign_key(
            "characters_story_id_fkey", "stories", ["story_id"], ["story_id"]
        )

    with op.batch_alter_table("stories") as batch_op:
        batch_op.create_foreign_key(
            "stories_project_id_fkey", "projects", ["project_id"], ["project_id"]
        )
