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
from app.db.models import Character, Project, Scene, Story
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

    character_profiles = nodes.compute_character_profiles(
        payload.source_text, max_characters=payload.max_characters
    )
    existing_chars = list(db.execute(select(Character).where(Character.story_id == story_id)).scalars().all())
    existing_by_name = {c.name.strip().lower(): c for c in existing_chars if c.name}

    new_characters: list[Character] = []
    for profile in character_profiles:
        name = str(profile.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in existing_by_name:
            continue
        character = Character(
            story_id=story_id,
            name=name,
            description=profile.get("description"),
            role=profile.get("role") or "secondary",
            identity_line=profile.get("identity_line"),
        )
        db.add(character)
        new_characters.append(character)

    if new_characters:
        db.commit()
        for character in new_characters:
            db.refresh(character)

    chunks = nodes.compute_scene_chunker(payload.source_text, max_scenes=payload.max_scenes)
    if not chunks:
        raise HTTPException(status_code=400, detail="story generate produced no scenes")

    scenes: list[Scene] = []
    for chunk in chunks:
        scene = Scene(story_id=story_id, source_text=chunk)
        db.add(scene)
        scenes.append(scene)

    db.commit()
    for scene in scenes:
        db.refresh(scene)

    style_id = payload.style_id or story.default_image_style or "default"
    genre = story.default_story_style or "default"

    for scene in scenes:
        nodes.run_scene_intent_extractor(db=db, scene_id=scene.scene_id, genre=genre)
        nodes.run_panel_plan_generator(db=db, scene_id=scene.scene_id, panel_count=payload.panel_count)
        nodes.run_panel_plan_normalizer(db=db, scene_id=scene.scene_id)
        nodes.run_layout_template_resolver(db=db, scene_id=scene.scene_id)
        nodes.run_panel_semantic_filler(db=db, scene_id=scene.scene_id)
        nodes.run_qc_checker(db=db, scene_id=scene.scene_id)
        # Extract dialogue for chat bubble pre-generation
        nodes.run_dialogue_extractor(db=db, scene_id=scene.scene_id)
        if payload.generate_render_spec:
            nodes.run_prompt_compiler(db=db, scene_id=scene.scene_id, style_id=style_id)

    all_characters = list(
        db.execute(select(Character).where(Character.story_id == story_id)).scalars().all()
    )
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
