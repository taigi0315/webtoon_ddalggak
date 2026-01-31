from __future__ import annotations

import hashlib
import mimetypes

from .utils import *
from app.core.metrics import track_graph_node
from app.core.request_context import log_context
from app.graphs.nodes.helpers.character import _active_variants_by_character
from app.graphs.nodes.helpers.media import _load_character_reference_images
from app.graphs.nodes.helpers.scene import _get_scene, _list_characters
from app.graphs.nodes.utils import _character_ids_with_reference_images, _render_image_from_prompt


def compute_prompt_compiler(
    panel_semantics: dict,
    layout_template: dict,
    style_id: str,
    characters: list[Character] | None = None,
    reference_char_ids: set[uuid.UUID] | None = None,
    variants_by_character: dict[uuid.UUID, CharacterVariant] | None = None,
) -> dict:
    prompt = _compile_prompt(
        panel_semantics=panel_semantics,
        layout_template=layout_template,
        style_id=style_id,
        characters=characters or [],
        reference_char_ids=reference_char_ids or set(),
        variants_by_character=variants_by_character,
    )
    return {
        "prompt": f"STYLE: {style_id}\n{prompt}",
        "style_id": style_id,
    }


def run_prompt_compiler(
    db: Session,
    scene_id: uuid.UUID,
    style_id: str,
    prompt_override: str | None = None,
):
    with track_graph_node("scene_render", "prompt_compiler"):
        with log_context(node_name="prompt_compiler", scene_id=scene_id):
            with trace_span("graph.prompt_compiler", scene_id=str(scene_id), style_id=style_id):
                svc = ArtifactService(db)
                panel_semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
                layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)
                if panel_semantics is None or layout is None:
                    raise ValueError("panel_semantics and layout_template artifacts are required")

                scene = _get_scene(db, scene_id)
                story = db.get(Story, scene.story_id)
                
                # Check for scene-level style override
                effective_style_id = style_id or scene.image_style_override or (story.default_image_style if story else "default") or "default"
                
                # Load art direction artifact
                art_direction_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_ART_DIRECTION)
                art_direction = None
                if art_direction_artifact and art_direction_artifact.payload:
                    art_direction = art_direction_artifact.payload
                
                characters = _list_characters(db, scene.story_id)
                reference_char_ids = _character_ids_with_reference_images(db, scene.story_id)
                variants_by_character = _active_variants_by_character(db, scene.story_id)
                panel_count = _panel_count(panel_semantics.payload)
                layout_panels = layout.payload.get("panels")
                layout_count = len(layout_panels) if isinstance(layout_panels, list) else None
                if layout_count is not None and panel_count != layout_count:
                    raise ValueError(
                        f"Layout/template panel count mismatch: panel_semantics={panel_count} layout={layout_count}"
                    )

                prompt = prompt_override
                if not prompt:
                    prompt = _compile_prompt(
                        panel_semantics=panel_semantics.payload,
                        layout_template=layout.payload,
                        style_id=effective_style_id,
                        characters=characters,
                        reference_char_ids=reference_char_ids,
                        variants_by_character=variants_by_character,
                        art_direction=art_direction,
                    )
                
                payload = {
                    "prompt": prompt,
                    "style_id": effective_style_id,
                    "layout_template_id": layout.payload.get("template_id"),
                    "panel_count": panel_count,
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                }
                return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_SPEC, payload=payload)

def generate_character_reference_image(
    db: Session,
    character_id: uuid.UUID,
    ref_type: str = "face",
    gemini: GeminiClient | None = None,
) -> CharacterReferenceImage:
    character = db.get(Character, character_id)
    if character is None:
        raise ValueError("character not found")

    if not character.description and not character.identity_line:
        raise ValueError("character needs description or identity_line to generate reference images")

    gemini = gemini or _build_gemini_client()

    style_prompt = get_character_style_prompt(character.gender, character.age_range)
    identity = character.identity_line or character.description or character.name

    prompt_parts = [
        "High-quality character reference image.",
        f"Character: {character.name}.",
        f"Identity: {identity}.",
        f"Ref type: {ref_type}.",
    ]
    if style_prompt:
        prompt_parts.append(style_prompt)
    prompt_parts.append("Plain background, clean silhouette, full body if possible.")

    prompt = " ".join([part for part in prompt_parts if part])

    image_bytes, mime_type = gemini.generate_image(prompt=prompt)

    store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
    _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

    ref = CharacterReferenceImage(
        character_id=character_id,
        image_url=url,
        ref_type=ref_type,
        approved=False,
        is_primary=False,
        metadata_={
            "mime_type": mime_type,
            "model": getattr(gemini, "last_model", None),
            "request_id": getattr(gemini, "last_request_id", None),
            "usage": getattr(gemini, "last_usage", None),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        },
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def _format_variant_attributes(override_attributes: dict) -> str:
    if not override_attributes:
        return ""
    parts: list[str] = []
    outfit = override_attributes.get("outfit") or override_attributes.get("clothing")
    if outfit:
        parts.append(f"Outfit: {outfit}.")
    hair = override_attributes.get("hair") or override_attributes.get("hairstyle")
    if hair:
        parts.append(f"Hair: {hair}.")
    accessories = override_attributes.get("accessories") or override_attributes.get("accessory")
    if accessories:
        parts.append(f"Accessories: {accessories}.")
    props = override_attributes.get("props") or override_attributes.get("items")
    if props:
        parts.append(f"Props: {props}.")
    if override_attributes.get("bag"):
        parts.append(f"Bag: {override_attributes.get('bag')}.")
    used_keys = {"outfit", "clothing", "hair", "hairstyle", "accessories", "accessory", "props", "items", "bag"}
    extras = {k: v for k, v in override_attributes.items() if k not in used_keys}
    if extras:
        extras_text = ", ".join([f"{key}: {value}" for key, value in extras.items()])
        parts.append(f"Additional details: {extras_text}.")
    return " ".join(parts)


def _load_reference_image_bytes(ref: CharacterReferenceImage) -> tuple[bytes, str]:
    path = _resolve_media_path(ref.image_url)
    with open(path, "rb") as handle:
        data = handle.read()
    mime_type = mimetypes.guess_type(path)[0] or "image/png"
    return data, mime_type


def generate_character_variant_reference_image(
    db: Session,
    character_id: uuid.UUID,
    variant_type: str,
    override_attributes: dict,
    base_reference: CharacterReferenceImage,
    gemini: GeminiClient | None = None,
) -> CharacterReferenceImage:
    character = db.get(Character, character_id)
    if character is None:
        raise ValueError("character not found")

    if not character.description and not character.identity_line:
        raise ValueError("character needs description or identity_line to generate reference images")

    gemini = gemini or _build_gemini_client()

    style_prompt = get_character_style_prompt(character.gender, character.age_range)
    identity = character.identity_line or character.description or character.name
    variant_text = _format_variant_attributes(override_attributes)

    prompt_parts = [
        "High-quality character reference image.",
        f"Character: {character.name}.",
        f"Identity: {identity}.",
        f"Variant: {variant_type.replace('_', ' ')}.",
        "Use the provided reference image for face, proportions, and features.",
        "Preserve identity exactly; only update the variant details.",
        "Full body if possible.",
    ]
    if variant_text:
        prompt_parts.append(variant_text)
    if style_prompt:
        prompt_parts.append(style_prompt)
    prompt_parts.append("Plain background, clean silhouette.")

    prompt = " ".join([part for part in prompt_parts if part])

    ref_image = _load_reference_image_bytes(base_reference)
    image_bytes, mime_type, metadata = _render_image_from_prompt(
        prompt,
        gemini=gemini,
        reference_images=[ref_image],
    )

    store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
    _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

    ref = CharacterReferenceImage(
        character_id=character_id,
        image_url=url,
        ref_type="face",
        approved=False,
        is_primary=False,
        metadata_={
            "mime_type": mime_type,
            "model": metadata.get("model"),
            "request_id": metadata.get("request_id"),
            "usage": metadata.get("usage"),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "variant_type": variant_type,
            "override_attributes": override_attributes,
            "base_reference_id": str(base_reference.reference_image_id),
        },
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref

def generate_character_variant_suggestions(
    db: Session,
    story_id: uuid.UUID,
    gemini: GeminiClient | None = None,
) -> list[dict]:
    story = db.get(Story, story_id)
    if story is None:
        raise ValueError("story not found")

    scenes = list(db.execute(select(Scene).where(Scene.story_id == story_id)).scalars().all())
    scene_text = "\n\n".join([s.source_text for s in scenes[:5] if s.source_text])[:4000]
    characters = _list_characters(db, story_id)
    character_names = [c.name for c in characters if c.name]
    if not character_names:
        return []

    if gemini is None:
        try:
            gemini = _build_gemini_client()
        except Exception:  # noqa: BLE001
            gemini = None

    if gemini is None:
        return []

    prompt = _prompt_variant_suggestions(story_id, story.title, scene_text, character_names)
    raw = _maybe_json_from_gemini(
        gemini,
        prompt,
        expected_schema="{ suggestions: [{ character_name: string, variant_type: string, override_attributes: object }] }",
    )
    if not isinstance(raw, dict):
        return []

    suggestions = raw.get("suggestions")
    if not isinstance(suggestions, list):
        return []

    by_name = {c.name.lower(): c for c in characters if c.name}
    normalized: list[dict] = []
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        name = str(item.get("character_name") or "").strip()
        if not name:
            continue
        character = by_name.get(name.lower())
        if not character:
            continue
        variant_type = str(item.get("variant_type") or "outfit_change").strip()
        override_attributes = item.get("override_attributes") if isinstance(item.get("override_attributes"), dict) else {}
        if not override_attributes:
            continue
        normalized.append(
            {
                "character_id": character.character_id,
                "variant_type": variant_type,
                "override_attributes": override_attributes,
            }
        )
    return normalized

def run_image_renderer(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
    reason: str | None = None,
):
    with track_graph_node("scene_render", "image_renderer"):
        with log_context(node_name="image_renderer", scene_id=scene_id):
            with trace_span("graph.image_renderer", scene_id=str(scene_id), reason=reason):
                svc = ArtifactService(db)
                render_spec = svc.get_latest_artifact(scene_id, ARTIFACT_RENDER_SPEC)
                if render_spec is None:
                    raise ValueError("render_spec artifact not found")

                prompt = render_spec.payload.get("prompt")
                if not prompt:
                    raise ValueError("render_spec is missing prompt")

                reference_images = None
                if gemini is not None:
                    scene = _get_scene(db, scene_id)
                    style_id = render_spec.payload.get("style_id")
                    reference_images = _load_character_reference_images(
                        db, scene.story_id, style_id=style_id
                    )

                image_bytes, mime_type, metadata = _render_image_from_prompt(
                    prompt,
                    gemini=gemini,
                    reference_images=reference_images,
                )

                store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
                _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

                image = ImageService(db).create_image(
                    image_url=url,
                    artifact_id=None,
                    metadata=metadata,
                )

                payload = {
                    "image_id": str(image.image_id),
                    "image_url": image.image_url,
                    "mime_type": mime_type,
                    "model": metadata.get("model"),
                    "request_id": metadata.get("request_id"),
                    "usage": metadata.get("usage"),
                    "prompt_sha256": render_spec.payload.get("prompt_sha256"),
                    "prompt": prompt,
                    "approved": False,
                    "reason": reason,
                }
                return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_RESULT, payload=payload)
