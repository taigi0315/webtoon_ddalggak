import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import SceneAutoChunkRequest, SceneRead, StoryCreate, StoryRead, StorySetStyleDefaultsRequest
from app.config.loaders import has_image_style, has_story_style
from app.db.models import Project, Scene, Story
from app.graphs import nodes


router = APIRouter(tags=["stories"])


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
