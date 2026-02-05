import logging
import uuid

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    JobStatusRead,
)
from app.config.loaders import has_image_style
from app.db.session import get_sessionmaker
from app.db.models import Scene, Story
from sqlalchemy import select
from app.graphs import nodes
from app.graphs.pipeline import run_full_pipeline, run_scene_planning, run_scene_render
from app.services.artifacts import ArtifactService
from app.services import job_queue
from app.services.vertex_gemini import GeminiClient
from app.core.request_context import get_request_id, log_context, reset_request_id, set_request_id


router = APIRouter(tags=["generation"])


class GenerateFullRequest(BaseModel):
    panel_count: int = Field(default=3, ge=1, le=3)
    style_id: str = Field(min_length=1)
    genre: str | None = None
    prompt_override: str | None = None


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


class ScenePlanRequest(BaseModel):
    panel_count: int = Field(default=3, ge=1, le=12)
    genre: str | None = None


class ScenePlanResponse(BaseModel):
    scene_intent_artifact_id: uuid.UUID
    panel_plan_artifact_id: uuid.UUID
    panel_plan_normalized_artifact_id: uuid.UUID
    layout_template_artifact_id: uuid.UUID
    panel_semantics_artifact_id: uuid.UUID


class SceneRenderRequest(BaseModel):
    style_id: str | None = None
    prompt_override: str | None = None
    enforce_qc: bool = True


class SceneRenderResponse(BaseModel):
    panel_semantics_artifact_id: uuid.UUID
    layout_template_artifact_id: uuid.UUID
    render_spec_artifact_id: uuid.UUID
    render_result_artifact_id: uuid.UUID
    qc_report_artifact_id: uuid.UUID


class GenerateRenderAsyncRequest(BaseModel):
    style_id: str | None = None
    prompt_override: str | None = None
    enforce_qc: bool = False


class SceneWorkflowStatusResponse(BaseModel):
    scene_id: uuid.UUID
    planning_locked: bool
    planning_complete: bool
    render_complete: bool
    latest_artifacts: dict[str, uuid.UUID | None]


def _ensure_render_prerequisites(
    db,
    scene_id: uuid.UUID,
    gemini: GeminiClient,
    panel_count: int = 3,
) -> None:
    svc = ArtifactService(db)
    has_semantics = svc.get_latest_artifact(scene_id, nodes.ARTIFACT_PANEL_SEMANTICS) is not None
    has_layout = svc.get_latest_artifact(scene_id, nodes.ARTIFACT_LAYOUT_TEMPLATE) is not None
    if has_semantics and has_layout:
        return

    logger.info(
        "scene_render prerequisites missing; running planning first (scene_id=%s, has_semantics=%s, has_layout=%s)",
        scene_id,
        has_semantics,
        has_layout,
    )
    run_scene_planning(
        db=db,
        scene_id=scene_id,
        panel_count=panel_count,
        gemini=gemini,
    )


def _build_gemini_client() -> GeminiClient:
    return nodes._build_gemini_client()


def _scene_or_404(db, scene_id: uuid.UUID) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")
    return scene


def _handle_full_generation_job(job: job_queue.JobRecord) -> dict | None:
    payload = GenerateFullRequest(**job.payload["request"])
    scene_id = uuid.UUID(job.payload["scene_id"])
    token = set_request_id(job.request_id or str(job.job_id))
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        with log_context(node_name="scene_full_job", scene_id=scene_id):
            _scene_or_404(db, scene_id)
            if not has_image_style(payload.style_id):
                payload.style_id = "default"

            logger.info(
                "scene_full_job started (scene_id=%s, panel_count=%s, style_id=%s)",
                scene_id,
                payload.panel_count,
                payload.style_id,
            )

            gemini = _build_gemini_client()
            out = run_full_pipeline(
                db=db,
                scene_id=scene_id,
                panel_count=payload.panel_count,
                style_id=payload.style_id,
                genre=payload.genre,
                prompt_override=payload.prompt_override,
                gemini=gemini,
            )
            logger.info("scene_full_job finished (scene_id=%s)", scene_id)
            return out
    finally:
        db.close()
        reset_request_id(token)


def _handle_render_only_job(job: job_queue.JobRecord) -> dict | None:
    payload = GenerateRenderAsyncRequest(**job.payload["request"])
    scene_id = uuid.UUID(job.payload["scene_id"])
    token = set_request_id(job.request_id or str(job.job_id))
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        with log_context(node_name="scene_render_job", scene_id=scene_id):
            _scene_or_404(db, scene_id)
            logger.info(
                "scene_render_job started (scene_id=%s, style_id=%s, enforce_qc=%s)",
                scene_id,
                payload.style_id,
                payload.enforce_qc,
            )
            if payload.style_id and not has_image_style(payload.style_id):
                payload.style_id = "default"
            gemini = _build_gemini_client()
            _ensure_render_prerequisites(db=db, scene_id=scene_id, gemini=gemini, panel_count=3)
            out = run_scene_render(
                db=db,
                scene_id=scene_id,
                style_id=payload.style_id,
                enforce_qc=payload.enforce_qc,
                prompt_override=payload.prompt_override,
                gemini=gemini,
            )
            logger.info("scene_render_job finished (scene_id=%s)", scene_id)
            return out
    finally:
        db.close()
        reset_request_id(token)


def _handle_plan_only_job(job: job_queue.JobRecord) -> dict | None:
    payload = ScenePlanRequest(**job.payload["request"])
    scene_id = uuid.UUID(job.payload["scene_id"])
    token = set_request_id(job.request_id or str(job.job_id))
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        with log_context(node_name="scene_plan_job", scene_id=scene_id):
            _scene_or_404(db, scene_id)
            logger.info(
                "scene_plan_job started (scene_id=%s, panel_count=%s, genre=%s)",
                scene_id,
                payload.panel_count,
                payload.genre,
            )
            gemini = _build_gemini_client()
            out = run_scene_planning(
                db=db,
                scene_id=scene_id,
                panel_count=payload.panel_count,
                genre=payload.genre,
                gemini=gemini,
            )
            logger.info("scene_plan_job finished (scene_id=%s)", scene_id)
            return out
    finally:
        db.close()
        reset_request_id(token)


@router.post("/scenes/{scene_id}/plan", response_model=ScenePlanResponse)
def plan_scene(scene_id: uuid.UUID, payload: ScenePlanRequest, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    gemini = _build_gemini_client()
    out = run_scene_planning(
        db=db,
        scene_id=scene_id,
        panel_count=payload.panel_count,
        genre=payload.genre,
        gemini=gemini,
    )
    return ScenePlanResponse(
        scene_intent_artifact_id=uuid.UUID(out["scene_intent_artifact_id"]),
        panel_plan_artifact_id=uuid.UUID(out["panel_plan_artifact_id"]),
        panel_plan_normalized_artifact_id=uuid.UUID(out["panel_plan_normalized_artifact_id"]),
        layout_template_artifact_id=uuid.UUID(out["layout_template_artifact_id"]),
        panel_semantics_artifact_id=uuid.UUID(out["panel_semantics_artifact_id"]),
    )


@router.post("/scenes/{scene_id}/render", response_model=SceneRenderResponse)
def render_scene(scene_id: uuid.UUID, payload: SceneRenderRequest, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    if payload.style_id and not has_image_style(payload.style_id):
        payload.style_id = "default"
    gemini = _build_gemini_client()
    _ensure_render_prerequisites(db=db, scene_id=scene_id, gemini=gemini, panel_count=3)
    out = run_scene_render(
        db=db,
        scene_id=scene_id,
        style_id=payload.style_id,
        enforce_qc=payload.enforce_qc,
        prompt_override=payload.prompt_override,
        gemini=gemini,
    )
    return SceneRenderResponse(
        panel_semantics_artifact_id=uuid.UUID(out["panel_semantics_artifact_id"]),
        layout_template_artifact_id=uuid.UUID(out["layout_template_artifact_id"]),
        render_spec_artifact_id=uuid.UUID(out["render_spec_artifact_id"]),
        render_result_artifact_id=uuid.UUID(out["render_result_artifact_id"]),
        qc_report_artifact_id=uuid.UUID(out["qc_report_artifact_id"]),
    )


@router.get("/scenes/{scene_id}/status", response_model=SceneWorkflowStatusResponse)
def get_scene_status(scene_id: uuid.UUID, db=DbSessionDep):
    scene = _scene_or_404(db, scene_id)
    svc = ArtifactService(db)
    artifact_types = [
        nodes.ARTIFACT_SCENE_INTENT,
        nodes.ARTIFACT_PANEL_PLAN,
        nodes.ARTIFACT_PANEL_PLAN_NORMALIZED,
        nodes.ARTIFACT_LAYOUT_TEMPLATE,
        nodes.ARTIFACT_PANEL_SEMANTICS,
        nodes.ARTIFACT_RENDER_SPEC,
        nodes.ARTIFACT_RENDER_RESULT,
        nodes.ARTIFACT_QC_REPORT,
        nodes.ARTIFACT_BLIND_TEST_REPORT,
    ]
    latest: dict[str, uuid.UUID | None] = {}
    for artifact_type in artifact_types:
        artifact = svc.get_latest_artifact(scene_id, artifact_type)
        latest[artifact_type] = artifact.artifact_id if artifact else None

    planning_complete = all(
        latest.get(t)
        for t in (
            nodes.ARTIFACT_SCENE_INTENT,
            nodes.ARTIFACT_PANEL_PLAN,
            nodes.ARTIFACT_PANEL_PLAN_NORMALIZED,
            nodes.ARTIFACT_LAYOUT_TEMPLATE,
            nodes.ARTIFACT_PANEL_SEMANTICS,
        )
    )
    render_complete = all(
        latest.get(t)
        for t in (
            nodes.ARTIFACT_RENDER_SPEC,
            nodes.ARTIFACT_RENDER_RESULT,
        )
    )

    return SceneWorkflowStatusResponse(
        scene_id=scene_id,
        planning_locked=bool(scene.planning_locked),
        planning_complete=planning_complete,
        render_complete=render_complete,
        latest_artifacts=latest,
    )


@router.post("/scenes/{scene_id}/generate/full", response_model=GenerateFullResponse)
def generate_full(scene_id: uuid.UUID, payload: GenerateFullRequest, db=DbSessionDep):
    _scene_or_404(db, scene_id)
    if not has_image_style(payload.style_id):
        # Fallback to default instead of crashing if style is unknown
        payload.style_id = "default"

    gemini = _build_gemini_client()

    out = run_full_pipeline(
        db=db,
        scene_id=scene_id,
        panel_count=payload.panel_count,
        style_id=payload.style_id,
        genre=payload.genre,
        prompt_override=payload.prompt_override,
        gemini=gemini,
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


@router.post("/scenes/{scene_id}/generate/full_async", response_model=JobStatusRead)
def generate_full_async(
    scene_id: uuid.UUID,
    payload: GenerateFullRequest,
    response: Response,
    db=DbSessionDep,
):
    _scene_or_404(db, scene_id)
    if not has_image_style(payload.style_id):
        payload.style_id = "default"

    job = job_queue.enqueue_job(
        "scene_full",
        {"scene_id": str(scene_id), "request": payload.model_dump()},
        _handle_full_generation_job,
        request_id=get_request_id(),
    )
    response.status_code = 202
    return JobStatusRead(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        progress=job.progress,
        result=job.result,
        error=job.error,
    )


@router.post("/scenes/{scene_id}/plan_async", response_model=JobStatusRead)
def plan_scene_async(
    scene_id: uuid.UUID,
    payload: ScenePlanRequest,
    response: Response,
    db=DbSessionDep,
):
    _scene_or_404(db, scene_id)

    job = job_queue.enqueue_job(
        "scene_plan",
        {"scene_id": str(scene_id), "request": payload.model_dump()},
        _handle_plan_only_job,
        request_id=get_request_id(),
    )
    response.status_code = 202
    return JobStatusRead(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        progress=job.progress,
        result=job.result,
        error=job.error,
    )


@router.post("/scenes/{scene_id}/generate/render_async", response_model=JobStatusRead)
def generate_render_async(
    scene_id: uuid.UUID,
    payload: GenerateRenderAsyncRequest,
    response: Response,
    db=DbSessionDep,
):
    _scene_or_404(db, scene_id)
    if payload.style_id and not has_image_style(payload.style_id):
        payload.style_id = "default"

    job = job_queue.enqueue_job(
        "scene_render",
        {"scene_id": str(scene_id), "request": payload.model_dump()},
        _handle_render_only_job,
        request_id=get_request_id(),
    )
    response.status_code = 202
    return JobStatusRead(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        progress=job.progress,
        result=job.result,
        error=job.error,
    )
