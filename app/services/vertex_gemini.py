
import time
import uuid
import logging
from typing import Callable

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


_DEFAULT_IMAGE_CONFIG = types.ImageConfig(aspect_ratio="9:16")
_DEFAULT_SAFETY_SETTINGS = [
    {"category": types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": types.HarmBlockThreshold.BLOCK_NONE},
    {"category": types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": types.HarmBlockThreshold.BLOCK_NONE},
    {"category": types.HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": types.HarmBlockThreshold.BLOCK_NONE},
    {"category": types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": types.HarmBlockThreshold.BLOCK_NONE},
]


class GeminiClient:
    def __init__(
        self,
        project: str | None,
        location: str | None,
        api_key: str | None,
        text_model: str,
        image_model: str,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        initial_backoff_seconds: float = 0.8,
        rate_limit_backoff_seconds: list[float] | None = None,
    ):
        if not api_key and (not project or not location):
            raise RuntimeError(
                "Either GEMINI_API_KEY or both GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be configured"
            )

        self._text_model = text_model
        self._image_model = image_model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._initial_backoff_seconds = initial_backoff_seconds
        self._rate_limit_backoff_seconds = rate_limit_backoff_seconds or [10, 30, 180, 600]

        self.last_request_id: str | None = None
        self.last_model: str | None = None
        self.last_usage: dict | None = None

        if project and location:
            self._client = genai.Client(vertexai=True, project=project, location=location)
        else:
            self._client = genai.Client(api_key=api_key)

    def _retry(
        self,
        func: Callable[[], types.GenerateContentResponse],
        model_name: str,
        request_type: str,
    ) -> types.GenerateContentResponse:
        last_exc: Exception | None = None
        request_id = str(uuid.uuid4())
        attempt = 0
        max_attempts = self._max_retries
        while attempt < max_attempts:
            try:
                response = func()
                self.last_request_id = response.response_id or request_id
                self.last_model = model_name
                if response.usage_metadata:
                    self.last_usage = response.usage_metadata.model_dump()
                else:
                    self.last_usage = {"model": model_name}
                return response
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                error_text = str(exc)
                is_rate_limited = "RESOURCE_EXHAUSTED" in error_text or "429" in error_text
                if is_rate_limited:
                    max_attempts = max(max_attempts, len(self._rate_limit_backoff_seconds) + 1)
                    idx = min(attempt, len(self._rate_limit_backoff_seconds) - 1)
                    backoff = self._rate_limit_backoff_seconds[idx]
                else:
                    backoff = self._initial_backoff_seconds * (2**attempt)
                logger.warning(
                    "gemini.%s failed request_id=%s model=%s attempt=%s error=%s",
                    request_type,
                    request_id,
                    model_name,
                    attempt + 1,
                    repr(exc),
                )
                if attempt + 1 >= max_attempts:
                    break
                time.sleep(backoff)
                attempt += 1
                continue
            attempt += 1

        raise RuntimeError(f"Gemini {request_type} failed after retries: {last_exc!r}")

    def _extract_text_from_response(self, response: types.GenerateContentResponse) -> str:
        candidate = (response.candidates or [None])[0]
        if candidate is None or not candidate.content or not candidate.content.parts:
            raise RuntimeError("Gemini returned empty content")

        texts: list[str] = []
        for part in candidate.content.parts:
            text = part.text
            if text:
                texts.append(text)

        if not texts:
            raise RuntimeError("Gemini returned no textual content")

        return "\n".join(texts).strip()

    def _extract_image(self, response: types.GenerateContentResponse) -> tuple[bytes, str]:
        candidate = (response.candidates or [None])[0]
        if candidate is None or not candidate.content or not candidate.content.parts:
            raise RuntimeError("Gemini returned empty content")

        for part in candidate.content.parts:
            inline_data = part.inline_data
            if inline_data and inline_data.data:
                mime_type = inline_data.mime_type or "image/png"
                return inline_data.data, mime_type

        raise RuntimeError("Gemini returned no image data")

    def generate_text(self, prompt: str, model: str | None = None) -> str:
        model_name = model or self._text_model

        response = self._retry(
            func=lambda: self._client.models.generate_content(
                model=model_name,
                contents=[prompt],
            ),
            model_name=model_name,
            request_type="generate_text",
        )

        return self._extract_text_from_response(response)

    def generate_image(
        self,
        prompt: str,
        model: str | None = None,
        reference_images: list[tuple[bytes, str]] | None = None,
    ) -> tuple[bytes, str]:
        """Generate an image with optional reference images for style/character consistency.

        Args:
            prompt: Text prompt for image generation
            model: Optional model override
            reference_images: Optional list of (image_bytes, mime_type) tuples for reference
        """
        model_name = model or self._image_model

        # Build contents with optional reference images
        contents: list = []

        if reference_images:
            # Add reference images first as context
            for img_bytes, mime_type in reference_images:
                contents.append(
                    types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
                )
            # Add prompt with instruction to maintain character consistency
            contents.append(
                f"Using the reference images above for character appearance consistency:\n\n{prompt}"
            )
        else:
            contents.append(prompt)

        response = self._retry(
            func=lambda: self._client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    image_config=_DEFAULT_IMAGE_CONFIG,
                    safety_settings=_DEFAULT_SAFETY_SETTINGS,
                ),
            ),
            model_name=model_name,
            request_type="generate_image",
        )

        return self._extract_image(response)
