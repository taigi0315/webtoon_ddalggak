# Actor System Implementation Plan

**Epic:** WEBTOON-CASTING-LIBRARY
**Created:** 2026-01-30
**Status:** In Progress

---

## Overview

Transform the current story-scoped character system into an "Actor" model where:
- Characters are reusable entities independent of stories
- Variants (looks) can exist without story context
- Users can generate character profile sheets from a standalone UI
- Reference-first generation ensures visual consistency

---

## Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Migration Strategy | Make `story_id` nullable | Non-breaking; supports both story-scoped and global variants |
| Profile Sheet | Single composite image from Gemini | Simpler; Gemini can handle layout in prompt |
| Naming | Keep `Character` model | Non-breaking; add Actor functionality via flags/fields |
| Frontend | Basic Casting tab in Phase 1 | Users need UI to test the feature |

---

## Implementation Phases

### Phase 1: Database Model Changes
### Phase 2: Backend API Endpoints
### Phase 3: Prompt Engineering
### Phase 4: Frontend Casting Tab
### Phase 5: Integration & Testing

---

## Phase 1: Database Model Changes

### 1.1 Modify CharacterVariant Model

**File:** `app/db/models.py`

**Changes:**
```python
class CharacterVariant(Base):
    __tablename__ = "character_variants"

    variant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), nullable=False
    )
    # CHANGE: Make story_id nullable for global variants
    story_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stories.story_id", ondelete="CASCADE"), nullable=True
    )
    variant_type: Mapped[str] = mapped_column(String(32), nullable=False, default="base")

    # NEW FIELDS
    variant_name: Mapped[str | None] = mapped_column(String(128), nullable=True)  # "Summer Look", "Battle Mode"
    image_style_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    story_style_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    traits: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # {face, hair, mood, outfit}

    override_attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reference_image_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("character_reference_images.reference_image_id", ondelete="SET NULL"), nullable=True
    )
    generated_image_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # NEW: list of image IDs
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # NEW
    is_active_for_story: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### 1.2 Add Fields to Character Model

**File:** `app/db/models.py`

**Changes:**
```python
class Character(Base):
    # ... existing fields ...

    # NEW FIELDS for Actor system
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)  # User-friendly name
    default_story_style_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_image_style_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # is_library_saved already exists - reuse for Actor system
```

### 1.3 Create Migration

**File:** `app/db/migrations/versions/20260130_0001_actor_system.py`

```python
"""Actor system - extend CharacterVariant for global variants.

Revision ID: 20260130_0001
Revises: 20260129_0009
Create Date: 2026-01-30
"""

import sqlalchemy as sa
from alembic import op

revision = "20260130_0001"
down_revision = "20260129_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make story_id nullable on character_variants
    op.alter_column(
        "character_variants",
        "story_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # Add new columns to character_variants
    op.add_column("character_variants", sa.Column("variant_name", sa.String(128), nullable=True))
    op.add_column("character_variants", sa.Column("image_style_id", sa.String(64), nullable=True))
    op.add_column("character_variants", sa.Column("story_style_id", sa.String(64), nullable=True))
    op.add_column("character_variants", sa.Column("traits", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("character_variants", sa.Column("generated_image_ids", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("character_variants", sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"))

    # Add new columns to characters
    op.add_column("characters", sa.Column("display_name", sa.String(128), nullable=True))
    op.add_column("characters", sa.Column("default_story_style_id", sa.String(64), nullable=True))
    op.add_column("characters", sa.Column("default_image_style_id", sa.String(64), nullable=True))


def downgrade() -> None:
    # Remove character columns
    op.drop_column("characters", "default_image_style_id")
    op.drop_column("characters", "default_story_style_id")
    op.drop_column("characters", "display_name")

    # Remove character_variants columns
    op.drop_column("character_variants", "is_default")
    op.drop_column("character_variants", "generated_image_ids")
    op.drop_column("character_variants", "traits")
    op.drop_column("character_variants", "story_style_id")
    op.drop_column("character_variants", "image_style_id")
    op.drop_column("character_variants", "variant_name")

    # Make story_id required again (may fail if NULL values exist)
    op.alter_column(
        "character_variants",
        "story_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
```

---

## Phase 2: Backend API Endpoints

### 2.1 New Schemas

**File:** `app/api/v1/schemas.py`

```python
# ============================================================================
# Actor/Casting System Schemas
# ============================================================================

class CharacterTraitsInput(BaseModel):
    """Input traits for character generation."""
    gender: str | None = Field(default=None, description="male, female, non-binary")
    age_range: str | None = Field(default=None, description="child, teen, young_adult, middle_aged, elderly")
    face_traits: str | None = Field(default=None, description="Sharp jawline, soft features, etc.")
    hair_traits: str | None = Field(default=None, description="Long black hair, short blonde, etc.")
    mood: str | None = Field(default=None, description="Confident, shy, mysterious, etc.")
    custom_prompt: str | None = Field(default=None, description="Additional custom description")


class GenerateCharacterRequest(BaseModel):
    """Request to generate a new character profile sheet."""
    story_style_id: str = Field(description="Story style for generation")
    image_style_id: str = Field(description="Image style for generation")
    traits: CharacterTraitsInput


class GenerateCharacterResponse(BaseModel):
    """Response after generating character profile sheet."""
    character_id: uuid.UUID | None = None  # None until saved
    image_url: str
    image_id: uuid.UUID
    traits_used: dict
    status: str


class SaveCharacterToLibraryRequest(BaseModel):
    """Request to save generated character to library."""
    image_id: uuid.UUID = Field(description="ID of the generated profile sheet image")
    display_name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    traits: CharacterTraitsInput
    story_style_id: str
    image_style_id: str


class ActorCharacterRead(BaseModel):
    """Actor character with variants for library display."""
    character_id: uuid.UUID
    project_id: uuid.UUID
    display_name: str | None
    name: str
    description: str | None
    default_story_style_id: str | None
    default_image_style_id: str | None
    is_library_saved: bool
    variants: list["ActorVariantRead"] = []

    model_config = {"from_attributes": True}


class ActorVariantRead(BaseModel):
    """Variant read model for actor system."""
    variant_id: uuid.UUID
    character_id: uuid.UUID
    variant_name: str | None
    variant_type: str
    image_style_id: str | None
    story_style_id: str | None
    traits: dict
    is_default: bool
    reference_image_url: str | None = None
    generated_image_urls: list[str] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class GenerateVariantRequest(BaseModel):
    """Request to generate a variant from existing character."""
    base_variant_id: uuid.UUID = Field(description="Variant to use as reference")
    variant_name: str | None = Field(default=None, max_length=128)
    story_style_id: str | None = None  # Override style
    image_style_id: str | None = None  # Override style
    trait_changes: CharacterTraitsInput  # What to change


class ImportCharacterRequest(BaseModel):
    """Request to import character from uploaded image."""
    image_url: str = Field(description="URL of uploaded image")
    display_name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    traits: CharacterTraitsInput
    story_style_id: str | None = None
    image_style_id: str | None = None
```

### 2.2 New API Router

**File:** `app/api/v1/casting.py` (NEW FILE)

```python
"""
Casting/Actor system API endpoints.

Provides standalone character generation and library management
independent of story context.
"""

import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    ActorCharacterRead,
    ActorVariantRead,
    GenerateCharacterRequest,
    GenerateCharacterResponse,
    GenerateVariantRequest,
    ImportCharacterRequest,
    SaveCharacterToLibraryRequest,
)
from app.db.models import (
    Character,
    CharacterReferenceImage,
    CharacterVariant,
    Image,
    Project,
)
from app.graphs import nodes
from app.services.casting import (
    generate_character_profile_sheet,
    generate_variant_from_reference,
)

router = APIRouter(prefix="/casting", tags=["casting"])


@router.post("/projects/{project_id}/generate", response_model=GenerateCharacterResponse)
async def generate_character(
    project_id: uuid.UUID,
    payload: GenerateCharacterRequest,
    db=DbSessionDep,
):
    """
    Generate a new character profile sheet.

    Returns an image that can be previewed before saving to library.
    The character is NOT saved until explicitly requested.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    result = await generate_character_profile_sheet(
        db=db,
        project_id=project_id,
        story_style_id=payload.story_style_id,
        image_style_id=payload.image_style_id,
        traits=payload.traits.model_dump(exclude_none=True),
    )

    return GenerateCharacterResponse(
        character_id=None,  # Not saved yet
        image_url=result["image_url"],
        image_id=result["image_id"],
        traits_used=result["traits_used"],
        status="generated",
    )


@router.post("/projects/{project_id}/save", response_model=ActorCharacterRead)
def save_character_to_library(
    project_id: uuid.UUID,
    payload: SaveCharacterToLibraryRequest,
    db=DbSessionDep,
):
    """
    Save a generated character to the project library.

    Creates Character + default CharacterVariant + links the generated image.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    # Verify image exists
    image = db.get(Image, payload.image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="generated image not found")

    # Create character
    character = Character(
        project_id=project_id,
        name=payload.display_name,
        display_name=payload.display_name,
        description=payload.description,
        gender=payload.traits.gender,
        age_range=payload.traits.age_range,
        default_story_style_id=payload.story_style_id,
        default_image_style_id=payload.image_style_id,
        is_library_saved=True,
        approved=True,
    )
    db.add(character)
    db.flush()

    # Create reference image record
    ref_image = CharacterReferenceImage(
        character_id=character.character_id,
        image_url=image.image_url,
        ref_type="profile_sheet",
        approved=True,
        is_primary=True,
    )
    db.add(ref_image)
    db.flush()

    # Create default variant
    variant = CharacterVariant(
        character_id=character.character_id,
        story_id=None,  # Global variant
        variant_type="base",
        variant_name="Default",
        image_style_id=payload.image_style_id,
        story_style_id=payload.story_style_id,
        traits=payload.traits.model_dump(exclude_none=True),
        reference_image_id=ref_image.reference_image_id,
        generated_image_ids=[str(payload.image_id)],
        is_default=True,
    )
    db.add(variant)
    db.commit()

    db.refresh(character)
    return _build_actor_character_read(character, db)


@router.get("/projects/{project_id}/library", response_model=list[ActorCharacterRead])
def list_library_characters(project_id: uuid.UUID, db=DbSessionDep):
    """
    List all characters in the project library (Actor system).
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    stmt = (
        select(Character)
        .where(
            Character.project_id == project_id,
            Character.is_library_saved.is_(True),
        )
        .order_by(Character.created_at.desc())
    )
    characters = list(db.execute(stmt).scalars().all())

    return [_build_actor_character_read(c, db) for c in characters]


@router.get("/characters/{character_id}", response_model=ActorCharacterRead)
def get_character_with_variants(character_id: uuid.UUID, db=DbSessionDep):
    """
    Get a character with all its variants.
    """
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    return _build_actor_character_read(character, db)


@router.post("/characters/{character_id}/variants/generate", response_model=ActorVariantRead)
async def generate_variant(
    character_id: uuid.UUID,
    payload: GenerateVariantRequest,
    db=DbSessionDep,
):
    """
    Generate a new variant using an existing variant as reference.
    """
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    base_variant = db.get(CharacterVariant, payload.base_variant_id)
    if base_variant is None or base_variant.character_id != character_id:
        raise HTTPException(status_code=404, detail="base variant not found")

    result = await generate_variant_from_reference(
        db=db,
        character=character,
        base_variant=base_variant,
        trait_changes=payload.trait_changes.model_dump(exclude_none=True),
        story_style_id=payload.story_style_id,
        image_style_id=payload.image_style_id,
        variant_name=payload.variant_name,
    )

    return result


@router.post("/projects/{project_id}/import", response_model=ActorCharacterRead)
def import_character(
    project_id: uuid.UUID,
    payload: ImportCharacterRequest,
    db=DbSessionDep,
):
    """
    Import a character from an uploaded image.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    # Create character
    character = Character(
        project_id=project_id,
        name=payload.display_name,
        display_name=payload.display_name,
        description=payload.description,
        gender=payload.traits.gender if payload.traits else None,
        age_range=payload.traits.age_range if payload.traits else None,
        default_story_style_id=payload.story_style_id,
        default_image_style_id=payload.image_style_id,
        is_library_saved=True,
        approved=True,
    )
    db.add(character)
    db.flush()

    # Create reference image from upload
    ref_image = CharacterReferenceImage(
        character_id=character.character_id,
        image_url=payload.image_url,
        ref_type="imported",
        approved=True,
        is_primary=True,
    )
    db.add(ref_image)
    db.flush()

    # Create default variant
    traits = payload.traits.model_dump(exclude_none=True) if payload.traits else {}
    variant = CharacterVariant(
        character_id=character.character_id,
        story_id=None,
        variant_type="imported",
        variant_name="Imported",
        image_style_id=payload.image_style_id,
        story_style_id=payload.story_style_id,
        traits=traits,
        reference_image_id=ref_image.reference_image_id,
        is_default=True,
    )
    db.add(variant)
    db.commit()

    db.refresh(character)
    return _build_actor_character_read(character, db)


@router.delete("/variants/{variant_id}")
def delete_variant(variant_id: uuid.UUID, db=DbSessionDep):
    """
    Delete a character variant.
    """
    variant = db.get(CharacterVariant, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="variant not found")

    if variant.is_default:
        raise HTTPException(status_code=400, detail="cannot delete default variant")

    db.delete(variant)
    db.commit()
    return {"deleted": True}


def _build_actor_character_read(character: Character, db) -> ActorCharacterRead:
    """Build ActorCharacterRead with variants."""
    # Get variants (global only - no story_id)
    stmt = (
        select(CharacterVariant)
        .where(
            CharacterVariant.character_id == character.character_id,
            CharacterVariant.story_id.is_(None),
        )
        .order_by(CharacterVariant.is_default.desc(), CharacterVariant.created_at.desc())
    )
    variants = list(db.execute(stmt).scalars().all())

    variant_reads = []
    for v in variants:
        # Get reference image URL
        ref_url = None
        if v.reference_image_id:
            ref = db.get(CharacterReferenceImage, v.reference_image_id)
            if ref:
                ref_url = ref.image_url

        # Get generated image URLs
        gen_urls = []
        for img_id_str in (v.generated_image_ids or []):
            try:
                img = db.get(Image, uuid.UUID(img_id_str))
                if img:
                    gen_urls.append(img.image_url)
            except (ValueError, TypeError):
                pass

        variant_reads.append(ActorVariantRead(
            variant_id=v.variant_id,
            character_id=v.character_id,
            variant_name=v.variant_name,
            variant_type=v.variant_type,
            image_style_id=v.image_style_id,
            story_style_id=v.story_style_id,
            traits=v.traits or {},
            is_default=v.is_default,
            reference_image_url=ref_url,
            generated_image_urls=gen_urls,
            created_at=v.created_at,
        ))

    return ActorCharacterRead(
        character_id=character.character_id,
        project_id=character.project_id,
        display_name=character.display_name,
        name=character.name,
        description=character.description,
        default_story_style_id=character.default_story_style_id,
        default_image_style_id=character.default_image_style_id,
        is_library_saved=character.is_library_saved,
        variants=variant_reads,
    )
```

### 2.3 Register Router

**File:** `app/api/v1/__init__.py` or `app/main.py`

Add:
```python
from app.api.v1.casting import router as casting_router
app.include_router(casting_router, prefix="/v1")
```

---

## Phase 3: Prompt Engineering

### 3.1 Character Profile Sheet Prompt

**File:** `app/prompts/v1/casting/profile_sheet.yaml` (NEW)

```yaml
# Character Profile Sheet Generation Prompt
# Version: 1.0
# Description: Generate character profile sheet with full body and expression insets
# Required Variables: gender, age_range, face_traits, hair_traits, mood, custom_prompt, story_style, image_style

prompt_profile_sheet: |
  {{ system_prompt_json }}
  {{ global_constraints }}

  You are generating a CHARACTER PROFILE SHEET for a Korean webtoon character.

  STYLE CONTEXT:
  - Story Style: {{ story_style }}
  - Image Style: {{ image_style }}

  CHARACTER TRAITS:
  {% if gender %}- Gender: {{ gender }}{% endif %}
  {% if age_range %}- Age Range: {{ age_range }}{% endif %}
  {% if face_traits %}- Face: {{ face_traits }}{% endif %}
  {% if hair_traits %}- Hair: {{ hair_traits }}{% endif %}
  {% if mood %}- Mood/Expression: {{ mood }}{% endif %}
  {% if custom_prompt %}- Additional Details: {{ custom_prompt }}{% endif %}

  OUTPUT REQUIREMENTS (CRITICAL):
  1. Aspect Ratio: 9:16 VERTICAL (portrait orientation)
  2. Layout:
     - MAIN: Full-body front view (head-to-toe), centered, taking ~70% of frame
     - INSETS: 2-3 small headshot boxes in corners showing different expressions
  3. Pose: Neutral standing pose, arms relaxed, facing viewer
  4. Background: Clean solid color or simple gradient (no complex scenes)
  5. Style: High-quality Korean manhwa/webtoon art style
  6. FORBIDDEN: No text, no speech bubbles, no watermarks, no logos

  The character should look like a professional character design sheet that an artist would use as reference for drawing this character consistently across multiple panels.

  Generate the image now.
```

### 3.2 Variant Generation Prompt

**File:** `app/prompts/v1/casting/variant_generation.yaml` (NEW)

```yaml
# Variant Generation Prompt (Reference-First)
# Version: 1.0
# Description: Generate character variant using base reference for identity preservation
# Required Variables: base_traits, trait_changes, story_style, image_style

prompt_variant_generation: |
  {{ system_prompt_json }}
  {{ global_constraints }}

  You are generating a CHARACTER VARIANT using the provided reference image as the PRIMARY IDENTITY ANCHOR.

  REFERENCE IMAGE AUTHORITY (CRITICAL):
  The provided reference image defines the character's:
  - Face structure, features, and proportions
  - Eye shape and color
  - Skin tone
  - Body proportions and height

  YOU MUST PRESERVE THESE EXACTLY. The person in the output must be recognizably the SAME PERSON.

  STYLE CONTEXT:
  - Story Style: {{ story_style }}
  - Image Style: {{ image_style }}

  BASE CHARACTER TRAITS:
  {{ base_traits | tojson }}

  CHANGES TO APPLY (only these should differ):
  {% if trait_changes.hair_traits %}- Hair Change: {{ trait_changes.hair_traits }}{% endif %}
  {% if trait_changes.mood %}- Mood/Expression Change: {{ trait_changes.mood }}{% endif %}
  {% if trait_changes.custom_prompt %}- Additional Changes: {{ trait_changes.custom_prompt }}{% endif %}

  OUTPUT REQUIREMENTS:
  1. Aspect Ratio: 9:16 VERTICAL
  2. Layout: Full-body front view with 2-3 expression insets
  3. Pose: Neutral standing pose
  4. Background: Clean solid color or simple gradient
  5. Identity: MUST match reference image face/body exactly
  6. FORBIDDEN: No text, no speech bubbles, no watermarks

  Generate the variant now.
```

### 3.3 Casting Service

**File:** `app/services/casting.py` (NEW)

```python
"""
Casting service for Actor system character generation.
"""

import uuid
import logging
from typing import Any

from app.core.settings import settings
from app.db.models import Character, CharacterReferenceImage, CharacterVariant, Image
from app.prompts.loader import render_prompt
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.utils import save_image_locally

logger = logging.getLogger(__name__)


def _build_gemini_client() -> GeminiClient:
    """Build Gemini client for image generation."""
    return GeminiClient(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        api_key=settings.gemini_api_key,
        text_model=settings.gemini_text_model,
        image_model=settings.gemini_image_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
    )


async def generate_character_profile_sheet(
    db,
    project_id: uuid.UUID,
    story_style_id: str,
    image_style_id: str,
    traits: dict[str, Any],
) -> dict:
    """
    Generate a character profile sheet image.

    Returns dict with image_url, image_id, traits_used.
    """
    # Build prompt
    prompt = render_prompt(
        "prompt_profile_sheet",
        gender=traits.get("gender"),
        age_range=traits.get("age_range"),
        face_traits=traits.get("face_traits"),
        hair_traits=traits.get("hair_traits"),
        mood=traits.get("mood"),
        custom_prompt=traits.get("custom_prompt"),
        story_style=story_style_id,
        image_style=image_style_id,
    )

    # Generate image
    client = _build_gemini_client()

    import asyncio
    loop = asyncio.get_running_loop()
    image_bytes, mime_type = await loop.run_in_executor(
        None,
        lambda: client.generate_image(prompt)
    )

    # Save image
    image_url = save_image_locally(image_bytes, mime_type)

    # Create Image record
    image = Image(
        image_url=image_url,
        metadata_={
            "type": "profile_sheet",
            "story_style": story_style_id,
            "image_style": image_style_id,
            "traits": traits,
        },
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return {
        "image_url": image_url,
        "image_id": image.image_id,
        "traits_used": traits,
    }


async def generate_variant_from_reference(
    db,
    character: Character,
    base_variant: CharacterVariant,
    trait_changes: dict[str, Any],
    story_style_id: str | None,
    image_style_id: str | None,
    variant_name: str | None,
) -> "ActorVariantRead":
    """
    Generate a variant using base variant's reference image.
    """
    from app.api.v1.schemas import ActorVariantRead

    # Get reference image
    if not base_variant.reference_image_id:
        raise ValueError("Base variant has no reference image")

    ref_image = db.get(CharacterReferenceImage, base_variant.reference_image_id)
    if not ref_image:
        raise ValueError("Reference image not found")

    # Use base variant styles if not overridden
    final_story_style = story_style_id or base_variant.story_style_id or character.default_story_style_id
    final_image_style = image_style_id or base_variant.image_style_id or character.default_image_style_id

    # Merge traits
    merged_traits = {**(base_variant.traits or {}), **trait_changes}

    # Build prompt
    prompt = render_prompt(
        "prompt_variant_generation",
        base_traits=base_variant.traits or {},
        trait_changes=trait_changes,
        story_style=final_story_style,
        image_style=final_image_style,
    )

    # Load reference image bytes
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(ref_image.image_url)
        ref_bytes = resp.content

    # Generate with reference
    gemini = _build_gemini_client()

    import asyncio
    loop = asyncio.get_running_loop()
    image_bytes, mime_type = await loop.run_in_executor(
        None,
        lambda: gemini.generate_image(prompt, reference_images=[ref_bytes])
    )

    # Save image
    image_url = save_image_locally(image_bytes, mime_type)

    # Create Image record
    image = Image(
        image_url=image_url,
        metadata_={
            "type": "variant",
            "character_id": str(character.character_id),
            "base_variant_id": str(base_variant.variant_id),
        },
    )
    db.add(image)
    db.flush()

    # Create reference image record
    new_ref = CharacterReferenceImage(
        character_id=character.character_id,
        image_url=image_url,
        ref_type="variant",
        approved=True,
        is_primary=False,
    )
    db.add(new_ref)
    db.flush()

    # Create variant
    variant = CharacterVariant(
        character_id=character.character_id,
        story_id=None,  # Global variant
        variant_type="variant",
        variant_name=variant_name or f"Variant {uuid.uuid4().hex[:6]}",
        image_style_id=final_image_style,
        story_style_id=final_story_style,
        traits=merged_traits,
        reference_image_id=new_ref.reference_image_id,
        generated_image_ids=[str(image.image_id)],
        is_default=False,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)

    return ActorVariantRead(
        variant_id=variant.variant_id,
        character_id=variant.character_id,
        variant_name=variant.variant_name,
        variant_type=variant.variant_type,
        image_style_id=variant.image_style_id,
        story_style_id=variant.story_style_id,
        traits=variant.traits,
        is_default=variant.is_default,
        reference_image_url=image_url,
        generated_image_urls=[image_url],
        created_at=variant.created_at,
    )
```

---

## Phase 4: Frontend Casting Tab

### 4.1 New Page Structure

**File:** `frontend/app/studio/casting/page.tsx` (NEW)

Key components:
1. **Left Panel**: Character library grid
2. **Center Panel**: Generation form OR character detail view
3. **Right Panel**: Preview + variant list

### 4.2 Main Page Layout

```tsx
// frontend/app/studio/casting/page.tsx

"use client";

import { useState } from "react";
import CharacterLibraryGrid from "@/components/casting/CharacterLibraryGrid";
import CharacterGenerationForm from "@/components/casting/CharacterGenerationForm";
import CharacterDetailView from "@/components/casting/CharacterDetailView";
import VariantPanel from "@/components/casting/VariantPanel";

export default function CastingPage() {
  const [selectedCharacter, setSelectedCharacter] = useState(null);
  const [mode, setMode] = useState<"generate" | "view">("generate");
  const [generatedPreview, setGeneratedPreview] = useState(null);

  return (
    <div className="flex h-full">
      {/* Left: Library Grid */}
      <div className="w-64 border-r p-4 overflow-y-auto">
        <h2 className="font-bold mb-4">Character Library</h2>
        <button
          onClick={() => { setMode("generate"); setSelectedCharacter(null); }}
          className="w-full mb-4 p-2 bg-blue-500 text-white rounded"
        >
          + Generate New
        </button>
        <CharacterLibraryGrid
          onSelect={(char) => { setSelectedCharacter(char); setMode("view"); }}
          selectedId={selectedCharacter?.character_id}
        />
      </div>

      {/* Center: Form or Detail */}
      <div className="flex-1 p-6 overflow-y-auto">
        {mode === "generate" ? (
          <CharacterGenerationForm
            onGenerated={setGeneratedPreview}
            onSaved={(char) => { setSelectedCharacter(char); setMode("view"); }}
          />
        ) : (
          <CharacterDetailView
            character={selectedCharacter}
            onVariantGenerated={() => {/* refresh */}}
          />
        )}
      </div>

      {/* Right: Variants */}
      <div className="w-80 border-l p-4 overflow-y-auto">
        {selectedCharacter && (
          <VariantPanel
            character={selectedCharacter}
            onCreateVariant={() => {/* open modal */}}
          />
        )}
        {mode === "generate" && generatedPreview && (
          <div>
            <h3 className="font-bold mb-2">Preview</h3>
            <img src={generatedPreview.image_url} alt="Generated" className="w-full rounded" />
          </div>
        )}
      </div>
    </div>
  );
}
```

### 4.3 Generation Form Component

```tsx
// frontend/components/casting/CharacterGenerationForm.tsx

"use client";

import { useState } from "react";

interface Props {
  onGenerated: (result: any) => void;
  onSaved: (character: any) => void;
}

export default function CharacterGenerationForm({ onGenerated, onSaved }: Props) {
  const [loading, setLoading] = useState(false);
  const [traits, setTraits] = useState({
    gender: "",
    age_range: "",
    face_traits: "",
    hair_traits: "",
    mood: "",
    custom_prompt: "",
  });
  const [storyStyle, setStoryStyle] = useState("default");
  const [imageStyle, setImageStyle] = useState("default");
  const [result, setResult] = useState(null);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/casting/projects/${projectId}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          story_style_id: storyStyle,
          image_style_id: imageStyle,
          traits,
        }),
      });
      const data = await res.json();
      setResult(data);
      onGenerated(data);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (name: string) => {
    const res = await fetch(`/api/v1/casting/projects/${projectId}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_id: result.image_id,
        display_name: name,
        traits,
        story_style_id: storyStyle,
        image_style_id: imageStyle,
      }),
    });
    const saved = await res.json();
    onSaved(saved);
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Generate New Character</h2>

      {/* Style Selectors */}
      <div className="grid grid-cols-2 gap-4">
        <select value={storyStyle} onChange={e => setStoryStyle(e.target.value)}>
          <option value="default">Default Story Style</option>
          {/* Add style options */}
        </select>
        <select value={imageStyle} onChange={e => setImageStyle(e.target.value)}>
          <option value="default">Default Image Style</option>
          {/* Add style options */}
        </select>
      </div>

      {/* Trait Inputs */}
      <div className="grid grid-cols-2 gap-4">
        <input
          placeholder="Gender (e.g., male, female)"
          value={traits.gender}
          onChange={e => setTraits(t => ({ ...t, gender: e.target.value }))}
        />
        <input
          placeholder="Age Range (e.g., young_adult)"
          value={traits.age_range}
          onChange={e => setTraits(t => ({ ...t, age_range: e.target.value }))}
        />
        <input
          placeholder="Face Traits (e.g., sharp jawline)"
          value={traits.face_traits}
          onChange={e => setTraits(t => ({ ...t, face_traits: e.target.value }))}
        />
        <input
          placeholder="Hair Traits (e.g., long black hair)"
          value={traits.hair_traits}
          onChange={e => setTraits(t => ({ ...t, hair_traits: e.target.value }))}
        />
        <input
          placeholder="Mood (e.g., confident)"
          value={traits.mood}
          onChange={e => setTraits(t => ({ ...t, mood: e.target.value }))}
        />
      </div>

      <textarea
        placeholder="Custom prompt (optional)"
        value={traits.custom_prompt}
        onChange={e => setTraits(t => ({ ...t, custom_prompt: e.target.value }))}
        className="w-full h-20"
      />

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded"
        >
          {loading ? "Generating..." : "Generate"}
        </button>
        {result && (
          <>
            <button onClick={handleGenerate} className="px-4 py-2 border rounded">
              Regenerate
            </button>
            <button
              onClick={() => {
                const name = prompt("Character name:");
                if (name) handleSave(name);
              }}
              className="px-4 py-2 bg-green-500 text-white rounded"
            >
              Save to Library
            </button>
          </>
        )}
      </div>

      {/* Preview */}
      {result && (
        <div className="mt-4">
          <img src={result.image_url} alt="Generated" className="max-w-md rounded shadow" />
        </div>
      )}
    </div>
  );
}
```

### 4.4 Navigation Update

**File:** `frontend/components/Sidebar.tsx` (or equivalent)

Add navigation item:
```tsx
<NavItem href="/studio/casting" icon={<UsersIcon />}>
  Casting
</NavItem>
```

---

## Phase 5: Integration & Testing

### 5.1 Test Cases

**File:** `tests/test_casting_api.py`

```python
"""Tests for Casting/Actor system API."""

import uuid
import pytest
from unittest.mock import patch, MagicMock

from app.api.v1.schemas import (
    CharacterTraitsInput,
    GenerateCharacterRequest,
)


class TestCastingSchemas:
    def test_character_traits_input_optional_fields(self):
        traits = CharacterTraitsInput()
        assert traits.gender is None
        assert traits.age_range is None

    def test_character_traits_with_values(self):
        traits = CharacterTraitsInput(
            gender="female",
            age_range="young_adult",
            face_traits="sharp features",
            hair_traits="long black",
            mood="confident",
        )
        assert traits.gender == "female"
        assert traits.face_traits == "sharp features"

    def test_generate_request_requires_styles(self):
        traits = CharacterTraitsInput(gender="male")
        req = GenerateCharacterRequest(
            story_style_id="romance",
            image_style_id="manhwa",
            traits=traits,
        )
        assert req.story_style_id == "romance"


class TestCastingModelChanges:
    def test_character_variant_nullable_story_id(self):
        from app.db.models import CharacterVariant
        # Variant can be created without story_id
        variant = CharacterVariant(
            character_id=uuid.uuid4(),
            story_id=None,  # Global variant
            variant_type="base",
        )
        assert variant.story_id is None

    def test_character_new_fields(self):
        from app.db.models import Character
        char = Character(
            project_id=uuid.uuid4(),
            name="Test",
            display_name="Test Display",
            default_story_style_id="romance",
            default_image_style_id="manhwa",
        )
        assert char.display_name == "Test Display"
```

### 5.2 Integration Test

```python
@pytest.mark.asyncio
async def test_full_casting_workflow(db_session, project):
    """Test complete casting workflow: generate → save → create variant."""

    # 1. Generate character
    from app.services.casting import generate_character_profile_sheet

    with patch("app.services.casting._build_gemini_client") as mock_client:
        mock_client.return_value.generate_image.return_value = (b"fake_image", "image/png")

        result = await generate_character_profile_sheet(
            db=db_session,
            project_id=project.project_id,
            story_style_id="romance",
            image_style_id="manhwa",
            traits={"gender": "female", "hair_traits": "long black"},
        )

    assert result["image_url"] is not None
    assert result["image_id"] is not None

    # 2. Save to library (would be API call in real test)
    # ...

    # 3. Generate variant
    # ...
```

---

## File Checklist

### New Files to Create
- [ ] `app/db/migrations/versions/20260130_0001_actor_system.py`
- [ ] `app/api/v1/casting.py`
- [ ] `app/services/casting.py`
- [ ] `app/prompts/v1/casting/profile_sheet.yaml`
- [ ] `app/prompts/v1/casting/variant_generation.yaml`
- [ ] `frontend/app/studio/casting/page.tsx`
- [ ] `frontend/components/casting/CharacterGenerationForm.tsx`
- [ ] `frontend/components/casting/CharacterLibraryGrid.tsx`
- [ ] `frontend/components/casting/CharacterDetailView.tsx`
- [ ] `frontend/components/casting/VariantPanel.tsx`
- [ ] `tests/test_casting_api.py`

### Files to Modify
- [ ] `app/db/models.py` - Add new fields to Character and CharacterVariant
- [ ] `app/api/v1/schemas.py` - Add Actor system schemas
- [ ] `app/api/v1/__init__.py` or `app/main.py` - Register casting router
- [ ] `frontend/components/Sidebar.tsx` - Add Casting nav item

---

## Implementation Order

1. **Database**: Migration + model changes
2. **Schemas**: Add Pydantic models
3. **Prompts**: Create profile_sheet and variant_generation prompts
4. **Service**: Create casting.py service
5. **API**: Create casting.py router and register
6. **Tests**: Backend tests
7. **Frontend**: Casting page and components
8. **Integration**: End-to-end testing

---

## Notes

- Keep existing story-scoped character system working
- Global variants have `story_id=None`
- Profile sheet uses 9:16 vertical aspect ratio
- Reference-first generation uses base variant image as identity anchor
- Frontend should fetch styles from `/v1/config/styles` endpoint
