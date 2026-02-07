"""
Casting service for Actor system character generation.

Provides standalone character profile sheet generation and variant creation
independent of story/project context. Actors are global entities that can
be "cast" into any project or story.
"""

from __future__ import annotations

import logging
import mimetypes
import shutil
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.settings import settings
from app.db.models import Character, CharacterReferenceImage, CharacterVariant, Image
from app.prompts.loader import render_prompt
from app.services.storage import LocalMediaStore
from app.services.vertex_gemini import GeminiClient

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _build_gemini_client() -> GeminiClient:
    """Build Gemini client for image generation."""
    if not settings.google_cloud_project and not settings.gemini_api_key:
        raise RuntimeError("Gemini is not configured")

    return GeminiClient(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        api_key=settings.gemini_api_key,
        text_model=settings.gemini_text_model,
        image_model=settings.gemini_image_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
        initial_backoff_seconds=settings.gemini_initial_backoff_seconds,
    )


def _save_image(image_bytes: bytes, mime_type: str) -> str:
    """Save image bytes and return URL."""
    store = LocalMediaStore(
        root_dir=settings.media_root,
        url_prefix=settings.media_url_prefix,
    )
    _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)
    return url


def _copy_local_file_to_media(file_path: str) -> str:
    """
    Copy a local file to the media directory and return the media URL.

    Args:
        file_path: Local file path (can use ~ for home directory)

    Returns:
        Media URL for the copied file

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    # Expand ~ to home directory
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {file_path}")

    # Read the file
    with open(path, "rb") as f:
        image_bytes = f.read()

    # Determine mime type
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        # Default to png for unknown types
        mime_type = "image/png"

    # Save to media directory
    return _save_image(image_bytes, mime_type)


def generate_character_profile_sheet(
    db: "Session",
    project_id: uuid.UUID | None,
    image_style_id: str,
    traits: dict[str, Any],
) -> dict:
    """
    Generate a character profile sheet image.

    This creates a 9:16 vertical image with:
    - Full-body front view (head-to-toe)
    - 2-3 expression inset boxes

    Args:
        db: Database session
        project_id: Optional project ID (None for global actors)
        image_style_id: Image style to use
        traits: Character traits dictionary

    Returns:
        dict with image_url, image_id, traits_used.
        The character is NOT saved to the database - just the image.
    """
    # Build prompt from traits
    from app.config.loaders import load_character_style_text, load_style_guide_text

    image_style_guide = load_style_guide_text(image_style_id)
    character_style_guide = load_character_style_text(image_style_id)

    prompt = render_prompt(
        "prompt_profile_sheet",
        gender=traits.get("gender"),
        age_range=traits.get("age_range"),
        face_traits=traits.get("face_traits"),
        hair_traits=traits.get("hair_traits"),
        mood=traits.get("mood"),
        custom_prompt=traits.get("custom_prompt"),
        image_style=image_style_id,
        image_style_guide=image_style_guide,
        character_style_guide=character_style_guide,
    )

    project_info = f"project {project_id}" if project_id else "global"
    logger.info(f"Generating profile sheet for {project_info} with style: {image_style_id}")

    # Generate image
    client = _build_gemini_client()
    image_bytes, mime_type = client.generate_image(prompt=prompt)

    # Save image
    image_url = _save_image(image_bytes, mime_type)

    # Create Image record (not linked to artifact yet)
    image = Image(
        image_url=image_url,
        metadata_={
            "type": "profile_sheet",
            "project_id": str(project_id) if project_id else None,
            "image_style": image_style_id,
            "traits": traits,
        },
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    logger.info(f"Generated profile sheet image {image.image_id}")

    return {
        "image_url": image_url,
        "image_id": image.image_id,
        "traits_used": traits,
    }


def save_actor_to_library(
    db: "Session",
    project_id: uuid.UUID | None,
    image_id: uuid.UUID,
    display_name: str,
    description: str | None,
    traits: dict[str, Any],
    image_style_id: str,
) -> Character:
    """
    Save a generated character to the actor library.

    Creates:
    - Character entity (global if project_id is None)
    - CharacterReferenceImage linked to the generated image
    - Default CharacterVariant (global, no story_id)

    Args:
        db: Database session
        project_id: Optional project ID (None for global actors)
        image_id: ID of the generated profile sheet image
        display_name: Display name for the actor
        description: Optional description
        traits: Character traits dictionary
        image_style_id: Image style used

    Returns:
        The created Character.
    """
    # Verify image exists
    image = db.get(Image, image_id)
    if image is None:
        raise ValueError(f"Image {image_id} not found")

    # Create character (project_id can be None for global actors)
    character = Character(
        project_id=project_id,
        name=display_name,
        display_name=display_name,
        description=description,
        gender=traits.get("gender"),
        age_range=traits.get("age_range"),
        default_image_style_id=image_style_id,
        is_library_saved=True,
        approved=True,
    )
    db.add(character)
    db.flush()

    scope = f"project {project_id}" if project_id else "global"
    logger.info(f"Created {scope} character {character.character_id} ({display_name})")

    # Create reference image record
    ref_image = CharacterReferenceImage(
        character_id=character.character_id,
        image_url=image.image_url,
        ref_type="profile_sheet",
        approved=True,
        is_primary=True,
        metadata_={
            "source_image_id": str(image_id),
            "traits": traits,
        },
    )
    db.add(ref_image)
    db.flush()

    # Create default variant (global - no story_id)
    variant = CharacterVariant(
        character_id=character.character_id,
        story_id=None,  # Global variant for Actor system
        variant_type="base",
        variant_name="Default",
        image_style_id=image_style_id,
        traits=traits,
        reference_image_id=ref_image.reference_image_id,
        generated_image_ids=[str(image_id)],
        is_default=True,
    )
    db.add(variant)
    db.commit()

    db.refresh(character)
    logger.info(f"Saved character {character.character_id} to library with default variant")

    return character


def generate_variant_from_reference(
    db: "Session",
    character: Character,
    base_variant: CharacterVariant,
    trait_changes: dict[str, Any],
    image_style_id: str | None,
    variant_name: str | None,
) -> CharacterVariant:
    """
    Generate a new variant using an existing variant's reference image.

    The base variant's reference image is used as identity anchor.
    Only the specified trait changes are applied.

    Returns the newly created CharacterVariant.
    """
    # Get reference image
    if not base_variant.reference_image_id:
        raise ValueError("Base variant has no reference image")

    ref_image = db.get(CharacterReferenceImage, base_variant.reference_image_id)
    if not ref_image:
        raise ValueError("Reference image not found")

    # Use base variant styles if not overridden
    final_image_style = image_style_id or base_variant.image_style_id or character.default_image_style_id or "default"

    # Merge traits - start with base, apply changes
    merged_traits = {**(base_variant.traits or {})}
    for key, value in trait_changes.items():
        if value is not None:
            merged_traits[key] = value

    logger.info(f"Generating variant for character {character.character_id} with changes: {trait_changes}")

    # Build prompt
    prompt = render_prompt(
        "prompt_variant_generation",
        base_traits=base_variant.traits or {},
        hair_changes=trait_changes.get("hair_traits"),
        mood_changes=trait_changes.get("mood"),
        outfit_changes=trait_changes.get("custom_prompt"),  # Use custom_prompt for outfit changes
        custom_changes=None,
        image_style=final_image_style,
    )

    # Load reference image bytes
    ref_bytes, ref_mime = _load_image_bytes(ref_image.image_url)

    # Generate with reference
    gemini = _build_gemini_client()
    image_bytes, mime_type = gemini.generate_image(
        prompt=prompt,
        reference_images=[(ref_bytes, ref_mime)],
    )

    # Save image
    image_url = _save_image(image_bytes, mime_type)

    # Create Image record
    image = Image(
        image_url=image_url,
        metadata_={
            "type": "variant",
            "character_id": str(character.character_id),
            "base_variant_id": str(base_variant.variant_id),
            "trait_changes": trait_changes,
        },
    )
    db.add(image)
    db.flush()

    # Create reference image record for the new variant
    new_ref = CharacterReferenceImage(
        character_id=character.character_id,
        image_url=image_url,
        ref_type="variant",
        approved=True,
        is_primary=False,
        metadata_={
            "source_image_id": str(image.image_id),
            "base_variant_id": str(base_variant.variant_id),
        },
    )
    db.add(new_ref)
    db.flush()

    # Create variant (global - no story_id)
    variant = CharacterVariant(
        character_id=character.character_id,
        story_id=None,  # Global variant
        variant_type="variant",
        variant_name=variant_name or f"Variant {uuid.uuid4().hex[:6]}",
        image_style_id=final_image_style,
        traits=merged_traits,
        reference_image_id=new_ref.reference_image_id,
        generated_image_ids=[str(image.image_id)],
        is_default=False,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)

    logger.info(f"Created variant {variant.variant_id} for character {character.character_id}")

    return variant


def _load_image_bytes(image_url: str) -> tuple[bytes, str]:
    """
    Load image bytes from URL or local media path.

    Args:
        image_url: URL or local media path (/media/...)

    Returns:
        Tuple of (bytes, mime_type)
    """
    import httpx

    # Check if it's a local media URL
    if image_url.startswith("/media/"):
        # Load from local file system
        media_path = Path(settings.media_root) / image_url.replace("/media/", "")
        if not media_path.exists():
            raise ValueError(f"Media file not found: {image_url}")

        with open(media_path, "rb") as f:
            image_bytes = f.read()

        mime_type, _ = mimetypes.guess_type(str(media_path))
        return image_bytes, mime_type or "image/png"

    # Load from URL
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(image_url)
            resp.raise_for_status()
            return resp.content, resp.headers.get("content-type", "image/png")
    except Exception as e:
        logger.error(f"Failed to load image from URL: {e}")
        raise ValueError(f"Failed to load image: {e}")


def import_actor_from_image(
    db: "Session",
    project_id: uuid.UUID | None,
    image_url: str,
    display_name: str,
    description: str | None,
    traits: dict[str, Any] | None,
    image_style_id: str | None,
) -> Character:
    """
    Import a character from an external image URL.

    Creates Character + CharacterReferenceImage + default variant
    without generating a new image.

    Args:
        db: Database session
        project_id: Optional project ID (None for global actors)
        image_url: URL of the image to import
        display_name: Display name for the actor
        description: Optional description
        traits: Optional character traits
        image_style_id: Optional image style

    Returns:
        The created Character.
    """
    traits = traits or {}

    # Create character (project_id can be None for global actors)
    character = Character(
        project_id=project_id,
        name=display_name,
        display_name=display_name,
        description=description,
        gender=traits.get("gender"),
        age_range=traits.get("age_range"),
        default_image_style_id=image_style_id,
        is_library_saved=True,
        approved=True,
    )
    db.add(character)
    db.flush()

    scope = f"project {project_id}" if project_id else "global"
    logger.info(f"Importing {scope} character {character.character_id} ({display_name}) from URL")

    # Create reference image from URL
    ref_image = CharacterReferenceImage(
        character_id=character.character_id,
        image_url=image_url,
        ref_type="imported",
        approved=True,
        is_primary=True,
        metadata_={
            "imported": True,
            "source_url": image_url,
        },
    )
    db.add(ref_image)
    db.flush()

    # Create default variant (global)
    variant = CharacterVariant(
        character_id=character.character_id,
        story_id=None,
        variant_type="imported",
        variant_name="Imported",
        image_style_id=image_style_id,
        traits=traits,
        reference_image_id=ref_image.reference_image_id,
        is_default=True,
    )
    db.add(variant)
    db.commit()

    db.refresh(character)
    logger.info(f"Imported character {character.character_id} to library")

    return character


def import_actor_from_local_file(
    db: "Session",
    project_id: uuid.UUID | None,
    file_path: str,
    display_name: str,
    description: str | None,
    traits: dict[str, Any] | None,
    image_style_id: str | None,
) -> Character:
    """
    Import a character from a local file.

    Copies the file to the media directory and creates Character +
    CharacterReferenceImage + default variant.

    Args:
        db: Database session
        project_id: Optional project ID (None for global actors)
        file_path: Local file path (supports ~ for home directory)
        display_name: Display name for the actor
        description: Optional description
        traits: Optional character traits
        image_style_id: Optional image style

    Returns:
        The created Character.

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    # Copy file to media directory
    media_url = _copy_local_file_to_media(file_path)

    traits = traits or {}

    # Create character (project_id can be None for global actors)
    character = Character(
        project_id=project_id,
        name=display_name,
        display_name=display_name,
        description=description,
        gender=traits.get("gender"),
        age_range=traits.get("age_range"),
        default_image_style_id=image_style_id,
        is_library_saved=True,
        approved=True,
    )
    db.add(character)
    db.flush()

    scope = f"project {project_id}" if project_id else "global"
    logger.info(f"Importing {scope} character {character.character_id} ({display_name}) from local file: {file_path}")

    # Create reference image with media URL
    ref_image = CharacterReferenceImage(
        character_id=character.character_id,
        image_url=media_url,
        ref_type="imported",
        approved=True,
        is_primary=True,
        metadata_={
            "imported": True,
            "source_type": "local_file",
            "source_path": file_path,
        },
    )
    db.add(ref_image)
    db.flush()

    # Create default variant (global)
    variant = CharacterVariant(
        character_id=character.character_id,
        story_id=None,
        variant_type="imported",
        variant_name="Imported",
        image_style_id=image_style_id,
        traits=traits,
        reference_image_id=ref_image.reference_image_id,
        is_default=True,
    )
    db.add(variant)
    db.commit()

    db.refresh(character)
    logger.info(f"Imported character {character.character_id} to library from local file")

    return character
