import hashlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DbSessionDep
from app.core.settings import settings
from app.services.vertex_gemini import GeminiClient
from app.services.images import ImageService
from app.services.storage import LocalMediaStore


router = APIRouter(tags=["gemini"])


class GenerateImageRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None


class GenerateImageResponse(BaseModel):
    image_id: str
    image_url: str
    mime_type: str


class GenerateTextRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None


class GenerateTextResponse(BaseModel):
    text: str


def _build_client() -> GeminiClient:
    if not settings.google_cloud_project:
        raise HTTPException(status_code=500, detail="GOOGLE_CLOUD_PROJECT is not configured")

    return GeminiClient(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        api_key=settings.gemini_api_key,
        text_model=settings.gemini_text_model,
        image_model=settings.gemini_image_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
        initial_backoff_seconds=settings.gemini_initial_backoff_seconds,
    )


@router.post("/gemini/generate-image", response_model=GenerateImageResponse)
def generate_image(payload: GenerateImageRequest, db=DbSessionDep):
    gemini = _build_client()

    image_bytes, mime_type = gemini.generate_image(prompt=payload.prompt, model=payload.model)

    store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
    _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

    prompt_hash = hashlib.sha256(payload.prompt.encode("utf-8")).hexdigest()
    image = ImageService(db).create_image(
        image_url=url,
        metadata={
            "mime_type": mime_type,
            "model": getattr(gemini, "last_model", None) or (payload.model or settings.gemini_image_model),
            "request_id": getattr(gemini, "last_request_id", None),
            "usage": getattr(gemini, "last_usage", None),
            "prompt_sha256": prompt_hash,
        },
    )

    return GenerateImageResponse(image_id=str(image.image_id), image_url=image.image_url, mime_type=mime_type)


@router.post("/gemini/generate-text", response_model=GenerateTextResponse)
def generate_text(payload: GenerateTextRequest):
    gemini = _build_client()
    text = gemini.generate_text(prompt=payload.prompt, model=payload.model)
    return GenerateTextResponse(text=text)
