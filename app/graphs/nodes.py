from __future__ import annotations

import json
import uuid
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.loaders import load_grammar_to_prompt_mapping_v1, select_template
from app.core.settings import settings
from app.db.models import Character, Scene
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from app.services.images import ImageService
from app.services.storage import LocalMediaStore


logger = logging.getLogger(__name__)


ARTIFACT_SCENE_INTENT = "scene_intent"
ARTIFACT_PANEL_PLAN = "panel_plan"
ARTIFACT_PANEL_PLAN_NORMALIZED = "panel_plan_normalized"
ARTIFACT_LAYOUT_TEMPLATE = "layout_template"
ARTIFACT_PANEL_SEMANTICS = "panel_semantics"
ARTIFACT_RENDER_SPEC = "render_spec"
ARTIFACT_RENDER_RESULT = "render_result"
ARTIFACT_BLIND_TEST_REPORT = "blind_test_report"


def compute_prompt_compiler(
    panel_semantics: dict,
    layout_template: dict,
    style_id: str = "default",
) -> dict:
    mapping = load_grammar_to_prompt_mapping_v1().mapping

    panels = panel_semantics.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ValueError("panel_semantics.panels must be a non-empty list")

    parts: list[str] = []
    parts.append(f"STYLE: {style_id}")

    template_id = layout_template.get("template_id")
    if template_id:
        parts.append(f"LAYOUT_TEMPLATE: {template_id}")

    for idx, panel in enumerate(panels, start=1):
        grammar_id = panel.get("grammar_id")
        semantic_text = panel.get("text")

        mapped = mapping.get(grammar_id, "") if isinstance(grammar_id, str) else ""
        line = f"PANEL {idx}: {mapped}".strip()
        if semantic_text:
            line = f"{line} | {semantic_text}" if line else str(semantic_text)
        parts.append(line)

    prompt = "\n".join([p for p in parts if p])
    return {"style_id": style_id, "prompt": prompt}


def compute_layout_template_resolver(panel_plan: dict | list, derived_features: dict | None = None) -> dict:
    template = select_template(panel_plan, derived_features=derived_features)
    return template.model_dump()


def compute_panel_plan_normalizer(panel_plan: dict) -> dict:
    panels = panel_plan.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ValueError("panel_plan.panels must be a non-empty list")

    normalized: list[dict] = []
    last_two: list[str] = []
    closeup_count = 0

    for p in panels:
        grammar_id = p.get("grammar_id")
        if grammar_id == "emotion_closeup":
            closeup_count += 1
            if closeup_count > 1:
                grammar_id = "reaction"

        if isinstance(grammar_id, str):
            if len(last_two) == 2 and last_two[0] == last_two[1] == grammar_id:
                grammar_id = "reaction"

        out = dict(p)
        if grammar_id is not None:
            out["grammar_id"] = grammar_id
        normalized.append(out)

        if isinstance(grammar_id, str):
            last_two.append(grammar_id)
            last_two = last_two[-2:]

    return {"panels": normalized}


def _build_gemini_client() -> GeminiClient:
    if not settings.google_cloud_project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured")

    return GeminiClient(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        text_model=settings.gemini_text_model,
        image_model=settings.gemini_image_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
        initial_backoff_seconds=settings.gemini_initial_backoff_seconds,
    )


def compute_scene_intent_extractor(source_text: str, genre: str | None = None, gemini: GeminiClient | None = None) -> dict:
    gemini = gemini or _build_gemini_client()

    prompt = (
        "Extract scene intent as JSON with keys: summary, mood, beats (list of short strings).\n\n"
        f"SCENE_TEXT:\n{source_text}\n"
    )
    if genre:
        prompt = f"GENRE: {genre}\n" + prompt

    text = gemini.generate_text(prompt)
    try:
        payload = json.loads(text)
    except Exception:
        payload = {"summary": text.strip(), "mood": None, "beats": []}

    payload.setdefault("_meta", {})
    payload["_meta"].update(
        {
            "model": getattr(gemini, "last_model", None),
            "usage": getattr(gemini, "last_usage", None),
        }
    )
    return payload


def compute_panel_plan_generator(
    scene_intent: dict,
    panel_count: int,
    gemini: GeminiClient | None = None,
) -> dict:
    gemini = gemini or _build_gemini_client()

    prompt = (
        "Generate a panel plan as JSON: {\"panels\": [{\"grammar_id\": <string>, \"story_function\": <string>}...]}\n"
        f"Constraints: exactly {panel_count} panels. Use grammar ids from this set: "
        "[establishing, dialogue_medium, emotion_closeup, action, reaction, object_focus].\n\n"
        f"SCENE_INTENT_JSON:\n{json.dumps(scene_intent, ensure_ascii=False)}\n"
    )

    text = gemini.generate_text(prompt)
    try:
        payload = json.loads(text)
    except Exception:
        payload = {"panels": [{"grammar_id": "dialogue_medium", "story_function": "progress"} for _ in range(panel_count)]}

    panels = payload.get("panels")
    if not isinstance(panels, list):
        panels = []

    panels = panels[:panel_count]
    while len(panels) < panel_count:
        panels.append({"grammar_id": "reaction", "story_function": "bridge"})

    out = {
        "panels": panels,
        "_meta": {"model": getattr(gemini, "last_model", None), "usage": getattr(gemini, "last_usage", None)},
    }
    return out


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


def compute_blind_test_evaluator(
    panel_semantics: dict,
    source_text: str,
    gemini: GeminiClient | None = None,
) -> dict:
    gemini = gemini or _build_gemini_client()

    prompt = (
        "Evaluate whether the panel semantics preserves the original scene. Return JSON with keys:"
        " coherence_score (0-10), faithfulness_score (0-10), notes (string).\n\n"
        f"SCENE_TEXT:\n{source_text}\n\n"
        f"PANEL_SEMANTICS_JSON:\n{json.dumps(panel_semantics, ensure_ascii=False)}\n"
    )

    text = gemini.generate_text(prompt)
    try:
        payload = json.loads(text)
    except Exception:
        payload = {"coherence_score": None, "faithfulness_score": None, "notes": text.strip()}

    if isinstance(payload, dict):
        payload.setdefault("_meta", {})
        payload["_meta"].update(
            {"model": getattr(gemini, "last_model", None), "usage": getattr(gemini, "last_usage", None)}
        )
    return payload


def run_scene_intent_extractor(
    db: Session,
    scene_id: uuid.UUID,
    genre: str | None = None,
    gemini: GeminiClient | None = None,
):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")

    payload = compute_scene_intent_extractor(scene.source_text, genre=genre, gemini=gemini)
    artifact = ArtifactService(db).create_artifact(scene_id=scene_id, type=ARTIFACT_SCENE_INTENT, payload=payload)
    logger.info(
        "node_complete node_name=SceneIntentExtractor scene_id=%s artifact_id=%s model=%s",
        scene_id,
        artifact.artifact_id,
        (payload.get("_meta") or {}).get("model"),
    )
    return artifact


def run_panel_plan_generator(
    db: Session,
    scene_id: uuid.UUID,
    panel_count: int,
    gemini: GeminiClient | None = None,
):
    svc = ArtifactService(db)
    intent = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
    if intent is None:
        raise ValueError("scene_intent artifact not found")

    payload = compute_panel_plan_generator(intent.payload, panel_count=panel_count, gemini=gemini)
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_PLAN, payload=payload)
    logger.info(
        "node_complete node_name=PanelPlanGenerator scene_id=%s artifact_id=%s model=%s",
        scene_id,
        artifact.artifact_id,
        (payload.get("_meta") or {}).get("model"),
    )
    return artifact


def run_panel_plan_normalizer(db: Session, scene_id: uuid.UUID):
    svc = ArtifactService(db)
    plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
    if plan is None:
        raise ValueError("panel_plan artifact not found")

    payload = compute_panel_plan_normalizer(plan.payload)
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_PLAN_NORMALIZED, payload=payload)
    logger.info(
        "node_complete node_name=PanelPlanNormalizer scene_id=%s artifact_id=%s",
        scene_id,
        artifact.artifact_id,
    )
    return artifact


def run_layout_template_resolver(db: Session, scene_id: uuid.UUID):
    svc = ArtifactService(db)
    plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED) or svc.get_latest_artifact(
        scene_id, ARTIFACT_PANEL_PLAN
    )
    if plan is None:
        raise ValueError("panel_plan artifact not found")

    payload = compute_layout_template_resolver(plan.payload)
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_LAYOUT_TEMPLATE, payload=payload)
    logger.info(
        "node_complete node_name=LayoutTemplateResolver scene_id=%s artifact_id=%s",
        scene_id,
        artifact.artifact_id,
    )
    return artifact


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
    characters = [
        {"character_id": str(c.character_id), "name": c.name, "description": c.description}
        for c in chars
    ]

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


def run_prompt_compiler(db: Session, scene_id: uuid.UUID, style_id: str = "default"):
    svc = ArtifactService(db)
    semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
    if semantics is None:
        raise ValueError("panel_semantics artifact not found")

    layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)
    if layout is None:
        raise ValueError("layout_template artifact not found")

    payload = compute_prompt_compiler(
        panel_semantics=semantics.payload,
        layout_template=layout.payload,
        style_id=style_id,
    )
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_SPEC, payload=payload)
    logger.info(
        "node_complete node_name=PromptCompiler scene_id=%s artifact_id=%s",
        scene_id,
        artifact.artifact_id,
    )
    return artifact


def run_image_renderer(db: Session, scene_id: uuid.UUID, gemini: GeminiClient | None = None):
    svc = ArtifactService(db)
    spec = svc.get_latest_artifact(scene_id, ARTIFACT_RENDER_SPEC)
    if spec is None:
        raise ValueError("render_spec artifact not found")

    gemini = gemini or _build_gemini_client()
    image_bytes, mime_type = gemini.generate_image(prompt=spec.payload["prompt"], model=None)

    store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
    _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

    image_row = ImageService(db).create_image(
        image_url=url,
        metadata={
            "mime_type": mime_type,
            "model": getattr(gemini, "last_model", None),
            "request_id": getattr(gemini, "last_request_id", None),
            "usage": getattr(gemini, "last_usage", None),
        },
    )

    payload = {
        "image_id": str(image_row.image_id),
        "image_url": url,
        "mime_type": mime_type,
        "_meta": {"model": getattr(gemini, "last_model", None), "usage": getattr(gemini, "last_usage", None)},
    }
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_RESULT, payload=payload)
    logger.info(
        "node_complete node_name=ImageRenderer scene_id=%s artifact_id=%s model=%s",
        scene_id,
        artifact.artifact_id,
        getattr(gemini, "last_model", None),
    )
    return artifact


def run_blind_test_evaluator(db: Session, scene_id: uuid.UUID, gemini: GeminiClient | None = None):
    svc = ArtifactService(db)
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")

    semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
    if semantics is None:
        raise ValueError("panel_semantics artifact not found")

    payload = compute_blind_test_evaluator(semantics.payload, source_text=scene.source_text, gemini=gemini)
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_BLIND_TEST_REPORT, payload=payload)
    logger.info(
        "node_complete node_name=BlindTestEvaluator scene_id=%s artifact_id=%s model=%s",
        scene_id,
        artifact.artifact_id,
        (payload.get("_meta") or {}).get("model") if isinstance(payload, dict) else None,
    )
    return artifact
