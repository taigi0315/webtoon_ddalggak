import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    DialogueLayerCreate,
    DialogueLayerRead,
    DialogueLayerUpdate,
    DialogueSuggestionsRead,
)
from app.db.models import DialogueLayer, Scene
from app.services.artifacts import ArtifactService
from app.graphs.nodes import ARTIFACT_DIALOGUE_SUGGESTIONS


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


@router.get("/scenes/{scene_id}/dialogue/suggestions", response_model=DialogueSuggestionsRead)
def get_dialogue_suggestions(scene_id: uuid.UUID, db=DbSessionDep):
    """Get pre-generated dialogue suggestions extracted from scene text."""
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    artifact = ArtifactService(db).get_latest_artifact(scene_id, ARTIFACT_DIALOGUE_SUGGESTIONS)
    if artifact is None:
        raise HTTPException(status_code=404, detail="dialogue suggestions not found; run story blueprint first")

    return DialogueSuggestionsRead(
        scene_id=scene_id,
        suggestions=artifact.payload.get("suggestions", []),
    )
