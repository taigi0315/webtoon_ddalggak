import uuid
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    JobStatusRead,
    SceneAnalysisRead,
    SceneAutoChunkRequest,
    SceneEstimationRequest,
    SceneEstimationResponse,
    SceneRead,
    StoryCreate,
    StoryProgress,
    StoryRead,
    StorySetStyleDefaultsRequest,
    StoryGenerateRequest,
    StoryGenerateResponse,
    StoryProgressRead,
)
from app.config.loaders import has_image_style
from app.core.settings import settings
from app.db.session import get_sessionmaker
from app.db.models import Character, Project, Scene, Story, StoryCharacter
from app.graphs import nodes
from app.graphs.story_build import run_story_build_graph
from app.services import job_queue
from app.services.audit import log_audit_entry
from app.services.story_analysis import (
    estimate_scene_count_heuristic,
    estimate_scene_count_llm,
)
from app.core.gemini_factory import GeminiNotConfiguredError, build_gemini_client
from app.core.request_context import get_request_id, reset_request_id, set_request_id


router = APIRouter(tags=["stories"])
logger = logging.getLogger(__name__)


@router.post("/projects/{project_id}/stories", response_model=StoryRead)
def create_story(project_id: uuid.UUID, payload: StoryCreate, db=DbSessionDep):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    if not has_image_style(payload.default_image_style):
        raise HTTPException(status_code=400, detail="unknown default_image_style")

    request_id = get_request_id()
    story = Story(
        project_id=project_id,
        title=payload.title,
        default_image_style=payload.default_image_style,
        created_by=request_id,
        updated_by=request_id,
    )
    story.updated_by = get_request_id()
    db.add(story)
    db.commit()
    db.refresh(story)
    log_audit_entry(
        db,
        entity_type="story",
        entity_id=story.story_id,
        action="created",
        new_value={
            "project_id": str(story.project_id),
            "title": story.title,
            "default_image_style": story.default_image_style,
        },
    )
    return story


@router.get("/stories/{story_id}", response_model=StoryRead)
def get_story(story_id: uuid.UUID, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")
    return story


@router.get("/projects/{project_id}/stories", response_model=list[StoryRead])
def list_project_stories(project_id: uuid.UUID, db=DbSessionDep):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    stories = db.execute(select(Story).where(Story.project_id == project_id)).scalars().all()
    return list(stories)


@router.post("/stories/{story_id}/scenes/auto-chunk", response_model=list[SceneRead])
def auto_chunk_scenes(story_id: uuid.UUID, payload: SceneAutoChunkRequest, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    chunks = nodes.compute_scene_chunker(payload.source_text, max_scenes=payload.max_scenes)
    if not chunks:
        raise HTTPException(status_code=400, detail="auto-chunk produced no scenes")

    request_id = get_request_id()
    scenes: list[Scene] = []
    for chunk in chunks:
        scene = Scene(
            story_id=story_id,
            source_text=chunk,
            created_by=request_id,
            updated_by=request_id,
        )
        db.add(scene)
        scenes.append(scene)

    db.commit()
    for scene in scenes:
        db.refresh(scene)

    return scenes


@router.post("/stories/{story_id}/generate/blueprint", response_model=StoryGenerateResponse)
def generate_story_blueprint(story_id: uuid.UUID, payload: StoryGenerateRequest, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    existing_scenes = list(db.execute(select(Scene).where(Scene.story_id == story_id)).scalars().all())
    if existing_scenes and not payload.allow_append:
        raise HTTPException(
            status_code=400,
            detail="story already has scenes; set allow_append to true to append more",
        )

    if payload.style_id and not has_image_style(payload.style_id):
        raise HTTPException(status_code=400, detail="unknown style_id")

    gemini = build_gemini_client()

    planning_mode = "characters_only"

    try:
        run_story_build_graph(
            db=db,
            story_id=story_id,
            story_text=payload.source_text,
            max_scenes=payload.max_scenes,
            max_characters=payload.max_characters,
            panel_count=payload.panel_count,
            allow_append=payload.allow_append,
            image_style=payload.style_id or story.default_image_style,
            gemini=gemini,
            planning_mode=planning_mode,
            require_hero_single=payload.require_hero_single,
        )
    except ValueError as exc:
        logger.exception(
            "story blueprint validation failed (story_id=%s, request_id=%s)",
            story_id,
            get_request_id(),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "story blueprint generation failed (story_id=%s, request_id=%s)",
            story_id,
            get_request_id(),
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    scenes = list(db.execute(select(Scene).where(Scene.story_id == story_id)).scalars().all())

    if payload.generate_render_spec and planning_mode == "full":
        style_id = payload.style_id or story.default_image_style or "default"
        for scene in scenes:
            nodes.run_prompt_compiler(db=db, scene_id=scene.scene_id, style_id=style_id)

    all_characters = list(
        db.execute(
            select(Character)
            .join(StoryCharacter, StoryCharacter.character_id == Character.character_id)
            .where(StoryCharacter.story_id == story_id)
        )
        .scalars()
        .all()
    )
    return StoryGenerateResponse(scenes=scenes, characters=all_characters)


def _handle_story_blueprint_job(job: job_queue.JobRecord) -> dict | None:
    payload = StoryGenerateRequest(**job.payload["request"])
    story_id = uuid.UUID(job.payload["story_id"])
    token = set_request_id(job.request_id or str(job.job_id))
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        story = db.get(Story, story_id)
        if story is None:
            raise ValueError("story not found")
        previous_status = story.generation_status
        story.generation_status = "running"
        story.generation_error = None
        story.progress = {
            "current_node": "Queued",
            "message": "Queued for generation...",
            "step": 0,
            "total_steps": 5,
        }
        story.progress_updated_at = datetime.utcnow()
        db.add(story)
        db.commit()
        log_audit_entry(
            db,
            entity_type="story",
            entity_id=story.story_id,
            action="generation_started",
            old_value={"generation_status": previous_status},
            new_value={"generation_status": "running"},
        )

        gemini = build_gemini_client()
        planning_mode = "characters_only"
        run_story_build_graph(
            db=db,
            story_id=story_id,
            story_text=payload.source_text,
            max_scenes=payload.max_scenes,
            max_characters=payload.max_characters,
            panel_count=payload.panel_count,
            allow_append=payload.allow_append,
            image_style=payload.style_id or story.default_image_style,
            gemini=gemini,
            planning_mode=planning_mode,
            require_hero_single=payload.require_hero_single,
        )

        story = db.get(Story, story_id)
        if story is not None:
            prev_status = story.generation_status
            story.generation_status = "succeeded"
            story.generation_error = None
            story.progress_updated_at = datetime.utcnow()
            db.add(story)
            db.commit()
            log_audit_entry(
                db,
                entity_type="story",
                entity_id=story.story_id,
                action="generation_succeeded",
                old_value={"generation_status": prev_status},
                new_value={"generation_status": "succeeded"},
            )
        return {"story_id": str(story_id)}
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "story blueprint async job failed (story_id=%s, job_id=%s, request_id=%s)",
            story_id,
            job.job_id,
            job.request_id,
        )
        story = db.get(Story, story_id)
        if story is not None:
            prev_status = story.generation_status
            story.generation_status = "failed"
            story.generation_error = str(exc)
            story.progress_updated_at = datetime.utcnow()
            db.add(story)
            db.commit()
            log_audit_entry(
                db,
                entity_type="story",
                entity_id=story.story_id,
                action="generation_failed",
                old_value={"generation_status": prev_status},
                new_value={"generation_status": "failed"},
            )
        raise
    finally:
        db.close()
        reset_request_id(token)


@router.post("/stories/{story_id}/generate/blueprint_async", response_model=JobStatusRead)
def generate_story_blueprint_async(
    story_id: uuid.UUID,
    payload: StoryGenerateRequest,
    response: Response,
    db=DbSessionDep,
):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    existing_scenes = list(db.execute(select(Scene).where(Scene.story_id == story_id)).scalars().all())
    if existing_scenes and not payload.allow_append:
        raise HTTPException(
            status_code=400,
            detail="story already has scenes; set allow_append to true to append more",
        )

    if payload.style_id and not has_image_style(payload.style_id):
        raise HTTPException(status_code=400, detail="unknown style_id")

    story.generation_status = "queued"
    story.generation_error = None
    story.progress = {
        "current_node": "Queued",
        "message": "Queued for generation...",
        "step": 0,
        "total_steps": 5,
    }
    story.progress_updated_at = datetime.utcnow()
    db.add(story)
    db.commit()
    log_audit_entry(
        db,
        entity_type="story",
        entity_id=story_id,
        action="generation_queued",
        new_value={"generation_status": "queued"},
    )

    job = job_queue.enqueue_job(
        "story_blueprint",
        {"story_id": str(story_id), "request": payload.model_dump()},
        _handle_story_blueprint_job,
        request_id=get_request_id(),
    )
    response.status_code = 202

    return JobStatusRead(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        progress=job.progress,
        result=job.result,
        error=job.error,
    )


@router.get("/stories/{story_id}/progress", response_model=StoryProgressRead)
def get_story_progress(story_id: uuid.UUID, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    # Convert dict to typed StoryProgress model if present
    typed_progress = None
    if story.progress and isinstance(story.progress, dict):
        try:
            typed_progress = StoryProgress.model_validate(story.progress)
        except Exception:
            # Fall back to None if the dict doesn't match the expected schema
            typed_progress = None

    return StoryProgressRead(
        story_id=story_id,
        status=story.generation_status,
        progress=typed_progress,
        error=story.generation_error,
        updated_at=story.progress_updated_at,
    )


@router.post("/stories/{story_id}/set-style-defaults", response_model=StoryRead)
def set_story_style_defaults(story_id: uuid.UUID, payload: StorySetStyleDefaultsRequest, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    if not has_image_style(payload.default_image_style):
        raise HTTPException(status_code=400, detail="unknown default_image_style")

    story.default_image_style = payload.default_image_style
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


@router.post("/stories/{story_id}/estimate-scenes", response_model=SceneEstimationResponse)
async def estimate_scene_count(
    story_id: uuid.UUID,
    payload: SceneEstimationRequest,
    db=DbSessionDep,
):
    """
    Recommend the optimal number of scenes for a story.

    Analyzes the story text to recommend a scene count targeting a webtoon video
    duration of 60-90 seconds (approximately 80 seconds ideal).

    - **Ideal range**: 7-15 scenes
    - **too_short**: Story has minimal content, minimum 5 scenes recommended
    - **too_long**: Story is complex, consider splitting into episodes
    - **ok**: Story fits well within target duration

    If source_text is not provided, the endpoint will concatenate existing scenes'
    source_text from the story.
    """
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    # Get source text from request or from existing scenes
    source_text = payload.source_text
    if not source_text:
        # Concatenate existing scenes' source_text
        scenes = db.scalars(
            select(Scene)
            .where(Scene.story_id == story_id)
            .order_by(Scene.created_at)
        ).all()
        if scenes:
            source_text = "\n\n".join(s.source_text for s in scenes if s.source_text)

    if not source_text:
        raise HTTPException(
            status_code=400,
            detail="No source text provided and story has no existing scenes",
        )

    # Perform estimation
    if payload.use_llm:
        try:
            gemini_client = _build_gemini_client()
            estimation = await estimate_scene_count_llm(source_text, gemini_client)
        except HTTPException:
            # Gemini not configured, fall back to heuristic
            estimation = estimate_scene_count_heuristic(source_text)
    else:
        estimation = estimate_scene_count_heuristic(source_text)

    # Build response
    analysis = None
    if estimation.analysis:
        analysis = SceneAnalysisRead(
            narrative_beats=estimation.analysis.narrative_beats,
            estimated_duration_seconds=estimation.analysis.estimated_duration_seconds,
            pacing=estimation.analysis.pacing.value,
            complexity=estimation.analysis.complexity.value,
            dialogue_density=estimation.analysis.dialogue_density.value,
            key_moments=estimation.analysis.key_moments,
        )


@router.post("/utils/estimate-scenes", response_model=SceneEstimationResponse)
async def estimate_scene_count_stateless(
    payload: SceneEstimationRequest,
):
    """
    Stateless version of scene estimation.
    Does not require a story_id. Takes source_text directly.
    """
    source_text = payload.source_text
    if not source_text:
        raise HTTPException(
            status_code=400,
            detail="source_text is required for stateless estimation",
        )

    # Perform estimation
    if payload.use_llm:
        try:
            gemini_client = _build_gemini_client()
            estimation = await estimate_scene_count_llm(source_text, gemini_client)
        except HTTPException:
            # Gemini not configured, fall back to heuristic
            estimation = estimate_scene_count_heuristic(source_text)
    else:
        estimation = estimate_scene_count_heuristic(source_text)

    # Build response
    analysis = None
    if estimation.analysis:
        analysis = SceneAnalysisRead(
            narrative_beats=estimation.analysis.narrative_beats,
            estimated_duration_seconds=estimation.analysis.estimated_duration_seconds,
            pacing=estimation.analysis.pacing.value,
            complexity=estimation.analysis.complexity.value,
            dialogue_density=estimation.analysis.dialogue_density.value,
            key_moments=estimation.analysis.key_moments,
        )

    return SceneEstimationResponse(
        recommended_count=estimation.recommended_count,
        status=estimation.status.value,
        message=estimation.message,
        analysis=analysis,
    )
