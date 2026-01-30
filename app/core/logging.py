import json
import logging

from app.core.request_context import (
    get_artifact_id,
    get_node_name,
    get_request_id,
    get_scene_id,
)


class RequestIdFilter(logging.Filter):
    """Populate structured log records with mission-critical IDs."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "unknown"
        record.node_name = get_node_name() or ""
        record.scene_id = get_scene_id() or ""
        record.artifact_id = get_artifact_id() or ""
        return True


class StructuredJsonFormatter(logging.Formatter):
    """Emit log records as JSON with consistent fields."""

    _SKIP_FIELDS = {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "request_id",
        "node_name",
        "scene_id",
        "artifact_id",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, object | None] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "unknown"),
            "node_name": getattr(record, "node_name", ""),
            "scene_id": getattr(record, "scene_id", ""),
        }
        artifact_id = getattr(record, "artifact_id", None)
        if artifact_id:
            log_payload["artifact_id"] = artifact_id
        log_payload.update(self._extract_extra(record))
        if record.exc_info:
            log_payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_payload["stack_info"] = record.stack_info
        try:
            return json.dumps(log_payload, default=str)
        except (TypeError, ValueError):
            return super().format(record)

    def _extract_extra(self, record: logging.LogRecord) -> dict[str, object]:
        extras: dict[str, object] = {}
        for key, value in record.__dict__.items():
            if key in self._SKIP_FIELDS or key.startswith("_"):
                continue
            if value is None:
                continue
            extras[key] = value
        return extras
