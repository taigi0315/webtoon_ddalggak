"""Story seed expansion / population logic."""

from __future__ import annotations

from typing import Any

from app.services.vertex_gemini import GeminiClient
from ..utils import logger, _maybe_json_from_gemini, render_prompt


def _validate_story_profile(raw: dict[str, Any], max_characters: int) -> dict[str, Any]:
    expanded = str(raw.get("expanded_story_text") or "").strip()
    if not expanded:
        logger.error("story_populator validation failed: expanded_story_text is empty")
        raise ValueError("story_populator invalid output: expanded_story_text is required")

    characters = raw.get("character_plan")
    if not isinstance(characters, list):
        logger.error(
            "story_populator validation failed: character_plan is not a list (type=%s)",
            type(characters).__name__,
        )
        raise ValueError("story_populator invalid output: character_plan must be a list")

    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    hard_max = max(1, int(max_characters))
    for char in characters:
        if not isinstance(char, dict):
            continue
        name = str(char.get("name") or "").strip()
        if not name:
            continue
        if name.lower() in {"narrator", "voiceover", "voice-over", "i"}:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(
            {
                "name": name,
                "role": char.get("role", "secondary"),
                "gender": char.get("gender", "male"),
                "age_range": char.get("age_range", "young_adult"),
                "description": char.get("description"),
                "appearance_hint": char.get("appearance_hint"),
                "outfit_hint": char.get("outfit_hint"),
            }
        )
        if len(cleaned) >= hard_max:
            break

    if not cleaned:
        logger.error("story_populator validation failed: character_plan is empty after cleanup")
        raise ValueError("story_populator invalid output: character_plan must include at least one character")

    recommended = int(raw.get("max_characters_recommended") or len(cleaned))
    recommended = max(1, min(recommended, hard_max))

    return {
        "seed_intent": str(raw.get("seed_intent") or "").strip(),
        "expanded_story_text": expanded,
        "character_plan": cleaned,
        "fidelity_notes": raw.get("fidelity_notes") if isinstance(raw.get("fidelity_notes"), list) else [],
        "max_characters_recommended": recommended,
    }


def run_story_populator(
    story_text: str,
    target_scene_count: int,
    max_characters: int,
    story_style: str | None = None,
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    if gemini is None:
        logger.error("story_populator fail-fast: Gemini client missing")
        raise RuntimeError("story_populator requires Gemini client (fallback disabled)")

    rendered_prompt = render_prompt(
        "prompt_story_populator",
        story_text=story_text,
        target_scene_count=max(1, int(target_scene_count or 6)),
        max_characters=max(1, int(max_characters)),
        story_style=story_style or "General",
    )
    logger.info(
        "story_populator llm request started (target_scene_count=%s, max_characters=%s)",
        max(1, int(target_scene_count or 6)),
        max(1, int(max_characters)),
    )
    result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not isinstance(result, dict):
        logger.error("story_populator generation failed: invalid/empty Gemini JSON")
        raise RuntimeError("story_populator failed: Gemini returned invalid JSON")

    return _validate_story_profile(result, max_characters=max_characters)

