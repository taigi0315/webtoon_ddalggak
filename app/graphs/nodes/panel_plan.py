import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.config.loaders import load_grammar_library_v1
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from .constants import ARTIFACT_PANEL_PLAN, ARTIFACT_PANEL_PLAN_NORMALIZED, ARTIFACT_SCENE_INTENT
from .gemini import _build_gemini_client


logger = logging.getLogger(__name__)


def compute_panel_plan_generator(
    scene_intent: dict,
    panel_count: int,
    gemini: GeminiClient | None = None,
) -> dict:
    gemini = gemini or _build_gemini_client()

    grammar_ids = [g.id for g in load_grammar_library_v1().grammars]
    prompt = (
        "Generate a panel plan as JSON: {\"panels\": [{\"grammar_id\": <string>, \"story_function\": <string>}...]}\n"
        f"Constraints: exactly {panel_count} panels. Use grammar ids from this set: "
        f"{grammar_ids}.\n\n"
        f"SCENE_INTENT_JSON:\n{json.dumps(scene_intent, ensure_ascii=False)}\n"
    )

    text = gemini.generate_text(prompt)
    try:
        payload = json.loads(text)
    except Exception:
        payload = {
            "panels": [
                {"grammar_id": "dialogue_medium", "story_function": "progress"}
                for _ in range(panel_count)
            ]
        }

    panels = payload.get("panels")
    if not isinstance(panels, list):
        panels = []

    panels = panels[:panel_count]
    while len(panels) < panel_count:
        panels.append({"grammar_id": "reaction", "story_function": "bridge"})

    out = {
        "panels": panels,
        "_meta": {
            "model": getattr(gemini, "last_model", None),
            "usage": getattr(gemini, "last_usage", None),
        },
    }
    return out


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
    artifact = svc.create_artifact(
        scene_id=scene_id,
        type=ARTIFACT_PANEL_PLAN_NORMALIZED,
        payload=payload,
    )
    logger.info(
        "node_complete node_name=PanelPlanNormalizer scene_id=%s artifact_id=%s",
        scene_id,
        artifact.artifact_id,
    )
    return artifact
