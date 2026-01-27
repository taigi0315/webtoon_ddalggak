from __future__ import annotations

import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.graphs import nodes
from app.db.models import Scene
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient


class PipelineState(TypedDict, total=False):
    db: Session
    scene_id: uuid.UUID
    panel_count: int
    style_id: str
    genre: str | None
    gemini: GeminiClient | None

    scene_intent_artifact_id: str
    panel_plan_artifact_id: str
    panel_plan_normalized_artifact_id: str
    layout_template_artifact_id: str
    panel_semantics_artifact_id: str
    render_spec_artifact_id: str
    render_result_artifact_id: str
    qc_report_artifact_id: str
    blind_test_report_artifact_id: str


def _node_scene_intent(state: PipelineState) -> dict[str, Any]:
    artifact = nodes.run_scene_intent_extractor(
        db=state["db"],
        scene_id=state["scene_id"],
        genre=state.get("genre"),
        gemini=state.get("gemini"),
    )
    return {"scene_intent_artifact_id": str(artifact.artifact_id)}


def _node_panel_plan(state: PipelineState) -> dict[str, Any]:
    artifact = nodes.run_panel_plan_generator(
        db=state["db"],
        scene_id=state["scene_id"],
        panel_count=int(state.get("panel_count") or 3),
        gemini=state.get("gemini"),
    )
    return {"panel_plan_artifact_id": str(artifact.artifact_id)}


def _node_panel_plan_normalize(state: PipelineState) -> dict[str, Any]:
    artifact = nodes.run_panel_plan_normalizer(db=state["db"], scene_id=state["scene_id"])
    return {"panel_plan_normalized_artifact_id": str(artifact.artifact_id)}


def _node_layout(state: PipelineState) -> dict[str, Any]:
    artifact = nodes.run_layout_template_resolver(db=state["db"], scene_id=state["scene_id"])
    return {"layout_template_artifact_id": str(artifact.artifact_id)}


def _node_panel_semantics(state: PipelineState) -> dict[str, Any]:
    artifact = nodes.run_panel_semantic_filler(
        db=state["db"],
        scene_id=state["scene_id"],
        gemini=state.get("gemini"),
    )
    return {"panel_semantics_artifact_id": str(artifact.artifact_id)}


def _node_qc(state: PipelineState) -> dict[str, Any]:
    artifact = nodes.run_qc_checker(db=state["db"], scene_id=state["scene_id"])
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    if not payload.get("passed"):
        raise ValueError("QC failed; fix panel plan or semantics before rendering")
    return {"qc_report_artifact_id": str(artifact.artifact_id)}


def _node_render_spec(state: PipelineState) -> dict[str, Any]:
    if not state.get("style_id"):
        raise ValueError("style_id is required for render spec generation")
    artifact = nodes.run_prompt_compiler(
        db=state["db"],
        scene_id=state["scene_id"],
        style_id=state.get("style_id") or "default",
    )
    return {"render_spec_artifact_id": str(artifact.artifact_id)}


def _node_render(state: PipelineState) -> dict[str, Any]:
    artifact = nodes.run_image_renderer(
        db=state["db"],
        scene_id=state["scene_id"],
        gemini=state.get("gemini"),
    )
    return {"render_result_artifact_id": str(artifact.artifact_id)}


def _node_blind_test(state: PipelineState) -> dict[str, Any]:
    artifact = nodes.run_blind_test_evaluator(
        db=state["db"],
        scene_id=state["scene_id"],
        gemini=state.get("gemini"),
    )
    return {"blind_test_report_artifact_id": str(artifact.artifact_id)}


def build_full_pipeline_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("scene_intent", _node_scene_intent)
    graph.add_node("panel_plan", _node_panel_plan)
    graph.add_node("panel_plan_normalize", _node_panel_plan_normalize)
    graph.add_node("layout", _node_layout)
    graph.add_node("panel_semantics", _node_panel_semantics)
    graph.add_node("qc_check", _node_qc)
    graph.add_node("render_spec", _node_render_spec)
    graph.add_node("render", _node_render)
    graph.add_node("blind_test", _node_blind_test)

    graph.set_entry_point("scene_intent")
    graph.add_edge("scene_intent", "panel_plan")
    graph.add_edge("panel_plan", "panel_plan_normalize")
    graph.add_edge("panel_plan_normalize", "layout")
    graph.add_edge("layout", "panel_semantics")
    graph.add_edge("panel_semantics", "qc_check")
    graph.add_edge("qc_check", "render_spec")
    graph.add_edge("render_spec", "render")
    graph.add_edge("render", "blind_test")
    graph.add_edge("blind_test", END)

    return graph.compile()


def run_full_pipeline(
    db: Session,
    scene_id: uuid.UUID,
    panel_count: int = 3,
    style_id: str | None = None,
    genre: str | None = None,
    gemini: GeminiClient | None = None,
) -> PipelineState:
    if not style_id:
        raise ValueError("style_id is required for full generation")
    scene = db.get(Scene, scene_id)
    if scene is not None and scene.planning_locked:
        svc = ArtifactService(db)
        required = {
            "scene_intent_artifact_id": nodes.ARTIFACT_SCENE_INTENT,
            "panel_plan_artifact_id": nodes.ARTIFACT_PANEL_PLAN,
            "panel_plan_normalized_artifact_id": nodes.ARTIFACT_PANEL_PLAN_NORMALIZED,
            "layout_template_artifact_id": nodes.ARTIFACT_LAYOUT_TEMPLATE,
            "panel_semantics_artifact_id": nodes.ARTIFACT_PANEL_SEMANTICS,
        }

        locked_state: PipelineState = {
            "db": db,
            "scene_id": scene_id,
            "panel_count": panel_count,
            "style_id": style_id,
            "genre": genre,
            "gemini": gemini,
        }

        missing: list[str] = []
        for key, t in required.items():
            art = svc.get_latest_artifact(scene_id, t)
            if art is None:
                missing.append(t)
            else:
                locked_state[key] = str(art.artifact_id)

        if missing:
            raise ValueError(f"planning is locked but missing artifacts: {', '.join(missing)}")

        qc = nodes.run_qc_checker(db=db, scene_id=scene_id)
        if not (qc.payload or {}).get("passed"):
            raise ValueError("QC failed; fix panel plan or semantics before rendering")
        locked_state["qc_report_artifact_id"] = str(qc.artifact_id)

        spec = nodes.run_prompt_compiler(db=db, scene_id=scene_id, style_id=style_id)
        locked_state["render_spec_artifact_id"] = str(spec.artifact_id)

        render = nodes.run_image_renderer(db=db, scene_id=scene_id, gemini=gemini)
        locked_state["render_result_artifact_id"] = str(render.artifact_id)

        blind = nodes.run_blind_test_evaluator(db=db, scene_id=scene_id, gemini=gemini)
        locked_state["blind_test_report_artifact_id"] = str(blind.artifact_id)
        return locked_state

    app = build_full_pipeline_graph()
    state: PipelineState = {
        "db": db,
        "scene_id": scene_id,
        "panel_count": panel_count,
        "style_id": style_id,
        "genre": genre,
        "gemini": gemini,
    }
    return app.invoke(state)
