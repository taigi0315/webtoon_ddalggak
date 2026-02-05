"""Silent panel classification logic."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.utils import logger


def run_silent_panel_classifier(
    visual_beats: list[dict],
) -> list[dict]:
    """Identify panels that should have NO dialogue based on research heuristics."""
    if not visual_beats:
        return []

    for beat in visual_beats:
        action_complexity = beat.get("action_complexity", 1)
        beat_type = beat.get("beat_type", "initial")
        emotional_intensity = beat.get("emotional_intensity", 0.5)
        
        is_silent = False
        silence_type = None

        # Heuristic 1: Action Panels (Self-explanatory movements)
        if action_complexity == 1 and beat.get("silence_candidate"):
            is_silent = True
            silence_type = "action"
        
        # Heuristic 2: Reaction Panels (Psychological impact moment)
        elif beat_type == "release" and emotional_intensity > 0.8:
            is_silent = True
            silence_type = "reaction"

        # Force silence if DialogueMinimizer flagged it
        if beat.get("can_be_silent"):
            is_silent = True
            silence_type = silence_type or "minimized"

        beat["is_silent"] = is_silent
        beat["silence_type"] = silence_type
        
        if is_silent:
            beat["dialogue"] = None

    return visual_beats
