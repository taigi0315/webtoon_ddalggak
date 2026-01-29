from __future__ import annotations

import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.graphs import nodes
from app.db.models import Scene, Story
from app.core.telemetry import trace_span
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient


class PlanningState(TypedDict, total=False):
    db: Session
    scene_id: uuid.UUID
    panel_count: int
    genre: str | None
    gemini: GeminiClient | None

    scene_intent_artifact_id: str
    panel_plan_artifact_id: str
    panel_plan_normalized_artifact_id: str
    layout_template_artifact_id: str
    panel_semantics_artifact_id: str


class RenderState(TypedDict, total=False):
    db: Session
    scene_id: uuid.UUID
    style_id: str | None
    prompt_override: str | None
    enforce_qc: bool
    gemini: GeminiClient | None

    panel_semantics_artifact_id: str
    layout_template_artifact_id: str
    render_spec_artifact_id: str
    render_result_artifact_id: str
    qc_report_artifact_id: str


class PipelineState(TypedDict, total=False):
    db: Session
    scene_id: uuid.UUID
    panel_count: int
    style_id: str
    genre: str | None
    prompt_override: str | None
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


def _node_llm_scene_intent(state: PlanningState) -> dict[str, Any]:
    artifact = nodes.run_scene_intent_extractor(
        db=state["db"],
        scene_id=state["scene_id"],
        genre=state.get("genre"),
        gemini=state.get("gemini"),
    )
    return {"scene_intent_artifact_id": str(artifact.artifact_id)}


def _node_llm_panel_plan(state: PlanningState) -> dict[str, Any]:
    artifact = nodes.run_panel_plan_generator(
        db=state["db"],
        scene_id=state["scene_id"],
        panel_count=int(state.get("panel_count") or 3),
        gemini=state.get("gemini"),
    )
    return {"panel_plan_artifact_id": str(artifact.artifact_id)}


def _node_rule_panel_plan_normalize(state: PlanningState) -> dict[str, Any]:
    artifact = nodes.run_panel_plan_normalizer(db=state["db"], scene_id=state["scene_id"])
    return {"panel_plan_normalized_artifact_id": str(artifact.artifact_id)}


def _node_rule_layout(state: PlanningState) -> dict[str, Any]:
    artifact = nodes.run_layout_template_resolver(db=state["db"], scene_id=state["scene_id"])
    return {"layout_template_artifact_id": str(artifact.artifact_id)}


def _node_llm_panel_semantics(state: PlanningState) -> dict[str, Any]:
    artifact = nodes.run_panel_semantic_filler(
        db=state["db"],
        scene_id=state["scene_id"],
        gemini=state.get("gemini"),
    )
    return {"panel_semantics_artifact_id": str(artifact.artifact_id)}

def _node_load_active_scene_artifacts(state: RenderState) -> dict[str, Any]:
    svc = ArtifactService(state["db"])
    scene_id = state["scene_id"]

    panel_semantics = svc.get_latest_artifact(scene_id, nodes.ARTIFACT_PANEL_SEMANTICS)
    layout = svc.get_latest_artifact(scene_id, nodes.ARTIFACT_LAYOUT_TEMPLATE)
    if panel_semantics is None or layout is None:
        raise ValueError("panel_semantics and layout_template artifacts are required")

    style_id = state.get("style_id")
    if not style_id:
        scene = state["db"].get(Scene, scene_id)
        if scene is None:
            raise ValueError("scene not found")
        story = state["db"].get(Story, scene.story_id)
        style_id = scene.image_style_override or (story.default_image_style if story else "default") or "default"

    return {
        "panel_semantics_artifact_id": str(panel_semantics.artifact_id),
        "layout_template_artifact_id": str(layout.artifact_id),
        "style_id": style_id,
    }


def _node_qc(state: RenderState) -> dict[str, Any]:
    artifact = nodes.run_qc_checker(db=state["db"], scene_id=state["scene_id"])
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    if state.get("enforce_qc") and not payload.get("passed"):
        raise ValueError("QC failed; fix panel plan or semantics before rendering")
    return {"qc_report_artifact_id": str(artifact.artifact_id)}


def _node_render_spec(state: RenderState) -> dict[str, Any]:
    if not state.get("style_id"):
        raise ValueError("style_id is required for render spec generation")
    artifact = nodes.run_prompt_compiler(
        db=state["db"],
        scene_id=state["scene_id"],
        style_id=state.get("style_id") or "default",
        prompt_override=state.get("prompt_override"),
    )
    return {"render_spec_artifact_id": str(artifact.artifact_id)}


def _node_render(state: RenderState) -> dict[str, Any]:
    artifact = nodes.run_image_renderer(
        db=state["db"],
        scene_id=state["scene_id"],
        gemini=state.get("gemini"),
    )
    return {"render_result_artifact_id": str(artifact.artifact_id)}


def build_scene_planning_graph():
    graph = StateGraph(PlanningState)

    # LLM nodes
    graph.add_node("llm_scene_intent", _node_llm_scene_intent)
    graph.add_node("llm_panel_plan", _node_llm_panel_plan)
    graph.add_node("llm_panel_semantics", _node_llm_panel_semantics)

    # Rule-based nodes
    graph.add_node("rule_panel_plan_normalize", _node_rule_panel_plan_normalize)
    graph.add_node("rule_layout", _node_rule_layout)

    graph.set_entry_point("llm_scene_intent")
    graph.add_edge("llm_scene_intent", "llm_panel_plan")
    graph.add_edge("llm_panel_plan", "rule_panel_plan_normalize")
    graph.add_edge("rule_panel_plan_normalize", "rule_layout")
    graph.add_edge("rule_layout", "llm_panel_semantics")
    graph.add_edge("llm_panel_semantics", END)

    return graph.compile()


def build_scene_render_graph():
    graph = StateGraph(RenderState)
    graph.add_node("load_artifacts", _node_load_active_scene_artifacts)
    graph.add_node("render_spec", _node_render_spec)
    graph.add_node("render", _node_render)
    graph.add_node("qc_check", _node_qc)

    graph.set_entry_point("load_artifacts")
    graph.add_edge("load_artifacts", "render_spec")
    graph.add_edge("render_spec", "render")
    graph.add_edge("render", "qc_check")
    graph.add_edge("qc_check", END)
    return graph.compile()


def run_scene_planning(
    db: Session,
    scene_id: uuid.UUID,
    panel_count: int = 3,
    genre: str | None = None,
    gemini: GeminiClient | None = None,
) -> PlanningState:
    with trace_span("graph.scene_planning", scene_id=str(scene_id)):
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

            locked_state: PlanningState = {
                "db": db,
                "scene_id": scene_id,
                "panel_count": panel_count,
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

            return locked_state

        app = build_scene_planning_graph()
        state: PlanningState = {
            "db": db,
            "scene_id": scene_id,
            "panel_count": panel_count,
            "genre": genre,
            "gemini": gemini,
        }
        return app.invoke(state)


def run_scene_render(
    db: Session,
    scene_id: uuid.UUID,
    style_id: str | None = None,
    enforce_qc: bool = True,
    prompt_override: str | None = None,
    gemini: GeminiClient | None = None,
) -> RenderState:
    with trace_span("graph.scene_render", scene_id=str(scene_id), style_id=style_id):
        app = build_scene_render_graph()
        state: RenderState = {
            "db": db,
            "scene_id": scene_id,
            "style_id": style_id,
            "prompt_override": prompt_override,
            "enforce_qc": enforce_qc,
            "gemini": gemini,
        }
        return app.invoke(state)


def run_full_pipeline(
    db: Session,
    scene_id: uuid.UUID,
    panel_count: int = 3,
    style_id: str | None = None,
    genre: str | None = None,
    prompt_override: str | None = None,
    gemini: GeminiClient | None = None,
) -> PipelineState:
    with trace_span("graph.full_pipeline", scene_id=str(scene_id), style_id=style_id):
        if not style_id:
            scene = db.get(Scene, scene_id)
            if scene is not None:
                story = db.get(Story, scene.story_id)
                style_id = scene.image_style_override or (story.default_image_style if story else None)
        if not style_id:
            raise ValueError("style_id is required for full generation")

        planning_state = run_scene_planning(
            db=db,
            scene_id=scene_id,
            panel_count=panel_count,
            genre=genre,
            gemini=gemini,
        )

        blind = nodes.run_blind_test_evaluator(db=db, scene_id=scene_id, gemini=gemini)

        render_state = run_scene_render(
            db=db,
            scene_id=scene_id,
            style_id=style_id,
            enforce_qc=False,
            prompt_override=prompt_override,
            gemini=gemini,
        )

        out: PipelineState = {
            **planning_state,
            **render_state,
            "blind_test_report_artifact_id": str(blind.artifact_id),
        }
        return out
