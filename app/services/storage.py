import os
import uuid


def _ext_from_mime(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if mime == "image/png":
        return ".png"
    if mime in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if mime == "image/webp":
        return ".webp"
    return ".bin"


class LocalMediaStore:
    def __init__(self, root_dir: str, url_prefix: str):
        self.root_dir = root_dir
        self.url_prefix = url_prefix.rstrip("/")

    def save_image_bytes(self, image_bytes: bytes, mime_type: str) -> tuple[str, str]:
        os.makedirs(self.root_dir, exist_ok=True)

        file_id = str(uuid.uuid4())
        ext = _ext_from_mime(mime_type)
        filename = f"{file_id}{ext}"
        file_path = os.path.join(self.root_dir, filename)

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        url = f"{self.url_prefix}/{filename}"
        return file_path, url
