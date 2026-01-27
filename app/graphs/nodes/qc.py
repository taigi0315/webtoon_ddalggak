import logging
import uuid

from sqlalchemy.orm import Session

from app.config.loaders import load_qc_rules_v1
from app.services.artifacts import ArtifactService
from .constants import ARTIFACT_PANEL_PLAN, ARTIFACT_PANEL_SEMANTICS, ARTIFACT_QC_REPORT


logger = logging.getLogger(__name__)


def compute_qc_report(panel_plan: dict, panel_semantics: dict) -> dict:
    rules = load_qc_rules_v1()
    panels = panel_semantics.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ValueError("panel_semantics.panels must be a non-empty list")

    issues: list[dict] = []
    total = len(panels)

    closeup_count = 0
    dialogue_count = 0
    last_three: list[str | None] = []
    has_establishing = False
    establishing_missing_env = False

    env_keywords = {kw.lower() for kw in rules.environment_keywords}

    for panel in panels:
        grammar_id = panel.get("grammar_id")
        grammar_str = grammar_id if isinstance(grammar_id, str) else ""
        text = panel.get("text") or ""

        if "closeup" in grammar_str or "close_up" in grammar_str:
            closeup_count += 1

        if "dialogue" in grammar_str:
            dialogue_count += 1

        if grammar_str == "establishing":
            has_establishing = True
            if rules.require_environment_on_establishing:
                text_lower = text.lower() if isinstance(text, str) else ""
                if not any(keyword in text_lower for keyword in env_keywords):
                    establishing_missing_env = True

        last_three.append(grammar_str if grammar_str else None)
        last_three = last_three[-rules.repeated_framing_run_length :]
        if (
            len(last_three) == rules.repeated_framing_run_length
            and last_three[0]
            and last_three[0] == last_three[1] == last_three[-1]
        ):
            issues.append(
                {
                    "code": "repeated_framing",
                    "severity": "low",
                    "message": "Repeated framing across consecutive panels.",
                    "suggested_reroute": "panel_plan",
                }
            )

    if total >= 4 and closeup_count / total > rules.closeup_ratio_max:
        issues.append(
            {
                "code": "over_closeup_density",
                "severity": "low",
                "message": "Closeup panels exceed allowed ratio.",
                "suggested_reroute": "panel_plan",
            }
        )

    if total >= 3 and dialogue_count / total > rules.dialogue_ratio_max:
        issues.append(
            {
                "code": "over_dialogue_density",
                "severity": "medium",
                "message": "Dialogue-heavy panels exceed allowed ratio.",
                "suggested_reroute": "panel_semantics",
            }
        )

    if has_establishing and establishing_missing_env:
        issues.append(
            {
                "code": "missing_environment",
                "severity": "high",
                "message": "Establishing panel lacks clear environment description.",
                "suggested_reroute": "panel_semantics",
            }
        )

    passed = len(issues) == 0
    return {"passed": passed, "issues": issues, "panel_count": total}


def run_qc_checker(db: Session, scene_id: uuid.UUID):
    svc = ArtifactService(db)
    plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
    if plan is None:
        raise ValueError("panel_plan artifact not found")

    semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
    if semantics is None:
        raise ValueError("panel_semantics artifact not found")

    payload = compute_qc_report(plan.payload, semantics.payload)
    artifact = svc.create_artifact(scene_id=scene_id, type=ARTIFACT_QC_REPORT, payload=payload)
    logger.info(
        "node_complete node_name=QualityControl scene_id=%s artifact_id=%s passed=%s",
        scene_id,
        artifact.artifact_id,
        payload.get("passed"),
    )
    return artifact
