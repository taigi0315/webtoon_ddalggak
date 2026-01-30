"""Dialogue extraction functions."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.request_context import log_context
from app.core.telemetry import trace_span
from app.services.artifacts import ArtifactService

from ..utils import (
    ARTIFACT_PANEL_SEMANTICS,
    ARTIFACT_DIALOGUE_SUGGESTIONS,
    _get_scene,
    _list_characters,
    _build_gemini_client,
    _generate_dialogue_script,
)


def run_dialogue_extractor(db: Session, scene_id: uuid.UUID):
    """Extract dialogue script from scene and panel semantics.

    Args:
        db: Database session
        scene_id: UUID of the scene

    Returns:
        Created dialogue_suggestions artifact
    """
    with log_context(node_name="dialogue_extractor", scene_id=scene_id):
        with trace_span("graph.dialogue_extractor", scene_id=str(scene_id)):
            scene = _get_scene(db, scene_id)
            panel_semantics = ArtifactService(db).get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
            characters = _list_characters(db, scene.story_id)
            character_names = [c.name for c in characters if c.name]
            panel_payload = panel_semantics.payload if panel_semantics else {}

            gemini = None
            try:
                gemini = _build_gemini_client()
            except Exception:  # noqa: BLE001
                gemini = None

            dialogue_script = _generate_dialogue_script(
                scene_id=scene_id,
                scene_text=scene.source_text,
                panel_semantics=panel_payload,
                character_names=character_names,
                gemini=gemini,
            )

            payload = {"dialogue_by_panel": dialogue_script.get("dialogue_by_panel", [])}
            return ArtifactService(db).create_artifact(
                scene_id=scene_id, type=ARTIFACT_DIALOGUE_SUGGESTIONS, payload=payload
            )
