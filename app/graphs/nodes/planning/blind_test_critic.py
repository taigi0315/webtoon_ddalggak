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
    tone_analysis: dict[str, Any] | None = None,
    quality_signals: dict[str, Any] | None = None,
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    """Analyze blind test results and decide if rewrite is needed."""
    if not gemini:
        logger.error("blind_test_critic fail-fast: Gemini client missing")
        raise RuntimeError("blind_test_critic requires Gemini client (fallback disabled)")

    svc = ArtifactService(db)
    reports = []
    for sid in scene_ids:
        art = svc.get_latest_artifact(uuid.UUID(sid), ARTIFACT_BLIND_TEST_REPORT)
        if art:
            reports.append(art.payload)

    if not reports:
        logger.error("blind_test_critic fail-fast: no blind test reports available")
        raise ValueError("blind_test_critic requires blind_test_report artifacts")

    rendered_prompt = render_prompt(
        "prompt_blind_test_critic",
        story_text=story_text,
        episode_intent=script.get("episode_intent", "Unknown") if script else "Unknown",
        tone_analysis=json.dumps(tone_analysis or {}, ensure_ascii=False),
        quality_signals_json=json.dumps(quality_signals or {}, ensure_ascii=False),
        reports_json=json.dumps(reports, ensure_ascii=False, indent=2),
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not result or not isinstance(result, dict):
        logger.error("blind_test_critic generation failed: invalid Gemini JSON")
        raise RuntimeError("blind_test_critic failed: Gemini returned invalid JSON")
    return result
