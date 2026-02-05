"""Character extraction and normalization functions."""

from __future__ import annotations

import re
from typing import Iterable

from ..utils import (
    logger,
    _extract_metadata_names,
    _extract_names,
    _maybe_json_from_gemini,
    _prompt_character_extraction,
    _prompt_character_normalization,
    GeminiClient,
)


# Style keywords that should not appear in character descriptions
FORBIDDEN_STYLE_KEYWORDS = [
    "manhwa",
    "webtoon",
    "aesthetic",
    "flower-boy",
    "k-drama",
    "korean male lead",
    "romance female lead",
    "naver webtoon",
    "authentic",
    "trending",
    "statuesque",
    "willowy",
]

_NARRATOR_LIKE_NAMES = {
    "narrator",
    "the narrator",
    "voiceover",
    "voice-over",
    "inner voice",
    "first person narrator",
    "i",
    "me",
    "myself",
}


def _canonicalize_character_name(raw_name: str, source_text: str, character_hints: list[dict] | None = None) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return ""
    lowered = name.lower()
    if lowered in _NARRATOR_LIKE_NAMES:
        if character_hints:
            for hint in character_hints:
                hinted_name = str((hint or {}).get("name") or "").strip()
                if hinted_name:
                    return hinted_name
        # Keep a concrete, render-friendly fallback name instead of "Narrator".
        if re.search(r"\b(dragon|beast|quest|sword|magic|flame)\b", source_text or "", re.IGNORECASE):
            return "Kael"
        return "Min"
    return name


def compute_character_profiles(source_text: str, max_characters: int = 6) -> list[dict]:
    """Extract character profiles from story text using heuristics.

    Args:
        source_text: Story text to analyze
        max_characters: Maximum number of characters to extract

    Returns:
        List of character profile dicts with name, description, role, identity_line
    """
    text = (source_text or "").strip()
    max_characters = max(1, int(max_characters))

    excluded = _extract_metadata_names(text)
    names = _extract_names(text, excluded=excluded)
    profiles: list[dict] = []

    if not names:
        profiles.append(
            {
                "name": "Protagonist",
                "description": None,
                "role": "main",
                "identity_line": "Protagonist: central character.",
            }
        )
        return profiles

    for idx, name in enumerate(names[:max_characters]):
        role = "main" if idx < 2 else "secondary"
        profiles.append(
            {
                "name": name,
                "description": None,
                "role": role,
                "identity_line": f"{name}: {role} character.",
            }
        )
    return profiles


def normalize_character_profiles(profiles: Iterable[dict]) -> list[dict]:
    """Normalize character profiles to ensure consistent structure.

    Args:
        profiles: Iterable of character profile dicts

    Returns:
        List of normalized character profile dicts
    """
    seen: set[str] = set()
    normalized: list[dict] = []
    unnamed_count = 0

    for profile in profiles:
        name = str(profile.get("name") or "").strip()
        if not name:
            unnamed_count += 1
            name = f"Unnamed Character {unnamed_count}"
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        role = (profile.get("role") or "secondary").strip() or "secondary"
        description = profile.get("description")
        identity_line = profile.get("identity_line")
        if not identity_line:
            if description:
                identity_line = f"{name}: {description}"
            else:
                identity_line = f"{name}: {role} character."

        normalized.append(
            {
                "name": name,
                "description": description,
                "role": role,
                "identity_line": identity_line,
            }
        )
    return normalized


def compute_character_profiles_llm(
    source_text: str,
    max_characters: int = 6,
    character_hints: list[dict] | None = None,
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """LLM-enhanced character extraction.

    Extracts both explicit and implied characters with evidence.

    Args:
        source_text: Story text to analyze
        max_characters: Maximum number of characters to extract
        gemini: Optional GeminiClient for LLM-based extraction

    Returns:
        List of character profile dicts
    """
    if gemini is None:
        logger.error("character_extractor fail-fast: Gemini client missing")
        raise RuntimeError("character_extractor requires Gemini client (fallback disabled)")

    prompt = _prompt_character_extraction(source_text, max_characters, character_hints=character_hints or [])
    logger.info("character_extractor llm request started (max_characters=%s)", max_characters)
    result = _maybe_json_from_gemini(gemini, prompt)

    if result and isinstance(result.get("characters"), list):
        profiles = []
        seen_names: set[str] = set()
        for char in result["characters"][:max_characters]:
            name = _canonicalize_character_name(char.get("name", ""), source_text, character_hints=character_hints)
            if not name:
                continue
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            profiles.append({
                "name": name,
                "role": char.get("role", "secondary"),
                "description": char.get("relationship_to_main"),
                "evidence_quotes": char.get("evidence_quotes", []),
                "implied": char.get("implied", False),
            })
        if profiles:
            return profiles

    err_type = getattr(gemini, "last_error_type", None)
    req_id = getattr(gemini, "last_request_id", None)
    hint = ""
    if err_type == "invalid_request":
        hint = " (hint: check GEMINI_API_KEY / Google AI Studio key validity)"
    logger.error(
        "character_extractor generation failed: invalid/empty Gemini JSON (error_type=%s, request_id=%s)%s",
        err_type,
        req_id,
        hint,
    )
    raise RuntimeError(
        f"character_extractor failed: Gemini returned invalid JSON"
        f"{' [invalid_request: check API key]' if err_type == 'invalid_request' else ''}"
    )


def normalize_character_profiles_llm(
    profiles: list[dict],
    source_text: str = "",
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """LLM-enhanced character normalization with appearance details.

    Args:
        profiles: List of character profile dicts to normalize
        source_text: Story text for context
        gemini: Optional GeminiClient for LLM-based normalization

    Returns:
        List of normalized character profile dicts with appearance details
    """
    if not profiles:
        return normalize_character_profiles(profiles)
    if gemini is None:
        logger.error("character_normalizer fail-fast: Gemini client missing")
        raise RuntimeError("character_normalizer requires Gemini client (fallback disabled)")

    prompt = _prompt_character_normalization(profiles, source_text)
    logger.info("character_normalizer llm request started (input_characters=%s)", len(profiles))
    result = _maybe_json_from_gemini(gemini, prompt)

    if result and isinstance(result.get("characters"), list):
        normalized = []
        seen: set[str] = set()
        for char in result["characters"]:
            name = str(char.get("name", "")).strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)

            # Sanitize character output to remove style keywords
            char = _sanitize_character_output(char, name)

            # Build identity line if not provided
            identity_line = char.get("identity_line")
            if not identity_line:
                parts = []
                if char.get("age_range"):
                    parts.append(char["age_range"])
                if char.get("gender") and char["gender"] != "unknown":
                    parts.append(char["gender"])
                appearance = char.get("appearance", {})
                if appearance.get("hair"):
                    parts.append(appearance["hair"])
                if appearance.get("build"):
                    parts.append(appearance["build"])
                if char.get("outfit"):
                    parts.append(char["outfit"])
                identity_line = f"{name}: {', '.join(parts)}" if parts else f"{name}: {char.get('role', 'character')}"

            normalized.append({
                "name": name,
                "role": char.get("role", "secondary"),
                "description": char.get("description"),
                "gender": char.get("gender"),
                "age_range": char.get("age_range"),
                "appearance": char.get("appearance"),
                "outfit": char.get("outfit"),
                "identity_line": identity_line,
            })
        if normalized:
            return normalized

    err_type = getattr(gemini, "last_error_type", None)
    req_id = getattr(gemini, "last_request_id", None)
    hint = ""
    if err_type == "invalid_request":
        hint = " (hint: check GEMINI_API_KEY / Google AI Studio key validity)"
    logger.error(
        "character_normalizer generation failed: invalid/empty Gemini JSON (error_type=%s, request_id=%s)%s",
        err_type,
        req_id,
        hint,
    )
    raise RuntimeError(
        f"character_normalizer failed: Gemini returned invalid JSON"
        f"{' [invalid_request: check API key]' if err_type == 'invalid_request' else ''}"
    )


def _sanitize_character_output(char: dict, name: str) -> dict:
    """Remove forbidden style keywords from character output.
    
    Args:
        char: Character dict from LLM output
        name: Character name for logging
        
    Returns:
        Sanitized character dict
    """
    def _remove_keywords(text: str | None) -> str | None:
        """Remove forbidden keywords from text (case-insensitive)."""
        if not text:
            return text
        
        # Ensure text is a string
        if not isinstance(text, str):
            logger.warning(
                f"Expected string for character '{name}', got {type(text).__name__}. Converting to string."
            )
            text = str(text)
        
        cleaned = text
        found_keywords = []
        
        for keyword in FORBIDDEN_STYLE_KEYWORDS:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            if pattern.search(cleaned):
                found_keywords.append(keyword)
                cleaned = pattern.sub("", cleaned)
        
        # Clean up extra spaces and punctuation
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(r"\s*,\s*,", ",", cleaned)  # Remove double commas
        cleaned = re.sub(r"^[,\s]+|[,\s]+$", "", cleaned)  # Remove leading/trailing commas
        
        if found_keywords:
            logger.warning(
                f"Removed style keywords from character '{name}': {', '.join(found_keywords)}"
            )
        
        return cleaned
    
    # Sanitize identity_line
    if char.get("identity_line"):
        char["identity_line"] = _remove_keywords(char["identity_line"])
    
    # Sanitize appearance fields
    if isinstance(char.get("appearance"), dict):
        appearance = char["appearance"]
        for field in ["hair", "face", "build"]:
            if appearance.get(field):
                # Ensure the field value is a string before processing
                if isinstance(appearance[field], str):
                    appearance[field] = _remove_keywords(appearance[field])
                else:
                    logger.warning(
                        f"Character '{name}' appearance.{field} is not a string (type: {type(appearance[field]).__name__}), skipping sanitization"
                    )
    
    # Sanitize outfit
    if char.get("outfit"):
        char["outfit"] = _remove_keywords(char["outfit"])
    
    # Sanitize description
    if char.get("description"):
        char["description"] = _remove_keywords(char["description"])
    
    return char
