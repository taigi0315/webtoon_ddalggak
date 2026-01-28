import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    DialogueLayerCreate,
    DialogueLayerRead,
    DialogueLayerUpdate,
    DialogueSuggestionsRead,
)
from app.db.models import DialogueLayer, Scene, Character
from app.services.artifacts import ArtifactService
from app.graphs import nodes
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

    bubbles = [bubble.model_dump(mode="json") for bubble in payload.bubbles]
    layer = DialogueLayer(scene_id=scene_id, bubbles=bubbles)
    db.add(layer)
    db.commit()
    db.refresh(layer)
    return layer


@router.put("/dialogue/{dialogue_id}", response_model=DialogueLayerRead)
def update_dialogue(dialogue_id: uuid.UUID, payload: DialogueLayerUpdate, db=DbSessionDep):
    layer = db.get(DialogueLayer, dialogue_id)
    if layer is None:
        raise HTTPException(status_code=404, detail="dialogue not found")

    layer.bubbles = [bubble.model_dump(mode="json") for bubble in payload.bubbles]
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

    svc = ArtifactService(db)
    artifact = svc.get_latest_artifact(scene_id, ARTIFACT_DIALOGUE_SUGGESTIONS)
    suggestions = artifact.payload.get("suggestions", []) if artifact else []

    if not artifact:
        suggestions = nodes._extract_dialogue_suggestions(scene.source_text)

    characters = list(
        db.execute(select(Character).where(Character.story_id == scene.story_id)).scalars().all()
    )
    names = [char.name for char in characters if char.name]
    has_unknown = any((item.get("speaker") in {None, "", "unknown"} for item in suggestions))

    if names and has_unknown:
        idx = 0
        for item in suggestions:
            speaker = item.get("speaker")
            if not speaker or speaker == "unknown":
                item["speaker"] = names[idx % len(names)]
                idx += 1

        artifact = svc.create_artifact(
            scene_id=scene_id,
            type=ARTIFACT_DIALOGUE_SUGGESTIONS,
            payload={"suggestions": suggestions},
        )
    elif artifact is None:
        artifact = svc.create_artifact(
            scene_id=scene_id,
            type=ARTIFACT_DIALOGUE_SUGGESTIONS,
            payload={"suggestions": suggestions},
        )

    return DialogueSuggestionsRead(
        scene_id=scene_id,
        suggestions=artifact.payload.get("suggestions", []),
    )
