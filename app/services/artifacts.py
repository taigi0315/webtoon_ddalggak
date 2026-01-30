import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.metrics import record_artifact_creation
from app.core.request_context import get_request_id
from app.db.models import Artifact
from app.services.audit import log_audit_entry


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
        for _ in range(3):
            latest = self.db.execute(
                select(Artifact)
                .where(Artifact.scene_id == scene_id, Artifact.type == type)
                .order_by(desc(Artifact.version))
                .limit(1)
            ).scalar_one_or_none()

            next_version = 1
            next_parent_id = parent_id
            if latest is not None:
                next_version = latest.version + 1
                if next_parent_id is None:
                    next_parent_id = latest.artifact_id

            request_id = get_request_id()
            payload_with_request = dict(payload)
            if request_id:
                payload_with_request.setdefault("request_id", request_id)
            artifact = Artifact(
                scene_id=scene_id,
                type=type,
                version=next_version,
                parent_id=next_parent_id,
                payload=payload_with_request,
                created_by=request_id,
                updated_by=request_id,
            )
            self.db.add(artifact)
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                continue
            self.db.refresh(artifact)
            log_audit_entry(
                self.db,
                entity_type="artifact",
                entity_id=artifact.artifact_id,
                action="created",
                new_value={
                    "scene_id": str(scene_id),
                    "type": type,
                    "version": artifact.version,
                },
            )
            record_artifact_creation(type)
            return artifact

        raise IntegrityError(
            "artifact version conflict after retries",
            params=None,
            orig=None,
        )

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
