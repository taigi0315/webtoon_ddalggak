from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import Uuid

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    stories: Mapped[list["Story"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Story(Base):
    __tablename__ = "stories"

    story_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    default_story_style: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    default_image_style: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    generation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="idle")
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    progress_updated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    project: Mapped[Project] = relationship(back_populates="stories")
    scenes: Mapped[list["Scene"]] = relationship(back_populates="story", cascade="all, delete-orphan")
    character_links: Mapped[list["StoryCharacter"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )
    character_variants: Mapped[list["CharacterVariant"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )
    characters: Mapped[list["Character"]] = relationship(
        secondary="story_characters",
        back_populates="stories",
        viewonly=True,
    )


class Scene(Base):
    __tablename__ = "scenes"

    scene_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.story_id", ondelete="CASCADE"), nullable=False
    )
    environment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("environment_anchors.environment_id", ondelete="SET NULL"), nullable=True
    )
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    scene_importance: Mapped[str | None] = mapped_column(String(24), nullable=True)
    planning_locked: Mapped[bool] = mapped_column(nullable=False, default=False)
    story_style_override: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_style_override: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    story: Mapped[Story] = relationship(back_populates="scenes")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="scene", cascade="all, delete-orphan")


class Character(Base):
    __tablename__ = "characters"

    character_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False
    )
    canonical_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="secondary")
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    age_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    appearance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hair_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_outfit: Mapped[str | None] = mapped_column(Text, nullable=True)
    identity_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship()
    story_links: Mapped[list["StoryCharacter"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    stories: Mapped[list[Story]] = relationship(
        secondary="story_characters",
        back_populates="characters",
        viewonly=True,
    )
    variants: Mapped[list["CharacterVariant"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    reference_images: Mapped[list["CharacterReferenceImage"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )


class StoryCharacter(Base):
    __tablename__ = "story_characters"

    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.story_id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    story: Mapped[Story] = relationship(back_populates="character_links")
    character: Mapped[Character] = relationship(back_populates="story_links")


class CharacterReferenceImage(Base):
    __tablename__ = "character_reference_images"

    reference_image_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), nullable=False
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    ref_type: Mapped[str] = mapped_column(String(32), nullable=False, default="face")
    approved: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_primary: Mapped[bool] = mapped_column(nullable=False, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    character: Mapped[Character] = relationship(back_populates="reference_images")


class CharacterVariant(Base):
    __tablename__ = "character_variants"

    variant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), nullable=False
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.story_id", ondelete="CASCADE"), nullable=False
    )
    variant_type: Mapped[str] = mapped_column(String(32), nullable=False, default="outfit_change")
    override_attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reference_image_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("character_reference_images.reference_image_id", ondelete="SET NULL"), nullable=True
    )
    is_active_for_story: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    character: Mapped[Character] = relationship(back_populates="variants")
    story: Mapped[Story] = relationship(back_populates="character_variants")
    reference_image: Mapped[CharacterReferenceImage | None] = relationship()


class CharacterVariantSuggestion(Base):
    __tablename__ = "character_variant_suggestions"

    suggestion_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.story_id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), nullable=False
    )
    variant_type: Mapped[str] = mapped_column(String(32), nullable=False, default="outfit_change")
    override_attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    character: Mapped[Character] = relationship()
    story: Mapped[Story] = relationship()


class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenes.scene_id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("artifacts.artifact_id", ondelete="SET NULL"), nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    scene: Mapped[Scene] = relationship(back_populates="artifacts")
    parent: Mapped[Artifact | None] = relationship(
        "Artifact",
        foreign_keys=[parent_id],
        remote_side="Artifact.artifact_id",
    )


class Image(Base):
    __tablename__ = "images"

    image_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("artifacts.artifact_id", ondelete="SET NULL"), nullable=True
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DialogueLayer(Base):
    __tablename__ = "dialogue_layers"

    dialogue_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenes.scene_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    bubbles: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnvironmentAnchor(Base):
    __tablename__ = "environment_anchors"

    environment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anchor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="descriptive")
    reference_images: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    locked_elements: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    pinned: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExportJob(Base):
    __tablename__ = "exports"

    export_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.scene_id", ondelete="SET NULL"), nullable=True
    )
    episode_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("episodes.episode_id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    output_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Episode(Base):
    __tablename__ = "episodes"

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.story_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    default_story_style: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    default_image_style: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EpisodeScene(Base):
    __tablename__ = "episode_scenes"

    episode_scene_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodes.episode_id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenes.scene_id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)


class EpisodeAsset(Base):
    __tablename__ = "episode_assets"

    episode_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodes.episode_id", ondelete="CASCADE"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)


class Layer(Base):
    __tablename__ = "layers"

    layer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenes.scene_id", ondelete="CASCADE"), nullable=False
    )
    layer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    objects: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StylePreset(Base):
    """Custom style presets for story/image generation.

    Style presets can be global (system-provided) or project-specific (user-created).
    They support inheritance via parent_id to allow customization of base styles.
    """

    __tablename__ = "style_presets"

    preset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("style_presets.preset_id", ondelete="SET NULL"), nullable=True
    )
    style_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "story" or "image"
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    style_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
