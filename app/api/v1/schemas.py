import uuid
from enum import Enum

from pydantic import BaseModel, Field
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectRead(BaseModel):
    project_id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    default_image_style: str = Field(default="default", min_length=1, max_length=64)


class StoryRead(BaseModel):
    story_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    default_image_style: str
    generation_status: str | None = None
    generation_error: str | None = None

    model_config = {"from_attributes": True}


class StoryProgress(BaseModel):
    """Typed model for Story.progress JSON field.

    Tracks the current state of story generation workflow.
    """

    current_node: str = Field(description="Name of the current processing node/step")
    message: str = Field(description="Human-readable status message")
    step: int = Field(ge=0, description="Current step number (0-indexed)")
    total_steps: int = Field(ge=1, description="Total number of steps in the workflow")

    @property
    def percent_complete(self) -> float:
        """Calculate completion percentage."""
        if self.total_steps <= 0:
            return 0.0
        return (self.step / self.total_steps) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if all steps are done."""
        return self.step >= self.total_steps

    @classmethod
    def create(
        cls,
        current_node: str,
        message: str,
        step: int,
        total_steps: int,
    ) -> dict:
        """Create a progress dict for storing in Story.progress JSON field.

        Returns a dict suitable for direct assignment to Story.progress.

        Example:
            story.progress = StoryProgress.create(
                current_node="Queued",
                message="Queued for generation...",
                step=0,
                total_steps=5,
            )
        """
        return cls(
            current_node=current_node,
            message=message,
            step=step,
            total_steps=total_steps,
        ).model_dump()


class StoryProgressRead(BaseModel):
    story_id: uuid.UUID
    status: str
    progress: StoryProgress | None = None
    error: str | None = None
    updated_at: datetime | None = None


class JobStatusRead(BaseModel):
    job_id: uuid.UUID
    job_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    progress: dict | None = None
    result: dict | None = None
    error: str | None = None


class SceneCreate(BaseModel):
    source_text: str = Field(min_length=1)
    environment_id: uuid.UUID | None = None


class SceneRead(BaseModel):
    scene_id: uuid.UUID
    story_id: uuid.UUID
    environment_id: uuid.UUID | None
    source_text: str
    scene_importance: str | None
    planning_locked: bool
    image_style_override: str | None

    model_config = {"from_attributes": True}


class ScenePlanningLockRequest(BaseModel):
    locked: bool = True


class SceneSetStyleRequest(BaseModel):
    image_style_id: str | None = Field(default=None, min_length=1, max_length=64)


class SceneSetEnvironmentRequest(BaseModel):
    environment_id: uuid.UUID | None = None


class SceneAutoChunkRequest(BaseModel):
    source_text: str = Field(min_length=1)
    max_scenes: int = Field(default=6, ge=1, le=20)


class StorySetStyleDefaultsRequest(BaseModel):
    default_image_style: str = Field(min_length=1, max_length=64)


class StyleItemRead(BaseModel):
    id: str
    label: str
    description: str
    image_url: str | None = None


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    role: str = Field(default="secondary", min_length=1, max_length=32)
    gender: str | None = Field(default=None, min_length=1, max_length=16)
    age_range: str | None = Field(default=None, min_length=1, max_length=32)
    appearance: dict | None = None
    hair_description: str | None = None
    base_outfit: str | None = None
    identity_line: str | None = None


class CharacterRead(BaseModel):
    character_id: uuid.UUID
    project_id: uuid.UUID
    canonical_code: str | None
    name: str
    description: str | None
    role: str
    gender: str | None
    age_range: str | None
    appearance: dict | None
    hair_description: str | None
    base_outfit: str | None
    identity_line: str | None
    generation_prompt: str | None = None
    is_library_saved: bool = False
    narrative_description: str | None = None
    approved: bool

    model_config = {"from_attributes": True}


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    role: str | None = Field(default=None, min_length=1, max_length=32)
    gender: str | None = Field(default=None, min_length=1, max_length=16)
    age_range: str | None = Field(default=None, min_length=1, max_length=32)
    appearance: dict | None = None
    hair_description: str | None = None
    base_outfit: str | None = None
    identity_line: str | None = None


class StoryGenerateRequest(BaseModel):
    source_text: str = Field(min_length=1)
    max_scenes: int = Field(default=6, ge=1, le=20)
    panel_count: int = Field(default=3, ge=1, le=12)
    style_id: str | None = Field(default=None, min_length=1, max_length=64)
    max_characters: int = Field(default=6, ge=1, le=20)
    generate_render_spec: bool = True
    allow_append: bool = False
    # If true, ensure at least one single-panel "hero" scene is present in the episode
    require_hero_single: bool = False


class StoryGenerateResponse(BaseModel):
    scenes: list[SceneRead]
    characters: list[CharacterRead]





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


class CharacterVariantCreate(BaseModel):
    variant_type: str = Field(default="outfit_change", min_length=1, max_length=32)
    override_attributes: dict | None = None
    reference_image_id: uuid.UUID | None = None
    is_active_for_story: bool = True


class CharacterVariantRead(BaseModel):
    variant_id: uuid.UUID
    character_id: uuid.UUID
    story_id: uuid.UUID
    variant_type: str
    override_attributes: dict
    reference_image_id: uuid.UUID | None
    is_active_for_story: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class CharacterVariantActivate(BaseModel):
    is_active_for_story: bool = True


class CharacterApproveRefRequest(BaseModel):
    reference_image_id: uuid.UUID


class CharacterSetPrimaryRefRequest(BaseModel):
    reference_image_id: uuid.UUID


class CharacterGenerateRefsRequest(BaseModel):
    ref_types: list[str] = Field(default=["face"], min_length=1)
    count_per_type: int = Field(default=2, ge=1, le=5)


class CharacterGenerateRefsResponse(BaseModel):
    character_id: uuid.UUID
    generated_refs: list["CharacterRefRead"]


class DialogueLine(BaseModel):
    speaker: str
    type: str
    text: str


class DialoguePanelBlock(BaseModel):
    panel_id: int
    lines: list[DialogueLine]
    notes: str | None = None


class DialogueSuggestionsRead(BaseModel):
    scene_id: uuid.UUID
    dialogue_by_panel: list[DialoguePanelBlock]


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


class CharacterVariantSuggestionRead(BaseModel):
    suggestion_id: uuid.UUID
    story_id: uuid.UUID
    character_id: uuid.UUID
    variant_type: str
    override_attributes: dict
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class CharacterVariantGenerationResult(BaseModel):
    character_id: uuid.UUID
    story_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    reference_image_id: uuid.UUID | None = None
    variant_type: str | None = None
    override_attributes: dict | None = None
    status: str
    detail: str | None = None


class CharacterVariantGenerateRequest(BaseModel):
    character_id: uuid.UUID | None = None


class BubbleType(str, Enum):
    """Valid bubble types for dialogue rendering."""
    CHAT = "chat"          # Regular dialogue/speech
    THOUGHT = "thought"    # Internal thoughts
    NARRATION = "narration"  # Narrative text boxes
    SFX = "sfx"           # Sound effects


class DialogueBubble(BaseModel):
    bubble_id: uuid.UUID
    panel_id: int = Field(ge=1)
    bubble_type: BubbleType = Field(default=BubbleType.CHAT)  # Enum: chat, thought, narration, sfx
    speaker: str | None = Field(default=None, max_length=255)
    text: str = Field(min_length=1)
    position: BubblePosition
    size: BubbleSize
    tail: BubblePosition | None = None


class DialogueLayerCreate(BaseModel):
    bubbles: list[DialogueBubble] = Field(default_factory=list)  # Allow empty dialogue layers


class DialogueLayerUpdate(BaseModel):
    bubbles: list[DialogueBubble] = Field(default_factory=list)  # Allow empty dialogue layers


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
    default_image_style: str = Field(default="default", min_length=1, max_length=64)


class EpisodeRead(BaseModel):
    episode_id: uuid.UUID
    story_id: uuid.UUID
    title: str
    default_image_style: str
    status: str
    scene_ids_ordered: list[uuid.UUID]

    model_config = {"from_attributes": True}


class EpisodeScenesUpdate(BaseModel):
    scene_ids_ordered: list[uuid.UUID] = Field(min_length=1)


class EpisodeSetStyleRequest(BaseModel):
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


# Scene Estimation Schemas
class SceneAnalysisRead(BaseModel):
    """Detailed analysis of story for scene estimation."""

    narrative_beats: int = Field(description="Number of distinct story beats identified")
    estimated_duration_seconds: int = Field(description="Estimated video duration in seconds")
    pacing: str = Field(description="Story pacing: fast, normal, or slow")
    complexity: str = Field(description="Story complexity: simple, moderate, or complex")
    dialogue_density: str = Field(description="Dialogue density: low, medium, or high")
    key_moments: list[str] = Field(default_factory=list, description="Key visual moments identified")


class SceneEstimationRequest(BaseModel):
    """Request model for scene count estimation."""

    source_text: str | None = Field(
        default=None,
        description="Story text to analyze. If not provided, uses existing scenes' source_text.",
    )
    use_llm: bool = Field(
        default=True,
        description="Use LLM for more accurate analysis (slower) or heuristics only (faster)",
    )


class SceneEstimationResponse(BaseModel):
    """Response model for scene count estimation."""

    recommended_count: int = Field(ge=5, le=15, description="Recommended number of scenes")
    status: str = Field(description="Status: ok, too_short, or too_long")
    message: str = Field(description="User-friendly explanation of the recommendation")
    analysis: SceneAnalysisRead | None = Field(
        default=None,
        description="Detailed analysis of the story structure",
    )


# Character Library Schemas
class LibraryCharacterRead(BaseModel):
    """Character from the project library with primary reference image."""

    character_id: uuid.UUID
    project_id: uuid.UUID
    canonical_code: str | None
    name: str
    description: str | None
    role: str
    gender: str | None
    age_range: str | None
    appearance: dict | None
    hair_description: str | None
    base_outfit: str | None
    identity_line: str | None
    generation_prompt: str | None
    approved: bool
    primary_reference_image: "CharacterRefRead | None" = None

    model_config = {"from_attributes": True}


class SaveToLibraryRequest(BaseModel):
    """Request to save a character to the project library."""

    generation_prompt: str | None = Field(
        default=None,
        description="Original text prompt used for generation (optional, for documentation)",
    )


class SaveToLibraryResponse(BaseModel):
    """Response after saving a character to library."""

    character_id: uuid.UUID
    is_library_saved: bool
    message: str


class LoadFromLibraryRequest(BaseModel):
    """Request to load a character from library into a story."""

    library_character_id: uuid.UUID = Field(
        description="ID of the character to load from the project library",
    )


class LoadFromLibraryResponse(BaseModel):
    """Response after loading a character from library."""

    character_id: uuid.UUID
    story_id: uuid.UUID
    already_linked: bool
    message: str


class GenerateWithReferenceRequest(BaseModel):
    """Request to generate a character variant using a library character's reference."""

    library_character_id: uuid.UUID = Field(
        description="ID of the library character whose reference image to use",
    )
    variant_description: str | None = Field(
        default=None,
        description="Optional description for the variant (e.g., 'wearing a spacesuit')",
    )
    variant_type: str = Field(
        default="story_context",
        description="Type of variant: outfit_change, age_progression, expression, story_context",
    )


class GenerateWithReferenceResponse(BaseModel):
    """Response after generating a character with reference."""

    character_id: uuid.UUID
    story_id: uuid.UUID
    variant_id: uuid.UUID | None
    reference_image_id: uuid.UUID | None
    status: str
    message: str


# ============================================================================
# Actor/Casting System Schemas
# ============================================================================


class CharacterTraitsInput(BaseModel):
    """Input traits for character generation in Actor system."""

    gender: str | None = Field(default=None, description="male, female, non-binary")
    age_range: str | None = Field(default=None, description="child, teen, young_adult, middle_aged, elderly")
    face_traits: str | None = Field(default=None, description="Sharp jawline, soft features, etc.")
    hair_traits: str | None = Field(default=None, description="Long black hair, short blonde, etc.")
    mood: str | None = Field(default=None, description="Confident, shy, mysterious, etc.")
    custom_prompt: str | None = Field(default=None, description="Additional custom description")


class GenerateActorRequest(BaseModel):
    """Request to generate a new character profile sheet."""

    image_style_id: str = Field(description="Image style for generation")
    traits: CharacterTraitsInput


class GenerateActorResponse(BaseModel):
    """Response after generating character profile sheet."""

    character_id: uuid.UUID | None = None  # None until saved
    image_url: str
    image_id: uuid.UUID
    traits_used: dict
    status: str


class SaveActorToLibraryRequest(BaseModel):
    """Request to save generated character to library."""

    image_id: uuid.UUID = Field(description="ID of the generated profile sheet image")
    display_name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    traits: CharacterTraitsInput
    image_style_id: str


class ActorVariantRead(BaseModel):
    """Variant read model for actor system."""

    variant_id: uuid.UUID
    character_id: uuid.UUID
    variant_name: str | None
    variant_type: str
    image_style_id: str | None
    traits: dict
    is_default: bool
    reference_image_url: str | None = None
    generated_image_urls: list[str] = Field(default_factory=list)
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ActorCharacterRead(BaseModel):
    """Actor character with variants for library display."""

    character_id: uuid.UUID
    project_id: uuid.UUID | None  # None for global actors
    display_name: str | None
    name: str
    description: str | None
    gender: str | None
    age_range: str | None
    default_image_style_id: str | None
    is_library_saved: bool
    variants: list[ActorVariantRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class GenerateActorVariantRequest(BaseModel):
    """Request to generate a variant from existing character."""

    base_variant_id: uuid.UUID = Field(description="Variant to use as reference")
    variant_name: str | None = Field(default=None, max_length=128)
    image_style_id: str | None = None  # Override style
    trait_changes: CharacterTraitsInput  # What to change


class ImportActorRequest(BaseModel):
    """Request to import character from uploaded image."""

    image_url: str = Field(description="URL of uploaded image")
    display_name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    traits: CharacterTraitsInput | None = None
    image_style_id: str | None = None
