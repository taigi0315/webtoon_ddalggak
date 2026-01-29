import uuid

from fastapi import APIRouter, HTTPException
from typing import Literal

from pydantic import BaseModel, Field

from app.api.deps import DbSessionDep
from app.core.settings import settings
from app.db.models import Artifact, Scene
from app.graphs import nodes
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient


router = APIRouter(tags=["review"])


class ArtifactIdResponse(BaseModel):
    artifact_id: uuid.UUID


class ApproveRequest(BaseModel):
    artifact_id: uuid.UUID | None = None


class RegenerateRequest(BaseModel):
    reason: Literal["bad_faces", "bad_mood", "bad_composition"] | None = Field(default=None)


def _scene_or_404(db, scene_id: uuid.UUID) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")
    return scene


def _build_gemini_client() -> GeminiClient:
    return nodes._build_gemini_client()


@router.post("/scenes/{scene_id}/review/regenerate", response_model=ArtifactIdResponse)
def regenerate(scene_id: uuid.UUID, payload: RegenerateRequest | None = None, db=DbSessionDep):
    _scene_or_404(db, scene_id)

    spec = ArtifactService(db).get_latest_artifact(scene_id, nodes.ARTIFACT_RENDER_SPEC)
    if spec is None:
        raise HTTPException(status_code=400, detail="render_spec artifact not found")

    nodes.run_qc_checker(db=db, scene_id=scene_id)

    reason = payload.reason if payload else None
    gemini = _build_gemini_client()
    artifact = nodes.run_image_renderer(db=db, scene_id=scene_id, reason=reason, gemini=gemini)
    return ArtifactIdResponse(artifact_id=artifact.artifact_id)


@router.post("/scenes/{scene_id}/review/approve", response_model=ArtifactIdResponse)
def approve(scene_id: uuid.UUID, payload: ApproveRequest, db=DbSessionDep):
    _scene_or_404(db, scene_id)

    svc = ArtifactService(db)

    target: Artifact | None
    if payload.artifact_id is not None:
        target = svc.get_artifact(payload.artifact_id)
        if target is None:
            raise HTTPException(status_code=404, detail="artifact not found")
        if target.scene_id != scene_id:
            raise HTTPException(status_code=400, detail="artifact does not belong to scene")
        if target.type != nodes.ARTIFACT_RENDER_RESULT:
            raise HTTPException(status_code=400, detail="artifact is not a render_result")
    else:
        target = svc.get_latest_artifact(scene_id, nodes.ARTIFACT_RENDER_RESULT)
        if target is None:
            raise HTTPException(status_code=400, detail="render_result artifact not found")

    new_payload = dict(target.payload or {})
    new_payload["approved"] = True

    approved = svc.create_artifact(
        scene_id=scene_id,
        type=nodes.ARTIFACT_RENDER_RESULT,
        payload=new_payload,
        parent_id=target.artifact_id,
    )
    return ArtifactIdResponse(artifact_id=approved.artifact_id)
