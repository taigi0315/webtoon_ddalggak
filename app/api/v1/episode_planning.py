import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.core.gemini_factory import build_gemini_client
from app.db.models import Episode, EpisodeScene, Scene
from app.graphs.pipeline import run_full_pipeline


router = APIRouter(tags=["episode-planning"])


class EpisodePlanRequest(BaseModel):
    scenes: list[uuid.UUID] | None = None
    mode: str = Field(default="draft", min_length=1)
    style_id: str = Field(min_length=1)


class EpisodePlanResponse(BaseModel):
    planned_scene_ids: list[uuid.UUID]


@router.post("/episodes/{episode_id}/generate/plan", response_model=EpisodePlanResponse)
def generate_episode_plan(episode_id: uuid.UUID, payload: EpisodePlanRequest, db=DbSessionDep):
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="episode not found")

    if payload.scenes is None:
        scene_ids = (
            db.execute(
                select(EpisodeScene.scene_id)
                .where(EpisodeScene.episode_id == episode_id)
                .order_by(EpisodeScene.order_index.asc())
            )
            .scalars()
            .all()
        )
    else:
        scene_ids = payload.scenes

    if not scene_ids:
        raise HTTPException(status_code=400, detail="no scenes to plan")

    planned: list[uuid.UUID] = []
    for scene_id in scene_ids:
        scene = db.get(Scene, scene_id)
        if scene is None or scene.story_id != episode.story_id:
            raise HTTPException(status_code=400, detail="scene does not belong to episode story")
        if payload.mode != "draft":
            gemini = build_gemini_client()
            run_full_pipeline(
                db=db,
                scene_id=scene_id,
                panel_count=3,
                style_id=payload.style_id,
                genre=None,
                gemini=gemini,
            )
        planned.append(scene_id)

    return EpisodePlanResponse(planned_scene_ids=planned)
