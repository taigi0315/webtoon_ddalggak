"""Blind test evaluation functions."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.request_context import log_context
from app.core.metrics import record_blind_test_result, track_graph_node
from app.core.telemetry import trace_span
from app.services.artifacts import ArtifactService

from ..utils import (
    ARTIFACT_PANEL_SEMANTICS,
    ARTIFACT_BLIND_TEST_REPORT,
    _get_scene,
    _panel_semantics_text,
    _rough_similarity,
    _maybe_json_from_gemini,
    _prompt_blind_reader,
    _prompt_comparator,
    GeminiClient,
)


def run_blind_test_evaluator(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
):
    """Evaluate panel semantics using blind test methodology.

    Args:
        db: Database session
        scene_id: UUID of the scene
        gemini: Optional GeminiClient for LLM-based evaluation

    Returns:
        Created blind_test_report artifact
    """
    with track_graph_node("scene_planning", "blind_test_evaluator"):
        with log_context(node_name="blind_test_evaluator", scene_id=scene_id):
            with trace_span("graph.blind_test_evaluator", scene_id=str(scene_id)):
                svc = ArtifactService(db)
                scene = _get_scene(db, scene_id)
                panel_semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
                if panel_semantics is None:
                    raise ValueError("panel_semantics artifact not found")

                semantics_text = _panel_semantics_text(panel_semantics.payload)
                reconstructed = semantics_text
                score = _rough_similarity(scene.source_text, semantics_text)
                comparison = f"Similarity score: {score:.2f}"
                scores = None
                failure_points = []
                repair_suggestions = []

                # New fields for visual storytelling evaluation
                emotional_takeaway = None
                visual_observations = []

                if gemini is None:
                    raise RuntimeError("blind_test_evaluator requires Gemini client (fallback disabled)")

                blind_reading = _maybe_json_from_gemini(
                    gemini,
                    _prompt_blind_reader(panel_semantics.payload),
                )
                if not blind_reading or not isinstance(blind_reading, dict):
                    raise RuntimeError("blind_test_evaluator failed: blind_reader returned invalid JSON")

                reconstructed = blind_reading.get("reconstructed_story", reconstructed)
                emotional_takeaway = blind_reading.get("emotional_takeaway")
                visual_observations = blind_reading.get("visual_storytelling_observations", [])

                comparison_result = _maybe_json_from_gemini(
                    gemini,
                    _prompt_comparator(scene.source_text, blind_reading),
                )
                if not comparison_result or not isinstance(comparison_result, dict):
                    raise RuntimeError("blind_test_evaluator failed: comparator returned invalid JSON")

                comparison = comparison_result.get("comparison", comparison)
                scores = comparison_result.get("scores")
                score = float(comparison_result.get("weighted_score", score))
                failure_points = comparison_result.get("failure_points", [])
                repair_suggestions = comparison_result.get("repair_suggestions", [])

                payload = {
                    "reconstructed_story": reconstructed,
                    "comparison": comparison,
                    "emotional_takeaway": emotional_takeaway,
                    "visual_storytelling_observations": visual_observations,
                    "score": score,
                    "passed": score >= 0.25,
                    "scores": scores,
                    "failure_points": failure_points,
                    "repair_suggestions": repair_suggestions,
                }
                record_blind_test_result(payload["passed"])
                return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_BLIND_TEST_REPORT, payload=payload)
