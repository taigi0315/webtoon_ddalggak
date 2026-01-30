import contextvars
from contextlib import contextmanager
import uuid

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
node_name_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("node_name", default=None)
scene_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("scene_id", default=None)
artifact_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("artifact_id", default=None)


def set_request_id(request_id: str) -> contextvars.Token:
    """Store the current request ID in a context variable."""
    return request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    """Reset the request ID context variable to a previous state."""
    request_id_var.reset(token)


def get_request_id() -> str | None:
    """Retrieve the current request ID from the context."""
    return request_id_var.get()


def _normalize_id(value: uuid.UUID | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


def get_node_name() -> str | None:
    """Retrieve the current node name for logging."""
    return node_name_var.get()


def get_scene_id() -> str | None:
    """Retrieve the current scene ID for logging."""
    return scene_id_var.get()


def get_artifact_id() -> str | None:
    """Retrieve the current artifact ID for logging."""
    return artifact_id_var.get()


@contextmanager
def log_context(
    node_name: str | None = None,
    scene_id: uuid.UUID | str | None = None,
    artifact_id: uuid.UUID | str | None = None,
):
    """Temporarily scope node/scene/artifact context for structured logs."""
    tokens: list[tuple[contextvars.ContextVar[str | None], contextvars.Token]] = []
    if node_name is not None:
        tokens.append((node_name_var, node_name_var.set(node_name)))
    if scene_id is not None:
        tokens.append((scene_id_var, scene_id_var.set(_normalize_id(scene_id))))
    if artifact_id is not None:
        tokens.append((artifact_id_var, artifact_id_var.set(_normalize_id(artifact_id))))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
