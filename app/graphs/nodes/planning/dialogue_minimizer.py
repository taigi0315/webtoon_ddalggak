"""Dialogue minimization logic to enforce the 25% rule."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.prompts.builders import render_prompt
from app.graphs.nodes.json_parser import _maybe_json_from_gemini
from app.graphs.nodes.utils import logger


def run_dialogue_minimizer(
    db: Session,
    scene_id: uuid.UUID,
    visual_beats: list[dict],
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """Minimize dialogue to enforce the 25% rule and word count constraints."""
    if gemini is None or not visual_beats:
        return visual_beats

    minimized_beats = []
    for beat in visual_beats:
        dialogue = beat.get("dialogue")
        if not dialogue or dialogue == "None":
            minimized_beats.append(beat)
            continue

        rendered_prompt = render_prompt(
            "prompt_dialogue_minimizer",
            original_dialogue=dialogue,
            scene_context=beat.get("visual_action", ""),
            speaker=json.dumps(beat.get("characters", []), ensure_ascii=False),
        )

        result = _maybe_json_from_gemini(gemini, rendered_prompt)
        if result:
            beat["minimized_dialogue"] = result.get("minimized_dialogue", dialogue)
            beat["visual_cues"] = result.get("visual_cues", [])
            beat["can_be_silent"] = result.get("can_be_silent", False)
            # Update main dialogue field with minimized version
            beat["dialogue"] = beat["minimized_dialogue"]
        
        minimized_beats.append(beat)

    return minimized_beats
