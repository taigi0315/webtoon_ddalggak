"""Style presets management API."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import StylePreset
from app.db.session import get_db

router = APIRouter(prefix="/style-presets", tags=["style-presets"])


class StyleConfigBase(BaseModel):
    """Base style configuration."""

    model_config = ConfigDict(extra="allow")

    # Common style attributes
    atmosphere: str | None = None
    lighting: str | None = None
    color_palette: str | None = None
    composition: str | None = None
    rendering_notes: str | None = None


class StylePresetCreate(BaseModel):
    """Request model for creating a style preset."""

    project_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    style_type: Literal["story", "image"] = "image"
    name: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=256)
    description: str | None = None
    style_config: dict = Field(default_factory=dict)


class StylePresetUpdate(BaseModel):
    """Request model for updating a style preset."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    label: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    style_config: dict | None = None
    is_active: bool | None = None


class StylePresetRead(BaseModel):
    """Response model for a style preset."""

    model_config = ConfigDict(from_attributes=True)

    preset_id: uuid.UUID
    project_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    style_type: str
    name: str
    label: str
    description: str | None
    style_config: dict
    is_system: bool
    is_active: bool
    # Computed from inheritance
    effective_config: dict | None = None


def _get_effective_config(
    preset: StylePreset,
    db: Session,
    visited: set[uuid.UUID] | None = None,
) -> dict:
    """Recursively compute effective config with parent inheritance."""
    visited = visited or set()

    # Prevent circular inheritance
    if preset.preset_id in visited:
        return preset.style_config or {}

    visited.add(preset.preset_id)

    # Base case: no parent
    if preset.parent_id is None:
        return preset.style_config or {}

    # Get parent
    parent = db.get(StylePreset, preset.parent_id)
    if parent is None:
        return preset.style_config or {}

    # Merge parent config with this preset's config (this preset takes precedence)
    parent_config = _get_effective_config(parent, db, visited)
    merged = {**parent_config, **(preset.style_config or {})}
    return merged


@router.get("", response_model=list[StylePresetRead])
def list_style_presets(
    style_type: Literal["story", "image"] | None = None,
    project_id: uuid.UUID | None = None,
    include_system: bool = True,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List style presets, optionally filtered by type and project."""
    query = select(StylePreset)

    if style_type:
        query = query.where(StylePreset.style_type == style_type)

    if active_only:
        query = query.where(StylePreset.is_active == True)  # noqa: E712

    # Include system presets and optionally project-specific ones
    if project_id:
        if include_system:
            query = query.where(
                (StylePreset.project_id == project_id) | (StylePreset.is_system == True)  # noqa: E712
            )
        else:
            query = query.where(StylePreset.project_id == project_id)
    elif include_system:
        query = query.where(StylePreset.is_system == True)  # noqa: E712

    presets = db.scalars(query.order_by(StylePreset.name)).all()

    # Add effective config to each preset
    result = []
    for preset in presets:
        preset_read = StylePresetRead.model_validate(preset)
        preset_read.effective_config = _get_effective_config(preset, db)
        result.append(preset_read)

    return result


@router.post("", response_model=StylePresetRead, status_code=status.HTTP_201_CREATED)
def create_style_preset(
    data: StylePresetCreate,
    db: Session = Depends(get_db),
):
    """Create a new style preset."""
    # Validate parent exists if specified
    if data.parent_id:
        parent = db.get(StylePreset, data.parent_id)
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent preset not found",
            )
        # Ensure same style type
        if parent.style_type != data.style_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent preset must have same style_type",
            )

    preset = StylePreset(
        project_id=data.project_id,
        parent_id=data.parent_id,
        style_type=data.style_type,
        name=data.name,
        label=data.label,
        description=data.description,
        style_config=data.style_config,
        is_system=False,  # User-created presets are never system presets
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)

    result = StylePresetRead.model_validate(preset)
    result.effective_config = _get_effective_config(preset, db)
    return result


@router.get("/{preset_id}", response_model=StylePresetRead)
def get_style_preset(
    preset_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get a specific style preset by ID."""
    preset = db.get(StylePreset, preset_id)
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style preset not found",
        )

    result = StylePresetRead.model_validate(preset)
    result.effective_config = _get_effective_config(preset, db)
    return result


@router.patch("/{preset_id}", response_model=StylePresetRead)
def update_style_preset(
    preset_id: uuid.UUID,
    data: StylePresetUpdate,
    db: Session = Depends(get_db),
):
    """Update a style preset."""
    preset = db.get(StylePreset, preset_id)
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style preset not found",
        )

    # Don't allow editing system presets
    if preset.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system presets",
        )

    # Update fields
    if data.name is not None:
        preset.name = data.name
    if data.label is not None:
        preset.label = data.label
    if data.description is not None:
        preset.description = data.description
    if data.style_config is not None:
        preset.style_config = data.style_config
    if data.is_active is not None:
        preset.is_active = data.is_active

    db.commit()
    db.refresh(preset)

    result = StylePresetRead.model_validate(preset)
    result.effective_config = _get_effective_config(preset, db)
    return result


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_style_preset(
    preset_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Delete a style preset."""
    preset = db.get(StylePreset, preset_id)
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style preset not found",
        )

    # Don't allow deleting system presets
    if preset.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system presets",
        )

    # Check if any other presets inherit from this one
    children = db.scalars(
        select(StylePreset).where(StylePreset.parent_id == preset_id)
    ).all()
    if children:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {len(children)} preset(s) inherit from this preset",
        )

    db.delete(preset)
    db.commit()


@router.post("/{preset_id}/clone", response_model=StylePresetRead, status_code=status.HTTP_201_CREATED)
def clone_style_preset(
    preset_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    new_name: str | None = None,
    db: Session = Depends(get_db),
):
    """Clone a style preset, optionally to a different project."""
    original = db.get(StylePreset, preset_id)
    if original is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style preset not found",
        )

    clone = StylePreset(
        project_id=project_id or original.project_id,
        parent_id=original.parent_id,
        style_type=original.style_type,
        name=new_name or f"{original.name}_copy",
        label=f"{original.label} (Copy)",
        description=original.description,
        style_config=original.style_config.copy() if original.style_config else {},
        is_system=False,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)

    result = StylePresetRead.model_validate(clone)
    result.effective_config = _get_effective_config(clone, db)
    return result
