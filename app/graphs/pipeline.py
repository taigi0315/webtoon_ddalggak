from __future__ import annotations

import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.graphs import nodes
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


def _node_render_spec(state: PipelineState) -> dict[str, Any]:
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
    graph.add_node("render_spec", _node_render_spec)
    graph.add_node("render", _node_render)
    graph.add_node("blind_test", _node_blind_test)

    graph.set_entry_point("scene_intent")
    graph.add_edge("scene_intent", "panel_plan")
    graph.add_edge("panel_plan", "panel_plan_normalize")
    graph.add_edge("panel_plan_normalize", "layout")
    graph.add_edge("layout", "panel_semantics")
    graph.add_edge("panel_semantics", "render_spec")
    graph.add_edge("render_spec", "render")
    graph.add_edge("render", "blind_test")
    graph.add_edge("blind_test", END)

    return graph.compile()


def run_full_pipeline(
    db: Session,
    scene_id: uuid.UUID,
    panel_count: int = 3,
    style_id: str = "default",
    genre: str | None = None,
    gemini: GeminiClient | None = None,
) -> PipelineState:
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
