"""Visual metaphor recommendation logic for webtoon narrative depth."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.constants import ARTIFACT_METAPHOR_DIRECTIONS, ARTIFACT_PANEL_SEMANTICS
from app.graphs.nodes.prompts.builders import render_prompt
from app.graphs.nodes.json_parser import _maybe_json_from_gemini
from app.graphs.nodes.utils import logger


def run_metaphor_recommender(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
) -> Any:
    """Recommend visual metaphors based on emotional intensity and character state."""
    if gemini is None:
        return None

    # Check for existing artifact
    svc = ArtifactService(db)
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_METAPHOR_DIRECTIONS)
    if existing:
        return existing

    # We need panel semantics to understand character emotions
    semantics_art = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
    if not semantics_art:
        logger.warning(f"Panel semantics missing for scene {scene_id}, cannot recommend metaphors")
        return None

    # Load lexicon
    try:
        with open("app/core/metaphor_lexicon.json", "r") as f:
            lexicon = json.load(f)
    except Exception:
        lexicon = []

    rendered_prompt = render_prompt(
        "prompt_metaphor_recommender",
        lexicon_json=json.dumps(lexicon, ensure_ascii=False, indent=2),
        semantics_json=json.dumps(semantics_art.payload, ensure_ascii=False, indent=2)
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not result or "metaphor_directions" not in result:
        logger.error(f"Failed to recommend metaphors for scene {scene_id}")
        return None
        
    payload = {"metaphor_directions": result["metaphor_directions"]}
    return svc.create_artifact(scene_id, ARTIFACT_METAPHOR_DIRECTIONS, payload)
