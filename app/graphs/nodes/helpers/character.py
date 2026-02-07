import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Character, CharacterReferenceImage, CharacterVariant, StoryCharacter
from app.prompts.loader import get_prompt_data

CHARACTER_STYLE_MAP = get_prompt_data("character_style_map")


def get_character_style_prompt(gender: str | None, age_range: str | None) -> str:
    """Get the appropriate character style prompt based on gender and age."""
    if not gender or not age_range:
        return ""
    gender_key = gender.lower()
    age_key = age_range.lower()
    by_gender = CHARACTER_STYLE_MAP.get(gender_key)
    if isinstance(by_gender, dict):
        value = by_gender.get(age_key)
        return value or ""
    return ""


def _active_variants_by_character(
    db: Session,
    story_id: uuid.UUID,
) -> dict[uuid.UUID | tuple[uuid.UUID, str], CharacterVariant]:
    """Get mapping of (character_id, variant_type) to variant."""
    variants = list(
        db.execute(
            select(CharacterVariant)
            .where(
                CharacterVariant.story_id == story_id,
                CharacterVariant.is_active_for_story.is_(True),
            )
        )
        .scalars()
        .all()
    )
    results = {}
    for variant in variants:
        # Default by character_id
        if variant.character_id not in results:
            results[variant.character_id] = variant
        # Specific key by (character_id, type)
        results[(variant.character_id, variant.variant_type.lower())] = variant
    return results


def _active_variant_reference_images(
    db: Session,
    story_id: uuid.UUID,
) -> dict[tuple[uuid.UUID, str], CharacterReferenceImage]:
    """Get mapping of (character_id, variant_type) to reference image."""
    variants = list(_active_variants_by_character(db, story_id).values())
    if not variants:
        return {}

    variant_ids = {variant.reference_image_id for variant in variants if variant.reference_image_id}
    if not variant_ids:
        return {}

    refs = list(
        db.execute(
            select(CharacterReferenceImage).where(CharacterReferenceImage.reference_image_id.in_(variant_ids))
        )
        .scalars()
        .all()
    )
    ref_lookup = {ref.reference_image_id: ref for ref in refs}
    results: dict[tuple[uuid.UUID, str], CharacterReferenceImage] = {}
    for variant in variants:
        ref = ref_lookup.get(variant.reference_image_id)
        if ref is None:
            continue
        results[(variant.character_id, variant.variant_type.lower())] = ref
    return results


def _character_codes(characters: list[Character]) -> dict[uuid.UUID, str]:
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

    codes: dict[uuid.UUID, str] = {}
    used = {c.canonical_code for c in characters if c.canonical_code}
    idx = 0
    for c in characters:
        if c.canonical_code:
            codes[c.character_id] = c.canonical_code
            continue
        while True:
            code = _code_from_index(idx)
            idx += 1
            if code not in used:
                used.add(code)
                codes[c.character_id] = code
                break
    return codes


def _inject_character_identities(
    panel_semantics: dict,
    characters: list[Character],
    reference_char_ids: set[uuid.UUID],
    variants_by_character: dict[tuple[uuid.UUID, str], CharacterVariant] | dict[uuid.UUID, CharacterVariant] | None = None,
    style_id: str | None = None,
) -> dict:
    if not panel_semantics or not characters:
        return panel_semantics

    codes = _character_codes(characters)
    name_map: dict[str, dict[str, str]] = {}
    variants_by_character = variants_by_character or {}
    
    for c in characters:
        code = codes.get(c.character_id, "CHAR_X")
        base = f"{code} ({c.name})"
        dialogue_label = base
        
        # Resolve variant: style-specific -> chibi (if chibi style) -> default -> any
        variant = None
        if isinstance(variants_by_character, dict):
            if style_id:
                style_key = style_id.lower()
                variant = variants_by_character.get((c.character_id, style_key))
                
                # Check for "chibi" heuristic if specific style variant not found
                if not variant and "chibi" in style_key:
                    variant = variants_by_character.get((c.character_id, "chibi"))
                    
            if not variant:
                variant = variants_by_character.get((c.character_id, "default"))
            if not variant:
                # Fallback to simple lookup if the map is {character_id: variant}
                variant = variants_by_character.get(c.character_id)
                if not variant:
                    # Fallback to searching first variant for this character if it's a tuple map
                    for key, v in variants_by_character.items():
                        if isinstance(key, tuple) and len(key) == 2:
                            cid, _vtype = key
                            if cid == c.character_id:
                                variant = v
                                break

        variant_outfit = None
        if variant and isinstance(variant.override_attributes, dict):
            variant_outfit = variant.override_attributes.get("outfit") or variant.override_attributes.get("clothing")
        
        if c.character_id in reference_char_ids:
            parts = [base, "matching reference image"]
            if variant_outfit:
                parts.append(f"wearing {variant_outfit}")
            label = ", ".join(parts)
        else:
            parts = [base]
            if variant_outfit:
                parts.append(f"wearing {variant_outfit}")
            elif c.base_outfit:
                parts.append(f"wearing {c.base_outfit}")
            if c.hair_description:
                parts.append(f"hair: {c.hair_description}")
            label = ", ".join(parts)
        name_map[c.name.lower()] = {"label": label, "code": base, "dialogue_label": dialogue_label}

    forbidden_terms = [
        "hair",
        "hairstyle",
        "bangs",
        "eyes",
        "eye",
        "jawline",
        "cheekbones",
        "face",
        "facial",
        "height",
        "tall",
        "short",
        "slender",
        "muscular",
        "curvy",
        "build",
        "physique",
        "proportions",
        "handsome",
        "beautiful",
        "pretty",
        "attractive",
    ]

    def _strip_forbidden_descriptors(text: str) -> str:
        cleaned = text
        cleaned = re.sub(r"\b\d{2,3}\s?cm\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d\.\d\s?m\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d'\d{1,2}\"?\b", "", cleaned)
        for term in forbidden_terms:
            cleaned = re.sub(rf"\b{re.escape(term)}\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        return cleaned

    def _replace_text(text: str, label_key: str = "label") -> str:
        if not text:
            return text
        updated = text
        matched_reference = False
        for name, payload in name_map.items():
            pattern = re.compile(rf"\b({re.escape(name)})('s)?\b", re.IGNORECASE)
            if pattern.search(updated):
                for c in characters:
                    if c.name and c.name.lower() == name and c.character_id in reference_char_ids:
                        matched_reference = True
                        break

            def _repl(match: re.Match) -> str:
                suffix = match.group(2) or ""
                return f"{payload[label_key]}{suffix}"

            updated = pattern.sub(_repl, updated)
        if matched_reference:
            updated = _strip_forbidden_descriptors(updated)
        return updated

    cloned = dict(panel_semantics)
    panels = []
    for panel in panel_semantics.get("panels", []) or []:
        updated_panel = dict(panel)
        if updated_panel.get("description"):
            updated_panel["description"] = _replace_text(str(updated_panel["description"]), "label")
        if updated_panel.get("dialogue"):
            updated_dialogue = []
            for line in updated_panel["dialogue"]:
                if isinstance(line, dict):
                    char_name = str(line.get("character") or "")
                    key = char_name.lower()
                    if key in name_map:
                        updated_line = dict(line)
                        updated_line["character"] = name_map[key]["dialogue_label"]
                        updated_dialogue.append(updated_line)
                    else:
                        updated_dialogue.append(line)
                else:
                    updated_dialogue.append(_replace_text(str(line), "dialogue_label"))
            updated_panel["dialogue"] = updated_dialogue
        panels.append(updated_panel)
    cloned["panels"] = panels
    return cloned
