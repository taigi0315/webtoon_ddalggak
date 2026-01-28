import uuid
import os
import time
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.api.deps import DbSessionDep
from app.api.v1.schemas import ExportRead
from app.core.settings import settings
from app.db.models import Episode, EpisodeScene, ExportJob, Layer, Scene, DialogueLayer
from app.graphs import nodes
from app.services.artifacts import ArtifactService


router = APIRouter(tags=["exports"])
logger = logging.getLogger(__name__)


@router.post("/scenes/{scene_id}/export", response_model=ExportRead)
def create_scene_export(scene_id: uuid.UUID, db=DbSessionDep):
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    latest = ArtifactService(db).get_latest_artifact(scene_id, nodes.ARTIFACT_RENDER_RESULT)
    if latest is not None:
        output_url = latest.payload.get("image_url")
        job = ExportJob(
            scene_id=scene_id,
            episode_id=None,
            status="succeeded" if output_url else "queued",
            output_url=output_url,
            metadata_={"source": "render_result", "artifact_id": str(latest.artifact_id)},
        )
    else:
        job = ExportJob(scene_id=scene_id, episode_id=None, status="queued", output_url=None, metadata_={})
    
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/episodes/{episode_id}/export", response_model=ExportRead)
def create_episode_export(episode_id: uuid.UUID, db=DbSessionDep):
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="episode not found")

    scene_ids = (
        db.query(EpisodeScene.scene_id)
        .filter(EpisodeScene.episode_id == episode_id)
        .order_by(EpisodeScene.order_index.asc())
        .all()
    )
    ordered_scene_ids = [row[0] for row in scene_ids]
    images: list[dict] = []
    all_ready = True
    svc = ArtifactService(db)
    for scene_id in ordered_scene_ids:
        latest = svc.get_latest_artifact(scene_id, nodes.ARTIFACT_RENDER_RESULT)
        if latest is None:
            all_ready = False
            images.append({"scene_id": str(scene_id), "image_url": None})
        else:
            images.append({"scene_id": str(scene_id), "image_url": latest.payload.get("image_url")})
            if not latest.payload.get("image_url"):
                all_ready = False

    status = "succeeded" if all_ready and ordered_scene_ids else "queued"
    job = ExportJob(
        scene_id=None,
        episode_id=episode_id,
        status=status,
        output_url=None,
        metadata_={"scenes": images},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/exports/{export_id}", response_model=ExportRead)
def get_export(export_id: uuid.UUID, db=DbSessionDep):
    job = db.get(ExportJob, export_id)
    if job is None:
        raise HTTPException(status_code=404, detail="export not found")
    # Fail stuck processing jobs after 10 minutes
    if job.status == "processing":
        started_at = None
        if isinstance(job.metadata_, dict):
            started_at = job.metadata_.get("started_at")
        if isinstance(started_at, (int, float)) and time.time() - float(started_at) > 600:
            job.status = "failed"
            job.metadata_["error"] = "Video export timed out."
            db.add(job)
            db.commit()
            db.refresh(job)
    return job


@router.get("/exports/{export_id}/download")
def download_export(export_id: uuid.UUID, db=DbSessionDep):
    job = db.get(ExportJob, export_id)
    if job is None:
        raise HTTPException(status_code=404, detail="export not found")
    if not job.output_url:
        if job.status == "succeeded":
            if job.scene_id:
                return {"manifest": {"scene_id": str(job.scene_id), "layers": job.metadata_.get("layers", [])}}
            return {"manifest": job.metadata_.get("scenes", [])}
        raise HTTPException(status_code=400, detail="export not ready")
    return {"download_url": job.output_url}


@router.post("/exports/{export_id}/finalize", response_model=ExportRead)
def finalize_export(export_id: uuid.UUID, db=DbSessionDep):
    job = db.get(ExportJob, export_id)
    if job is None:
        raise HTTPException(status_code=404, detail="export not found")

    if job.scene_id:
        latest = ArtifactService(db).get_latest_artifact(job.scene_id, nodes.ARTIFACT_RENDER_RESULT)
        if latest is None or not latest.payload.get("image_url"):
            raise HTTPException(status_code=400, detail="render output missing")
        layer_rows = db.query(Layer).filter(Layer.scene_id == job.scene_id).all()
        layers = [
            {"layer_id": str(layer.layer_id), "layer_type": layer.layer_type, "objects": layer.objects}
            for layer in layer_rows
        ]
        dialogue_layer = (
            db.query(DialogueLayer).filter(DialogueLayer.scene_id == job.scene_id).one_or_none()
        )
        dialogue_bubbles = []
        if dialogue_layer is not None:
            for bubble in dialogue_layer.bubbles:
                dialogue_bubbles.append(
                    {
                        "text": bubble.get("text", ""),
                        "speaker": bubble.get("speaker", ""),
                        "geometry": {
                            "x": bubble.get("position", {}).get("x", 0.1),
                            "y": bubble.get("position", {}).get("y", 0.1),
                            "w": bubble.get("size", {}).get("w", 0.3),
                            "h": bubble.get("size", {}).get("h", 0.15),
                        },
                    }
                )
        job.output_url = latest.payload.get("image_url")
        job.status = "succeeded"
        job.metadata_ = {
            "source": "render_result",
            "artifact_id": str(latest.artifact_id),
            "layers": layers,
            "dialogue_bubbles": dialogue_bubbles,
        }
    elif job.episode_id:
        scene_ids = (
            db.query(EpisodeScene.scene_id)
            .filter(EpisodeScene.episode_id == job.episode_id)
            .order_by(EpisodeScene.order_index.asc())
            .all()
        )
        ordered_scene_ids = [row[0] for row in scene_ids]
        images: list[dict] = []
        svc = ArtifactService(db)
        for scene_id in ordered_scene_ids:
            latest = svc.get_latest_artifact(scene_id, nodes.ARTIFACT_RENDER_RESULT)
            if latest is None or not latest.payload.get("image_url"):
                raise HTTPException(status_code=400, detail="render output missing")
            layer_rows = db.query(Layer).filter(Layer.scene_id == scene_id).all()
            layers = [
                {"layer_id": str(layer.layer_id), "layer_type": layer.layer_type, "objects": layer.objects}
                for layer in layer_rows
            ]
            dialogue_layer = (
                db.query(DialogueLayer).filter(DialogueLayer.scene_id == scene_id).one_or_none()
            )
            dialogue_bubbles = []
            if dialogue_layer is not None:
                for bubble in dialogue_layer.bubbles:
                    dialogue_bubbles.append(
                        {
                            "text": bubble.get("text", ""),
                            "speaker": bubble.get("speaker", ""),
                            "geometry": {
                                "x": bubble.get("position", {}).get("x", 0.1),
                                "y": bubble.get("position", {}).get("y", 0.1),
                                "w": bubble.get("size", {}).get("w", 0.3),
                                "h": bubble.get("size", {}).get("h", 0.15),
                            },
                        }
                    )
            images.append(
                {
                    "scene_id": str(scene_id),
                    "image_url": latest.payload.get("image_url"),
                    "layers": layers,
                    "dialogue_bubbles": dialogue_bubbles,
                }
            )
        job.status = "succeeded"
        job.metadata_ = {"scenes": images}
    else:
        raise HTTPException(status_code=400, detail="export target missing")

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _generate_video_background(export_id: uuid.UUID, db_session_factory):
    """Background task to generate video from export."""
    from sqlalchemy.orm import Session
    from app.services.video import generate_video_from_export_data

    db: Session = db_session_factory()
    try:
        job = db.get(ExportJob, export_id)
        if job is None:
            return

        try:
            video_path = generate_video_from_export_data(
                export_metadata=job.metadata_,
                media_root=settings.media_root,
                output_dir=os.path.join(settings.media_root, "videos"),
            )

            # Update job with video URL
            video_url = f"/media/videos/{os.path.basename(video_path)}"
            job.output_url = video_url
            job.status = "succeeded"
            job.metadata_["video_path"] = video_path
            db.add(job)
            db.commit()

        except Exception as e:
            logger.exception("video_generation_failed export_id=%s error=%s", export_id, e)
            job.status = "failed"
            if job.metadata_ is None:
                job.metadata_ = {}
            job.metadata_["error"] = str(e)
            db.add(job)
            db.commit()
            return

    finally:
        db.close()


@router.post("/exports/{export_id}/generate-video", response_model=ExportRead)
def generate_video_export(
    export_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db=DbSessionDep,
):
    """Generate a video from an episode export.

    The export must be finalized first. Video generation runs in the background.
    Check the export status to see when it's complete.
    """
    job = db.get(ExportJob, export_id)
    if job is None:
        raise HTTPException(status_code=404, detail="export not found")

    if job.status != "succeeded":
        raise HTTPException(status_code=400, detail="export must be finalized first")

    if not job.episode_id:
        raise HTTPException(status_code=400, detail="video export only supported for episodes")

    if not job.metadata_.get("scenes"):
        raise HTTPException(status_code=400, detail="no scenes in export metadata")

    # Mark as processing
    job.status = "processing"
    if job.metadata_ is None:
        job.metadata_ = {}
    job.metadata_["started_at"] = time.time()
    db.add(job)
    db.commit()
    db.refresh(job)

    # Start background video generation
    # Note: We need to pass the session factory, not the session itself
    from app.db.session import get_sessionmaker
    background_tasks.add_task(_generate_video_background, export_id, get_sessionmaker())

    return job


@router.get("/exports/{export_id}/video")
def download_video_export(export_id: uuid.UUID, db=DbSessionDep):
    """Download the generated video file."""
    job = db.get(ExportJob, export_id)
    if job is None:
        raise HTTPException(status_code=404, detail="export not found")

    video_path = job.metadata_.get("video_path")
    if not video_path or not os.path.exists(video_path):
        if job.status == "processing":
            raise HTTPException(status_code=202, detail="video generation in progress")
        raise HTTPException(status_code=404, detail="video not found")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"webtoon_export_{export_id}.mp4",
    )
