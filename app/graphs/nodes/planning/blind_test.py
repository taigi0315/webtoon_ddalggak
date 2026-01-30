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
    _prompt_blind_test,
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

                if gemini is not None:
                    # Try two-stage blind test process
                    two_stage_success = False

                    # Stage 1: Blind reader reconstructs story
                    blind_reading = _maybe_json_from_gemini(
                        gemini,
                        _prompt_blind_reader(panel_semantics.payload),
                    )

                    if blind_reading and isinstance(blind_reading, dict):
                        reconstructed = blind_reading.get("reconstructed_story", reconstructed)

                        # Stage 2: Comparator scores the reconstruction
                        comparison_result = _maybe_json_from_gemini(
                            gemini,
                            _prompt_comparator(scene.source_text, blind_reading),
                        )

                        if comparison_result and isinstance(comparison_result, dict):
                            two_stage_success = True
                            comparison = comparison_result.get("comparison", comparison)
                            scores = comparison_result.get("scores")
                            score = float(comparison_result.get("weighted_score", score))
                            failure_points = comparison_result.get("failure_points", [])
                            repair_suggestions = comparison_result.get("repair_suggestions", [])

                    # Fallback to single-prompt if two-stage failed
                    if not two_stage_success:
                        llm = _maybe_json_from_gemini(
                            gemini,
                            _prompt_blind_test(scene.source_text, panel_semantics.payload),
                        )
                        if isinstance(llm, dict):
                            reconstructed = llm.get("reconstructed_story", reconstructed)
                            comparison = llm.get("comparison", comparison)
                            score = float(llm.get("score", score))
                            scores = llm.get("scores")
                            failure_points = llm.get("failure_points", [])
                            repair_suggestions = llm.get("repair_suggestions", [])

                payload = {
                    "reconstructed_story": reconstructed,
                    "comparison": comparison,
                    "score": score,
                    "passed": score >= 0.25,
                    "scores": scores,
                    "failure_points": failure_points,
                    "repair_suggestions": repair_suggestions,
                }
                record_blind_test_result(payload["passed"])
                return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_BLIND_TEST_REPORT, payload=payload)
