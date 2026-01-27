import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSessionDep
from app.api.v1.schemas import LayerCreate, LayerRead, LayerUpdate
from app.db.models import Layer, Scene


router = APIRouter(tags=["layers"])

_ALLOWED_LAYER_TYPES = {"dialogue", "narration", "sfx"}


@router.post("/scenes/{scene_id}/layers", response_model=LayerRead)
def create_layer(scene_id: uuid.UUID, payload: LayerCreate, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")
    if payload.layer_type not in _ALLOWED_LAYER_TYPES:
        raise HTTPException(status_code=400, detail="invalid layer_type")

    layer = Layer(scene_id=scene_id, layer_type=payload.layer_type, objects=[obj.model_dump(by_alias=True) for obj in payload.objects])
    db.add(layer)
    db.commit()
    db.refresh(layer)
    return LayerRead(
        layer_id=layer.layer_id,
        scene_id=layer.scene_id,
        layer_type=layer.layer_type,
        objects=layer.objects,
    )


@router.put("/layers/{layer_id}", response_model=LayerRead)
def update_layer(layer_id: uuid.UUID, payload: LayerUpdate, db=DbSessionDep):
    layer = db.get(Layer, layer_id)
    if layer is None:
        raise HTTPException(status_code=404, detail="layer not found")

    layer.objects = [obj.model_dump(by_alias=True) for obj in payload.objects]
    db.add(layer)
    db.commit()
    db.refresh(layer)
    return LayerRead(
        layer_id=layer.layer_id,
        scene_id=layer.scene_id,
        layer_type=layer.layer_type,
        objects=layer.objects,
    )


@router.get("/scenes/{scene_id}/layers", response_model=list[LayerRead])
def list_layers(scene_id: uuid.UUID, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    layers = db.query(Layer).filter(Layer.scene_id == scene_id).all()
    return [
        LayerRead(
            layer_id=layer.layer_id,
            scene_id=layer.scene_id,
            layer_type=layer.layer_type,
            objects=layer.objects,
        )
        for layer in layers
    ]
