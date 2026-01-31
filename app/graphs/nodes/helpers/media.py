import logging
import mimetypes
import os
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.models import CharacterReferenceImage, StoryCharacter
from app.graphs.nodes.helpers.character import _active_variant_reference_images

logger = logging.getLogger(__name__)


def _resolve_media_path(image_url: str) -> str:
    prefix = settings.media_url_prefix.rstrip("/")
    if image_url.startswith(f"{prefix}/"):
        return os.path.join(settings.media_root, image_url[len(prefix) + 1 :])
    if image_url.startswith("/media/"):
        return os.path.join(settings.media_root, image_url[len("/media/") :])
    if image_url.startswith("media/"):
        return os.path.join(settings.media_root, image_url[len("media/") :])
    if os.path.isabs(image_url):
        return image_url
    return os.path.join(settings.media_root, image_url)


def _load_character_reference_images(
    db: Session,
    story_id: uuid.UUID,
    max_images: int = 6,
    style_id: str | None = None,
) -> list[tuple[bytes, str]]:
    variant_refs = _active_variant_reference_images(db, story_id)
    stmt = (
        select(CharacterReferenceImage)
        .join(StoryCharacter, CharacterReferenceImage.character_id == StoryCharacter.character_id)
        .where(
            StoryCharacter.story_id == story_id,
            CharacterReferenceImage.approved.is_(True),
            CharacterReferenceImage.ref_type == "face",
        )
        .order_by(
            CharacterReferenceImage.character_id.asc(),
            CharacterReferenceImage.is_primary.desc(),
            CharacterReferenceImage.created_at.desc(),
        )
    )

    refs = list(db.execute(stmt).scalars().all())
    picked: dict[uuid.UUID, CharacterReferenceImage] = {}
    
    # 1. First priority: Variants matching the current scene style
    if style_id:
        s_id = style_id.lower()
        for (cid, vtype), ref in variant_refs.items():
            if cid not in picked and vtype == s_id:
                picked[cid] = ref
                if len(picked) >= max_images:
                    break

    # 2. Second priority: Default variants
    if len(picked) < max_images:
        for (cid, vtype), ref in variant_refs.items():
            if cid not in picked and vtype == "default":
                picked[cid] = ref
                if len(picked) >= max_images:
                    break

    # 3. Third priority: Any active variant for this character if still not picked
    if len(picked) < max_images:
        for (cid, vtype), ref in variant_refs.items():
            if cid not in picked:
                picked[cid] = ref
                if len(picked) >= max_images:
                    break

    # 4. Final priority: Base reference images
    for ref in refs:
        if ref.character_id in picked:
            continue
        picked[ref.character_id] = ref
        if len(picked) >= max_images:
            break

    results: list[tuple[bytes, str]] = []
    for ref in picked.values():
        try:
            path = _resolve_media_path(ref.image_url)
            with open(path, "rb") as handle:
                data = handle.read()
            mime_type = mimetypes.guess_type(path)[0] or "image/png"
            results.append((data, mime_type))
        except OSError as exc:
            logger.warning("reference image load failed ref_id=%s error=%s", ref.reference_image_id, exc)
            continue

    return results
