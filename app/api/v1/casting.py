"""
Casting/Actor system API endpoints.

Provides standalone character generation and library management
independent of project/story context. Actors are global and can be
"cast" into any project or story.
"""

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.core.settings import settings

logger = logging.getLogger(__name__)
from app.api.v1.schemas import (
    ActorCharacterRead,
    ActorVariantRead,
    CharacterTraitsInput,
    GenerateActorRequest,
    GenerateActorResponse,
    GenerateActorVariantRequest,
    ImportActorRequest,
    SaveActorToLibraryRequest,
)
from app.db.models import (
    Character,
    CharacterReferenceImage,
    CharacterVariant,
    Image,
    Project,
)
from app.services.casting import (
    generate_character_profile_sheet,
    generate_variant_from_reference,
    import_actor_from_image,
    import_actor_from_local_file,
    save_actor_to_library,
)
from app.services.storage import LocalMediaStore

router = APIRouter(prefix="/casting", tags=["casting"])


def _build_actor_variant_read(variant: CharacterVariant, db) -> ActorVariantRead:
    """Build ActorVariantRead from variant model."""
    # Get reference image URL
    ref_url = None
    if variant.reference_image_id:
        ref = db.get(CharacterReferenceImage, variant.reference_image_id)
        if ref:
            ref_url = ref.image_url

    # Get generated image URLs
    gen_urls = []
    for img_id_str in (variant.generated_image_ids or []):
        try:
            img = db.get(Image, uuid.UUID(img_id_str))
            if img:
                gen_urls.append(img.image_url)
        except (ValueError, TypeError):
            pass

    return ActorVariantRead(
        variant_id=variant.variant_id,
        character_id=variant.character_id,
        variant_name=variant.variant_name,
        variant_type=variant.variant_type,
        image_style_id=variant.image_style_id,
        traits=variant.traits or {},
        is_default=variant.is_default,
        reference_image_url=ref_url,
        generated_image_urls=gen_urls,
        created_at=variant.created_at,
    )


def _build_actor_character_read(character: Character, db) -> ActorCharacterRead:
    """Build ActorCharacterRead with variants."""
    # Get global variants (story_id is NULL)
    stmt = (
        select(CharacterVariant)
        .where(
            CharacterVariant.character_id == character.character_id,
            CharacterVariant.story_id.is_(None),
        )
        .order_by(CharacterVariant.is_default.desc(), CharacterVariant.created_at.desc())
    )
    variants = list(db.execute(stmt).scalars().all())

    variant_reads = [_build_actor_variant_read(v, db) for v in variants]

    return ActorCharacterRead(
        character_id=character.character_id,
        project_id=character.project_id,
        display_name=character.display_name,
        name=character.name,
        description=character.description,
        gender=character.gender,
        age_range=character.age_range,
        default_image_style_id=character.default_image_style_id,
        is_library_saved=character.is_library_saved,
        variants=variant_reads,
    )


# ============================================================================
# Global Actor Endpoints (no project required)
# ============================================================================


@router.post("/generate", response_model=GenerateActorResponse)
def generate_actor(
    payload: GenerateActorRequest,
    db=DbSessionDep,
):
    """
    Generate a new character profile sheet (global actor).

    Returns an image that can be previewed before saving to library.
    The character is NOT saved until explicitly requested via /save endpoint.

    The generated image is a 9:16 vertical profile sheet with:
    - Full-body front view (head-to-toe)
    - 2-3 expression inset boxes in corners
    """
    try:
        result = generate_character_profile_sheet(
            db=db,
            project_id=None,  # Global actor - no project
            image_style_id=payload.image_style_id,
            traits=payload.traits.model_dump(exclude_none=True),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    return GenerateActorResponse(
        character_id=None,  # Not saved yet
        image_url=result["image_url"],
        image_id=result["image_id"],
        traits_used=result["traits_used"],
        status="generated",
    )


@router.post("/save", response_model=ActorCharacterRead)
def save_actor(
    payload: SaveActorToLibraryRequest,
    db=DbSessionDep,
):
    """
    Save a generated character to the global actor library.

    Creates Character + default CharacterVariant + links the generated image.
    The character becomes available globally for casting into any project/story.
    """
    # Verify image exists
    image = db.get(Image, payload.image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="generated image not found")

    try:
        character = save_actor_to_library(
            db=db,
            project_id=None,  # Global actor
            image_id=payload.image_id,
            display_name=payload.display_name,
            description=payload.description,
            traits=payload.traits.model_dump(exclude_none=True),
            image_style_id=payload.image_style_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {e}")

    return _build_actor_character_read(character, db)


@router.get("/library", response_model=list[ActorCharacterRead])
def list_actor_library(
    db=DbSessionDep,
    project_id: uuid.UUID | None = Query(default=None, description="Filter by project (optional)"),
):
    """
    List all actors in the global library.

    Optionally filter by project_id to see project-specific actors.
    Global actors (project_id=NULL) are always included.
    """
    # Build query for global actors + optionally project-specific
    if project_id:
        # Include both global actors AND project-specific actors
        stmt = (
            select(Character)
            .where(
                Character.is_library_saved.is_(True),
                (Character.project_id.is_(None) | (Character.project_id == project_id)),
            )
            .order_by(Character.created_at.desc())
        )
    else:
        # Only global actors
        stmt = (
            select(Character)
            .where(
                Character.is_library_saved.is_(True),
                Character.project_id.is_(None),
            )
            .order_by(Character.created_at.desc())
        )

    characters = list(db.execute(stmt).scalars().all())
    return [_build_actor_character_read(c, db) for c in characters]


@router.post("/import/file", response_model=ActorCharacterRead)
async def import_actor_file(
    display_name: str = Form(...),
    description: str | None = Form(None),
    traits: str | None = Form(None),  # JSON string
    image_style_id: str | None = Form(None),
    project_id: uuid.UUID | None = Form(None),
    file: UploadFile = File(...),
    db=DbSessionDep,
):
    """
    Import a character from an uploaded file.
    """
    # Parse traits JSON
    traits_dict = {}
    if traits:
        try:
            traits_dict = json.loads(traits)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid traits JSON")

    try:
        # Save file to media directory
        store = LocalMediaStore(
            root_dir=settings.media_root,
            url_prefix=settings.media_url_prefix,
        )
        file_bytes = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        
        # Save to media directory using helper
        _, image_url = store.save_image_bytes(file_bytes, mime_type)
        
        # Import actor using the saved image URL
        character = import_actor_from_image(
            db=db,
            project_id=project_id,
            image_url=image_url,
            display_name=display_name,
            description=description,
            traits=traits_dict,
            image_style_id=image_style_id,
        )
        
        return _build_actor_character_read(character, db)

    except Exception as e:
        logger.error(f"Import file failed: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/import", response_model=ActorCharacterRead)
def import_actor(
    payload: ImportActorRequest,
    db=DbSessionDep,
):
    """
    Import a character from an image URL or local file path.

    For local development, you can provide a local file path instead of a URL.
    The file will be copied to the media directory.

    Examples:
    - URL: "https://example.com/character.png"
    - Local: "/path/to/character.png" or "~/images/character.png"
    """
    traits = payload.traits.model_dump(exclude_none=True) if payload.traits else {}
    image_source = payload.image_url

    try:
        # Check if it's a local file path
        if _is_local_path(image_source):
            character = import_actor_from_local_file(
                db=db,
                project_id=None,  # Global actor
                file_path=image_source,
                display_name=payload.display_name,
                description=payload.description,
                traits=traits,
                image_style_id=payload.image_style_id,
            )
        else:
            character = import_actor_from_image(
                db=db,
                project_id=None,  # Global actor
                image_url=image_source,
                display_name=payload.display_name,
                description=payload.description,
                traits=traits,
                image_style_id=payload.image_style_id,
            )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")

    return _build_actor_character_read(character, db)


def _is_local_path(path: str) -> bool:
    """Check if the path is a local file path (not a URL)."""
    if path.startswith(("http://", "https://", "/media/")):
        return False
    # Check for local path patterns
    if path.startswith(("/", "~", "./")):
        return True
    # Check for Windows paths
    if len(path) > 1 and path[1] == ":":
        return True
    return False


# ============================================================================
# Actor Management Endpoints
# ============================================================================


@router.get("/characters/{character_id}", response_model=ActorCharacterRead)
def get_actor(character_id: uuid.UUID, db=DbSessionDep):
    """
    Get a character with all its global variants.
    """
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    return _build_actor_character_read(character, db)


@router.get("/characters/{character_id}/variants", response_model=list[ActorVariantRead])
def list_actor_variants(character_id: uuid.UUID, db=DbSessionDep):
    """
    List all global variants for a character.
    """
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    stmt = (
        select(CharacterVariant)
        .where(
            CharacterVariant.character_id == character_id,
            CharacterVariant.story_id.is_(None),
        )
        .order_by(CharacterVariant.is_default.desc(), CharacterVariant.created_at.desc())
    )
    variants = list(db.execute(stmt).scalars().all())

    return [_build_actor_variant_read(v, db) for v in variants]


@router.post("/characters/{character_id}/variants/generate", response_model=ActorVariantRead)
def generate_actor_variant(
    character_id: uuid.UUID,
    payload: GenerateActorVariantRequest,
    db=DbSessionDep,
):
    """
    Generate a new variant using an existing variant as reference.

    The base variant's reference image is used as identity anchor.
    Only the specified trait changes are applied while preserving identity.
    """
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    base_variant = db.get(CharacterVariant, payload.base_variant_id)
    if base_variant is None or base_variant.character_id != character_id:
        raise HTTPException(status_code=404, detail="base variant not found")

    try:
        variant = generate_variant_from_reference(
            db=db,
            character=character,
            base_variant=base_variant,
            trait_changes=payload.trait_changes.model_dump(exclude_none=True),
            image_style_id=payload.image_style_id,
            variant_name=payload.variant_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variant generation failed: {e}")

    return _build_actor_variant_read(variant, db)


@router.delete("/variants/{variant_id}")
def delete_actor_variant(variant_id: uuid.UUID, db=DbSessionDep):
    """
    Delete a character variant.

    Cannot delete the default variant.
    """
    variant = db.get(CharacterVariant, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="variant not found")

    if variant.is_default:
        raise HTTPException(status_code=400, detail="cannot delete default variant")

    db.delete(variant)
    db.commit()
    return {"deleted": True}


@router.delete("/characters/{character_id}")
def delete_actor(character_id: uuid.UUID, db=DbSessionDep):
    """
    Remove a character from the library.

    This sets is_library_saved=False. The character and its data remain
    but won't appear in the library.
    """
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    character.is_library_saved = False
    db.add(character)
    db.commit()

    return {"removed": True, "character_id": str(character_id)}


# ============================================================================
# Legacy Project-Scoped Endpoints (for backward compatibility)
# ============================================================================


@router.post("/projects/{project_id}/generate", response_model=GenerateActorResponse)
def generate_actor_for_project(
    project_id: uuid.UUID,
    payload: GenerateActorRequest,
    db=DbSessionDep,
):
    """
    Generate a new character profile sheet (project-scoped).

    DEPRECATED: Use POST /casting/generate for global actors.
    This endpoint is kept for backward compatibility.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        result = generate_character_profile_sheet(
            db=db,
            project_id=project_id,
            image_style_id=payload.image_style_id,
            traits=payload.traits.model_dump(exclude_none=True),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    return GenerateActorResponse(
        character_id=None,
        image_url=result["image_url"],
        image_id=result["image_id"],
        traits_used=result["traits_used"],
        status="generated",
    )


@router.post("/projects/{project_id}/save", response_model=ActorCharacterRead)
def save_actor_to_project(
    project_id: uuid.UUID,
    payload: SaveActorToLibraryRequest,
    db=DbSessionDep,
):
    """
    Save a generated character to a project's library.

    DEPRECATED: Use POST /casting/save for global actors.
    This endpoint is kept for backward compatibility.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    image = db.get(Image, payload.image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="generated image not found")

    try:
        character = save_actor_to_library(
            db=db,
            project_id=project_id,
            image_id=payload.image_id,
            display_name=payload.display_name,
            description=payload.description,
            traits=payload.traits.model_dump(exclude_none=True),
            image_style_id=payload.image_style_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {e}")

    return _build_actor_character_read(character, db)


@router.get("/projects/{project_id}/library", response_model=list[ActorCharacterRead])
def list_project_actor_library(project_id: uuid.UUID, db=DbSessionDep):
    """
    List actors available to a project.

    DEPRECATED: Use GET /casting/library?project_id=... instead.

    Returns both global actors AND project-specific actors.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    # Include both global actors AND project-specific actors
    stmt = (
        select(Character)
        .where(
            Character.is_library_saved.is_(True),
            (Character.project_id.is_(None) | (Character.project_id == project_id)),
        )
        .order_by(Character.created_at.desc())
    )
    characters = list(db.execute(stmt).scalars().all())

    return [_build_actor_character_read(c, db) for c in characters]


@router.post("/projects/{project_id}/import", response_model=ActorCharacterRead)
def import_actor_to_project(
    project_id: uuid.UUID,
    payload: ImportActorRequest,
    db=DbSessionDep,
):
    """
    Import a character from an image (project-scoped).

    DEPRECATED: Use POST /casting/import for global actors.
    This endpoint is kept for backward compatibility.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    traits = payload.traits.model_dump(exclude_none=True) if payload.traits else {}
    image_source = payload.image_url

    try:
        if _is_local_path(image_source):
            character = import_actor_from_local_file(
                db=db,
                project_id=project_id,
                file_path=image_source,
                display_name=payload.display_name,
                description=payload.description,
                traits=traits,
                image_style_id=payload.image_style_id,
            )
        else:
            character = import_actor_from_image(
                db=db,
                project_id=project_id,
                image_url=image_source,
                display_name=payload.display_name,
                description=payload.description,
                traits=traits,
                image_style_id=payload.image_style_id,
            )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")

    return _build_actor_character_read(character, db)
