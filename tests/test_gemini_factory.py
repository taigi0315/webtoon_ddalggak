"""Tests for the centralized Gemini client factory."""

import pytest
from unittest.mock import patch

from app.core.gemini_factory import (
    GeminiNotConfiguredError,
    build_gemini_client,
)


class TestGeminiNotConfiguredError:
    def test_inherits_runtime_error(self):
        err = GeminiNotConfiguredError()
        assert isinstance(err, RuntimeError)

    def test_has_helpful_message(self):
        err = GeminiNotConfiguredError()
        assert "GEMINI_API_KEY" in str(err)
        assert "GOOGLE_CLOUD_PROJECT" in str(err)


class TestBuildGeminiClient:
    def test_raises_when_no_credentials(self, monkeypatch):
        from app.core import settings as settings_module

        monkeypatch.setattr(settings_module.settings, "google_cloud_project", None)
        monkeypatch.setattr(settings_module.settings, "gemini_api_key", None)

        with pytest.raises(GeminiNotConfiguredError):
            build_gemini_client()

    def test_builds_client_with_api_key(self, monkeypatch):
        from app.core import settings as settings_module

        monkeypatch.setattr(settings_module.settings, "google_cloud_project", None)
        monkeypatch.setattr(settings_module.settings, "gemini_api_key", "test-key")
        monkeypatch.setattr(settings_module.settings, "google_cloud_location", "us-central1")
        monkeypatch.setattr(settings_module.settings, "gemini_text_model", "gemini-2.5-flash")
        monkeypatch.setattr(settings_module.settings, "gemini_image_model", "gemini-2.5-flash-image")
        monkeypatch.setattr(settings_module.settings, "gemini_timeout_seconds", 60.0)
        monkeypatch.setattr(settings_module.settings, "gemini_max_retries", 3)
        monkeypatch.setattr(settings_module.settings, "gemini_initial_backoff_seconds", 0.8)

        client = build_gemini_client()
        assert client is not None
        assert client._text_model == "gemini-2.5-flash"

    def test_builds_client_with_gcp_project(self, monkeypatch):
        from app.core import settings as settings_module

        monkeypatch.setattr(settings_module.settings, "google_cloud_project", "test-project")
        monkeypatch.setattr(settings_module.settings, "gemini_api_key", None)
        monkeypatch.setattr(settings_module.settings, "google_cloud_location", "us-central1")
        monkeypatch.setattr(settings_module.settings, "gemini_text_model", "gemini-2.5-flash")
        monkeypatch.setattr(settings_module.settings, "gemini_image_model", "gemini-2.5-flash-image")
        monkeypatch.setattr(settings_module.settings, "gemini_timeout_seconds", 60.0)
        monkeypatch.setattr(settings_module.settings, "gemini_max_retries", 3)
        monkeypatch.setattr(settings_module.settings, "gemini_initial_backoff_seconds", 0.8)

        client = build_gemini_client()
        assert client is not None

    def test_passes_fallback_models(self, monkeypatch):
        from app.core import settings as settings_module

        monkeypatch.setattr(settings_module.settings, "google_cloud_project", None)
        monkeypatch.setattr(settings_module.settings, "gemini_api_key", "test-key")
        monkeypatch.setattr(settings_module.settings, "google_cloud_location", "us-central1")
        monkeypatch.setattr(settings_module.settings, "gemini_text_model", "gemini-2.5-flash")
        monkeypatch.setattr(settings_module.settings, "gemini_image_model", "gemini-2.5-flash-image")
        monkeypatch.setattr(settings_module.settings, "gemini_timeout_seconds", 60.0)
        monkeypatch.setattr(settings_module.settings, "gemini_max_retries", 3)
        monkeypatch.setattr(settings_module.settings, "gemini_initial_backoff_seconds", 0.8)
        monkeypatch.setattr(settings_module.settings, "gemini_fallback_text_model", "gemini-2.0-flash")
        monkeypatch.setattr(settings_module.settings, "gemini_fallback_image_model", None)

        client = build_gemini_client()
        assert client._fallback_text_model == "gemini-2.0-flash"
