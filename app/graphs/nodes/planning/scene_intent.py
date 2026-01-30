"""Scene intent extraction functions."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.metrics import track_graph_node
from app.core.request_context import log_context
from app.core.telemetry import trace_span
from app.db.models import Story
from app.services.artifacts import ArtifactService

from ..utils import (
    ARTIFACT_SCENE_INTENT,
    _get_scene,
    _list_characters,
    _summarize_text,
    _extract_setting,
    _extract_beats,
    _maybe_json_from_gemini,
    _prompt_scene_intent,
    GeminiClient,
)


def run_scene_intent_extractor(
    db: Session,
    scene_id: uuid.UUID,
    genre: str | None = None,
    gemini: GeminiClient | None = None,
):
    """Extract scene intent including pacing, emotional arc, and visual motifs.

    Args:
        db: Database session
        scene_id: UUID of the scene to analyze
        genre: Optional genre/style hint
        gemini: Optional GeminiClient for LLM-based extraction

    Returns:
        Created scene_intent artifact
    """
    with track_graph_node("scene_planning", "scene_intent_extractor"):
        with log_context(node_name="scene_intent_extractor", scene_id=scene_id):
            with trace_span("graph.scene_intent_extractor", scene_id=str(scene_id), genre=genre):
                scene = _get_scene(db, scene_id)
                story = db.get(Story, scene.story_id)
                characters = _list_characters(db, scene.story_id)
                character_names = [c.name for c in characters]
                summary = _summarize_text(scene.source_text)

            payload = {
                "summary": summary,
                "genre": genre or (story.default_story_style if story else None),
                "setting": _extract_setting(scene.source_text),
                "beats": _extract_beats(scene.source_text, max_beats=3),
                "characters": character_names,
                "logline": None,
                "pacing": "normal",
                "emotional_arc": None,
                "visual_motifs": [],
            }

            if gemini is not None:
                llm = _maybe_json_from_gemini(
                    gemini,
                    _prompt_scene_intent(scene.source_text, payload["genre"], character_names),
                )
                if isinstance(llm, dict):
                    payload = {**payload, **llm}

            return ArtifactService(db).create_artifact(
                scene_id=scene_id, type=ARTIFACT_SCENE_INTENT, payload=payload
            )
