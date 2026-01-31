"""Blind Test Critic node for narrative quality control."""

from __future__ import annotations

import json
from typing import Any
import uuid

from app.services.vertex_gemini import GeminiClient
from app.services.artifacts import ArtifactService
from ..utils import (
    logger,
    _maybe_json_from_gemini,
    render_prompt,
    ARTIFACT_BLIND_TEST_REPORT,
)

def run_blind_test_critic(
    db: Any, # Session
    story_text: str,
    script: dict[str, Any] | None,
    scene_ids: list[str],
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    """Analyze blind test results and decide if rewrite is needed."""
    if not gemini:
        return {"action": "proceed"}

    svc = ArtifactService(db)
    reports = []
    for sid in scene_ids:
        art = svc.get_latest_artifact(uuid.UUID(sid), ARTIFACT_BLIND_TEST_REPORT)
        if art:
            reports.append(art.payload)

    if not reports:
        return {"action": "proceed"}

    rendered_prompt = render_prompt(
        "prompt_blind_test_critic",
        story_text=story_text,
        episode_intent=script.get("episode_intent", "Unknown") if script else "Unknown",
        reports_json=json.dumps(reports, ensure_ascii=False, indent=2),
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    return result or {"action": "proceed"}
