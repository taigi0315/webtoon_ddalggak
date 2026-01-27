from __future__ import annotations

import json
import re
import uuid
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.loaders import load_grammar_to_prompt_mapping_v1, load_qc_rules_v1, select_template
from app.core.settings import settings
from app.db.models import Character, CharacterReferenceImage, Scene
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
ARTIFACT_QC_REPORT = "qc_report"


def compute_prompt_compiler(
    panel_semantics: dict,
    layout_template: dict,
    style_id: str = "default",
    story_style_id: str | None = None,
    image_style_id: str | None = None,
) -> dict:
    mapping = load_grammar_to_prompt_mapping_v1().mapping

    panels = panel_semantics.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ValueError("panel_semantics.panels must be a non-empty list")

    image_style_id = image_style_id or style_id or "default"

    parts: list[str] = []
    parts.append(f"STYLE: {image_style_id}")
    if story_style_id:
        parts.append(f"STORY_STYLE: {story_style_id}")
    if image_style_id:
        parts.append(f"IMAGE_STYLE: {image_style_id}")

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
    return {
        "style_id": image_style_id,
        "story_style_id": story_style_id,
        "image_style_id": image_style_id,
        "prompt": prompt,
    }


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


def compute_scene_chunker(
    source_text: str,
    max_scenes: int = 6,
    gemini: GeminiClient | None = None,
) -> list[str]:
    if not source_text or not source_text.strip():
        raise ValueError("source_text is required for auto-chunking")

    gemini = gemini or _build_gemini_client()
    prompt = (
        "Split the story into distinct scenes. Return ONLY a JSON list of scene strings.\n"
        "Rules:\n"
        "- Each scene should be 1-4 sentences.\n"
        f"- Max scenes: {max_scenes}.\n"
        "- Do not include numbering or extra keys.\n\n"
        f"STORY_TEXT:\n{source_text}\n"
    )

    text = gemini.generate_text(prompt)
    chunks: list[str] = []
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            chunks = [str(item).strip() for item in payload if str(item).strip()]
    except Exception:
        chunks = []

    if len(chunks) <= 1:
        chunks = []

    if not chunks:
        # Fallback: split by paragraphs, then by sentences.
        paragraphs = [p.strip() for p in source_text.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            chunks = paragraphs
        else:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", source_text.strip()) if s.strip()]
            if sentences:
                size = 2
                chunks = [" ".join(sentences[i : i + size]) for i in range(0, len(sentences), size)]

    if max_scenes and len(chunks) > max_scenes:
        chunks = chunks[:max_scenes]

    return chunks


def compute_qc_report(panel_plan: dict, panel_semantics: dict) -> dict:
    rules = load_qc_rules_v1()
    panels = panel_semantics.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ValueError("panel_semantics.panels must be a non-empty list")

    issues: list[dict] = []
    total = len(panels)

    closeup_count = 0
    dialogue_count = 0
    last_three: list[str | None] = []
    has_establishing = False
    establishing_missing_env = False

    env_keywords = {kw.lower() for kw in rules.environment_keywords}

    for panel in panels:
        grammar_id = panel.get("grammar_id")
        grammar_str = grammar_id if isinstance(grammar_id, str) else ""
        text = panel.get("text") or ""

        if "closeup" in grammar_str or "close_up" in grammar_str:
            closeup_count += 1

        if "dialogue" in grammar_str:
            dialogue_count += 1

        if grammar_str == "establishing":
            has_establishing = True
            if rules.require_environment_on_establishing:
                text_lower = text.lower() if isinstance(text, str) else ""
                if not any(keyword in text_lower for keyword in env_keywords):
                    establishing_missing_env = True

        last_three.append(grammar_str if grammar_str else None)
        last_three = last_three[-rules.repeated_framing_run_length :]
        if (
            len(last_three) == rules.repeated_framing_run_length
            and last_three[0]
            and last_three[0] == last_three[1] == last_three[-1]
        ):
            issues.append(
                {
                    "code": "repeated_framing",
                    "severity": "medium",
                    "message": f"Same framing repeated {rules.repeated_framing_run_length} times in a row: {last_three[0]}",
                    "suggested_reroute": "panel_plan",
                }
            )
            last_three = []

    if total >= 4 and closeup_count / total > rules.closeup_ratio_max:
        issues.append(
            {
                "code": "too_many_closeups",
                "severity": "high",
                "message": "Closeup panels exceed allowed ratio.",
                "suggested_reroute": "panel_plan",
            }
        )

    if total >= 3 and dialogue_count / total > rules.dialogue_ratio_max:
        issues.append(
            {
                "code": "over_dialogue_density",
                "severity": "medium",
                "message": "Dialogue-heavy panels exceed allowed ratio.",
                "suggested_reroute": "panel_semantics",
            }
        )

    if has_establishing and establishing_missing_env:
        issues.append(
            {
                "code": "missing_environment",
                "severity": "high",
                "message": "Establishing panel lacks clear environment description.",
                "suggested_reroute": "panel_semantics",
            }
        )

    passed = len(issues) == 0
    return {"passed": passed, "issues": issues, "panel_count": total}


def _build_gemini_client() -> GeminiClient:
    if not settings.google_cloud_project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured")

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


def run_prompt_compiler(db: Session, scene_id: uuid.UUID, style_id: str = "default"):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")

    svc = ArtifactService(db)
    semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
    if semantics is None:
        raise ValueError("panel_semantics artifact not found")

    layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)
    if layout is None:
        raise ValueError("layout_template artifact not found")

    story_style_id = "default"
    image_style_id = "default"
    if scene.story is not None:
        story_style_id = scene.story.default_story_style or "default"
        image_style_id = scene.story.default_image_style or "default"

    if scene.story_style_override:
        story_style_id = scene.story_style_override
    if scene.image_style_override:
        image_style_id = scene.image_style_override

    if style_id:
        image_style_id = style_id

    payload = compute_prompt_compiler(
        panel_semantics=semantics.payload,
        layout_template=layout.payload,
        style_id=image_style_id,
        story_style_id=story_style_id,
        image_style_id=image_style_id,
    )
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_SPEC, payload=payload)
    logger.info(
        "node_complete node_name=PromptCompiler scene_id=%s artifact_id=%s",
        scene_id,
        artifact.artifact_id,
    )
    return artifact


def run_qc_checker(db: Session, scene_id: uuid.UUID):
    svc = ArtifactService(db)
    plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
    if plan is None:
        raise ValueError("panel_plan artifact not found")

    semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
    if semantics is None:
        raise ValueError("panel_semantics artifact not found")

    payload = compute_qc_report(plan.payload, semantics.payload)
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_QC_REPORT, payload=payload)
    logger.info(
        "node_complete node_name=QualityControl scene_id=%s artifact_id=%s passed=%s",
        scene_id,
        artifact.artifact_id,
        payload.get("passed"),
    )
    return artifact


def run_image_renderer(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
    reason: str | None = None,
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
    if reason:
        payload["regenerate_reason"] = reason
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
