import logging
import uuid

from sqlalchemy.orm import Session

from app.config.loaders import select_template
from app.services.artifacts import ArtifactService
from .constants import ARTIFACT_LAYOUT_TEMPLATE, ARTIFACT_PANEL_PLAN, ARTIFACT_PANEL_PLAN_NORMALIZED


logger = logging.getLogger(__name__)


def compute_layout_template_resolver(panel_plan: dict | list, derived_features: dict | None = None) -> dict:
    template = select_template(panel_plan, derived_features=derived_features)
    return template.model_dump()


def run_layout_template_resolver(db: Session, scene_id: uuid.UUID):
    svc = ArtifactService(db)
    plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED) or svc.get_latest_artifact(
        scene_id, ARTIFACT_PANEL_PLAN
    )
    if plan is None:
        raise ValueError("panel_plan artifact not found")

    payload = compute_layout_template_resolver(plan.payload)
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_LAYOUT_TEMPLATE, payload=payload)
    logger.info(
        "node_complete node_name=LayoutTemplateResolver scene_id=%s artifact_id=%s",
        scene_id,
        artifact.artifact_id,
    )
    return artifact
