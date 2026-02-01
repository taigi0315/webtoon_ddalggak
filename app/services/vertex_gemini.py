
import time
import uuid
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.core.metrics import track_gemini_call
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Exception Classes for Graceful Error Handling
# ---------------------------------------------------------------------------


class GeminiError(Exception):
    """Base exception for Gemini-related errors."""

    def __init__(self, message: str, request_id: str | None = None, model: str | None = None):
        super().__init__(message)
        self.request_id = request_id
        self.model = model


class GeminiRateLimitError(GeminiError):
    """Raised when rate limit is exceeded."""

    pass


class GeminiContentFilterError(GeminiError):
    """Raised when content is blocked by safety filters."""

    def __init__(
        self,
        message: str,
        request_id: str | None = None,
        model: str | None = None,
        blocked_categories: list[str] | None = None,
    ):
        super().__init__(message, request_id, model)
        self.blocked_categories = blocked_categories or []


class GeminiTimeoutError(GeminiError):
    """Raised when request times out."""

    pass


class GeminiCircuitOpenError(GeminiError):
    """Raised when circuit breaker is open (too many failures)."""

    def __init__(self, message: str, retry_after: datetime | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class GeminiModelUnavailableError(GeminiError):
    """Raised when the model is unavailable."""

    pass


# ---------------------------------------------------------------------------
# Circuit Breaker Implementation
# ---------------------------------------------------------------------------


@dataclass
class CircuitBreakerState:
    """Tracks circuit breaker state for a specific operation type."""

    failure_count: int = 0
    last_failure_time: datetime | None = None
    circuit_open_until: datetime | None = None
    consecutive_successes: int = 0

    # Configuration
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    half_open_success_threshold: int = 2

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.consecutive_successes = 0
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= self.failure_threshold:
            self.circuit_open_until = datetime.now(timezone.utc) + timedelta(
                seconds=self.recovery_timeout_seconds
            )
            logger.warning(
                "Circuit breaker OPEN: %d failures, retry after %s",
                self.failure_count,
                self.circuit_open_until.isoformat(),
            )

    def record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        self.consecutive_successes += 1

        if self.is_half_open and self.consecutive_successes >= self.half_open_success_threshold:
            self.reset()
            logger.info("Circuit breaker CLOSED: recovered after %d successes", self.consecutive_successes)

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_open_until = None
        self.consecutive_successes = 0

    @property
    def is_open(self) -> bool:
        """Check if circuit is fully open (not allowing any requests)."""
        if self.circuit_open_until is None:
            return False
        return datetime.now(timezone.utc) < self.circuit_open_until

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (allowing test requests)."""
        if self.circuit_open_until is None:
            return False
        return datetime.now(timezone.utc) >= self.circuit_open_until and self.failure_count > 0

    def check_circuit(self) -> None:
        """Check if request is allowed; raise if circuit is open."""
        if self.is_open:
            raise GeminiCircuitOpenError(
                f"Circuit breaker is open due to {self.failure_count} consecutive failures. "
                f"Retry after {self.circuit_open_until.isoformat() if self.circuit_open_until else 'unknown'}",
                retry_after=self.circuit_open_until,
            )


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
        fallback_text_model: str | None = None,
        fallback_image_model: str | None = None,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        if not api_key and (not project or not location):
            raise RuntimeError(
                "Either GEMINI_API_KEY or both GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be configured"
            )

        self._text_model = text_model
        self._image_model = image_model
        self._fallback_text_model = fallback_text_model
        self._fallback_image_model = fallback_image_model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._initial_backoff_seconds = initial_backoff_seconds
        self._rate_limit_backoff_seconds = rate_limit_backoff_seconds or [5, 10, 30, 60, 120, 300]

        self.last_request_id: str | None = None
        self.last_model: str | None = None
        self.last_usage: dict | None = None
        self.last_error_type: str | None = None

        # Circuit breakers for different operation types
        self._circuit_breakers: dict[str, CircuitBreakerState] = {
            "generate_text": CircuitBreakerState(
                failure_threshold=circuit_breaker_threshold,
                recovery_timeout_seconds=circuit_breaker_timeout,
            ),
            "generate_image": CircuitBreakerState(
                failure_threshold=circuit_breaker_threshold,
                recovery_timeout_seconds=circuit_breaker_timeout,
            ),
        }

        if project and location:
            self._client = genai.Client(vertexai=True, project=project, location=location)
        else:
            self._client = genai.Client(api_key=api_key)

    def _classify_error(self, exc: Exception, error_text: str) -> tuple[str, bool]:
        """Classify error type and determine if retryable.

        Returns:
            Tuple of (error_type, is_retryable)
        """
        if "RESOURCE_EXHAUSTED" in error_text or "429" in error_text:
            return "rate_limit", True
        if "SAFETY" in error_text.upper() or "blocked" in error_text.lower():
            return "content_filter", False
        if "timeout" in error_text.lower() or "deadline" in error_text.lower():
            return "timeout", True
        if "unavailable" in error_text.lower() or "503" in error_text:
            return "model_unavailable", True
        if "invalid" in error_text.lower() or "400" in error_text:
            return "invalid_request", False
        return "unknown", True

    def _check_response_safety(
        self,
        response: types.GenerateContentResponse,
        request_id: str,
        model_name: str,
    ) -> None:
        """Check if response was blocked by safety filters."""
        candidate = (response.candidates or [None])[0]
        if candidate is None:
            return

        # Check finish reason for safety blocks
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason and "SAFETY" in str(finish_reason).upper():
            blocked_categories = []
            safety_ratings = getattr(candidate, "safety_ratings", None)
            if safety_ratings:
                for rating in safety_ratings:
                    if getattr(rating, "blocked", False):
                        category = getattr(rating, "category", "UNKNOWN")
                        blocked_categories.append(str(category))

            raise GeminiContentFilterError(
                f"Content blocked by safety filters: {blocked_categories}",
                request_id=request_id,
                model=model_name,
                blocked_categories=blocked_categories,
            )

    def _retry(
        self,
        func: Callable[[], types.GenerateContentResponse],
        model_name: str,
        request_type: str,
    ) -> types.GenerateContentResponse:
        """Execute function with retry logic, circuit breaker, and error classification."""
        circuit_breaker = self._circuit_breakers.get(request_type)
        if circuit_breaker:
            circuit_breaker.check_circuit()

        last_exc: Exception | None = None
        last_error_type: str = "unknown"
        request_id = str(uuid.uuid4())
        attempt = 0
        max_attempts = self._max_retries

        while attempt < max_attempts:
            try:
                with track_gemini_call(request_type):
                    response = func()
                self.last_request_id = response.response_id or request_id
                self.last_model = model_name
                self.last_error_type = None

                if response.usage_metadata:
                    self.last_usage = response.usage_metadata.model_dump()
                else:
                    self.last_usage = {"model": model_name}

                # Check for safety filter blocks
                self._check_response_safety(response, request_id, model_name)

                # Record success for circuit breaker
                if circuit_breaker:
                    circuit_breaker.record_success()

                return response

            except GeminiContentFilterError:
                # Don't retry content filter errors, just re-raise
                self.last_error_type = "content_filter"
                if circuit_breaker:
                    circuit_breaker.record_failure()
                raise

            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                error_text = str(exc)
                error_type, is_retryable = self._classify_error(exc, error_text)
                last_error_type = error_type
                self.last_error_type = error_type

                if not is_retryable:
                    logger.error(
                        "gemini.%s non-retryable error request_id=%s model=%s type=%s error=%s",
                        request_type,
                        request_id,
                        model_name,
                        error_type,
                        repr(exc),
                    )
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    break

                # Calculate backoff
                if error_type == "rate_limit":
                    max_attempts = max(max_attempts, len(self._rate_limit_backoff_seconds) + 1)
                    idx = min(attempt, len(self._rate_limit_backoff_seconds) - 1)
                    backoff = self._rate_limit_backoff_seconds[idx]
                else:
                    backoff = self._initial_backoff_seconds * (2**attempt)

                logger.warning(
                    "gemini.%s failed request_id=%s model=%s attempt=%s/%s type=%s error=%s",
                    request_type,
                    request_id,
                    model_name,
                    attempt + 1,
                    max_attempts,
                    error_type,
                    repr(exc),
                )

                if attempt + 1 >= max_attempts:
                    break

                time.sleep(backoff)
                attempt += 1
                continue

            attempt += 1

        # Record failure for circuit breaker
        if circuit_breaker:
            circuit_breaker.record_failure()

        # Raise appropriate exception type
        self.last_request_id = request_id
        self.last_model = model_name

        if last_error_type == "rate_limit":
            raise GeminiRateLimitError(
                f"Rate limit exceeded after {attempt + 1} attempts",
                request_id=request_id,
                model=model_name,
            )
        elif last_error_type == "timeout":
            raise GeminiTimeoutError(
                f"Request timed out after {attempt + 1} attempts",
                request_id=request_id,
                model=model_name,
            )
        elif last_error_type == "model_unavailable":
            raise GeminiModelUnavailableError(
                f"Model {model_name} is unavailable",
                request_id=request_id,
                model=model_name,
            )
        else:
            raise GeminiError(
                f"Gemini {request_type} failed after {attempt + 1} retries: {last_exc!r}",
                request_id=request_id,
                model=model_name,
            )

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

    def generate_text(
        self,
        prompt: str,
        model: str | None = None,
        use_fallback: bool = True,
    ) -> str:
        """Generate text with optional fallback to alternate model.

        Args:
            prompt: Text prompt
            model: Optional model override
            use_fallback: Whether to try fallback model on failure (default True)

        Returns:
            Generated text

        Raises:
            GeminiError: On failure (with specific subclass for error type)
        """
        model_name = model or self._text_model

        try:
            response = self._retry(
                func=lambda: self._client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                ),
                model_name=model_name,
                request_type="generate_text",
            )
            return self._extract_text_from_response(response)

        except (GeminiModelUnavailableError, GeminiRateLimitError, GeminiTimeoutError) as exc:
            # Try fallback model if available and allowed
            fallback = self._fallback_text_model
            if use_fallback and fallback and fallback != model_name:
                logger.warning(
                    "Primary model %s failed, trying fallback %s: %s",
                    model_name,
                    fallback,
                    exc,
                )
                response = self._retry(
                    func=lambda: self._client.models.generate_content(
                        model=fallback,
                        contents=[prompt],
                    ),
                    model_name=fallback,
                    request_type="generate_text",
                )
                return self._extract_text_from_response(response)
            raise

    def generate_image(
        self,
        prompt: str,
        model: str | None = None,
        reference_images: list[tuple[bytes, str]] | None = None,
        use_fallback: bool = True,
    ) -> tuple[bytes, str]:
        """Generate an image with optional reference images for style/character consistency.

        Args:
            prompt: Text prompt for image generation
            model: Optional model override
            reference_images: Optional list of (image_bytes, mime_type) tuples for reference
            use_fallback: Whether to try fallback model on failure (default True)

        Returns:
            Tuple of (image_bytes, mime_type)

        Raises:
            GeminiError: On failure (with specific subclass for error type)
        """
        model_name = model or self._image_model

        # Build contents with optional reference images
        def build_contents() -> list:
            contents: list = []
            if reference_images:
                for img_bytes, mime_type in reference_images:
                    contents.append(
                        types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
                    )
                contents.append(
                    f"Using the reference images above for character appearance consistency:\n\n{prompt}"
                )
            else:
                contents.append(prompt)
            return contents

        try:
            response = self._retry(
                func=lambda: self._client.models.generate_content(
                    model=model_name,
                    contents=build_contents(),
                    config=types.GenerateContentConfig(
                        image_config=_DEFAULT_IMAGE_CONFIG,
                        safety_settings=_DEFAULT_SAFETY_SETTINGS,
                    ),
                ),
                model_name=model_name,
                request_type="generate_image",
            )
            return self._extract_image(response)

        except (GeminiModelUnavailableError, GeminiRateLimitError, GeminiTimeoutError) as exc:
            # Try fallback model if available and allowed
            fallback = self._fallback_image_model
            if use_fallback and fallback and fallback != model_name:
                logger.warning(
                    "Primary image model %s failed, trying fallback %s: %s",
                    model_name,
                    fallback,
                    exc,
                )
                response = self._retry(
                    func=lambda: self._client.models.generate_content(
                        model=fallback,
                        contents=build_contents(),
                        config=types.GenerateContentConfig(
                            image_config=_DEFAULT_IMAGE_CONFIG,
                            safety_settings=_DEFAULT_SAFETY_SETTINGS,
                        ),
                    ),
                    model_name=fallback,
                    request_type="generate_image",
                )
                return self._extract_image(response)
            raise

    def get_circuit_breaker_status(self) -> dict[str, dict]:
        """Get current status of all circuit breakers.

        Returns:
            Dict mapping operation type to circuit breaker status
        """
        status = {}
        for op_type, cb in self._circuit_breakers.items():
            status[op_type] = {
                "failure_count": cb.failure_count,
                "is_open": cb.is_open,
                "is_half_open": cb.is_half_open,
                "circuit_open_until": cb.circuit_open_until.isoformat() if cb.circuit_open_until else None,
                "consecutive_successes": cb.consecutive_successes,
            }
        return status

    def reset_circuit_breaker(self, operation_type: str | None = None) -> None:
        """Reset circuit breaker(s) to closed state.

        Args:
            operation_type: Specific operation to reset, or None for all
        """
        if operation_type:
            if operation_type in self._circuit_breakers:
                self._circuit_breakers[operation_type].reset()
                logger.info("Circuit breaker reset for %s", operation_type)
        else:
            for op_type, cb in self._circuit_breakers.items():
                cb.reset()
            logger.info("All circuit breakers reset")
