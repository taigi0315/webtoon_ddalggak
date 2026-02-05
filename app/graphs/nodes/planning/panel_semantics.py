"""Panel semantics filling functions."""

from __future__ import annotations

import uuid
import logging

from sqlalchemy.orm import Session

from app.core.metrics import track_graph_node
from app.core.request_context import log_context
from app.core.telemetry import trace_span
from app.db.models import Story
from app.services.artifacts import ArtifactService

from ..utils import (
    ARTIFACT_SCENE_INTENT,
    ARTIFACT_PANEL_PLAN,
    ARTIFACT_PANEL_PLAN_NORMALIZED,
    ARTIFACT_LAYOUT_TEMPLATE,
    ARTIFACT_PANEL_SEMANTICS,
    _get_scene,
    _list_characters,
    _maybe_json_from_gemini,
    _prompt_panel_semantics,
    GeminiClient,
)

logger = logging.getLogger(__name__)

# Style keywords that should NOT appear in Cinematographer output
FORBIDDEN_CINEMATOGRAPHER_KEYWORDS = [
    # Lighting quality
    "soft lighting", "harsh lighting", "dramatic lighting", "diffused lighting",
    "natural lighting", "artificial lighting", "ambient lighting",
    # Color temperature
    "warm", "cool", "golden", "blue tones", "warm tones", "cool tones",
    "color temperature", "golden hour",
    # Atmospheric mood
    "tense", "romantic", "mysterious", "ominous", "cheerful", "melancholic",
    "atmospheric", "moody", "dreamy", "ethereal", "gritty",
    # Color palette
    "vibrant colors", "muted colors", "pastel", "saturated", "desaturated",
    "color palette", "color scheme",
]


def _detect_style_keywords_in_panel_semantics(panel_semantics: dict) -> list[str]:
    """Detect forbidden style keywords in panel semantics output.
    
    Args:
        panel_semantics: Panel semantics dict from LLM
        
    Returns:
        List of detected forbidden keywords
    """
    detected = []
    
    panels = panel_semantics.get("panels", [])
    if not isinstance(panels, list):
        return detected
    
    for panel_idx, panel in enumerate(panels, start=1):
        if not isinstance(panel, dict):
            continue
        
        # Check description field
        description = panel.get("description", "")
        if isinstance(description, str):
            description_lower = description.lower()
            for keyword in FORBIDDEN_CINEMATOGRAPHER_KEYWORDS:
                if keyword.lower() in description_lower:
                    detected.append(f"Panel {panel_idx} description: '{keyword}'")
        
        # Check lighting field (should not exist)
        if "lighting" in panel:
            detected.append(f"Panel {panel_idx}: 'lighting' field present (should be removed)")
        
        # Check atmosphere_keywords field (should not exist)
        if "atmosphere_keywords" in panel:
            detected.append(f"Panel {panel_idx}: 'atmosphere_keywords' field present (should be removed)")
    
    return detected



def run_panel_semantic_filler(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
):
    """Fill detailed semantics for each panel in the plan.

    Args:
        db: Database session
        scene_id: UUID of the scene
        gemini: Optional GeminiClient for LLM-based filling

    Returns:
        Created panel_semantics artifact
    """
    with track_graph_node("scene_planning", "panel_semantic_filler"):
        with log_context(node_name="panel_semantic_filler", scene_id=scene_id):
            with trace_span("graph.panel_semantic_filler", scene_id=str(scene_id)):
                svc = ArtifactService(db)
                scene = _get_scene(db, scene_id)
                story = db.get(Story, scene.story_id)
                characters = _list_characters(db, scene.story_id)

            scene_intent_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
            scene_intent = scene_intent_artifact.payload if scene_intent_artifact else None
            panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
            if panel_plan is None:
                panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
            layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)

            if panel_plan is None or layout is None:
                raise ValueError("panel_plan and layout_template artifacts are required")

            if gemini is None:
                logger.error("panel_semantics fail-fast: Gemini client missing (scene_id=%s)", scene_id)
                raise RuntimeError("panel_semantics requires Gemini client (fallback disabled)")

            llm = _maybe_json_from_gemini(
                gemini,
                _prompt_panel_semantics(
                    scene.source_text,
                    panel_plan.payload,
                    layout.payload,
                    characters,
                    scene_intent=scene_intent,
                ),
            )
            if not isinstance(llm, dict) or not isinstance(llm.get("panels"), list):
                logger.error("panel_semantics generation failed: invalid Gemini JSON (scene_id=%s)", scene_id)
                raise RuntimeError("panel_semantics failed: Gemini returned invalid JSON")

            payload = {
                "panels": llm["panels"],
            }

            # Post-processing: Detect style keywords in LLM output
            detected_keywords = _detect_style_keywords_in_panel_semantics(payload)
            if detected_keywords:
                logger.warning(
                    f"Cinematographer output for scene {scene_id} contains style keywords "
                    f"(should be handled by Art Director): {detected_keywords}"
                )

            return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_SEMANTICS, payload=payload)
