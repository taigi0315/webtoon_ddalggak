"""Scene Optimizer node for budget management and style assignment."""

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

class OptimizedScene(BaseModel):
    scene_index: int
    summary: str
    source_text: str
    beats: list[dict] = Field(default_factory=list)
    image_style_id: str | None = "default"
    primary_tone: str | None = None

class SceneOptimizerResponse(BaseModel):
    action: str = "proceed"
    feedback: str | None = None
    scenes: list[OptimizedScene] = Field(default_factory=list)

    @field_validator("scenes")
    @classmethod
    def validate_scene_styles(cls, scenes: list[OptimizedScene]) -> list[OptimizedScene]:
        from app.config.loaders import has_image_style
        for scene in scenes:
            if scene.image_style_id and scene.image_style_id.lower() != "default":
                if not has_image_style(scene.image_style_id):
                    logger.warning(f"SceneOptimizer suggested unknown style '{scene.image_style_id}', falling back to default")
                    scene.image_style_id = "default"
        return scenes

def run_scene_optimizer(
    script: dict[str, Any] | None,
    tone_analysis: dict[str, Any] | None,
    max_scenes: int = 6,
    gemini: GeminiClient | None = None,
) -> dict[str, Any]:
    """Optimize script beats into final scenes based on budget and tone."""
    if not script or "visual_beats" not in script:
        return {"action": "proceed", "scenes": []}

    if gemini is None:
        logger.warning("Gemini client missing in SceneOptimizer, using simple grouping")
        # Fallback to simple grouping logic similar to old scene_splitter
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
                    "source_text": source_text,
                    "beats": batch,
                    "image_style_id": "default",
                }
            )
            if len(scenes) >= max_scenes:
                break
        return {"action": "proceed", "scenes": scenes}

    from app.config.loaders import load_image_styles_v1
    available_styles = [s.id for s in load_image_styles_v1().styles]

    rendered_prompt = render_prompt(
        "prompt_scene_optimizer",
        max_scenes=max_scenes,
        episode_intent=script.get("episode_intent", "Unknown"),
        beats_json=json.dumps(script.get("visual_beats", []), ensure_ascii=False, indent=2),
        tone_analysis_json=json.dumps(tone_analysis or {}, ensure_ascii=False, indent=2),
        available_styles=", ".join(available_styles),
    )

    raw_result = _maybe_json_from_gemini(gemini, rendered_prompt)
    if not raw_result or ("scenes" not in raw_result and raw_result.get("action") == "proceed"):
        logger.error("SceneOptimizer failed to produce optimized scenes")
        return {"action": "proceed", "scenes": []}
    
    try:
        validated = SceneOptimizerResponse.model_validate(raw_result)
        return validated.model_dump()
    except Exception as e:
        logger.error(f"SceneOptimizer validation error: {e}, raw_result={raw_result}")
        # Final fallback - return raw if possible, or empty structure
        return raw_result if isinstance(raw_result, dict) else {"action": "proceed", "scenes": []}
