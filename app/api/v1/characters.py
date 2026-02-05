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
    GenerateWithReferenceRequest,
    GenerateWithReferenceResponse,
    LibraryCharacterRead,
    LoadFromLibraryRequest,
    LoadFromLibraryResponse,
    SaveToLibraryRequest,
    SaveToLibraryResponse,
)
from app.config.loaders import has_image_style
from app.db.models import (
    Character,
    CharacterReferenceImage,
    CharacterVariant,
    CharacterVariantSuggestion,
    Project,
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
        select(Character, StoryCharacter.narrative_description)
        .join(StoryCharacter, StoryCharacter.character_id == Character.character_id)
        .where(StoryCharacter.story_id == story_id)
    )
    results = db.execute(stmt).all()
    characters = []
    for char, narrative_desc in results:
        char_read = CharacterRead.model_validate(char)
        char_read.narrative_description = narrative_desc
        characters.append(char_read)
    return characters


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

    should_generate = not suggestions
    if payload and payload.character_id and not should_generate:
        if not any(s.character_id == payload.character_id for s in suggestions):
            should_generate = True

    if should_generate:
        generated = nodes.generate_character_variant_suggestions(db, story_id)
        existing_keys = {(s.character_id, s.variant_type) for s in suggestions}

        for item in generated:
            c_id = item["character_id"]
            v_type = item.get("variant_type") or "outfit_change"
            
            if (c_id, v_type) in existing_keys:
                continue

            suggestion = CharacterVariantSuggestion(
                story_id=story_id,
                character_id=c_id,
                variant_type=v_type,
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

    style_id = payload.style_id if payload.style_id and has_image_style(payload.style_id) else None

    generated_refs: list[CharacterReferenceImage] = []
    for ref_type in payload.ref_types:
        for _ in range(payload.count_per_type):
            ref = nodes.generate_character_reference_image(
                db=db,
                character_id=character_id,
                ref_type=ref_type,
                style_id=style_id,
            )
            generated_refs.append(ref)

    return CharacterGenerateRefsResponse(
        character_id=character_id,
        generated_refs=generated_refs,
    )


# ============================================================================
# Character Library Endpoints
# ============================================================================


def _get_primary_ref(character_id: uuid.UUID, db) -> CharacterReferenceImage | None:
    """Get the primary reference image for a character."""
    return (
        db.execute(
            select(CharacterReferenceImage)
            .where(
                CharacterReferenceImage.character_id == character_id,
                CharacterReferenceImage.approved.is_(True),
            )
            .order_by(
                CharacterReferenceImage.is_primary.desc(),
                CharacterReferenceImage.created_at.desc(),
            )
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )


@router.get("/projects/{project_id}/library/characters", response_model=list[LibraryCharacterRead])
def list_library_characters(project_id: uuid.UUID, db=DbSessionDep):
    """
    List all characters saved to the project library.

    Returns characters with is_library_saved=True, along with their primary reference image.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    stmt = (
        select(Character)
        .where(
            Character.project_id == project_id,
            Character.is_library_saved.is_(True),
        )
        .order_by(Character.name)
    )
    characters = list(db.execute(stmt).scalars().all())

    result = []
    for char in characters:
        primary_ref = _get_primary_ref(char.character_id, db)
        char_read = LibraryCharacterRead.model_validate(char)
        if primary_ref:
            char_read.primary_reference_image = CharacterRefRead.model_validate(primary_ref)
        result.append(char_read)

    return result


@router.post("/characters/{character_id}/save-to-library", response_model=SaveToLibraryResponse)
def save_character_to_library(
    character_id: uuid.UUID,
    payload: SaveToLibraryRequest | None = None,
    db=DbSessionDep,
):
    """
    Save a character to the project library.

    Once saved, the character becomes available for reuse across all stories
    in the project via "Load from Library" or "Generate with Reference".
    """
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    if character.is_library_saved:
        return SaveToLibraryResponse(
            character_id=character_id,
            is_library_saved=True,
            message="Character is already saved to library",
        )

    # Require at least one approved reference image
    approved_refs = list(
        db.execute(
            select(CharacterReferenceImage).where(
                CharacterReferenceImage.character_id == character_id,
                CharacterReferenceImage.approved.is_(True),
            )
        )
        .scalars()
        .all()
    )
    if not approved_refs:
        raise HTTPException(
            status_code=400,
            detail="Character must have at least one approved reference image to save to library",
        )

    character.is_library_saved = True
    if payload and payload.generation_prompt:
        character.generation_prompt = payload.generation_prompt

    db.add(character)
    db.commit()
    db.refresh(character)

    return SaveToLibraryResponse(
        character_id=character_id,
        is_library_saved=True,
        message=f"Character '{character.name}' saved to project library",
    )


@router.post("/characters/{character_id}/remove-from-library", response_model=SaveToLibraryResponse)
def remove_character_from_library(character_id: uuid.UUID, db=DbSessionDep):
    """
    Remove a character from the project library.

    The character remains in any stories it's linked to, but won't appear
    in the library for future reuse.
    """
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")

    if not character.is_library_saved:
        return SaveToLibraryResponse(
            character_id=character_id,
            is_library_saved=False,
            message="Character is not in library",
        )

    character.is_library_saved = False
    db.add(character)
    db.commit()
    db.refresh(character)

    return SaveToLibraryResponse(
        character_id=character_id,
        is_library_saved=False,
        message=f"Character '{character.name}' removed from project library",
    )


@router.post("/characters/{character_id}/import-from-library", response_model=CharacterRefRead)
def import_reference_from_library(
    character_id: uuid.UUID,
    payload: LoadFromLibraryRequest,
    db=DbSessionDep,
):
    """
    Import reference image and attributes from a library character to a story character.
    This copies the library character's approved face reference to the target character.
    """
    target_char = db.get(Character, character_id)
    if target_char is None:
        raise HTTPException(status_code=404, detail="Target character not found")

    library_char = db.get(Character, payload.library_character_id)
    if library_char is None:
        raise HTTPException(status_code=404, detail="Library character not found")

    if not library_char.is_library_saved:
        raise HTTPException(status_code=400, detail="Source character is not in library")

    if library_char.project_id is not None and target_char.project_id != library_char.project_id:
        raise HTTPException(status_code=400, detail="Project mismatch")

    # Get primary face ref from library char
    ref = _get_primary_ref(library_char.character_id, db)
    if not ref:
        raise HTTPException(status_code=400, detail="Library character has no approved reference image")

    # Copy attributes if target is missing them
    if not target_char.description:
        target_char.description = library_char.description
    if not target_char.identity_line:
        target_char.identity_line = library_char.identity_line
    if not target_char.appearance:
        target_char.appearance = library_char.appearance
    if not target_char.base_outfit:
        target_char.base_outfit = library_char.base_outfit
    
    # Create new reference image record for target character
    new_ref = CharacterReferenceImage(
        character_id=target_char.character_id,
        image_url=ref.image_url,
        ref_type=ref.ref_type,
        approved=True,
        is_primary=True,
        metadata_=ref.metadata_.copy() if ref.metadata_ else {},
    )
    
    # Unset other primaries for this char
    stmt = select(CharacterReferenceImage).where(
        CharacterReferenceImage.character_id == character_id,
        CharacterReferenceImage.is_primary.is_(True),
    )
    for existing in db.execute(stmt).scalars().all():
        existing.is_primary = False
        db.add(existing)

    db.add(target_char)
    db.add(new_ref)
    db.commit()
    db.refresh(new_ref)
    
    return new_ref


@router.post("/stories/{story_id}/characters/load-from-library", response_model=LoadFromLibraryResponse)
def load_character_from_library(
    story_id: uuid.UUID,
    payload: LoadFromLibraryRequest,
    db=DbSessionDep,
):
    """
    Load a character from the project library into a story.

    This creates a link between the story and the library character,
    making it available in the story without re-generation.
    """
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    library_char = db.get(Character, payload.library_character_id)
    if library_char is None:
        raise HTTPException(status_code=404, detail="library character not found")

    if library_char.project_id is not None and library_char.project_id != story.project_id:
        raise HTTPException(
            status_code=400,
            detail="Library character must be from the same project or global",
        )

    if not library_char.is_library_saved:
        raise HTTPException(
            status_code=400,
            detail="Character is not saved to library",
        )

    # Check if already linked
    existing_link = db.get(
        StoryCharacter,
        {"story_id": story_id, "character_id": payload.library_character_id},
    )
    if existing_link:
        return LoadFromLibraryResponse(
            character_id=payload.library_character_id,
            story_id=story_id,
            already_linked=True,
            message=f"Character '{library_char.name}' is already in this story",
        )

    # Create the link
    db.add(StoryCharacter(story_id=story_id, character_id=payload.library_character_id))
    db.commit()

    return LoadFromLibraryResponse(
        character_id=payload.library_character_id,
        story_id=story_id,
        already_linked=False,
        message=f"Character '{library_char.name}' added to story from library",
    )


@router.post(
    "/stories/{story_id}/characters/generate-with-reference",
    response_model=GenerateWithReferenceResponse,
)
def generate_character_with_reference(
    story_id: uuid.UUID,
    payload: GenerateWithReferenceRequest,
    db=DbSessionDep,
):
    """
    Generate a new character variant using a library character's reference image.

    This creates a new variant that retains the facial identity of the library
    character but adopts new attributes based on the current story context
    or the provided variant description.
    """
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    library_char = db.get(Character, payload.library_character_id)
    if library_char is None:
        raise HTTPException(status_code=404, detail="library character not found")

    if library_char.project_id != story.project_id:
        raise HTTPException(
            status_code=400,
            detail="Library character must be from the same project",
        )

    if not library_char.is_library_saved:
        raise HTTPException(
            status_code=400,
            detail="Character is not saved to library",
        )

    # Get the approved reference image
    base_ref = (
        db.execute(
            select(CharacterReferenceImage)
            .where(
                CharacterReferenceImage.character_id == payload.library_character_id,
                CharacterReferenceImage.ref_type == "face",
                CharacterReferenceImage.approved.is_(True),
            )
            .order_by(
                CharacterReferenceImage.is_primary.desc(),
                CharacterReferenceImage.created_at.desc(),
            )
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if base_ref is None:
        raise HTTPException(
            status_code=400,
            detail="Library character has no approved face reference image",
        )

    # -------------------------------------------------------------------------
    # CLONE STRATEGY: Create a new independent character record
    # This ensures "Save to Library" will create a new entry rather than
    # validating the existing one, avoiding the "replace" bug.
    # -------------------------------------------------------------------------

    # 1. Generate new canonical code
    existing_codes = {
        c
        for c in db.execute(
            select(Character.canonical_code).where(Character.project_id == story.project_id)
        )
        .scalars()
        .all()
        if c
    }
    new_code = _next_character_code(existing_codes)

    # 2. Create the new character clone
    new_char = Character(
        project_id=story.project_id,
        canonical_code=new_code,
        name=f"{library_char.name}",  # Keep name, user can rename
        description=library_char.description,
        role=library_char.role,
        gender=library_char.gender,
        age_range=library_char.age_range,
        appearance=library_char.appearance,
        hair_description=library_char.hair_description,
        base_outfit=library_char.base_outfit,
        identity_line=library_char.identity_line,
        approved=True,  # Implicitly approved as it comes from library
        is_library_saved=False,  # New instance is NOT yet in library
    )
    db.add(new_char)
    db.flush()  # Get ID

    # 3. Link to story
    db.add(StoryCharacter(story_id=story_id, character_id=new_char.character_id))
    db.flush()

    # Build override attributes from variant description
    override_attributes = {}
    if payload.variant_description:
        override_attributes["description"] = payload.variant_description

    try:
        # 4. Generate the variant image using the NEW character ID
        new_ref = nodes.generate_character_variant_reference_image(
            db=db,
            character_id=new_char.character_id,
            variant_type=payload.variant_type,
            override_attributes=override_attributes,
            base_reference=base_ref,
        )
        
        # 5. Set the new generated image as primary/approved for this new character
        new_ref.approved = True
        new_ref.is_primary = True
        db.add(new_ref)

    except Exception as exc:
        db.rollback()
        return GenerateWithReferenceResponse(
            character_id=payload.library_character_id,
            story_id=story_id,
            variant_id=None,
            reference_image_id=None,
            status="error",
            message=f"Failed to generate variant: {exc}",
        )

    # 6. Create variant record (optional but good for tracking history)
    variant = CharacterVariant(
        character_id=new_char.character_id,
        story_id=story_id,
        variant_type=payload.variant_type,
        override_attributes=override_attributes,
        reference_image_id=new_ref.reference_image_id,
        is_active_for_story=True,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    db.refresh(new_char)

    return GenerateWithReferenceResponse(
        character_id=new_char.character_id,
        story_id=story_id,
        variant_id=variant.variant_id,
        reference_image_id=new_ref.reference_image_id,
        status="generated",
        message=f"Generated variant '{new_char.name}' from library reference",
    )
