"""Quality control checking functions."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.metrics import record_qc_issues, track_graph_node
from app.core.request_context import log_context
from app.core.telemetry import trace_span
from app.services.artifacts import ArtifactService

from ..utils import (
    ARTIFACT_PANEL_PLAN,
    ARTIFACT_PANEL_PLAN_NORMALIZED,
    ARTIFACT_PANEL_SEMANTICS,
    ARTIFACT_QC_REPORT,
    _qc_report,
)


def run_qc_checker(db: Session, scene_id: uuid.UUID):
    """Run quality control checks on panel plan and semantics.

    Args:
        db: Database session
        scene_id: UUID of the scene

    Returns:
        Created qc_report artifact
    """
    with track_graph_node("scene_planning", "qc_checker"):
        with log_context(node_name="qc_checker", scene_id=scene_id):
            with trace_span("graph.qc_checker", scene_id=str(scene_id)):
                svc = ArtifactService(db)
                panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
                if panel_plan is None:
                    panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
                panel_semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)

                if panel_plan is None:
                    raise ValueError("panel_plan artifact not found")

                report = _qc_report(panel_plan.payload, panel_semantics.payload if panel_semantics else None)
                return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_QC_REPORT, payload=report)
