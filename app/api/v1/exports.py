import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSessionDep
from app.api.v1.schemas import ExportRead
from app.db.models import Episode, EpisodeScene, ExportJob, Layer, Scene
from app.graphs import nodes
from app.services.artifacts import ArtifactService


router = APIRouter(tags=["exports"])


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
        job.output_url = latest.payload.get("image_url")
        job.status = "succeeded"
        job.metadata_ = {
            "source": "render_result",
            "artifact_id": str(latest.artifact_id),
            "layers": layers,
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
            images.append(
                {"scene_id": str(scene_id), "image_url": latest.payload.get("image_url"), "layers": layers}
            )
        job.status = "succeeded"
        job.metadata_ = {"scenes": images}
    else:
        raise HTTPException(status_code=400, detail="export target missing")

    db.add(job)
    db.commit()
    db.refresh(job)
    return job
