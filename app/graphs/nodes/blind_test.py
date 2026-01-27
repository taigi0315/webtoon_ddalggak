import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.db.models import Scene
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from .constants import ARTIFACT_BLIND_TEST_REPORT, ARTIFACT_PANEL_SEMANTICS
from .gemini import _build_gemini_client


logger = logging.getLogger(__name__)


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
