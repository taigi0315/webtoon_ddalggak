import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Character, CharacterReferenceImage, Scene
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from .constants import (
    ARTIFACT_LAYOUT_TEMPLATE,
    ARTIFACT_PANEL_PLAN,
    ARTIFACT_PANEL_PLAN_NORMALIZED,
    ARTIFACT_PANEL_SEMANTICS,
    ARTIFACT_SCENE_INTENT,
)
from .gemini import _build_gemini_client


logger = logging.getLogger(__name__)


def compute_panel_semantic_filler(
    source_text: str,
    scene_intent: dict,
    panel_plan: dict,
    layout_template: dict,
    characters: list[dict],
    gemini: GeminiClient | None = None,
) -> dict:
    gemini = gemini or _build_gemini_client()

    prompt = (
        "Fill panel semantics as JSON: {\"panels\": [{\"grammar_id\": <string>, \"text\": <string>}]}.\n"
        "For each panel, include a short visual description suitable for prompt compilation.\n\n"
        f"SCENE_TEXT:\n{source_text}\n\n"
        f"SCENE_INTENT_JSON:\n{json.dumps(scene_intent, ensure_ascii=False)}\n\n"
        f"PANEL_PLAN_JSON:\n{json.dumps(panel_plan, ensure_ascii=False)}\n\n"
        f"LAYOUT_TEMPLATE_JSON:\n{json.dumps(layout_template, ensure_ascii=False)}\n\n"
        f"CHARACTERS_JSON:\n{json.dumps(characters, ensure_ascii=False)}\n"
    )

    text = gemini.generate_text(prompt)
    try:
        payload = json.loads(text)
    except Exception:
        panels = panel_plan.get("panels")
        if not isinstance(panels, list):
            panels = []
        payload = {
            "panels": [
                {"grammar_id": p.get("grammar_id"), "text": f"Panel describing: {source_text[:80]}"}
                for p in panels
            ]
        }

    if isinstance(payload, dict):
        payload.setdefault("_meta", {})
        payload["_meta"].update(
            {"model": getattr(gemini, "last_model", None), "usage": getattr(gemini, "last_usage", None)}
        )
    return payload


def run_panel_semantic_filler(db: Session, scene_id: uuid.UUID, gemini: GeminiClient | None = None):
    svc = ArtifactService(db)
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")

    intent = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
    if intent is None:
        raise ValueError("scene_intent artifact not found")

    plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED) or svc.get_latest_artifact(
        scene_id, ARTIFACT_PANEL_PLAN
    )
    if plan is None:
        raise ValueError("panel_plan artifact not found")

    layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)
    if layout is None:
        raise ValueError("layout_template artifact not found")

    chars = list(db.execute(select(Character).where(Character.story_id == scene.story_id)).scalars().all())
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
    primary_face_by_character_id = {r.character_id: r for r in primary_refs}

    characters = []
    for c in chars:
        primary_face = primary_face_by_character_id.get(c.character_id)
        characters.append(
            {
                "character_id": str(c.character_id),
                "name": c.name,
                "description": c.description,
                "role": c.role,
                "identity_line": c.identity_line,
                "primary_face_ref_image_url": primary_face.image_url if primary_face else None,
            }
        )

    payload = compute_panel_semantic_filler(
        source_text=scene.source_text,
        scene_intent=intent.payload,
        panel_plan=plan.payload,
        layout_template=layout.payload,
        characters=characters,
        gemini=gemini,
    )
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_SEMANTICS, payload=payload)
    logger.info(
        "node_complete node_name=PanelSemanticFiller scene_id=%s artifact_id=%s model=%s",
        scene_id,
        artifact.artifact_id,
        (payload.get("_meta") or {}).get("model") if isinstance(payload, dict) else None,
    )
    return artifact
