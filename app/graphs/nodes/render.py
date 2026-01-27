import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.models import Character, CharacterReferenceImage, Scene
from app.services.artifacts import ArtifactService
from app.services.images import ImageService
from app.services.storage import LocalMediaStore
from app.services.vertex_gemini import GeminiClient
from .constants import ARTIFACT_RENDER_RESULT, ARTIFACT_RENDER_SPEC
from .gemini import _build_gemini_client


logger = logging.getLogger(__name__)


def _load_reference_images(primary_refs: list[CharacterReferenceImage]) -> list[tuple[bytes, str]]:
    """Load reference images from URLs for use in image generation."""
    import urllib.request
    import os

    reference_images: list[tuple[bytes, str]] = []
    for ref in primary_refs:
        try:
            url = ref.image_url
            # Handle local file URLs
            if url.startswith("/media/") or url.startswith("media/"):
                file_path = os.path.join(settings.media_root, url.lstrip("/media/"))
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        img_bytes = f.read()
                    mime_type = ref.metadata_.get("mime_type", "image/png")
                    reference_images.append((img_bytes, mime_type))
            elif url.startswith("http://") or url.startswith("https://"):
                with urllib.request.urlopen(url, timeout=30) as response:
                    img_bytes = response.read()
                mime_type = ref.metadata_.get("mime_type", "image/png")
                reference_images.append((img_bytes, mime_type))
        except Exception as e:
            logger.warning("failed to load reference image %s: %s", ref.reference_image_id, e)
            continue

    return reference_images


def run_image_renderer(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
    reason: str | None = None,
    use_character_refs: bool = True,
):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")

    chars = list(db.execute(select(Character).where(Character.story_id == scene.story_id)).scalars().all())
    if not chars:
        raise ValueError("no characters found; create characters and approve primary face refs before rendering")

    primary_refs = list(
        db.execute(
            select(CharacterReferenceImage).where(
                CharacterReferenceImage.character_id.in_([c.character_id for c in chars]),
                CharacterReferenceImage.ref_type == "face",
                CharacterReferenceImage.approved.is_(True),
                CharacterReferenceImage.is_primary.is_(True),
            )
        )
        .scalars()
        .all()
    )
    primary_by_character_id = {r.character_id for r in primary_refs}

    main_chars = [c for c in chars if (c.role or "").lower() == "main"]
    target_chars = main_chars if main_chars else chars
    missing = [c.name for c in target_chars if c.character_id not in primary_by_character_id]
    if missing:
        raise ValueError(f"missing primary face refs for: {', '.join(missing)}")

    svc = ArtifactService(db)
    spec = svc.get_latest_artifact(scene_id, ARTIFACT_RENDER_SPEC)
    if spec is None:
        raise ValueError("render_spec artifact not found")

    gemini = gemini or _build_gemini_client()

    # Load character reference images for consistency
    reference_images = None
    if use_character_refs and primary_refs:
        reference_images = _load_reference_images(primary_refs)
        if reference_images:
            logger.info(
                "using %d character reference images for scene %s",
                len(reference_images),
                scene_id,
            )

    image_bytes, mime_type = gemini.generate_image(
        prompt=spec.payload["prompt"],
        model=None,
        reference_images=reference_images,
    )

    store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
    _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

    image_row = ImageService(db).create_image(
        image_url=url,
        metadata={
            "mime_type": mime_type,
            "model": getattr(gemini, "last_model", None),
            "request_id": getattr(gemini, "last_request_id", None),
            "usage": getattr(gemini, "last_usage", None),
            "used_character_refs": len(reference_images) if reference_images else 0,
        },
    )

    payload = {
        "image_id": str(image_row.image_id),
        "image_url": url,
        "mime_type": mime_type,
        "used_character_refs": len(reference_images) if reference_images else 0,
        "_meta": {"model": getattr(gemini, "last_model", None), "usage": getattr(gemini, "last_usage", None)},
    }
    if reason:
        payload["regenerate_reason"] = reason
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_RESULT, payload=payload)
    logger.info(
        "node_complete node_name=ImageRenderer scene_id=%s artifact_id=%s model=%s refs_used=%d",
        scene_id,
        artifact.artifact_id,
        getattr(gemini, "last_model", None),
        len(reference_images) if reference_images else 0,
    )
    return artifact


def compute_character_image_prompt(
    character: Character,
    ref_type: str = "face",
    story_style: str | None = None,
) -> str:
    """Build a prompt for generating character reference images."""
    parts = []

    if ref_type == "face":
        parts.append("Character portrait, head and shoulders, frontal view, neutral background.")
    elif ref_type == "body":
        parts.append("Full body character illustration, standing pose, neutral background.")
    else:
        parts.append(f"Character illustration ({ref_type}), neutral background.")

    if story_style:
        parts.append(f"Style: {story_style} webtoon/manhwa style.")
    else:
        parts.append("Style: Korean webtoon/manhwa style, clean lines, vibrant colors.")

    parts.append(f"Character name: {character.name}")

    if character.description:
        parts.append(f"Appearance: {character.description}")

    if character.identity_line:
        parts.append(f"Visual identity: {character.identity_line}")

    if character.role == "main":
        parts.append("This is a main character - make them distinctive and memorable.")

    return "\n".join(parts)


def generate_character_reference_image(
    db: Session,
    character_id: uuid.UUID,
    ref_type: str = "face",
    story_style: str | None = None,
    gemini: GeminiClient | None = None,
) -> CharacterReferenceImage:
    """Generate a single character reference image using AI."""
    character = db.get(Character, character_id)
    if character is None:
        raise ValueError("character not found")

    # Get story style if not provided
    if story_style is None and character.story:
        story_style = character.story.default_story_style

    gemini = gemini or _build_gemini_client()
    prompt = compute_character_image_prompt(character, ref_type=ref_type, story_style=story_style)

    image_bytes, mime_type = gemini.generate_image(prompt=prompt)

    store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
    _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

    ref = CharacterReferenceImage(
        character_id=character_id,
        image_url=url,
        ref_type=ref_type,
        metadata_={
            "mime_type": mime_type,
            "model": getattr(gemini, "last_model", None),
            "prompt": prompt,
            "generated": True,
        },
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)

    logger.info(
        "character_ref_generated character_id=%s ref_type=%s model=%s",
        character_id,
        ref_type,
        getattr(gemini, "last_model", None),
    )
    return ref
