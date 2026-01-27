import uuid

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectRead(BaseModel):
    project_id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    default_story_style: str = Field(default="default", min_length=1, max_length=64)
    default_image_style: str = Field(default="default", min_length=1, max_length=64)


class StoryRead(BaseModel):
    story_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    default_story_style: str
    default_image_style: str

    model_config = {"from_attributes": True}


class SceneCreate(BaseModel):
    source_text: str = Field(min_length=1)
    environment_id: uuid.UUID | None = None


class SceneRead(BaseModel):
    scene_id: uuid.UUID
    story_id: uuid.UUID
    environment_id: uuid.UUID | None
    source_text: str
    planning_locked: bool
    story_style_override: str | None
    image_style_override: str | None

    model_config = {"from_attributes": True}


class ScenePlanningLockRequest(BaseModel):
    locked: bool = True


class SceneSetStyleRequest(BaseModel):
    story_style_id: str | None = Field(default=None, min_length=1, max_length=64)
    image_style_id: str | None = Field(default=None, min_length=1, max_length=64)


class SceneSetEnvironmentRequest(BaseModel):
    environment_id: uuid.UUID | None = None


class SceneAutoChunkRequest(BaseModel):
    source_text: str = Field(min_length=1)
    max_scenes: int = Field(default=6, ge=1, le=20)


class StorySetStyleDefaultsRequest(BaseModel):
    default_story_style: str = Field(min_length=1, max_length=64)
    default_image_style: str = Field(min_length=1, max_length=64)


class StyleItemRead(BaseModel):
    id: str
    label: str
    description: str


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    role: str = Field(default="secondary", min_length=1, max_length=32)
    identity_line: str | None = None


class CharacterRead(BaseModel):
    character_id: uuid.UUID
    story_id: uuid.UUID
    name: str
    description: str | None
    role: str
    identity_line: str | None
    approved: bool

    model_config = {"from_attributes": True}


class CharacterRefCreate(BaseModel):
    image_url: str = Field(min_length=1)
    ref_type: str = Field(default="face", min_length=1, max_length=32)


class CharacterRefRead(BaseModel):
    reference_image_id: uuid.UUID
    character_id: uuid.UUID
    image_url: str
    ref_type: str
    approved: bool
    is_primary: bool
    metadata_: dict

    model_config = {"from_attributes": True}


class CharacterApproveRefRequest(BaseModel):
    reference_image_id: uuid.UUID


class CharacterSetPrimaryRefRequest(BaseModel):
    reference_image_id: uuid.UUID


class ArtifactRead(BaseModel):
    artifact_id: uuid.UUID
    scene_id: uuid.UUID
    type: str
    version: int
    parent_id: uuid.UUID | None
    payload: dict

    model_config = {"from_attributes": True}


class BubblePosition(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class BubbleSize(BaseModel):
    w: float = Field(ge=0.01, le=1.0)
    h: float = Field(ge=0.01, le=1.0)


class DialogueBubble(BaseModel):
    bubble_id: uuid.UUID
    panel_id: int = Field(ge=1)
    text: str = Field(min_length=1)
    position: BubblePosition
    size: BubbleSize
    tail: BubblePosition | None = None


class DialogueLayerCreate(BaseModel):
    bubbles: list[DialogueBubble] = Field(min_length=1)


class DialogueLayerUpdate(BaseModel):
    bubbles: list[DialogueBubble] = Field(min_length=1)


class DialogueLayerRead(BaseModel):
    dialogue_id: uuid.UUID
    scene_id: uuid.UUID
    bubbles: list[DialogueBubble]

    model_config = {"from_attributes": True}


class EnvironmentCreate(BaseModel):
    description: str = Field(min_length=1)
    pinned: bool = False


class EnvironmentPromoteRequest(BaseModel):
    reference_images: list[dict] = Field(default_factory=list)
    locked_elements: list[dict] = Field(default_factory=list)


class EnvironmentRead(BaseModel):
    environment_id: uuid.UUID
    description: str
    usage_count: int
    anchor_type: str
    reference_images: list[dict]
    locked_elements: list[dict]
    pinned: bool

    model_config = {"from_attributes": True}


class ExportRead(BaseModel):
    export_id: uuid.UUID
    scene_id: uuid.UUID | None
    episode_id: uuid.UUID | None
    status: str
    output_url: str | None
    metadata_: dict

    model_config = {"from_attributes": True}


class EpisodeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    default_story_style: str = Field(default="default", min_length=1, max_length=64)
    default_image_style: str = Field(default="default", min_length=1, max_length=64)


class EpisodeRead(BaseModel):
    episode_id: uuid.UUID
    story_id: uuid.UUID
    title: str
    default_story_style: str
    default_image_style: str
    status: str
    scene_ids_ordered: list[uuid.UUID]

    model_config = {"from_attributes": True}


class EpisodeScenesUpdate(BaseModel):
    scene_ids_ordered: list[uuid.UUID] = Field(min_length=1)


class EpisodeSetStyleRequest(BaseModel):
    default_story_style: str = Field(min_length=1, max_length=64)
    default_image_style: str = Field(min_length=1, max_length=64)


class EpisodeAssetRead(BaseModel):
    episode_asset_id: uuid.UUID
    episode_id: uuid.UUID
    asset_type: str
    asset_id: uuid.UUID

    model_config = {"from_attributes": True}


class EpisodeAssetCreate(BaseModel):
    asset_type: str = Field(min_length=1, max_length=32)
    asset_id: uuid.UUID


class LayerObjectGeometry(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(ge=0.01, le=1.0)
    h: float = Field(ge=0.01, le=1.0)


class LayerObjectStyle(BaseModel):
    font: str = Field(default="default", min_length=1, max_length=64)
    weight: str = Field(default="normal", min_length=1, max_length=32)


class LayerObject(BaseModel):
    object_id: uuid.UUID = Field(validation_alias="id", serialization_alias="id")
    panel_id: int = Field(ge=1)
    type: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1)
    style: LayerObjectStyle | None = None
    geometry: LayerObjectGeometry
    tail: BubblePosition | None = None
    z_index: int = Field(default=0)

    model_config = {"populate_by_name": True}


class LayerCreate(BaseModel):
    layer_type: str = Field(min_length=1, max_length=32)
    objects: list[LayerObject] = Field(min_length=1)


class LayerUpdate(BaseModel):
    objects: list[LayerObject] = Field(min_length=1)


class LayerRead(BaseModel):
    layer_id: uuid.UUID
    scene_id: uuid.UUID
    layer_type: str
    objects: list[LayerObject]

    model_config = {"from_attributes": True}
