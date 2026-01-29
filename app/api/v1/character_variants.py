import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from app.api.deps import DbSessionDep
from app.api.v1.schemas import CharacterVariantActivate, CharacterVariantCreate, CharacterVariantRead
from app.db.models import Character, CharacterVariant, Story, StoryCharacter


router = APIRouter(tags=["character-variants"])


@router.post(
    "/stories/{story_id}/characters/{character_id}/variants",
    response_model=CharacterVariantRead,
)
def create_character_variant(
    story_id: uuid.UUID,
    character_id: uuid.UUID,
    payload: CharacterVariantCreate,
    db=DbSessionDep,
):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    if character.project_id != story.project_id:
        raise HTTPException(status_code=400, detail="character does not belong to this project")

    link = db.get(StoryCharacter, {"story_id": story_id, "character_id": character_id})
    if link is None:
        db.add(StoryCharacter(story_id=story_id, character_id=character_id))

    if payload.is_active_for_story:
        db.execute(
            update(CharacterVariant)
            .where(
                CharacterVariant.story_id == story_id,
                CharacterVariant.character_id == character_id,
            )
            .values(is_active_for_story=False)
        )

    variant = CharacterVariant(
        story_id=story_id,
        character_id=character_id,
        variant_type=payload.variant_type,
        override_attributes=payload.override_attributes or {},
        reference_image_id=payload.reference_image_id,
        is_active_for_story=payload.is_active_for_story,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.get(
    "/stories/{story_id}/characters/{character_id}/variants",
    response_model=list[CharacterVariantRead],
)
def list_character_variants(story_id: uuid.UUID, character_id: uuid.UUID, db=DbSessionDep):
    stmt = (
        select(CharacterVariant)
        .where(CharacterVariant.story_id == story_id, CharacterVariant.character_id == character_id)
        .order_by(CharacterVariant.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/stories/{story_id}/characters/{character_id}/variants/{variant_id}/activate",
    response_model=CharacterVariantRead,
)
def activate_character_variant(
    story_id: uuid.UUID,
    character_id: uuid.UUID,
    variant_id: uuid.UUID,
    payload: CharacterVariantActivate,
    db=DbSessionDep,
):
    variant = db.get(CharacterVariant, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="variant not found")

    if variant.story_id != story_id or variant.character_id != character_id:
        raise HTTPException(status_code=400, detail="variant does not belong to story/character")

    if payload.is_active_for_story:
        db.execute(
            update(CharacterVariant)
            .where(
                CharacterVariant.story_id == story_id,
                CharacterVariant.character_id == character_id,
            )
            .values(is_active_for_story=False)
        )
        variant.is_active_for_story = True
    else:
        variant.is_active_for_story = False

    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant
