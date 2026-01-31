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
) -> str:
    """Compile a production-grade image generation prompt with rich visual details."""
    style_desc = _style_description(style_id)
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

    mapping = loaders.load_grammar_to_prompt_mapping_v1().mapping

    lines = [
        "**ASPECT RATIO & FORMAT:**",
        "- CRITICAL: Vertical 9:16 webtoon/manhwa image for vertical scrolling.",
        "",
        "**REFERENCE IMAGE AUTHORITY:**",
        "- Character reference images are the PRIMARY source of facial identity, proportions, and features.",
        "- Do NOT reinterpret or redesign faces based on text.",
        "- Text descriptions are for role, action, emotion, and clothing ONLY.",
        "- Faces, hairstyles, glasses shape, and proportions must match reference images exactly.",
        "",
        f"**STYLE:** {style_desc}",
        "",
        "**PANEL COMPOSITION RULES:**",
        f"- Layout: {layout_text or f'{panel_count} panels, vertical flow'}",
        f"- Panel count: {panel_count} (do not add or remove panels)",
        "- Panels do NOT need equal sizes or grid alignment.",
        "- You may use one dominant panel with smaller inset panels.",
        "- Panels can vary in size and position if reading order is clear (top to bottom).",
        "- If there is a reveal/impact/emotional peak, make that panel dominant.",
        "",
    ]

    if identity_lines:
        lines.append("**CHARACTERS (reference images provided; keep appearance consistent):**")
        lines.extend(identity_lines)
        lines.append("")

    lines.append("**PANELS (action/emotion/environment only; no text in image):**")

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

    lines.extend(
        [
            "**TECHNICAL REQUIREMENTS:**",
            "- Korean webtoon/manhwa art style (Naver webtoon quality)",
            "- Show full body only when the scene composition requires it",
            "- Masterpiece best quality professional illustration",
            "- No text, speech bubbles, or watermarks in image",
            "- Leave clear space for dialogue bubbles to be added later",
            "- Consistent character appearance across panels",
            "",
            "**NEGATIVE:** text, watermark, signature, logo, speech bubbles, conflicting descriptions, "
            "square image, 1:1 ratio, horizontal image, landscape orientation, "
            "western comic style, anime chibi (unless specified), "
            "low quality, blurry, amateur, inconsistent character design",
        ]
    )

    return "\n".join([line for line in lines if line is not None])


def _style_description(style_id: str) -> str:
    from app.core.image_styles import get_style_semantic_hint
    return get_style_semantic_hint(style_id)


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
