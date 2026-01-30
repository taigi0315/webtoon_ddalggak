"""Character extraction and normalization functions."""

from __future__ import annotations

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
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """LLM-enhanced character extraction with fallback to heuristic.

    Extracts both explicit and implied characters with evidence.

    Args:
        source_text: Story text to analyze
        max_characters: Maximum number of characters to extract
        gemini: Optional GeminiClient for LLM-based extraction

    Returns:
        List of character profile dicts
    """
    if gemini is None:
        return compute_character_profiles(source_text, max_characters)

    prompt = _prompt_character_extraction(source_text, max_characters)
    result = _maybe_json_from_gemini(gemini, prompt)

    if result and isinstance(result.get("characters"), list):
        profiles = []
        for char in result["characters"][:max_characters]:
            name = char.get("name", "").strip()
            if not name:
                continue
            profiles.append({
                "name": name,
                "role": char.get("role", "secondary"),
                "description": char.get("relationship_to_main"),
                "evidence_quotes": char.get("evidence_quotes", []),
                "implied": char.get("implied", False),
            })
        if profiles:
            return profiles

    # Fallback to heuristic
    logger.info("Falling back to heuristic character extraction")
    return compute_character_profiles(source_text, max_characters)


def normalize_character_profiles_llm(
    profiles: list[dict],
    source_text: str = "",
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """LLM-enhanced character normalization with appearance details.

    Falls back to heuristic normalization if LLM fails.

    Args:
        profiles: List of character profile dicts to normalize
        source_text: Story text for context
        gemini: Optional GeminiClient for LLM-based normalization

    Returns:
        List of normalized character profile dicts with appearance details
    """
    if gemini is None or not profiles:
        return normalize_character_profiles(profiles)

    prompt = _prompt_character_normalization(profiles, source_text)
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

    # Fallback to heuristic
    logger.info("Falling back to heuristic character normalization")
    return normalize_character_profiles(profiles)
