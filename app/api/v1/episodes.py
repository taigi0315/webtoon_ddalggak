import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    EpisodeAssetRead,
    EpisodeAssetCreate,
    EpisodeCreate,
    EpisodeRead,
    EpisodeScenesUpdate,
    EpisodeSetStyleRequest,
)
from app.config.loaders import has_image_style, has_story_style
from app.db.models import Episode, EpisodeAsset, EpisodeScene, Scene, Story


router = APIRouter(tags=["episodes"])

_ALLOWED_ASSET_TYPES = {"character", "environment", "style"}


def _episode_or_404(db, episode_id: uuid.UUID) -> Episode:
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="episode not found")
    return episode


def _scene_ids_ordered(db, episode_id: uuid.UUID) -> list[uuid.UUID]:
    rows = (
        db.execute(
            select(EpisodeScene.scene_id)
            .where(EpisodeScene.episode_id == episode_id)
            .order_by(EpisodeScene.order_index.asc())
        )
        .scalars()
        .all()
    )
    return list(rows)


@router.post("/stories/{story_id}/episodes", response_model=EpisodeRead)
def create_episode(story_id: uuid.UUID, payload: EpisodeCreate, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")
    if not has_story_style(payload.default_story_style):
        raise HTTPException(status_code=400, detail="unknown default_story_style")
    if not has_image_style(payload.default_image_style):
        raise HTTPException(status_code=400, detail="unknown default_image_style")

    episode = Episode(
        story_id=story_id,
        title=payload.title,
        default_story_style=payload.default_story_style,
        default_image_style=payload.default_image_style,
        status="draft",
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)

    return EpisodeRead(
        episode_id=episode.episode_id,
        story_id=episode.story_id,
        title=episode.title,
        default_story_style=episode.default_story_style,
        default_image_style=episode.default_image_style,
        status=episode.status,
        scene_ids_ordered=[],
    )


@router.get("/stories/{story_id}/episodes", response_model=list[EpisodeRead])
def list_story_episodes(story_id: uuid.UUID, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    episodes = list(db.execute(select(Episode).where(Episode.story_id == story_id)).scalars().all())
    result: list[EpisodeRead] = []
    for episode in episodes:
        result.append(
            EpisodeRead(
                episode_id=episode.episode_id,
                story_id=episode.story_id,
                title=episode.title,
                default_story_style=episode.default_story_style,
                default_image_style=episode.default_image_style,
                status=episode.status,
                scene_ids_ordered=_scene_ids_ordered(db, episode.episode_id),
            )
        )
    return result


@router.get("/episodes/{episode_id}", response_model=EpisodeRead)
def get_episode(episode_id: uuid.UUID, db=DbSessionDep):
    episode = _episode_or_404(db, episode_id)
    return EpisodeRead(
        episode_id=episode.episode_id,
        story_id=episode.story_id,
        title=episode.title,
        default_story_style=episode.default_story_style,
        default_image_style=episode.default_image_style,
        status=episode.status,
        scene_ids_ordered=_scene_ids_ordered(db, episode_id),
    )


@router.post("/episodes/{episode_id}/scenes", response_model=EpisodeRead)
def set_episode_scenes(episode_id: uuid.UUID, payload: EpisodeScenesUpdate, db=DbSessionDep):
    episode = _episode_or_404(db, episode_id)

    for scene_id in payload.scene_ids_ordered:
        scene = db.get(Scene, scene_id)
        if scene is None:
            raise HTTPException(status_code=400, detail=f"scene not found: {scene_id}")
        if scene.story_id != episode.story_id:
            raise HTTPException(status_code=400, detail="scene does not belong to episode story")

    db.execute(delete(EpisodeScene).where(EpisodeScene.episode_id == episode_id))
    for idx, scene_id in enumerate(payload.scene_ids_ordered):
        db.add(EpisodeScene(episode_id=episode_id, scene_id=scene_id, order_index=idx))

    db.commit()
    db.refresh(episode)

    return EpisodeRead(
        episode_id=episode.episode_id,
        story_id=episode.story_id,
        title=episode.title,
        default_story_style=episode.default_story_style,
        default_image_style=episode.default_image_style,
        status=episode.status,
        scene_ids_ordered=_scene_ids_ordered(db, episode_id),
    )


@router.post("/episodes/{episode_id}/set-style", response_model=EpisodeRead)
def set_episode_style(episode_id: uuid.UUID, payload: EpisodeSetStyleRequest, db=DbSessionDep):
    episode = _episode_or_404(db, episode_id)
    if not has_story_style(payload.default_story_style):
        raise HTTPException(status_code=400, detail="unknown default_story_style")
    if not has_image_style(payload.default_image_style):
        raise HTTPException(status_code=400, detail="unknown default_image_style")

    episode.default_story_style = payload.default_story_style
    episode.default_image_style = payload.default_image_style
    db.add(episode)
    db.commit()
    db.refresh(episode)

    return EpisodeRead(
        episode_id=episode.episode_id,
        story_id=episode.story_id,
        title=episode.title,
        default_story_style=episode.default_story_style,
        default_image_style=episode.default_image_style,
        status=episode.status,
        scene_ids_ordered=_scene_ids_ordered(db, episode_id),
    )


@router.get("/episodes/{episode_id}/assets", response_model=list[EpisodeAssetRead])
def list_episode_assets(episode_id: uuid.UUID, db=DbSessionDep):
    _episode_or_404(db, episode_id)
    assets = (
        db.execute(select(EpisodeAsset).where(EpisodeAsset.episode_id == episode_id))
        .scalars()
        .all()
    )
    return assets


@router.post("/episodes/{episode_id}/assets", response_model=EpisodeAssetRead)
def add_episode_asset(episode_id: uuid.UUID, payload: EpisodeAssetCreate, db=DbSessionDep):
    _episode_or_404(db, episode_id)
    if payload.asset_type not in _ALLOWED_ASSET_TYPES:
        raise HTTPException(status_code=400, detail="invalid asset_type")

    existing = (
        db.execute(
            select(EpisodeAsset).where(
                EpisodeAsset.episode_id == episode_id,
                EpisodeAsset.asset_type == payload.asset_type,
                EpisodeAsset.asset_id == payload.asset_id,
            )
        )
        .scalars()
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="asset already pinned")

    asset = EpisodeAsset(
        episode_id=episode_id,
        asset_type=payload.asset_type,
        asset_id=payload.asset_id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/episodes/{episode_id}/assets/{asset_id}", response_model=dict)
def remove_episode_asset(episode_id: uuid.UUID, asset_id: uuid.UUID, db=DbSessionDep):
    _episode_or_404(db, episode_id)
    asset = (
        db.execute(
            select(EpisodeAsset).where(
                EpisodeAsset.episode_id == episode_id,
                EpisodeAsset.episode_asset_id == asset_id,
            )
        )
        .scalars()
        .one_or_none()
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="episode asset not found")
    db.delete(asset)
    db.commit()
    return {"status": "deleted"}
