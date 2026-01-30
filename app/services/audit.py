"""Audit logging helper for entity lifecycle events."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.db.models import AuditLog


def log_audit_entry(
    db: Session,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        request_id=get_request_id(),
        old_value=old_value,
        new_value=new_value,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
