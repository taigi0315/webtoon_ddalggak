import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSessionDep
from app.api.v1.schemas import DialogueLayerCreate, DialogueLayerRead, DialogueLayerUpdate
from app.db.models import DialogueLayer, Scene


router = APIRouter(tags=["dialogue"])


@router.post("/scenes/{scene_id}/dialogue", response_model=DialogueLayerRead)
def create_dialogue(scene_id: uuid.UUID, payload: DialogueLayerCreate, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    existing = db.query(DialogueLayer).filter(DialogueLayer.scene_id == scene_id).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="dialogue already exists for scene")

    layer = DialogueLayer(scene_id=scene_id, bubbles=payload.bubbles)
    db.add(layer)
    db.commit()
    db.refresh(layer)
    return layer


@router.put("/dialogue/{dialogue_id}", response_model=DialogueLayerRead)
def update_dialogue(dialogue_id: uuid.UUID, payload: DialogueLayerUpdate, db=DbSessionDep):
    layer = db.get(DialogueLayer, dialogue_id)
    if layer is None:
        raise HTTPException(status_code=404, detail="dialogue not found")

    layer.bubbles = payload.bubbles
    db.add(layer)
    db.commit()
    db.refresh(layer)
    return layer


@router.get("/scenes/{scene_id}/dialogue", response_model=DialogueLayerRead)
def get_dialogue(scene_id: uuid.UUID, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    layer = db.query(DialogueLayer).filter(DialogueLayer.scene_id == scene_id).one_or_none()
    if layer is None:
        raise HTTPException(status_code=404, detail="dialogue not found")
    return layer
