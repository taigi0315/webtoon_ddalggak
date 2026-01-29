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
    op.execute("ALTER TABLE stories DROP CONSTRAINT IF EXISTS stories_project_id_fkey")
    op.execute(
        "ALTER TABLE stories ADD CONSTRAINT stories_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE"
    )

    # stories -> scenes/characters/episodes
    op.execute("ALTER TABLE scenes DROP CONSTRAINT IF EXISTS scenes_story_id_fkey")
    op.execute(
        "ALTER TABLE scenes ADD CONSTRAINT scenes_story_id_fkey FOREIGN KEY (story_id) REFERENCES stories(story_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE characters DROP CONSTRAINT IF EXISTS characters_story_id_fkey")
    op.execute(
        "ALTER TABLE characters ADD CONSTRAINT characters_story_id_fkey FOREIGN KEY (story_id) REFERENCES stories(story_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE episodes DROP CONSTRAINT IF EXISTS episodes_story_id_fkey")
    op.execute(
        "ALTER TABLE episodes ADD CONSTRAINT episodes_story_id_fkey FOREIGN KEY (story_id) REFERENCES stories(story_id) ON DELETE CASCADE"
    )

    # scenes -> environment anchors
    op.execute("ALTER TABLE scenes DROP CONSTRAINT IF EXISTS scenes_environment_id_fkey")
    op.execute(
        "ALTER TABLE scenes ADD CONSTRAINT scenes_environment_id_fkey FOREIGN KEY (environment_id) REFERENCES environment_anchors(environment_id) ON DELETE SET NULL"
    )

    # characters -> reference images
    op.execute("ALTER TABLE character_reference_images DROP CONSTRAINT IF EXISTS character_reference_images_character_id_fkey")
    op.execute(
        "ALTER TABLE character_reference_images ADD CONSTRAINT character_reference_images_character_id_fkey FOREIGN KEY (character_id) REFERENCES characters(character_id) ON DELETE CASCADE"
    )

    # scenes -> artifacts/dialogue/layers/exports/episode_scenes
    op.execute("ALTER TABLE artifacts DROP CONSTRAINT IF EXISTS artifacts_scene_id_fkey")
    op.execute(
        "ALTER TABLE artifacts ADD CONSTRAINT artifacts_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE dialogue_layers DROP CONSTRAINT IF EXISTS dialogue_layers_scene_id_fkey")
    op.execute(
        "ALTER TABLE dialogue_layers ADD CONSTRAINT dialogue_layers_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE layers DROP CONSTRAINT IF EXISTS layers_scene_id_fkey")
    op.execute(
        "ALTER TABLE layers ADD CONSTRAINT layers_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE exports DROP CONSTRAINT IF EXISTS exports_scene_id_fkey")
    op.execute(
        "ALTER TABLE exports ADD CONSTRAINT exports_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE SET NULL"
    )
    op.execute("ALTER TABLE episode_scenes DROP CONSTRAINT IF EXISTS episode_scenes_scene_id_fkey")
    op.execute(
        "ALTER TABLE episode_scenes ADD CONSTRAINT episode_scenes_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE"
    )

    # artifacts -> images (nullable)
    op.execute("ALTER TABLE images DROP CONSTRAINT IF EXISTS images_artifact_id_fkey")
    op.execute(
        "ALTER TABLE images ADD CONSTRAINT images_artifact_id_fkey FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id) ON DELETE SET NULL"
    )
    op.execute("ALTER TABLE artifacts DROP CONSTRAINT IF EXISTS artifacts_parent_id_fkey")
    op.execute(
        "ALTER TABLE artifacts ADD CONSTRAINT artifacts_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES artifacts(artifact_id) ON DELETE SET NULL"
    )

    # episodes -> episode_scenes/assets/exports
    op.execute("ALTER TABLE episode_scenes DROP CONSTRAINT IF EXISTS episode_scenes_episode_id_fkey")
    op.execute(
        "ALTER TABLE episode_scenes ADD CONSTRAINT episode_scenes_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE episode_assets DROP CONSTRAINT IF EXISTS episode_assets_episode_id_fkey")
    op.execute(
        "ALTER TABLE episode_assets ADD CONSTRAINT episode_assets_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE exports DROP CONSTRAINT IF EXISTS exports_episode_id_fkey")
    op.execute(
        "ALTER TABLE exports ADD CONSTRAINT exports_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    # Keep downgrade minimal; restore to NO ACTION by dropping and recreating without ON DELETE.
    op.execute("ALTER TABLE exports DROP CONSTRAINT IF EXISTS exports_episode_id_fkey")
    op.execute("ALTER TABLE episode_assets DROP CONSTRAINT IF EXISTS episode_assets_episode_id_fkey")
    op.execute("ALTER TABLE episode_scenes DROP CONSTRAINT IF EXISTS episode_scenes_episode_id_fkey")
    op.execute("ALTER TABLE artifacts DROP CONSTRAINT IF EXISTS artifacts_parent_id_fkey")
    op.execute("ALTER TABLE images DROP CONSTRAINT IF EXISTS images_artifact_id_fkey")
    op.execute("ALTER TABLE episode_scenes DROP CONSTRAINT IF EXISTS episode_scenes_scene_id_fkey")
    op.execute("ALTER TABLE exports DROP CONSTRAINT IF EXISTS exports_scene_id_fkey")
    op.execute("ALTER TABLE layers DROP CONSTRAINT IF EXISTS layers_scene_id_fkey")
    op.execute("ALTER TABLE dialogue_layers DROP CONSTRAINT IF EXISTS dialogue_layers_scene_id_fkey")
    op.execute("ALTER TABLE artifacts DROP CONSTRAINT IF EXISTS artifacts_scene_id_fkey")
    op.execute("ALTER TABLE character_reference_images DROP CONSTRAINT IF EXISTS character_reference_images_character_id_fkey")
    op.execute("ALTER TABLE scenes DROP CONSTRAINT IF EXISTS scenes_environment_id_fkey")
    op.execute("ALTER TABLE episodes DROP CONSTRAINT IF EXISTS episodes_story_id_fkey")
    op.execute("ALTER TABLE characters DROP CONSTRAINT IF EXISTS characters_story_id_fkey")
    op.execute("ALTER TABLE scenes DROP CONSTRAINT IF EXISTS scenes_story_id_fkey")
    op.execute("ALTER TABLE stories DROP CONSTRAINT IF EXISTS stories_project_id_fkey")

    op.execute(
        "ALTER TABLE stories ADD CONSTRAINT stories_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(project_id)"
    )
    op.execute(
        "ALTER TABLE scenes ADD CONSTRAINT scenes_story_id_fkey FOREIGN KEY (story_id) REFERENCES stories(story_id)"
    )
    op.execute(
        "ALTER TABLE characters ADD CONSTRAINT characters_story_id_fkey FOREIGN KEY (story_id) REFERENCES stories(story_id)"
    )
    op.execute(
        "ALTER TABLE episodes ADD CONSTRAINT episodes_story_id_fkey FOREIGN KEY (story_id) REFERENCES stories(story_id)"
    )
    op.execute(
        "ALTER TABLE scenes ADD CONSTRAINT scenes_environment_id_fkey FOREIGN KEY (environment_id) REFERENCES environment_anchors(environment_id)"
    )
    op.execute(
        "ALTER TABLE character_reference_images ADD CONSTRAINT character_reference_images_character_id_fkey FOREIGN KEY (character_id) REFERENCES characters(character_id)"
    )
    op.execute(
        "ALTER TABLE artifacts ADD CONSTRAINT artifacts_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id)"
    )
    op.execute(
        "ALTER TABLE dialogue_layers ADD CONSTRAINT dialogue_layers_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id)"
    )
    op.execute(
        "ALTER TABLE layers ADD CONSTRAINT layers_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id)"
    )
    op.execute(
        "ALTER TABLE exports ADD CONSTRAINT exports_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id)"
    )
    op.execute(
        "ALTER TABLE episode_scenes ADD CONSTRAINT episode_scenes_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES scenes(scene_id)"
    )
    op.execute(
        "ALTER TABLE images ADD CONSTRAINT images_artifact_id_fkey FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id)"
    )
    op.execute(
        "ALTER TABLE artifacts ADD CONSTRAINT artifacts_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES artifacts(artifact_id)"
    )
    op.execute(
        "ALTER TABLE episode_scenes ADD CONSTRAINT episode_scenes_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES episodes(episode_id)"
    )
    op.execute(
        "ALTER TABLE episode_assets ADD CONSTRAINT episode_assets_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES episodes(episode_id)"
    )
    op.execute(
        "ALTER TABLE exports ADD CONSTRAINT exports_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES episodes(episode_id)"
    )
