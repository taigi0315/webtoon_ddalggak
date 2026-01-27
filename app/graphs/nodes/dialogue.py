import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.db.models import Scene
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from .constants import ARTIFACT_DIALOGUE_SUGGESTIONS
from .gemini import _build_gemini_client


logger = logging.getLogger(__name__)


def compute_dialogue_extraction(
    source_text: str,
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """Extract dialogue from scene text for chat bubble placement."""
    if not source_text or not source_text.strip():
        return []

    gemini = gemini or _build_gemini_client()
    prompt = (
        "Extract dialogue from this scene for webtoon chat bubbles. "
        "Return ONLY a JSON list of objects with keys: speaker, text, emotion (optional), panel_hint (optional integer 1-6).\n"
        "Rules:\n"
        "- Extract only actual spoken dialogue, not narration\n"
        "- speaker should be the character name\n"
        "- emotion can be: neutral, happy, sad, angry, surprised, thinking\n"
        "- panel_hint suggests which panel (1-6) this dialogue might fit in\n\n"
        f"SCENE_TEXT:\n{source_text}\n"
    )

    text = gemini.generate_text(prompt)
    dialogues: list[dict] = []
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                speaker = str(item.get("speaker") or "").strip()
                dialogue_text = str(item.get("text") or "").strip()
                if speaker and dialogue_text:
                    dialogues.append(
                        {
                            "speaker": speaker,
                            "text": dialogue_text,
                            "emotion": item.get("emotion") or "neutral",
                            "panel_hint": item.get("panel_hint"),
                        }
                    )
    except Exception:
        dialogues = []

    return dialogues


def run_dialogue_extractor(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
):
    """Extract dialogue suggestions from scene and store as artifact."""
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")

    dialogues = compute_dialogue_extraction(scene.source_text, gemini=gemini)

    payload = {
        "suggestions": dialogues,
        "_meta": {
            "model": getattr(gemini, "last_model", None) if gemini else None,
        },
    }

    artifact = ArtifactService(db).create_artifact(
        scene_id=scene_id,
        type=ARTIFACT_DIALOGUE_SUGGESTIONS,
        payload=payload,
    )
    logger.info(
        "node_complete node_name=DialogueExtractor scene_id=%s artifact_id=%s dialogue_count=%d",
        scene_id,
        artifact.artifact_id,
        len(dialogues),
    )
    return artifact
