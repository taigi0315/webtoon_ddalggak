"""Transition type classification logic."""

from __future__ import annotations

import json
import uuid
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.constants import ARTIFACT_TRANSITION_MAP
from app.graphs.nodes.prompts.builders import _prompt_transition_classifier
from app.graphs.nodes.json_parser import _maybe_json_from_gemini
from app.graphs.nodes.utils import logger


class TransitionType(Enum):
    MOMENT_TO_MOMENT = "moment_to_moment"      # High emotional tension
    ACTION_TO_ACTION = "action_to_action"      # Standard plot progression
    SUBJECT_TO_SUBJECT = "subject_to_subject"  # Multi-character scene
    SCENE_TO_SCENE = "scene_to_scene"          # Time/space jump
    ASPECT_TO_ASPECT = "aspect_to_aspect"      # Mood/atmosphere
    NON_SEQUITUR = "non_sequitur"              # Experimental only


def run_transition_type_classifier(
    db: Session,
    scene_id: uuid.UUID,
    visual_beats: list[dict],
    gemini: GeminiClient | None = None,
) -> Any:
    """Classify transitions between visual beats and persist as artifact."""
    if gemini is None:
        logger.error("transition_classifier fail-fast: Gemini client missing (scene_id=%s)", scene_id)
        raise RuntimeError("transition_classifier requires Gemini client (fallback disabled)")

    # Check for existing artifact
    svc = ArtifactService(db)
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_TRANSITION_MAP)
    if existing:
        return existing

    if not visual_beats or len(visual_beats) < 2:
        logger.info(
            "transition_classifier skipped: insufficient beats (scene_id=%s, beats=%d); writing empty transitions",
            scene_id,
            len(visual_beats or []),
        )
        return svc.create_artifact(scene_id, ARTIFACT_TRANSITION_MAP, {"transitions": []})

    rendered_prompt = _prompt_transition_classifier(
        visual_beats_json=json.dumps(visual_beats, ensure_ascii=False, indent=2)
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not result or "transitions" not in result:
        logger.error(f"transition_classifier generation failed: invalid Gemini JSON (scene_id={scene_id})")
        raise RuntimeError("transition_classifier failed: Gemini returned invalid JSON")
        
    # Create versioned artifact
    payload = {"transitions": result["transitions"]}
    return svc.create_artifact(scene_id, ARTIFACT_TRANSITION_MAP, payload)
