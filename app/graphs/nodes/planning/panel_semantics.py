"""Panel semantics filling functions."""

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
    ARTIFACT_PANEL_PLAN,
    ARTIFACT_PANEL_PLAN_NORMALIZED,
    ARTIFACT_LAYOUT_TEMPLATE,
    ARTIFACT_PANEL_SEMANTICS,
    _get_scene,
    _list_characters,
    _heuristic_panel_semantics,
    _maybe_json_from_gemini,
    _prompt_panel_semantics,
    GeminiClient,
)


def run_panel_semantic_filler(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
):
    """Fill detailed semantics for each panel in the plan.

    Args:
        db: Database session
        scene_id: UUID of the scene
        gemini: Optional GeminiClient for LLM-based filling

    Returns:
        Created panel_semantics artifact
    """
    with track_graph_node("scene_planning", "panel_semantic_filler"):
        with log_context(node_name="panel_semantic_filler", scene_id=scene_id):
            with trace_span("graph.panel_semantic_filler", scene_id=str(scene_id)):
                svc = ArtifactService(db)
                scene = _get_scene(db, scene_id)
                story = db.get(Story, scene.story_id)
                characters = _list_characters(db, scene.story_id)

            scene_intent_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
            scene_intent = scene_intent_artifact.payload if scene_intent_artifact else None
            panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
            if panel_plan is None:
                panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
            layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)

            if panel_plan is None or layout is None:
                raise ValueError("panel_plan and layout_template artifacts are required")

            payload = _heuristic_panel_semantics(
                scene_text=scene.source_text,
                panel_plan=panel_plan.payload,
                layout_template=layout.payload,
                characters=characters,
                scene_intent=scene_intent,
            )

            if gemini is not None:
                llm = _maybe_json_from_gemini(
                    gemini,
                    _prompt_panel_semantics(
                        scene.source_text,
                        panel_plan.payload,
                        layout.payload,
                        characters,
                        scene_intent=scene_intent,
                    ),
                )
                if isinstance(llm, dict) and isinstance(llm.get("panels"), list):
                    payload["panels"] = llm["panels"]

            return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_SEMANTICS, payload=payload)
