"""
Application-level exception types.

Provides domain-specific exceptions to replace bare `Exception` catches
and improve error tracing across the codebase.
"""

from __future__ import annotations


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        self.detail = detail or message
        super().__init__(message)


class GenerationError(AppError):
    """Raised when image/text generation fails."""


class CastingError(AppError):
    """Raised when casting operations fail."""


class StoryBuildError(AppError):
    """Raised when story build pipeline fails."""


class ConfigurationError(AppError):
    """Raised when required configuration is missing or invalid."""


class ArtifactNotFoundError(AppError):
    """Raised when a required artifact is missing."""


class SceneNotFoundError(AppError):
    """Raised when a scene cannot be found."""


class EntityNotFoundError(AppError):
    """Raised when a database entity cannot be found."""

    def __init__(self, entity_type: str, entity_id: object) -> None:
        super().__init__(
            f"{entity_type} not found: {entity_id}",
            detail=f"{entity_type} not found",
        )
        self.entity_type = entity_type
        self.entity_id = entity_id
