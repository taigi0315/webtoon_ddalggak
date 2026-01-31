"""Config management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import loaders
from app.prompts.loader import clear_cache as clear_prompt_cache
from app.services.config_watcher import is_watching, start_watcher, stop_watcher

router = APIRouter(prefix="/config", tags=["config"])


class ConfigStatusRead(BaseModel):
    """Config status response."""

    version: int
    watcher_active: bool
    image_styles: list[str]


class ConfigReloadResponse(BaseModel):
    """Config reload response."""

    success: bool
    version: int
    message: str


class WatcherStatusResponse(BaseModel):
    """Watcher status response."""

    active: bool
    message: str


@router.get("", response_model=ConfigStatusRead)
def get_config_status():
    """Get current configuration status."""
    return ConfigStatusRead(
        version=loaders.get_config_version(),
        watcher_active=is_watching(),
        image_styles=[s.id for s in loaders.load_image_styles_v1().styles],
    )


@router.post("/reload", response_model=ConfigReloadResponse)
def reload_config():
    """Manually reload all configuration from disk."""
    try:
        loaders.clear_config_cache()
        clear_prompt_cache()

        return ConfigReloadResponse(
            success=True,
            version=loaders.get_config_version(),
            message="Configuration reloaded successfully",
        )
    except Exception as e:
        return ConfigReloadResponse(
            success=False,
            version=loaders.get_config_version(),
            message=f"Failed to reload: {e}",
        )


@router.post("/watcher/start", response_model=WatcherStatusResponse)
def start_config_watcher():
    """Start the config file watcher for hot-reload."""
    if is_watching():
        return WatcherStatusResponse(active=True, message="Watcher already running")

    start_watcher()
    return WatcherStatusResponse(
        active=is_watching(),
        message="Watcher started" if is_watching() else "Failed to start watcher",
    )


@router.post("/watcher/stop", response_model=WatcherStatusResponse)
def stop_config_watcher():
    """Stop the config file watcher."""
    if not is_watching():
        return WatcherStatusResponse(active=False, message="Watcher not running")

    stop_watcher()
    return WatcherStatusResponse(active=False, message="Watcher stopped")
