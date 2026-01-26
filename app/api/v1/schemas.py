import uuid

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectRead(BaseModel):
    project_id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class StoryRead(BaseModel):
    story_id: uuid.UUID
    project_id: uuid.UUID
    title: str

    model_config = {"from_attributes": True}


class SceneCreate(BaseModel):
    source_text: str = Field(min_length=1)


class SceneRead(BaseModel):
    scene_id: uuid.UUID
    story_id: uuid.UUID
    source_text: str

    model_config = {"from_attributes": True}


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CharacterRead(BaseModel):
    character_id: uuid.UUID
    story_id: uuid.UUID
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class ArtifactRead(BaseModel):
    artifact_id: uuid.UUID
    scene_id: uuid.UUID
    type: str
    version: int
    parent_id: uuid.UUID | None
    payload: dict

    model_config = {"from_attributes": True}
