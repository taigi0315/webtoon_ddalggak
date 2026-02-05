"""Character presence mapping logic for webtoon continuity."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.constants import ARTIFACT_PRESENCE_MAP, ARTIFACT_PANEL_SEMANTICS
from app.graphs.nodes.prompts.builders import render_prompt
from app.graphs.nodes.json_parser import _maybe_json_from_gemini
from app.graphs.nodes.utils import logger


def run_presence_mapper(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
) -> Any:
    """Map character presence across panels to ensure continuity and prevent 'vanishing'."""
    if gemini is None:
        return None

    # Check for existing artifact
    svc = ArtifactService(db)
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_PRESENCE_MAP)
    if existing:
        return existing

    # We need panel semantics to understand which characters are in which panels
    semantics_art = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
    if not semantics_art:
        logger.warning(f"Panel semantics missing for scene {scene_id}, cannot map presence")
        return None

    rendered_prompt = render_prompt(
        "prompt_presence_mapper",
        scene_data_json=json.dumps(semantics_art.payload, ensure_ascii=False, indent=2)
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not result or "presence_map" not in result:
        logger.error(f"Failed to map character presence for scene {scene_id}")
        return None
        
    payload = {"presence_map": result["presence_map"]}
    return svc.create_artifact(scene_id, ARTIFACT_PRESENCE_MAP, payload)
