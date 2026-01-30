"""
Configuration file watcher for hot-reload support.

This module provides optional file watching to automatically reload
config files when they change on disk.

Usage:
    from app.services.config_watcher import start_watcher, stop_watcher

    # Start watching (call during app startup if hot-reload is enabled)
    start_watcher()

    # Stop watching (call during app shutdown)
    stop_watcher()
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

_watcher_task: asyncio.Task | None = None
_should_stop = False

# Callbacks to run when config changes
_on_change_callbacks: list[Callable[[], None]] = []


def register_on_change(callback: Callable[[], None]) -> None:
    """Register a callback to run when config files change."""
    _on_change_callbacks.append(callback)


def _get_config_files() -> list[Path]:
    """Get list of config files to watch."""
    from app.config.loaders import _config_dir

    config_dir = _config_dir()
    return list(config_dir.glob("*.json"))


def _get_file_mtimes(files: list[Path]) -> dict[Path, float]:
    """Get modification times for files."""
    mtimes = {}
    for f in files:
        try:
            mtimes[f] = f.stat().st_mtime
        except OSError:
            pass
    return mtimes


async def _watch_loop(poll_interval: float = 2.0) -> None:
    """Watch config files for changes and trigger reload."""
    global _should_stop

    from app.config.loaders import clear_config_cache
    from app.graphs.nodes.genre_guidelines import reload_guidelines
    from app.prompts.loader import clear_cache as clear_prompt_cache

    files = _get_config_files()
    mtimes = _get_file_mtimes(files)
    logger.info(f"Config watcher started, monitoring {len(files)} files")

    while not _should_stop:
        await asyncio.sleep(poll_interval)

        # Check for new files
        current_files = _get_config_files()
        current_mtimes = _get_file_mtimes(current_files)

        # Detect changes
        changed = False
        for f, mtime in current_mtimes.items():
            if f not in mtimes or mtimes[f] != mtime:
                logger.info(f"Config file changed: {f.name}")
                changed = True
                break

        if changed:
            logger.info("Reloading configuration...")
            try:
                clear_config_cache()
                reload_guidelines()
                clear_prompt_cache()

                # Run registered callbacks
                for callback in _on_change_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.warning(f"Config change callback failed: {e}")

                logger.info("Configuration reloaded successfully")
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")

            # Update tracked mtimes
            mtimes = current_mtimes
            files = current_files


def start_watcher(poll_interval: float = 2.0) -> None:
    """Start the config file watcher in the background."""
    global _watcher_task, _should_stop

    if _watcher_task is not None:
        logger.warning("Config watcher already running")
        return

    _should_stop = False

    try:
        loop = asyncio.get_running_loop()
        _watcher_task = loop.create_task(_watch_loop(poll_interval))
        logger.info("Config watcher task created")
    except RuntimeError:
        # No running loop, likely called outside async context
        logger.warning("Cannot start config watcher: no running event loop")


def stop_watcher() -> None:
    """Stop the config file watcher."""
    global _watcher_task, _should_stop

    _should_stop = True

    if _watcher_task is not None:
        _watcher_task.cancel()
        _watcher_task = None
        logger.info("Config watcher stopped")


def is_watching() -> bool:
    """Check if the watcher is currently running."""
    return _watcher_task is not None and not _watcher_task.done()
