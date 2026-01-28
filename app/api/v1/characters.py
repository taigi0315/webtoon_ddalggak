import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func

from app.api.deps import DbSessionDep
from app.api.v1.schemas import (
    CharacterApproveRefRequest,
    CharacterCreate,
    CharacterRead,
    CharacterRefCreate,
    CharacterRefRead,
    CharacterUpdate,
    CharacterSetPrimaryRefRequest,
    CharacterGenerateRefsRequest,
    CharacterGenerateRefsResponse,
)
from app.db.models import Character, CharacterReferenceImage, Story
from app.graphs import nodes


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
    db.flush()

    # Reuse project-level character references by name
    existing = (
        db.execute(
            select(Character)
            .join(Story, Character.story_id == Story.story_id)
            .where(
                Story.project_id == story.project_id,
                func.lower(Character.name) == func.lower(payload.name),
                Character.character_id != character.character_id,
            )
            .order_by(Character.created_at.desc())
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )

    if existing is not None:
        if character.description is None:
            character.description = existing.description
        if character.identity_line is None:
            character.identity_line = existing.identity_line
        if not character.role:
            character.role = existing.role

        refs = (
            db.execute(
                select(CharacterReferenceImage)
                .where(CharacterReferenceImage.character_id == existing.character_id)
            )
            .scalars()
            .all()
        )
        for ref in refs:
            db.add(
                CharacterReferenceImage(
                    character_id=character.character_id,
                    image_url=ref.image_url,
                    ref_type=ref.ref_type,
                    approved=ref.approved,
                    is_primary=ref.is_primary,
                    metadata_=ref.metadata_ or {},
                )
            )
        if existing.approved:
            character.approved = True
        if character.approved or refs:
            character.appearance = dict(character.appearance or {})
            character.appearance["project_reused"] = True

    db.commit()
    db.refresh(character)
    return character


@router.patch("/characters/{character_id}", response_model=CharacterRead)
def update_character(character_id: uuid.UUID, payload: CharacterUpdate, db=DbSessionDep):
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    if "name" in payload.model_fields_set and payload.name is not None:
        character.name = payload.name
    if "description" in payload.model_fields_set:
        character.description = payload.description
    if "role" in payload.model_fields_set and payload.role is not None:
        character.role = payload.role
    if "identity_line" in payload.model_fields_set:
        character.identity_line = payload.identity_line

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


@router.delete("/characters/{character_id}/refs/{reference_image_id}")
def delete_character_ref(character_id: uuid.UUID, reference_image_id: uuid.UUID, db=DbSessionDep):
    """Delete a character reference image."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    ref = db.get(CharacterReferenceImage, reference_image_id)
    if ref is None or ref.character_id != character_id:
        raise HTTPException(status_code=404, detail="reference image not found")

    db.delete(ref)
    db.commit()
    return {"deleted": True}


@router.post("/characters/{character_id}/generate-refs", response_model=CharacterGenerateRefsResponse)
def generate_character_refs(character_id: uuid.UUID, payload: CharacterGenerateRefsRequest, db=DbSessionDep):
    """Generate AI character reference images based on character description."""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    if not character.description and not character.identity_line:
        raise HTTPException(
            status_code=400,
            detail="character needs description or identity_line to generate reference images"
        )

    story_style = None
    if character.story:
        story_style = character.story.default_story_style

    generated_refs: list[CharacterReferenceImage] = []
    for ref_type in payload.ref_types:
        for _ in range(payload.count_per_type):
            ref = nodes.generate_character_reference_image(
                db=db,
                character_id=character_id,
                ref_type=ref_type,
                story_style=story_style,
            )
            generated_refs.append(ref)

    return CharacterGenerateRefsResponse(
        character_id=character_id,
        generated_refs=generated_refs,
    )
