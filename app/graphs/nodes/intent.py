import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.db.models import Scene
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from .constants import ARTIFACT_SCENE_INTENT
from .gemini import _build_gemini_client


logger = logging.getLogger(__name__)


def compute_scene_intent_extractor(
    source_text: str,
    genre: str | None = None,
    gemini: GeminiClient | None = None,
) -> dict:
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
    artifact = ArtifactService(db).create_artifact(
        scene_id=scene_id,
        type=ARTIFACT_SCENE_INTENT,
        payload=payload,
    )
    logger.info(
        "node_complete node_name=SceneIntentExtractor scene_id=%s artifact_id=%s model=%s",
        scene_id,
        artifact.artifact_id,
        (payload.get("_meta") or {}).get("model"),
    )
    return artifact
