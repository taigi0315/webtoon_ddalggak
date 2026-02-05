"""Studio Director node for unified tone analysis and production optimization."""

from __future__ import annotations

import json
from typing import Any
from pydantic import BaseModel, Field, field_validator

from app.services.vertex_gemini import GeminiClient
from ..utils import (
    logger,
    _maybe_json_from_gemini,
    render_prompt,
)

# Forbidden style-specific keywords that should not appear in Studio Director output
FORBIDDEN_STUDIO_DIRECTOR_KEYWORDS = [
    # Color palette keywords
    "color palette", "color scheme", "vibrant colors", "muted colors", "pastel colors",
    "warm colors", "cool colors", "monochrome", "black and white", "sepia",
    # Lighting keywords
    "lighting", "soft lighting", "harsh lighting", "dramatic lighting", "natural lighting",
    "studio lighting", "ambient lighting", "backlighting", "rim lighting",
    # Color temperature keywords
    "warm tones", "cool tones", "golden hour", "blue hour", "color temperature",
    # Atmospheric mood keywords (visual style-specific)
    "noir atmosphere", "romantic atmosphere", "gritty atmosphere", "dreamy atmosphere",
    "cinematic look", "film grain", "vintage look", "modern aesthetic",
]

class StudioScene(BaseModel):
    scene_index: int
    summary: str
    primary_tone: str
    image_style_id: str = "default"
    scene_emotion: str
    dramatic_intent: str
    beats: list[dict] = Field(default_factory=list)
    source_text: str

class StudioDirectorResponse(BaseModel):
    action: str = "proceed"
    feedback: str | None = None
    allocation_report: str | None = None
    scenes: list[StudioScene] = Field(default_factory=list)

    @field_validator("scenes")
    @classmethod
    def validate_scene_styles(cls, scenes: list[StudioScene]) -> list[StudioScene]:
        from app.config.loaders import has_image_style
        for scene in scenes:
            if scene.image_style_id and scene.image_style_id.lower() != "default":
                if not has_image_style(scene.image_style_id):
                    logger.error(
                        "studio_director validation failed: unknown image_style_id '%s' in scene %s",
                        scene.image_style_id,
                        scene.scene_index,
                    )
                    raise ValueError(f"Unknown image_style_id from studio_director: {scene.image_style_id}")
        return scenes


def _detect_style_keywords_in_studio_output(response: dict[str, Any]) -> list[str]:
    """
    Detect forbidden style-specific keywords in Studio Director output.
    
    Studio Director should focus on semantic emotional descriptions (scene_emotion, dramatic_intent)
    and NOT specify visual style characteristics like color palette or lighting.
    
    Args:
        response: Studio Director response dictionary
        
    Returns:
        List of detected forbidden keywords (empty if clean)
    """
    detected_keywords = []
    
    # Check scenes for style keywords
    scenes = response.get("scenes", [])
    for scene in scenes:
        # Check scene_emotion field
        scene_emotion = scene.get("scene_emotion", "").lower()
        for keyword in FORBIDDEN_STUDIO_DIRECTOR_KEYWORDS:
            if keyword.lower() in scene_emotion:
                detected_keywords.append(f"scene_emotion contains '{keyword}'")
        
        # Check dramatic_intent field
        dramatic_intent = scene.get("dramatic_intent", "").lower()
        for keyword in FORBIDDEN_STUDIO_DIRECTOR_KEYWORDS:
            if keyword.lower() in dramatic_intent:
                detected_keywords.append(f"dramatic_intent contains '{keyword}'")
        
        # Check summary field
        summary = scene.get("summary", "").lower()
        for keyword in FORBIDDEN_STUDIO_DIRECTOR_KEYWORDS:
            if keyword.lower() in summary:
                detected_keywords.append(f"summary contains '{keyword}'")
    
    return detected_keywords

def run_studio_director(
    script: dict[str, Any] | None,
    max_scenes: int = 6,
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    """Unified node for tone analysis, importance weighting, and budget-aware scene optimization."""
    if not script or "visual_beats" not in script:
        logger.error("studio_director fail-fast: missing script or visual_beats")
        raise ValueError("studio_director requires script with visual_beats")

    if gemini is None:
        logger.error("studio_director fail-fast: Gemini client missing")
        raise RuntimeError("studio_director requires Gemini client (fallback disabled)")

    from app.config.loaders import load_image_styles_v1
    from app.core.image_styles import get_style_semantic_hint
    
    styles = load_image_styles_v1().styles
    style_summary = "\n".join([f"- {s.id}: {get_style_semantic_hint(s.id)}" for s in styles])

    rendered_prompt = render_prompt(
        "prompt_studio_director",
        max_scenes=max_scenes,
        episode_intent=script.get("episode_intent", "Unknown"),
        beats_json=json.dumps(script.get("visual_beats", []), ensure_ascii=False, indent=2),
        style_library=style_summary,
    )

    raw_result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not raw_result:
        logger.error("studio_director generation failed: empty/invalid Gemini response")
        raise RuntimeError("studio_director failed: Gemini returned empty/invalid JSON")
    
    try:
        validated = StudioDirectorResponse.model_validate(raw_result)
        result_dict = validated.model_dump()
        
        # Detect style keywords in output
        detected_keywords = _detect_style_keywords_in_studio_output(result_dict)
        if detected_keywords:
            logger.warning(
                f"StudioDirector output contains style-specific keywords (should be style-agnostic): "
                f"{', '.join(set(detected_keywords))}"
            )
        
        return result_dict
    except Exception as e:
        logger.error(f"studio_director validation error: {e}, raw_result={raw_result}")
        raise RuntimeError("studio_director failed: response validation error") from e
