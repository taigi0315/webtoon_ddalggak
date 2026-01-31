import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    ArtifactRead,
    SceneCreate,
    ScenePlanningLockRequest,
    SceneRead,
    SceneSetEnvironmentRequest,
    SceneSetStyleRequest,
)
from app.services.artifacts import ArtifactService
from app.config.loaders import has_image_style
from app.db.models import EnvironmentAnchor, Scene, Story
from app.graphs import nodes
from app.services.artifacts import ArtifactService


router = APIRouter(tags=["scenes"])


@router.post("/stories/{story_id}/scenes", response_model=SceneRead)
def create_scene(story_id: uuid.UUID, payload: SceneCreate, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    if payload.environment_id is not None:
        env = db.get(EnvironmentAnchor, payload.environment_id)
        if env is None:
            raise HTTPException(status_code=400, detail="environment not found")

    scene = Scene(
        story_id=story_id,
        environment_id=payload.environment_id,
        source_text=payload.source_text,
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


@router.get("/scenes/{scene_id}", response_model=SceneRead)
def get_scene(scene_id: uuid.UUID, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")
    return scene


@router.get("/stories/{story_id}/scenes", response_model=list[SceneRead])
def list_story_scenes(story_id: uuid.UUID, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    scenes = db.execute(select(Scene).where(Scene.story_id == story_id)).scalars().all()
    return list(scenes)


@router.post("/scenes/{scene_id}/planning/lock", response_model=SceneRead)
def set_planning_lock(scene_id: uuid.UUID, payload: ScenePlanningLockRequest, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    if payload.locked:
        svc = ArtifactService(db)
        required_types = [
            nodes.ARTIFACT_SCENE_INTENT,
            nodes.ARTIFACT_PANEL_PLAN,
            nodes.ARTIFACT_PANEL_PLAN_NORMALIZED,
            nodes.ARTIFACT_LAYOUT_TEMPLATE,
            nodes.ARTIFACT_PANEL_SEMANTICS,
        ]
        missing = [t for t in required_types if svc.get_latest_artifact(scene_id, t) is None]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"cannot lock planning; missing artifacts: {', '.join(missing)}",
            )

    scene.planning_locked = bool(payload.locked)
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/scenes/{scene_id}/set-style", response_model=SceneRead)
def set_scene_style(scene_id: uuid.UUID, payload: SceneSetStyleRequest, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    if "image_style_id" in payload.model_fields_set:
        if payload.image_style_id is not None and not has_image_style(payload.image_style_id):
            raise HTTPException(status_code=400, detail="unknown image_style_id")
        scene.image_style_override = payload.image_style_id

    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/scenes/{scene_id}/set-environment", response_model=SceneRead)
def set_scene_environment(scene_id: uuid.UUID, payload: SceneSetEnvironmentRequest, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    if payload.environment_id is not None:
        env = db.get(EnvironmentAnchor, payload.environment_id)
        if env is None:
            raise HTTPException(status_code=400, detail="environment not found")
        scene.environment_id = payload.environment_id
    else:
        scene.environment_id = None

    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


@router.get("/scenes/{scene_id}/renders", response_model=list[ArtifactRead])
def list_scene_renders(scene_id: uuid.UUID, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    artifacts = ArtifactService(db).list_artifacts(scene_id=scene_id, type=nodes.ARTIFACT_RENDER_RESULT)
    return artifacts
