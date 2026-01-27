import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DbSessionDep
from app.config.loaders import has_image_style
from app.db.models import Scene
from app.graphs import nodes
from app.graphs.pipeline import run_full_pipeline


router = APIRouter(tags=["generation"])


class ArtifactIdResponse(BaseModel):
    artifact_id: uuid.UUID


class GeneratePanelPlanRequest(BaseModel):
    panel_count: int = Field(default=3, ge=1, le=12)


class GenerateRenderSpecRequest(BaseModel):
    style_id: str = Field(min_length=1)


class GenerateFullRequest(BaseModel):
    panel_count: int = Field(default=3, ge=1, le=12)
    style_id: str = Field(min_length=1)
    genre: str | None = None


class GenerateFullResponse(BaseModel):
    scene_intent_artifact_id: uuid.UUID
    panel_plan_artifact_id: uuid.UUID
    panel_plan_normalized_artifact_id: uuid.UUID
    layout_template_artifact_id: uuid.UUID
    panel_semantics_artifact_id: uuid.UUID
    qc_report_artifact_id: uuid.UUID
    render_spec_artifact_id: uuid.UUID
    render_result_artifact_id: uuid.UUID
    blind_test_report_artifact_id: uuid.UUID


def _scene_or_404(db, scene_id: uuid.UUID) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")
    return scene


@router.post("/scenes/{scene_id}/generate/scene-intent", response_model=ArtifactIdResponse)
def generate_scene_intent(scene_id: uuid.UUID, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    artifact = nodes.run_scene_intent_extractor(db=db, scene_id=scene_id)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/generate/panel-plan", response_model=ArtifactIdResponse)
def generate_panel_plan(scene_id: uuid.UUID, payload: GeneratePanelPlanRequest, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    artifact = nodes.run_panel_plan_generator(db=db, scene_id=scene_id, panel_count=payload.panel_count)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/generate/panel-plan/normalize", response_model=ArtifactIdResponse)
def normalize_panel_plan(scene_id: uuid.UUID, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    artifact = nodes.run_panel_plan_normalizer(db=db, scene_id=scene_id)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/generate/layout", response_model=ArtifactIdResponse)
def generate_layout(scene_id: uuid.UUID, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    artifact = nodes.run_layout_template_resolver(db=db, scene_id=scene_id)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/generate/panel-semantics", response_model=ArtifactIdResponse)
def generate_panel_semantics(scene_id: uuid.UUID, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    artifact = nodes.run_panel_semantic_filler(db=db, scene_id=scene_id)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/generate/render-spec", response_model=ArtifactIdResponse)
def generate_render_spec(scene_id: uuid.UUID, payload: GenerateRenderSpecRequest, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    if not has_image_style(payload.style_id):
        raise HTTPException(status_code=400, detail="unknown style_id")
    artifact = nodes.run_prompt_compiler(db=db, scene_id=scene_id, style_id=payload.style_id)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/generate/render", response_model=ArtifactIdResponse)
def generate_render(scene_id: uuid.UUID, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    qc = nodes.run_qc_checker(db=db, scene_id=scene_id)
    if not (qc.payload or {}).get("passed"):
        raise HTTPException(status_code=400, detail="qc failed; fix panel plan or semantics")
    artifact = nodes.run_image_renderer(db=db, scene_id=scene_id)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/evaluate/qc", response_model=ArtifactIdResponse)
def evaluate_qc(scene_id: uuid.UUID, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    artifact = nodes.run_qc_checker(db=db, scene_id=scene_id)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/evaluate/blind-test", response_model=ArtifactIdResponse)
def evaluate_blind_test(scene_id: uuid.UUID, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    artifact = nodes.run_blind_test_evaluator(db=db, scene_id=scene_id)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/generate/full", response_model=GenerateFullResponse)
def generate_full(scene_id: uuid.UUID, payload: GenerateFullRequest, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    if not has_image_style(payload.style_id):
        raise HTTPException(status_code=400, detail="unknown style_id")

    out = run_full_pipeline(
        db=db,
        scene_id=scene_id,
        panel_count=payload.panel_count,
        style_id=payload.style_id,
        genre=payload.genre,
        gemini=None,
    )

    return GenerateFullResponse(
        scene_intent_artifact_id=uuid.UUID(out["scene_intent_artifact_id"]),
        panel_plan_artifact_id=uuid.UUID(out["panel_plan_artifact_id"]),
        panel_plan_normalized_artifact_id=uuid.UUID(out["panel_plan_normalized_artifact_id"]),
        layout_template_artifact_id=uuid.UUID(out["layout_template_artifact_id"]),
        panel_semantics_artifact_id=uuid.UUID(out["panel_semantics_artifact_id"]),
        qc_report_artifact_id=uuid.UUID(out["qc_report_artifact_id"]),
        render_spec_artifact_id=uuid.UUID(out["render_spec_artifact_id"]),
        render_result_artifact_id=uuid.UUID(out["render_result_artifact_id"]),
        blind_test_report_artifact_id=uuid.UUID(out["blind_test_report_artifact_id"]),
    )
