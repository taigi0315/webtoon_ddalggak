"""Webtoon script writing logic."""

from __future__ import annotations

import json
from typing import Any

from app.services.vertex_gemini import GeminiClient
from ..utils import (
    logger,
    _maybe_json_from_gemini,
    render_prompt,
)

def run_webtoon_script_writer(
    story_text: str,
    characters: list[dict],
    story_style: str | None = None,
    feedback: list[str] | None = None,
    history: list[dict] | None = None,
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    """Translate raw story to a visual webtoon script."""
    if gemini is None:
        logger.warning("Gemini client missing, returning dummy script")
        return {
            "episode_intent": "Generic buildup",
            "visual_beats": [{"beat_index": 1, "visual_action": story_text}]
        }

    rendered_prompt = render_prompt(
        "prompt_script_writer",
        story_text=story_text,
        characters_json=json.dumps(characters, ensure_ascii=False, indent=2),
        story_style=story_style or "General",
        feedback="\n".join(feedback) if feedback else None,
        history=json.dumps(history, ensure_ascii=False, indent=2) if history else None,
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not result or "visual_beats" not in result:
        logger.error("Failed to generate webtoon script, falling back to original text")
        return {
            "episode_intent": "Fallback intent",
            "visual_beats": [{"beat_index": 1, "visual_action": story_text}]
        }
        
    return result
