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

def _validate_script_output(script: dict[str, Any], target_scene_count: int) -> dict[str, Any]:
    beats = script.get("visual_beats")
    if not isinstance(beats, list):
        logger.error(
            "script_writer validation failed: visual_beats is not a list (type=%s)",
            type(beats).__name__,
        )
        raise ValueError("script_writer invalid output: visual_beats must be a list")

    target = max(1, int(target_scene_count or 6))
    if len(beats) < target:
        logger.error(
            "script_writer validation failed: insufficient beats (actual=%d, target=%d)",
            len(beats),
            target,
        )
        raise ValueError(
            f"script_writer under-generated beats: got {len(beats)}, expected at least {target}"
        )

    for idx, beat in enumerate(beats, start=1):
        if not isinstance(beat, dict):
            logger.error(
                "script_writer validation failed: beat is not object (index=%d, type=%s)",
                idx,
                type(beat).__name__,
            )
            raise ValueError(f"script_writer invalid beat at index {idx}: not an object")
        action = str(beat.get("visual_action") or "").strip()
        if not action:
            logger.error(
                "script_writer validation failed: visual_action missing (index=%d, beat_type=%s)",
                idx,
                beat.get("beat_type"),
            )
            raise ValueError(f"script_writer invalid beat at index {idx}: visual_action is required")

    return script

def run_webtoon_script_writer(
    story_text: str,
    characters: list[dict],
    target_scene_count: int = 6,
    story_style: str | None = None,
    story_profile: dict | None = None,
    feedback: list[str] | None = None,
    history: list[dict] | None = None,
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    """Translate raw story to a visual webtoon script."""
    if gemini is None:
        logger.error(
            "script_writer fail-fast: missing Gemini client (target_scene_count=%d, story_len=%d)",
            max(1, int(target_scene_count or 6)),
            len((story_text or "").strip()),
        )
        raise RuntimeError("Gemini client is required (fail-fast mode); fallback is disabled")

    rendered_prompt = render_prompt(
        "prompt_script_writer",
        story_text=story_text,
        characters_json=json.dumps(characters, ensure_ascii=False, indent=2),
        target_scene_count=max(1, int(target_scene_count or 6)),
        story_style=story_style or "General",
        story_profile_json=json.dumps(story_profile, ensure_ascii=False, indent=2) if story_profile else None,
        feedback="\n".join(feedback) if feedback else None,
        history=json.dumps(history, ensure_ascii=False, indent=2) if history else None,
    )

    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not result or "visual_beats" not in result:
        logger.error(
            "script_writer generation failed: invalid/empty Gemini JSON (target_scene_count=%d, story_len=%d)",
            max(1, int(target_scene_count or 6)),
            len((story_text or "").strip()),
        )
        raise RuntimeError("script_writer failed: Gemini returned invalid or empty JSON")

    return _validate_script_output(result, target_scene_count)
