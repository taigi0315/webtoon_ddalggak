import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    SceneAutoChunkRequest,
    SceneRead,
    StoryCreate,
    StoryRead,
    StorySetStyleDefaultsRequest,
    StoryGenerateRequest,
    StoryGenerateResponse,
)
from app.config.loaders import has_image_style, has_story_style
from app.core.settings import settings
from app.db.models import Character, Project, Scene, Story
from app.graphs import nodes
from app.graphs.story_build import run_story_build_graph
from app.services.vertex_gemini import GeminiClient


router = APIRouter(tags=["stories"])


def _build_gemini_client() -> GeminiClient:
    if not settings.google_cloud_project and not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Gemini is not configured")

    return GeminiClient(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        api_key=settings.gemini_api_key,
        text_model=settings.gemini_text_model,
        image_model=settings.gemini_image_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
        initial_backoff_seconds=settings.gemini_initial_backoff_seconds,
    )


@router.post("/projects/{project_id}/stories", response_model=StoryRead)
def create_story(project_id: uuid.UUID, payload: StoryCreate, db=DbSessionDep):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    if not has_story_style(payload.default_story_style):
        raise HTTPException(status_code=400, detail="unknown default_story_style")
    if not has_image_style(payload.default_image_style):
        raise HTTPException(status_code=400, detail="unknown default_image_style")

    story = Story(
        project_id=project_id,
        title=payload.title,
        default_story_style=payload.default_story_style,
        default_image_style=payload.default_image_style,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
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

    scenes: list[Scene] = []
    for chunk in chunks:
        scene = Scene(story_id=story_id, source_text=chunk)
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

    gemini = _build_gemini_client()

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
            story_style=story.default_story_style,
            image_style=payload.style_id or story.default_image_style,
            gemini=gemini,
            planning_mode=planning_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    scenes = list(db.execute(select(Scene).where(Scene.story_id == story_id)).scalars().all())

    if payload.generate_render_spec and planning_mode == "full":
        style_id = payload.style_id or story.default_image_style or "default"
        for scene in scenes:
            nodes.run_prompt_compiler(db=db, scene_id=scene.scene_id, style_id=style_id)

    all_characters = list(db.execute(select(Character).where(Character.story_id == story_id)).scalars().all())
    return StoryGenerateResponse(scenes=scenes, characters=all_characters)


@router.post("/stories/{story_id}/set-style-defaults", response_model=StoryRead)
def set_story_style_defaults(story_id: uuid.UUID, payload: StorySetStyleDefaultsRequest, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    if not has_story_style(payload.default_story_style):
        raise HTTPException(status_code=400, detail="unknown default_story_style")
    if not has_image_style(payload.default_image_style):
        raise HTTPException(status_code=400, detail="unknown default_image_style")

    story.default_story_style = payload.default_story_style
    story.default_image_style = payload.default_image_style
    db.add(story)
    db.commit()
    db.refresh(story)
    return story
