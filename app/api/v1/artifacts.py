import uuid

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSessionDep
from app.api.v1.schemas import ArtifactRead
from app.db.models import Artifact, Scene
from app.services.artifacts import ArtifactService


router = APIRouter(tags=["artifacts"])


@router.get("/scenes/{scene_id}/artifacts", response_model=list[ArtifactRead])
def list_scene_artifacts(scene_id: uuid.UUID, type: str | None = Query(default=None), db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    service = ArtifactService(db)
    return service.list_artifacts(scene_id=scene_id, type=type)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: uuid.UUID, db=DbSessionDep):
    artifact = db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return artifact
