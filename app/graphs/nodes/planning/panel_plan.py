"""Panel plan generation and normalization functions."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.config import loaders
from app.core.metrics import track_graph_node
from app.core.request_context import log_context
from app.core.telemetry import trace_span
from app.services.artifacts import ArtifactService

from ..utils import (
    ARTIFACT_SCENE_INTENT,
    ARTIFACT_PANEL_PLAN,
    ARTIFACT_PANEL_PLAN_NORMALIZED,
    ARTIFACT_LAYOUT_TEMPLATE,
    ARTIFACT_VISUAL_PLAN,
    _get_scene,
    _list_characters,
    _panel_count_for_importance,
    _heuristic_panel_plan,
    _evaluate_and_prune_panel_plan,
    _assign_panel_weights,
    _derive_panel_plan_features,
    _normalize_panel_plan,
    _apply_weights_to_template,
    _maybe_json_from_gemini,
    _prompt_panel_plan,
    GeminiClient,
)

logger = logging.getLogger(__name__)


def run_panel_plan_generator(
    db: Session,
    scene_id: uuid.UUID,
    panel_count: int = 3,
    gemini: GeminiClient | None = None,
):
    """Generate panel plan for a scene.

    Args:
        db: Database session
        scene_id: UUID of the scene
        panel_count: Target number of panels
        gemini: Optional GeminiClient for LLM-based generation

    Returns:
        Created panel_plan artifact
    """
    with track_graph_node("scene_planning", "panel_plan_generator"):
        with log_context(node_name="panel_plan_generator", scene_id=scene_id):
            with trace_span(
                "graph.panel_plan_generator",
                scene_id=str(scene_id),
                panel_count=panel_count,
            ):
                svc = ArtifactService(db)
                scene = _get_scene(db, scene_id)
                characters = _list_characters(db, scene.story_id)
                character_names = [c.name for c in characters]
                panel_count = max(1, min(int(panel_count), 3))
                importance = scene.scene_importance

                if importance:
                    panel_count = _panel_count_for_importance(importance, scene.source_text, panel_count)
                    # Ensure panel count stays within limits even after importance adjustment
                    panel_count = max(1, min(panel_count, 3))

                # Get scene_intent if available
                scene_intent_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
                scene_intent = scene_intent_artifact.payload if scene_intent_artifact else None

                # Get QC rules for proactive constraints
                qc_rules_obj = loaders.load_qc_rules_v1()
                qc_rules = {
                    "closeup_ratio_max": qc_rules_obj.closeup_ratio_max,
                    "dialogue_ratio_max": qc_rules_obj.dialogue_ratio_max,
                    "repeated_framing_run_length": qc_rules_obj.repeated_framing_run_length,
                }

                plan = _heuristic_panel_plan(scene.source_text, panel_count)

                if gemini is not None:
                    # DEBUG: Log what we're sending to the LLM
                    logger.info(
                        f"Calling panel_plan LLM for scene {scene_id}: "
                        f"panel_count={panel_count}, scene_text_length={len(scene.source_text)}, "
                        f"importance={importance}"
                    )
                    
                    llm = _maybe_json_from_gemini(
                        gemini,
                        _prompt_panel_plan(
                            scene.source_text,
                            panel_count,
                            scene_intent=scene_intent,
                            scene_importance=importance,
                            character_names=character_names,
                            qc_rules=qc_rules,
                        ),
                    )
                    if isinstance(llm, dict) and isinstance(llm.get("panels"), list):
                        plan = {"panels": llm["panels"]}

                plan = _evaluate_and_prune_panel_plan(plan)
                # Assign weights and must_be_large flags to panels based on utility and scene importance
                plan = _assign_panel_weights(plan, importance)
                if not isinstance(plan, dict):
                    plan = {"panels": []}

                # CRITICAL: Force panel count to max 3
                if "panels" in plan and len(plan["panels"]) > 3:
                    logger.warning(
                        f"Panel plan for scene {scene_id} generated {len(plan['panels'])} panels, "
                        f"truncating to 3 (max allowed)"
                    )
                    plan["panels"] = plan["panels"][:3]
                    # Re-index panels
                    for idx, panel in enumerate(plan["panels"], start=1):
                        panel["panel_index"] = idx

                # Try to include scene-level must_show (from visual plan) into panel plan for derived features
                visual_plan_art = svc.get_latest_artifact(scene_id, ARTIFACT_VISUAL_PLAN)
                if visual_plan_art and isinstance(visual_plan_art.payload, dict):
                    plan["must_show"] = visual_plan_art.payload.get("must_show", [])

                # Compute and attach derived features (weights aggregates, hero count, etc.)
                characters_for_features = [c.name for c in _list_characters(db, scene.story_id)]
                derived = _derive_panel_plan_features(plan, characters_for_features)
                plan["derived_features"] = derived

                return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_PLAN, payload=plan)


def run_panel_plan_normalizer(db: Session, scene_id: uuid.UUID):
    """Normalize panel plan to ensure valid grammar IDs and structure.

    Args:
        db: Database session
        scene_id: UUID of the scene

    Returns:
        Created panel_plan_normalized artifact
    """
    with track_graph_node("scene_planning", "panel_plan_normalizer"):
        with log_context(node_name="panel_plan_normalizer", scene_id=scene_id):
            with trace_span("graph.panel_plan_normalizer", scene_id=str(scene_id)):
                svc = ArtifactService(db)
                panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
                if panel_plan is None:
                    raise ValueError("panel_plan artifact not found")
                normalized = _normalize_panel_plan(panel_plan.payload)
                return svc.create_artifact(
                    scene_id=scene_id, type=ARTIFACT_PANEL_PLAN_NORMALIZED, payload=normalized
                )


def run_layout_template_resolver(
    db: Session,
    scene_id: uuid.UUID,
    excluded_template_ids: list[str] | None = None,
):
    """Resolve layout template for a panel plan.

    Args:
        db: Database session
        scene_id: UUID of the scene
        excluded_template_ids: Optional list of template IDs to exclude

    Returns:
        Created layout_template artifact
    """
    with track_graph_node("scene_planning", "layout_template_resolver"):
        with log_context(node_name="layout_template_resolver", scene_id=scene_id):
            with trace_span("graph.layout_template_resolver", scene_id=str(scene_id)):
                svc = ArtifactService(db)
                panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
                if panel_plan is None:
                    panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
                if panel_plan is None:
                    raise ValueError("panel_plan artifact not found")

                # Derive simple features from panel plan for decision rules
                # Merge scene_importance with any derived features on the panel plan
                derived_features = dict(panel_plan.payload.get("derived_features", {}) or {})
                derived_features.setdefault("scene_importance", panel_plan.payload.get("scene_importance"))

                template = loaders.select_template(
                    panel_plan.payload,
                    derived_features=derived_features,
                    excluded_template_ids=excluded_template_ids,
                )

                # Apply panel weights to template geometry when relevant
                try:
                    weighted_template = _apply_weights_to_template(panel_plan.payload, template)
                except Exception:
                    weighted_template = template

                payload = {
                    "template_id": weighted_template.template_id,
                    "layout_text": weighted_template.layout_text,
                    "panels": [p.model_dump() for p in weighted_template.panels],
                }
                return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_LAYOUT_TEMPLATE, payload=payload)
