import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSessionDep
from app.api.v1.schemas import EnvironmentCreate, EnvironmentPromoteRequest, EnvironmentRead
from app.db.models import EnvironmentAnchor


router = APIRouter(tags=["environments"])


@router.post("/environments", response_model=EnvironmentRead)
def create_environment(payload: EnvironmentCreate, db=DbSessionDep):
    env = EnvironmentAnchor(
        description=payload.description,
        pinned=payload.pinned,
        anchor_type="descriptive",
        usage_count=0,
        reference_images=[],
        locked_elements=[],
    )
    db.add(env)
    db.commit()
    db.refresh(env)
    return env


@router.get("/environments/{environment_id}", response_model=EnvironmentRead)
def get_environment(environment_id: uuid.UUID, db=DbSessionDep):
    env = db.get(EnvironmentAnchor, environment_id)
    if env is None:
        raise HTTPException(status_code=404, detail="environment not found")
    return env


@router.post("/environments/{environment_id}/promote", response_model=EnvironmentRead)
def promote_environment(environment_id: uuid.UUID, payload: EnvironmentPromoteRequest, db=DbSessionDep):
    env = db.get(EnvironmentAnchor, environment_id)
    if env is None:
        raise HTTPException(status_code=404, detail="environment not found")

    env.anchor_type = "visual"
    if payload.reference_images:
        env.reference_images = payload.reference_images
    if payload.locked_elements:
        env.locked_elements = payload.locked_elements

    env.usage_count = int(env.usage_count or 0) + 1

    db.add(env)
    db.commit()
    db.refresh(env)
    return env
