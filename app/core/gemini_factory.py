"""
Centralized Gemini client factory.

Provides a single shared builder for GeminiClient instances,
eliminating the 7+ duplicate _build_gemini_client() functions
scattered across the codebase.
"""

from __future__ import annotations

from app.core.settings import settings
from app.services.vertex_gemini import GeminiClient


class GeminiNotConfiguredError(RuntimeError):
    """Raised when Gemini API credentials are missing."""

    def __init__(self) -> None:
        super().__init__(
            "Gemini is not configured. Set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT."
        )


def build_gemini_client() -> GeminiClient:
    """Build a GeminiClient from application settings.

    Raises:
        GeminiNotConfiguredError: If neither API key nor GCP project is set.
    """
    if not settings.google_cloud_project and not settings.gemini_api_key:
        raise GeminiNotConfiguredError()

    return GeminiClient(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        api_key=settings.gemini_api_key,
        text_model=settings.gemini_text_model,
        image_model=settings.gemini_image_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
        initial_backoff_seconds=settings.gemini_initial_backoff_seconds,
        fallback_text_model=getattr(settings, "gemini_fallback_text_model", None),
        fallback_image_model=getattr(settings, "gemini_fallback_image_model", None),
        circuit_breaker_threshold=getattr(settings, "gemini_circuit_breaker_threshold", 5),
        circuit_breaker_timeout=getattr(settings, "gemini_circuit_breaker_timeout", 60),
    )
