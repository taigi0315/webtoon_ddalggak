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
                    logger.warning(f"StudioDirector suggested unknown style '{scene.image_style_id}', falling back to default")
                    scene.image_style_id = "default"
        return scenes

def run_studio_director(
    script: dict[str, Any] | None,
    max_scenes: int = 6,
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    """Unified node for tone analysis, importance weighting, and budget-aware scene optimization."""
    if not script or "visual_beats" not in script:
        return {"action": "proceed", "scenes": []}

    if gemini is None:
        logger.warning("Gemini client missing in StudioDirector, using fallback splitter")
        # Reuse minimalist grouping if no LLM
        beats = script.get("visual_beats", [])
        total_beats = len(beats)
        beats_per_scene = max(1, (total_beats + max_scenes - 1) // max_scenes)
        
        scenes: list[dict] = []
        for i in range(0, total_beats, beats_per_scene):
            batch = beats[i : i + beats_per_scene]
            idx = len(scenes) + 1
            text_parts = []
            for b in batch:
                part = f"BEAT: {b.get('visual_action', '')}"
                if b.get("dialogue"):
                    part += f"\nDIALOGUE: {b.get('dialogue')}"
                if b.get("sfx"):
                    part += f"\nSFX: {b.get('sfx')}"
                text_parts.append(part)
            
            source_text = "\n\n".join(text_parts)
            scenes.append(
                {
                    "scene_index": idx,
                    "summary": batch[0].get("visual_action", "")[:100],
                    "primary_tone": "Neutral",
                    "image_style_id": "default",
                    "scene_emotion": "Neutral",
                    "dramatic_intent": "Progress the story",
                    "source_text": source_text,
                    "beats": batch,
                }
            )
            if len(scenes) >= max_scenes:
                break
        return {"action": "proceed", "scenes": scenes}

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
        logger.error("StudioDirector failed to produce response")
        return {"action": "proceed", "scenes": []}
    
    try:
        validated = StudioDirectorResponse.model_validate(raw_result)
        return validated.model_dump()
    except Exception as e:
        logger.error(f"StudioDirector validation error: {e}, raw_result={raw_result}")
        # Return what we can or empty
        return raw_result if isinstance(raw_result, dict) else {"action": "proceed", "scenes": []}
