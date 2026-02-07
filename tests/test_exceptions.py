"""Tests for application-level exception types."""

import pytest

from app.core.exceptions import (
    AppError,
    ArtifactNotFoundError,
    CastingError,
    ConfigurationError,
    EntityNotFoundError,
    GenerationError,
    SceneNotFoundError,
    StoryBuildError,
)


class TestAppError:
    def test_message_and_detail(self):
        err = AppError("something broke", detail="user-friendly msg")
        assert str(err) == "something broke"
        assert err.detail == "user-friendly msg"

    def test_detail_defaults_to_message(self):
        err = AppError("fallback message")
        assert err.detail == "fallback message"

    def test_inherits_exception(self):
        assert issubclass(AppError, Exception)


class TestDomainExceptions:
    @pytest.mark.parametrize(
        "exc_class",
        [GenerationError, CastingError, StoryBuildError, ConfigurationError,
         ArtifactNotFoundError, SceneNotFoundError],
    )
    def test_inherits_app_error(self, exc_class):
        assert issubclass(exc_class, AppError)

    def test_generation_error(self):
        err = GenerationError("image gen failed")
        assert "image gen" in str(err)
        assert isinstance(err, AppError)

    def test_casting_error(self):
        err = CastingError("cast failed", detail="no variants")
        assert err.detail == "no variants"


class TestEntityNotFoundError:
    def test_includes_entity_type_and_id(self):
        err = EntityNotFoundError("Character", "abc-123")
        assert "Character" in str(err)
        assert "abc-123" in str(err)
        assert err.entity_type == "Character"
        assert err.entity_id == "abc-123"

    def test_detail_is_user_friendly(self):
        err = EntityNotFoundError("Scene", 42)
        assert err.detail == "Scene not found"

    def test_inherits_app_error(self):
        assert issubclass(EntityNotFoundError, AppError)
