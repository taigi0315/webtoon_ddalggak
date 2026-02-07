import re
import uuid

from app.config import loaders
from app.db.models import Character, CharacterVariant
from app.graphs.nodes.helpers.character import _character_codes, _inject_character_identities


def _compile_prompt(
    panel_semantics: dict,
    layout_template: dict,
    style_id: str,
    characters: list[Character],
    reference_char_ids: set[uuid.UUID] | None = None,
    variants_by_character: dict[tuple[uuid.UUID, str], CharacterVariant] | dict[uuid.UUID, CharacterVariant] | None = None,
    art_direction: dict | None = None,
) -> str:
    """Compile a production-grade image generation prompt with layered hierarchy.
    
    Prompt Layering Hierarchy (highest to lowest priority):
    1. Image Style (user-selected, highest authority)
    2. Art Direction (mood & atmosphere from Art Director)
    3. Format & Composition (technical requirements)
    4. Reference Image Authority (character consistency)
    5. Panel Composition (cinematographer's layout)
    6. Characters (morphology only, style-neutral)
    7. Panels (scene-specific visual descriptions)
    8. Technical Requirements (style-agnostic quality standards)
    9. Negative Prompt (what to avoid)
    
    Args:
        panel_semantics: Panel descriptions from cinematographer
        layout_template: Layout geometry
        style_id: User-selected image style ID
        characters: List of characters in scene
        reference_char_ids: Character IDs with reference images
        variants_by_character: Character variant overrides
        art_direction: Art direction data (lighting, color_temperature, atmosphere)
    
    Returns:
        Compiled prompt string with layered structure
        
    Raises:
        ValueError: If prompt validation fails (forbidden anchors detected or expected style missing)
    """
    style_desc_raw = _style_description(style_id)
    style_desc, _ = _strip_forbidden_style_anchors(style_desc_raw)
    layout_text = layout_template.get("layout_text", "")
    reference_char_ids = reference_char_ids or set()
    panel_semantics = _inject_character_identities(
        panel_semantics=panel_semantics,
        characters=characters,
        reference_char_ids=reference_char_ids,
        variants_by_character=variants_by_character,
        style_id=style_id,
    )
    panels = panel_semantics.get("panels", []) or []
    panel_count = len(panels)

    # Build prompt layers
    layers = []
    
    # LAYER 1: Image Style (highest priority)
    layers.append(_build_style_layer(style_desc))
    
    # LAYER 2: Art Direction (mood & atmosphere)
    if art_direction:
        layers.append(_build_art_direction_layer(art_direction))
    
    # LAYER 3: Format & Composition
    layers.append(_build_format_layer())
    
    # LAYER 4: Reference Image Authority
    layers.append(_build_reference_authority_layer())
    
    # LAYER 5: Panel Composition (cinematographer)
    layers.append(_build_panel_composition_layer(layout_text, panel_count))
    
    # LAYER 6: Characters (morphology only)
    character_layer = _build_character_layer(
        characters, reference_char_ids, variants_by_character, style_id
    )
    if character_layer:
        layers.append(character_layer)
    
    # LAYER 7: Panels (scene-specific)
    layers.append(_build_panels_layer(panels))
    
    # LAYER 8: Technical Requirements
    layers.append(_build_technical_requirements_layer())
    
    # LAYER 9: Negative Prompt
    layers.append(_build_negative_prompt_layer())
    
    compiled_prompt = "\n\n".join(layers)
    compiled_prompt, removed_anchors = _strip_forbidden_style_anchors(compiled_prompt)
    if removed_anchors:
        import logging
        logging.getLogger(__name__).warning(
            "prompt_sanitized removed_anchors=%s style_id=%s",
            ",".join(sorted(set(removed_anchors))),
            style_id,
        )

    # Validate compiled prompt
    _validate_compiled_prompt(compiled_prompt, style_id, style_desc)
    
    return compiled_prompt


def _build_style_layer(style_desc: str) -> str:
    """Layer 1: Image Style (highest priority)."""
    return f"**STYLE:** {style_desc}"


def _build_art_direction_layer(art_direction: dict) -> str:
    """Layer 2: Art Direction (mood & atmosphere)."""
    lines = ["**ART DIRECTION:**"]
    
    if art_direction.get("lighting"):
        lines.append(f"- Lighting: {art_direction['lighting']}")
    
    if art_direction.get("color_temperature"):
        color_temp = art_direction["color_temperature"]
        # Filter out N/A values (case-insensitive check)
        if color_temp and not color_temp.upper().startswith("N/A"):
            lines.append(f"- Color Temperature: {color_temp}")
    
    if art_direction.get("atmosphere_keywords"):
        keywords = art_direction["atmosphere_keywords"]
        if isinstance(keywords, list) and keywords:
            lines.append(f"- Atmosphere: {', '.join(keywords[:5])}")
    
    return "\n".join(lines)


def _build_format_layer() -> str:
    """Layer 3: Format & Composition."""
    return "\n".join([
        "**ASPECT RATIO & FORMAT:**",
        "- CRITICAL: Vertical 9:16 format for vertical scrolling.",
    ])


def _build_reference_authority_layer() -> str:
    """Layer 4: Reference Image Authority."""
    return "\n".join([
        "**REFERENCE IMAGE AUTHORITY:**",
        "- Character reference images are the PRIMARY source of facial identity, proportions, and features.",
        "- Do NOT reinterpret or redesign faces based on text.",
        "- Text descriptions are for role, action, emotion, and clothing ONLY.",
        "- Faces, hairstyles, glasses shape, and proportions must match reference images exactly.",
    ])


def _build_panel_composition_layer(layout_text: str, panel_count: int) -> str:
    """Layer 5: Panel Composition (cinematographer)."""
    return "\n".join([
        "**PANEL COMPOSITION RULES:**",
        f"- Layout: {layout_text or f'{panel_count} panels, vertical flow'}",
        f"- Panel count: {panel_count} (do not add or remove panels)",
        "- Panels do NOT need equal sizes or grid alignment.",
        "- You may use one dominant panel with smaller inset panels.",
        "- Panels can vary in size and position if reading order is clear (top to bottom).",
        "- If there is a reveal/impact/emotional peak, make that panel dominant.",
    ])


def _build_character_layer(
    characters: list[Character],
    reference_char_ids: set[uuid.UUID],
    variants_by_character: dict | None,
    style_id: str,
) -> str | None:
    """Layer 6: Characters (morphology only, style-neutral)."""
    def _trim_outfit(text: str | None, max_words: int = 10) -> str | None:
        if not text:
            return None
        words = re.findall(r"\w+|[^\w\s]", str(text))
        if not words:
            return None
        trimmed = " ".join(words[:max_words]).strip()
        return trimmed

    identity_lines = []
    codes = _character_codes(characters)
    
    for c in characters:
        code = codes.get(c.character_id)
        role = c.role or "character"
        
        # Resolve variant for identity block
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
                variant = variants_by_character.get(c.character_id)
                if not variant:
                    for (cid, vtype), v in variants_by_character.items():
                        if cid == c.character_id:
                            variant = v
                            break

        variant_outfit = None
        if variant and isinstance(variant.override_attributes, dict):
            variant_outfit = variant.override_attributes.get("outfit") or variant.override_attributes.get("clothing")
        
        char_lines = [f"  - {code} ({c.name}) [{role}]"]
        
        if c.character_id in reference_char_ids:
            if variant_outfit:
                char_lines.append(f"    Outfit: {variant_outfit}")
            elif c.base_outfit:
                trimmed = _trim_outfit(c.base_outfit)
                if trimmed:
                    char_lines.append(f"    Outfit: {trimmed}")
        else:
            if variant_outfit:
                char_lines.append(f"    Outfit: {variant_outfit}")
            elif c.base_outfit:
                char_lines.append(f"    Outfit: {c.base_outfit}")
            
            appearance = getattr(c, "appearance", None)
            if isinstance(appearance, dict):
                brief = []
                if appearance.get("hair"):
                    brief.append(f"Hair: {appearance['hair']}")
                if appearance.get("face"):
                    brief.append(f"Face: {appearance['face']}")
                if appearance.get("build"):
                    brief.append(f"Build: {appearance['build']}")
                if brief:
                    char_lines.append(f"    Appearance: {'; '.join(brief)}")
            elif c.description:
                char_lines.append(f"    Appearance: {c.description}")
        
        identity_lines.extend(char_lines)
    
    if not identity_lines:
        return None
    
    lines = ["**CHARACTERS (reference images provided; keep appearance consistent):**"]
    lines.extend(identity_lines)
    return "\n".join(lines)


def _build_panels_layer(panels: list[dict]) -> str:
    """Layer 7: Panels (scene-specific visual descriptions)."""
    mapping = loaders.load_grammar_to_prompt_mapping_v1().mapping
    
    def _strip_layout_tokens(text: str) -> str:
        cleaned = text
        patterns = [
            r"\bvertical\s*9:16\s*webtoon\s*panel\b",
            r"\b9:16\s*webtoon\s*panel\b",
            r"\bvertical\s*9:16\b",
            r"\b9:16\s*vertical\b",
            r"\bvertical\s*panel\b",
        ]
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = cleaned.strip(" ,;:-")
        return cleaned
    
    lines = ["**PANELS (action/emotion/environment only; no text in image):**"]
    
    for panel in panels:
        grammar_id = panel.get("grammar_id")
        grammar_hint = mapping.get(grammar_id, "")
        desc = panel.get("description", "")
        if isinstance(desc, str) and desc:
            desc = _strip_layout_tokens(desc)

        environment = panel.get("environment", {})
        lighting = panel.get("lighting", {})
        atmosphere = panel.get("atmosphere_keywords", [])

        panel_lines = [f"Panel {panel.get('panel_index')}: {grammar_hint}".strip()]

        if desc:
            panel_lines.append(f"  Visual: {desc}")

        if isinstance(environment, dict):
            env_parts = []
            if environment.get("location"):
                env_parts.append(f"Location: {environment['location']}")
            if environment.get("architecture"):
                env_parts.append(f"Architecture: {environment['architecture']}")
            if environment.get("props"):
                env_parts.append(f"Props: {', '.join(environment['props'][:5])}")
            if env_parts:
                panel_lines.append(f"  Environment: {'; '.join(env_parts)}")

        if isinstance(lighting, dict):
            light_parts = []
            if lighting.get("source"):
                light_parts.append(f"{lighting['source']} light")
            if lighting.get("quality"):
                light_parts.append(lighting["quality"])
            if lighting.get("color_temperature"):
                light_parts.append(f"{lighting['color_temperature']} temperature")
            if light_parts:
                panel_lines.append(f"  Lighting: {', '.join(light_parts)}")

        if atmosphere:
            panel_lines.append(f"  Atmosphere: {', '.join(atmosphere[:5])}")

        dialogue = panel.get("dialogue") or []
        if dialogue:
            if isinstance(dialogue, list) and dialogue:
                if isinstance(dialogue[0], dict):
                    dialogue_text = " | ".join([f"{d.get('character', '?')}: \"{d.get('text', '')}\"" for d in dialogue[:3]])
                else:
                    dialogue_text = " | ".join([f"\"{d}\"" for d in dialogue[:3]])
            else:
                dialogue_text = str(dialogue)
            panel_lines.append(f"  Dialogue context (do NOT render text): {dialogue_text}")

        lines.extend(panel_lines)
        lines.append("")
    
    return "\n".join([line for line in lines if line is not None])


def _build_technical_requirements_layer() -> str:
    """Layer 8: Technical Requirements (style-agnostic)."""
    return "\n".join([
        "**TECHNICAL REQUIREMENTS:**",
        "- Show full body only when the scene composition requires it",
        "- Masterpiece best quality professional illustration",
        "- No text, speech bubbles, or watermarks in image",
        "- Leave clear space for dialogue bubbles to be added later",
        "- Consistent character appearance across panels",
    ])


def _build_negative_prompt_layer() -> str:
    """Layer 9: Negative Prompt."""
    return "\n".join([
        "**NEGATIVE:** text, watermark, signature, logo, speech bubbles, conflicting descriptions, "
        "square image, 1:1 ratio, horizontal image, landscape orientation, "
        "western comic style, anime chibi (unless specified), "
        "low quality, blurry, amateur, inconsistent character design",
    ])


def _style_description(style_id: str) -> str:
    from app.core.image_styles import get_style_semantic_hint
    return get_style_semantic_hint(style_id)


def _strip_forbidden_style_anchors(text: str) -> tuple[str, list[str]]:
    if not text:
        return text, []
    anchors = [
        "korean webtoon",
        "korean manhwa",
        "naver webtoon",
        "manhwa art style",
        "webtoon art style",
        "manhwa aesthetic",
        "webtoon aesthetic",
        "korean webtoon style",
        "korean manhwa style",
    ]
    cleaned = text
    removed: list[str] = []
    for anchor in anchors:
        pattern = rf"(?i)\b{re.escape(anchor)}\b"
        if re.search(pattern, cleaned):
            removed.append(anchor)
            cleaned = re.sub(pattern, "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), removed


def _validate_compiled_prompt(prompt: str, style_id: str, style_desc: str) -> None:
    """
    Validate compiled prompt for forbidden hardcoded anchors and expected style presence.
    
    Args:
        prompt: Compiled prompt string
        style_id: User-selected image style ID
        style_desc: Style description from get_style_semantic_hint
        
    Raises:
        ValueError: If validation fails
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Forbidden hardcoded anchors that should never appear in prompts
    forbidden_anchors = [
        "korean webtoon",
        "korean manhwa",
        "naver webtoon",
        "manhwa art style",
        "webtoon art style",
        "manhwa aesthetic",
        "webtoon aesthetic",
    ]
    
    prompt_lower = prompt.lower()
    
    # Check for forbidden anchors
    detected_anchors = []
    for anchor in forbidden_anchors:
        if anchor in prompt_lower:
            detected_anchors.append(anchor)
    
    if detected_anchors:
        error_msg = (
            f"Prompt validation failed: Forbidden hardcoded anchors detected: {', '.join(detected_anchors)}. "
            f"These anchors override user-selected style '{style_id}' and must not appear in prompts."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Verify expected style appears in prompt (unless it's "default")
    if style_id and style_id.lower() != "default":
        # Check if style description appears in prompt
        if style_desc and style_desc.lower() not in prompt_lower:
            warning_msg = (
                f"Prompt validation warning: Expected style '{style_id}' (description: '{style_desc}') "
                f"not found in compiled prompt. This may indicate a style loading issue."
            )
            logger.warning(warning_msg)
            # Don't raise exception for this, just log warning


def _panel_semantics_text(panel_semantics: dict) -> str:
    panels = panel_semantics.get("panels", []) or []
    lines = []
    for panel in panels:
        grammar_id = panel.get("grammar_id")
        description = panel.get("description", "")
        dialogue = panel.get("dialogue")
        lines.append(f"{grammar_id}: {description}")
        if dialogue:
            lines.append(f"dialogue: {dialogue}")
    return "\n".join(lines)
