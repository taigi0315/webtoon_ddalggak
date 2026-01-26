import uuid

from sqlalchemy.orm import Session

from app.db.models import Image


class ImageService:
    def __init__(self, db: Session):
        self.db = db

    def create_image(
        self,
        image_url: str,
        artifact_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> Image:
        row = Image(
            artifact_id=artifact_id,
            image_url=image_url,
            metadata_=(metadata or {}),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_image(self, image_id: uuid.UUID) -> Image | None:
        return self.db.get(Image, image_id)
