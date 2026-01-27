import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    CharacterApproveRefRequest,
    CharacterCreate,
    CharacterRead,
    CharacterRefCreate,
    CharacterRefRead,
    CharacterSetPrimaryRefRequest,
)
from app.db.models import Character, CharacterReferenceImage, Story


router = APIRouter(tags=["characters"])


@router.post("/stories/{story_id}/characters", response_model=CharacterRead)
def create_character(story_id: uuid.UUID, payload: CharacterCreate, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    character = Character(
        story_id=story_id,
        name=payload.name,
        description=payload.description,
        role=payload.role,
        identity_line=payload.identity_line,
    )
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


@router.post("/characters/{character_id}/approve", response_model=CharacterRead)
def approve_character(character_id: uuid.UUID, db=DbSessionDep):
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    if character.role == "main":
        stmt = select(CharacterReferenceImage).where(
            CharacterReferenceImage.character_id == character_id,
            CharacterReferenceImage.ref_type == "face",
            CharacterReferenceImage.approved.is_(True),
        )
        face_refs = list(db.execute(stmt).scalars().all())
        if not face_refs:
            raise HTTPException(status_code=400, detail="main characters must have at least one approved face ref")

    character.approved = True
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@router.post("/characters/{character_id}/refs", response_model=CharacterRefRead)
def add_character_ref(character_id: uuid.UUID, payload: CharacterRefCreate, db=DbSessionDep):
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    ref = CharacterReferenceImage(
        character_id=character_id,
        image_url=payload.image_url,
        ref_type=payload.ref_type,
        metadata_={},
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


@router.get("/characters/{character_id}/refs", response_model=list[CharacterRefRead])
def list_character_refs(character_id: uuid.UUID, db=DbSessionDep):
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    stmt = select(CharacterReferenceImage).where(CharacterReferenceImage.character_id == character_id)
    return list(db.execute(stmt).scalars().all())


@router.post("/characters/{character_id}/approve-ref", response_model=CharacterRefRead)
def approve_character_ref(character_id: uuid.UUID, payload: CharacterApproveRefRequest, db=DbSessionDep):
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    ref = db.get(CharacterReferenceImage, payload.reference_image_id)
    if ref is None or ref.character_id != character_id:
        raise HTTPException(status_code=404, detail="reference image not found")

    ref.approved = True
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


@router.post("/characters/{character_id}/set-primary-ref", response_model=CharacterRefRead)
def set_primary_character_ref(character_id: uuid.UUID, payload: CharacterSetPrimaryRefRequest, db=DbSessionDep):
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    ref = db.get(CharacterReferenceImage, payload.reference_image_id)
    if ref is None or ref.character_id != character_id:
        raise HTTPException(status_code=404, detail="reference image not found")

    if not ref.approved:
        raise HTTPException(status_code=400, detail="reference image must be approved before setting primary")

    stmt = select(CharacterReferenceImage).where(
        CharacterReferenceImage.character_id == character_id,
        CharacterReferenceImage.ref_type == ref.ref_type,
    )
    for other in db.execute(stmt).scalars().all():
        other.is_primary = other.reference_image_id == ref.reference_image_id
        db.add(other)

    db.commit()
    db.refresh(ref)
    return ref
