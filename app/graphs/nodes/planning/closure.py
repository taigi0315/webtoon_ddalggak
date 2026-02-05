"""Closure planning logic for webtoon gutters."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.constants import ARTIFACT_CLOSURE_PLAN, ARTIFACT_TRANSITION_MAP
from app.graphs.nodes.prompts.builders import _prompt_closure_planner
from app.graphs.nodes.json_parser import _maybe_json_from_gemini
from app.graphs.nodes.utils import logger


def run_closure_planner(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
) -> Any:
    """Explicitly plan what the reader infers in each gutter."""
    if gemini is None:
        return None

    # Check for existing artifact
    svc = ArtifactService(db)
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_CLOSURE_PLAN)
    if existing:
        return existing

    # We need the transition map to plan closure
    transition_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_TRANSITION_MAP)
    if not transition_artifact:
        logger.warning(f"Transition map missing for scene {scene_id}, cannot plan closure")
        return None

    transitions = transition_artifact.payload.get("transitions", [])
    closure_plans = []

    for trans in transitions:
        rendered_prompt = _prompt_closure_planner(
            panel_pair_json=json.dumps(trans, ensure_ascii=False, indent=2)
        )
        result = _maybe_json_from_gemini(gemini, rendered_prompt)
        if result:
            # Apply Heuristic Rules from research
            inference_difficulty = result.get("inference_difficulty", 0.0)
            closure_type = result.get("closure_type", "spatial")
            
            # Rule: If inference_difficulty > 0.8 -> Suggest adding panel
            if inference_difficulty > 0.8:
                result["explicit_if_needed"] = True
                result["recommendation"] = "Add intermediate panel to bridge high-difficulty jump"
            
            closure_plans.append(result)

    if not closure_plans:
        return None

    payload = {"closure_plans": closure_plans}
    return svc.create_artifact(scene_id, ARTIFACT_CLOSURE_PLAN, payload)
