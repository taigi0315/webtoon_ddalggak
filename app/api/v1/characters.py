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
    CharacterVariantGenerateRequest,
    CharacterVariantGenerationResult,
    CharacterVariantSuggestionRead,
)
from app.db.models import (
    Character,
    CharacterReferenceImage,
    CharacterVariant,
    CharacterVariantSuggestion,
    Story,
    StoryCharacter,
)
from app.graphs import nodes


router = APIRouter(tags=["characters"])

def _code_from_index(index: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""
    while True:
        index, rem = divmod(index, 26)
        result = alphabet[rem] + result
        if index == 0:
            break
        index -= 1
    return f"CHAR_{result}"


def _next_character_code(existing_codes: set[str]) -> str:
    idx = 0
    while True:
        code = _code_from_index(idx)
        if code not in existing_codes:
            return code
        idx += 1


@router.post("/stories/{story_id}/characters", response_model=CharacterRead)
def create_character(story_id: uuid.UUID, payload: CharacterCreate, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    existing_codes = {
        c.canonical_code
        for c in db.execute(select(Character.canonical_code).where(Character.project_id == story.project_id)).scalars().all()
        if c
    }

    existing = (
        db.execute(
            select(Character)
            .where(
                Character.project_id == story.project_id,
                func.lower(Character.name) == func.lower(payload.name),
            )
            .order_by(Character.created_at.desc())
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )

    if existing is not None:
        link = db.get(StoryCharacter, {"story_id": story_id, "character_id": existing.character_id})
        if link is None:
            db.add(StoryCharacter(story_id=story_id, character_id=existing.character_id))
            db.commit()
        db.refresh(existing)
        return existing

    character = Character(
        project_id=story.project_id,
        canonical_code=_next_character_code(existing_codes),
        name=payload.name,
        description=payload.description,
        role=payload.role,
        gender=payload.gender,
        age_range=payload.age_range,
        appearance=payload.appearance,
        hair_description=payload.hair_description,
        base_outfit=payload.base_outfit,
        identity_line=payload.identity_line,
    )
    db.add(character)
    db.flush()
    db.add(StoryCharacter(story_id=story_id, character_id=character.character_id))

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
    if "gender" in payload.model_fields_set:
        character.gender = payload.gender
    if "age_range" in payload.model_fields_set:
        character.age_range = payload.age_range
    if "appearance" in payload.model_fields_set:
        character.appearance = payload.appearance
    if "hair_description" in payload.model_fields_set:
        character.hair_description = payload.hair_description
    if "base_outfit" in payload.model_fields_set:
        character.base_outfit = payload.base_outfit
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

    stmt = (
        select(Character)
        .join(StoryCharacter, StoryCharacter.character_id == Character.character_id)
        .where(StoryCharacter.story_id == story_id)
    )
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/stories/{story_id}/character-variant-suggestions",
    response_model=list[CharacterVariantSuggestionRead],
)
def get_character_variant_suggestions(story_id: uuid.UUID, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    existing = list(
        db.execute(
            select(CharacterVariantSuggestion).where(CharacterVariantSuggestion.story_id == story_id)
        )
        .scalars()
        .all()
    )
    if existing:
        return existing

    suggestions = nodes.generate_character_variant_suggestions(db, story_id)
    created: list[CharacterVariantSuggestion] = []
    for item in suggestions:
        suggestion = CharacterVariantSuggestion(
            story_id=story_id,
            character_id=item["character_id"],
            variant_type=item.get("variant_type") or "outfit_change",
            override_attributes=item.get("override_attributes") or {},
        )
        db.add(suggestion)
        created.append(suggestion)
    db.commit()
    for suggestion in created:
        db.refresh(suggestion)
    return created


@router.post(
    "/stories/{story_id}/character-variant-suggestions/refresh",
    response_model=list[CharacterVariantSuggestionRead],
)
def refresh_character_variant_suggestions(story_id: uuid.UUID, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    db.execute(
        select(CharacterVariantSuggestion).where(CharacterVariantSuggestion.story_id == story_id)
    )
    db.query(CharacterVariantSuggestion).filter(CharacterVariantSuggestion.story_id == story_id).delete()
    db.commit()

    suggestions = nodes.generate_character_variant_suggestions(db, story_id)
    created: list[CharacterVariantSuggestion] = []
    for item in suggestions:
        suggestion = CharacterVariantSuggestion(
            story_id=story_id,
            character_id=item["character_id"],
            variant_type=item.get("variant_type") or "outfit_change",
            override_attributes=item.get("override_attributes") or {},
        )
        db.add(suggestion)
        created.append(suggestion)
    db.commit()
    for suggestion in created:
        db.refresh(suggestion)
    return created


@router.post(
    "/stories/{story_id}/character-variant-suggestions/generate",
    response_model=list[CharacterVariantGenerationResult],
)
def generate_character_variant_suggestion_refs(
    story_id: uuid.UUID,
    payload: CharacterVariantGenerateRequest | None = None,
    db=DbSessionDep,
):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    suggestions = list(
        db.execute(
            select(CharacterVariantSuggestion).where(CharacterVariantSuggestion.story_id == story_id)
        )
        .scalars()
        .all()
    )
    if not suggestions:
        generated = nodes.generate_character_variant_suggestions(db, story_id)
        for item in generated:
            suggestion = CharacterVariantSuggestion(
                story_id=story_id,
                character_id=item["character_id"],
                variant_type=item.get("variant_type") or "outfit_change",
                override_attributes=item.get("override_attributes") or {},
            )
            db.add(suggestion)
            suggestions.append(suggestion)
        db.commit()
        for suggestion in suggestions:
            db.refresh(suggestion)

    if payload and payload.character_id:
        suggestions = [s for s in suggestions if s.character_id == payload.character_id]
        if not suggestions:
            return [
                CharacterVariantGenerationResult(
                    character_id=payload.character_id,
                    story_id=story_id,
                    status="skipped",
                    detail="no suggestion for character",
                )
            ]

    results: list[CharacterVariantGenerationResult] = []
    for suggestion in suggestions:
        character = db.get(Character, suggestion.character_id)
        if character is None:
            results.append(
                CharacterVariantGenerationResult(
                    character_id=suggestion.character_id,
                    story_id=story_id,
                    variant_type=suggestion.variant_type,
                    override_attributes=suggestion.override_attributes,
                    status="skipped",
                    detail="character not found",
                )
            )
            continue

        base_ref = (
            db.execute(
                select(CharacterReferenceImage)
                .where(
                    CharacterReferenceImage.character_id == suggestion.character_id,
                    CharacterReferenceImage.ref_type == "face",
                    CharacterReferenceImage.approved.is_(True),
                )
                .order_by(CharacterReferenceImage.is_primary.desc(), CharacterReferenceImage.created_at.desc())
                .limit(1)
            )
            .scalars()
            .one_or_none()
        )
        if base_ref is None:
            results.append(
                CharacterVariantGenerationResult(
                    character_id=suggestion.character_id,
                    story_id=story_id,
                    variant_type=suggestion.variant_type,
                    override_attributes=suggestion.override_attributes,
                    status="skipped",
                    detail="no approved base reference image",
                )
            )
            continue

        try:
            ref = nodes.generate_character_variant_reference_image(
                db=db,
                character_id=suggestion.character_id,
                variant_type=suggestion.variant_type,
                override_attributes=suggestion.override_attributes,
                base_reference=base_ref,
                story_style=story.default_story_style,
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                CharacterVariantGenerationResult(
                    character_id=suggestion.character_id,
                    story_id=story_id,
                    variant_type=suggestion.variant_type,
                    override_attributes=suggestion.override_attributes,
                    status="error",
                    detail=str(exc),
                )
            )
            continue

        variant = CharacterVariant(
            character_id=suggestion.character_id,
            story_id=story_id,
            variant_type=suggestion.variant_type or "outfit_change",
            override_attributes=suggestion.override_attributes or {},
            reference_image_id=ref.reference_image_id,
            is_active_for_story=False,
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)

        results.append(
            CharacterVariantGenerationResult(
                character_id=suggestion.character_id,
                story_id=story_id,
                variant_id=variant.variant_id,
                reference_image_id=ref.reference_image_id,
                variant_type=variant.variant_type,
                override_attributes=variant.override_attributes,
                status="generated",
            )
        )

    return results


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
    linked_story = (
        db.execute(
            select(Story)
            .join(StoryCharacter, StoryCharacter.story_id == Story.story_id)
            .where(StoryCharacter.character_id == character_id)
            .order_by(Story.created_at.desc())
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if linked_story is not None:
        story_style = linked_story.default_story_style

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
