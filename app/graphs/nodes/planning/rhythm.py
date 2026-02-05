"""Vertical rhythm planning logic for webtoon pacing."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.constants import (
    ARTIFACT_CLOSURE_PLAN,
    ARTIFACT_PANEL_PLAN,
    ARTIFACT_SCENE_INTENT,
    ARTIFACT_TRANSITION_MAP,
    ARTIFACT_VERTICAL_RHYTHM,
)
from app.graphs.nodes.prompts.builders import render_prompt
from app.graphs.nodes.json_parser import _maybe_json_from_gemini
from app.graphs.nodes.utils import logger


def run_vertical_rhythm_planner(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
) -> Any:
    """Plan vertical spacing (gutters) and panel widths to create narrative rhythm."""
    if gemini is None:
        logger.error("rhythm_planner fail-fast: Gemini client missing (scene_id=%s)", scene_id)
        raise RuntimeError("rhythm_planner requires Gemini client (fallback disabled)")

    # Check for existing artifact
    svc = ArtifactService(db)
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_VERTICAL_RHYTHM)
    if existing:
        return existing

    # We need the panel plan to determine rhythm
    panel_plan_art = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
    if not panel_plan_art:
        logger.error(f"rhythm_planner fail-fast: panel plan missing (scene_id={scene_id})")
        raise ValueError("rhythm_planner requires panel_plan artifact")

    transition_art = svc.get_latest_artifact(scene_id, ARTIFACT_TRANSITION_MAP)
    closure_art = svc.get_latest_artifact(scene_id, ARTIFACT_CLOSURE_PLAN)
    intent_art = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)

    rendered_prompt = render_prompt(
        "prompt_vertical_rhythm_planner",
        scene_data_json=json.dumps(panel_plan_art.payload, ensure_ascii=False, indent=2),
        transition_map_json=json.dumps((transition_art.payload if transition_art else {}), ensure_ascii=False, indent=2),
        closure_plan_json=json.dumps((closure_art.payload if closure_art else {}), ensure_ascii=False, indent=2),
        scene_intent_json=json.dumps((intent_art.payload if intent_art else {}), ensure_ascii=False, indent=2),
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not result or "rhythm_map" not in result:
        logger.error(f"rhythm_planner generation failed: invalid Gemini JSON (scene_id={scene_id})")
        raise RuntimeError("rhythm_planner failed: Gemini returned invalid JSON")
        
    payload = {"rhythm_map": result["rhythm_map"]}
    return svc.create_artifact(scene_id, ARTIFACT_VERTICAL_RHYTHM, payload)
