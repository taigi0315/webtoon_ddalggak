import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSessionDep
from app.api.v1.schemas import SceneCreate, SceneRead
from app.db.models import Scene, Story


router = APIRouter(tags=["scenes"])


@router.post("/stories/{story_id}/scenes", response_model=SceneRead)
def create_scene(story_id: uuid.UUID, payload: SceneCreate, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    scene = Scene(story_id=story_id, source_text=payload.source_text)
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
