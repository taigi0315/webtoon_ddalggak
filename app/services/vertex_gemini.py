import time
import uuid
import logging
from typing import Any, Dict

import vertexai
from vertexai.generative_models import GenerativeModel, Image, Part

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(
        self,
        project: str | None,
        location: str,
        text_model: str,
        image_model: str,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        initial_backoff_seconds: float = 0.8,
    ):
        self._project = project
        self._location = location
        self._text_model = text_model
        self._image_model = image_model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._initial_backoff_seconds = initial_backoff_seconds

        self.last_request_id: str | None = None
        self.last_model: str | None = None
        self.last_usage: dict | None = None

        # Initialize Vertex AI
        vertexai.init(project=project, location=location)

    def generate_text(self, prompt: str, model: str | None = None) -> str:
        model_name = model or self._text_model
        request_id = str(uuid.uuid4())

        self.last_request_id = request_id
        self.last_model = model_name
        self.last_usage = None

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                gemini_model = GenerativeModel(model_name)
                resp = gemini_model.generate_content(prompt)
                # Usage metadata is not directly exposed in Vertex AI SDK; we store a placeholder
                self.last_usage = {"model": model_name}
                if not resp.candidates:
                    raise RuntimeError("Gemini returned no candidates")
                candidate = resp.candidates[0]
                if candidate.content is None or not candidate.content.parts:
                    raise RuntimeError("Gemini returned empty content")
                texts: list[str] = []
                for part in candidate.content.parts:
                    text = getattr(part, "text", None)
                    if text:
                        texts.append(text)
                return "\n".join(texts).strip()
            except Exception as e:
                last_exc = e
                backoff = self._initial_backoff_seconds * (2**attempt)
                logger.warning(
                    "gemini.generate_text failed request_id=%s model=%s attempt=%s error=%s",
                    request_id,
                    model_name,
                    attempt + 1,
                    repr(e),
                )
                if attempt + 1 >= self._max_retries:
                    break
                time.sleep(backoff)

        raise RuntimeError(f"Gemini generate_text failed after retries: {last_exc!r}")

    def generate_image(self, prompt: str, model: str | None = None) -> tuple[bytes, str]:
        model_name = model or self._image_model
        request_id = str(uuid.uuid4())

        self.last_request_id = request_id
        self.last_model = model_name
        self.last_usage = None

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                gemini_model = GenerativeModel(model_name)
                resp = gemini_model.generate_content(
                    [prompt],
                    generation_config={
                        "temperature": 0.9,
                        "top_p": 0.8,
                        "top_k": 40,
                        "candidate_count": 1,
                        "max_output_tokens": 8192,
                    },
                )
                self.last_usage = {"model": model_name}
                if not resp.candidates:
                    raise RuntimeError("Gemini returned no candidates")
                candidate = resp.candidates[0]
                if candidate.content is None or not candidate.content.parts:
                    raise RuntimeError("Gemini returned empty content")
                # Extract image bytes from response
                for part in candidate.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        img_bytes = part.inline_data.data
                        mime_type = part.inline_data.mime_type or "image/png"
                        return img_bytes, mime_type
                raise RuntimeError("Gemini returned no image data")
            except Exception as e:
                last_exc = e
                backoff = self._initial_backoff_seconds * (2**attempt)
                logger.warning(
                    "gemini.generate_image failed request_id=%s model=%s attempt=%s error=%s",
                    request_id,
                    model_name,
                    attempt + 1,
                    repr(e),
                )
                if attempt + 1 >= self._max_retries:
                    break
                time.sleep(backoff)

        raise RuntimeError(f"Gemini generate_image failed after retries: {last_exc!r}")
