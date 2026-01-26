import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import Artifact


class ArtifactService:
    def __init__(self, db: Session):
        self.db = db

    def create_artifact(
        self,
        scene_id: uuid.UUID,
        type: str,
        payload: dict,
        parent_id: uuid.UUID | None = None,
    ) -> Artifact:
        latest = self.db.execute(
            select(Artifact)
            .where(Artifact.scene_id == scene_id, Artifact.type == type)
            .order_by(desc(Artifact.version))
            .limit(1)
        ).scalar_one_or_none()

        next_version = 1
        if latest is not None:
            next_version = latest.version + 1
            if parent_id is None:
                parent_id = latest.artifact_id

        artifact = Artifact(
            scene_id=scene_id,
            type=type,
            version=next_version,
            parent_id=parent_id,
            payload=payload,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def list_artifacts(self, scene_id: uuid.UUID, type: str | None = None) -> list[Artifact]:
        stmt = select(Artifact).where(Artifact.scene_id == scene_id)
        if type is not None:
            stmt = stmt.where(Artifact.type == type)
        stmt = stmt.order_by(Artifact.type.asc(), Artifact.version.asc())
        return list(self.db.execute(stmt).scalars().all())

    def get_artifact(self, artifact_id: uuid.UUID) -> Artifact | None:
        return self.db.get(Artifact, artifact_id)

    def get_latest_artifact(self, scene_id: uuid.UUID, type: str) -> Artifact | None:
        stmt = (
            select(Artifact)
            .where(Artifact.scene_id == scene_id, Artifact.type == type)
            .order_by(desc(Artifact.version))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_next_version(self, scene_id: uuid.UUID, type: str) -> int:
        stmt = select(func.max(Artifact.version)).where(Artifact.scene_id == scene_id, Artifact.type == type)
        max_version = self.db.execute(stmt).scalar_one_or_none()
        return int(max_version or 0) + 1
