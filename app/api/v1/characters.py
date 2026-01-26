import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import CharacterCreate, CharacterRead
from app.db.models import Character, Story


router = APIRouter(tags=["characters"])


@router.post("/stories/{story_id}/characters", response_model=CharacterRead)
def create_character(story_id: uuid.UUID, payload: CharacterCreate, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    character = Character(story_id=story_id, name=payload.name, description=payload.description)
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@router.get("/stories/{story_id}/characters", response_model=list[CharacterRead])
def list_characters(story_id: uuid.UUID, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    stmt = select(Character).where(Character.story_id == story_id)
    return list(db.execute(stmt).scalars().all())
