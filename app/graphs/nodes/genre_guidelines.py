"""
Genre visual guidelines - loaded from config/genre_guidelines_v1.json

This module provides backwards-compatible dict access to genre guidelines
while loading the actual data from the JSON config file.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import loaders

if TYPE_CHECKING:
    pass


@lru_cache(maxsize=1)
def _load_genre_visual_guidelines() -> dict[str, dict[str, str]]:
    """Load genre guidelines as dict for backwards compatibility."""
    guidelines = loaders.load_genre_guidelines_v1()
    return {
        genre: {
            "shot_preferences": g.shot_preferences,
            "composition": g.composition,
            "camera": g.camera,
            "lighting": g.lighting,
            "props": g.props,
            "atmosphere": g.atmosphere,
            "color_palette": g.color_palette,
        }
        for genre, g in guidelines.genres.items()
    }


@lru_cache(maxsize=1)
def _load_shot_distribution() -> dict[str, dict[str, int | str]]:
    """Load shot distribution as dict for backwards compatibility."""
    guidelines = loaders.load_genre_guidelines_v1()
    return {
        genre: {
            "establishing": d.establishing,
            "medium": d.medium,
            "closeup": d.closeup,
            "dynamic": d.dynamic,
        }
        for genre, d in guidelines.shot_distribution.items()
    }


class _LazyDict(dict):
    """Dict that loads from config on first access."""

    def __init__(self, loader):
        super().__init__()
        self._loader = loader
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self.update(self._loader())
            self._loaded = True

    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)

    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)

    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)

    def keys(self):
        self._ensure_loaded()
        return super().keys()

    def values(self):
        self._ensure_loaded()
        return super().values()

    def items(self):
        self._ensure_loaded()
        return super().items()

    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()

    def __len__(self):
        self._ensure_loaded()
        return super().__len__()


# Backwards-compatible exports - these are now loaded from JSON config
GENRE_VISUAL_GUIDELINES = _LazyDict(_load_genre_visual_guidelines)
SHOT_DISTRIBUTION_BY_GENRE = _LazyDict(_load_shot_distribution)


def reload_guidelines() -> None:
    """Reload guidelines from config (clears caches)."""
    _load_genre_visual_guidelines.cache_clear()
    _load_shot_distribution.cache_clear()
    # Reset lazy dicts
    GENRE_VISUAL_GUIDELINES._loaded = False
    GENRE_VISUAL_GUIDELINES.clear()
    SHOT_DISTRIBUTION_BY_GENRE._loaded = False
    SHOT_DISTRIBUTION_BY_GENRE.clear()
