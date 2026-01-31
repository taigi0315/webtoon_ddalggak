"""Tone Auditor node for detecting mood shifts and assigning weights."""

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

class BeatAnalysis(BaseModel):
    beat_index: int
    tone: str
    weight: float = Field(ge=0.0, le=1.0)
    tone_shift: bool = False

class MoodSegment(BaseModel):
    start_index: int
    end_index: int
    dominant_tone: str
    suggested_style_id: str | None = "default"

class ToneAuditorResponse(BaseModel):
    beat_analysis: list[BeatAnalysis]
    mood_segments: list[MoodSegment] = Field(default_factory=list)

    @field_validator("mood_segments")
    @classmethod
    def validate_styles(cls, segments: list[MoodSegment]) -> list[MoodSegment]:
        from app.config.loaders import has_image_style
        for seg in segments:
            if seg.suggested_style_id and seg.suggested_style_id.lower() != "default":
                if not has_image_style(seg.suggested_style_id):
                    logger.warning(f"ToneAuditor suggested unknown style '{seg.suggested_style_id}', falling back to default")
                    seg.suggested_style_id = "default"
        return segments

def run_tone_auditor(
    script: dict[str, Any] | None,
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    """Analyze script beats for tone shifts and narrative weight."""
    if not script or "visual_beats" not in script:
        return {"beat_analysis": [], "mood_segments": []}

    if gemini is None:
        logger.warning("Gemini client missing in ToneAuditor, returning dummy weights")
        beats = script.get("visual_beats", [])
        return {
            "beat_analysis": [
                {
                    "beat_index": b.get("beat_index", i+1),
                    "tone": "Neutral",
                    "weight": 0.5,
                    "tone_shift": False
                } for i, b in enumerate(beats)
            ],
            "mood_segments": []
        }

    from app.config.loaders import load_image_styles_v1
    from app.core.image_styles import get_style_semantic_hint
    
    styles = load_image_styles_v1().styles
    style_summary = "\n".join([f"- {s.id}: {get_style_semantic_hint(s.id)}" for s in styles])

    rendered_prompt = render_prompt(
        "prompt_tone_auditor",
        episode_intent=script.get("episode_intent", "Unknown"),
        beats_json=json.dumps(script.get("visual_beats", []), ensure_ascii=False, indent=2),
        style_library=style_summary,
    )

    raw_result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not raw_result:
        logger.error("ToneAuditor failed to analyze tones")
        return {"beat_analysis": [], "mood_segments": []}
        
    try:
        validated = ToneAuditorResponse.model_validate(raw_result)
        return validated.model_dump()
    except Exception as e:
        logger.error(f"ToneAuditor validation error: {e}, raw_result={raw_result}")
        # Final fallback - return raw if possible, or empty structure
        return raw_result if isinstance(raw_result, dict) else {"beat_analysis": [], "mood_segments": []}
