"""Vertical rhythm planning logic for webtoon pacing."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.constants import ARTIFACT_VERTICAL_RHYTHM, ARTIFACT_PANEL_PLAN
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
        return None

    # Check for existing artifact
    svc = ArtifactService(db)
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_VERTICAL_RHYTHM)
    if existing:
        return existing

    # We need the panel plan to determine rhythm
    panel_plan_art = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
    if not panel_plan_art:
        logger.warning(f"Panel plan missing for scene {scene_id}, cannot plan rhythm")
        return None

    rendered_prompt = render_prompt(
        "prompt_vertical_rhythm_planner",
        scene_data_json=json.dumps(panel_plan_art.payload, ensure_ascii=False, indent=2)
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not result or "rhythm_map" not in result:
        logger.error(f"Failed to plan vertical rhythm for scene {scene_id}")
        return None
        
    payload = {"rhythm_map": result["rhythm_map"]}
    return svc.create_artifact(scene_id, ARTIFACT_VERTICAL_RHYTHM, payload)
