import json
import math
import re

from app.services.vertex_gemini import GeminiClient
from .gemini import _build_gemini_client


def compute_scene_chunker(
    source_text: str,
    max_scenes: int = 6,
    gemini: GeminiClient | None = None,
) -> list[str]:
    if not source_text or not source_text.strip():
        raise ValueError("source_text is required for auto-chunking")

    gemini = gemini or _build_gemini_client()
    prompt = (
        "Split the story into distinct scenes. Return ONLY a JSON list of scene strings.\n"
        "Rules:\n"
        "- Each scene should be 1-4 sentences.\n"
        f"- Max scenes: {max_scenes}.\n"
        "- Do not include numbering or extra keys.\n\n"
        f"STORY_TEXT:\n{source_text}\n"
    )

    text = gemini.generate_text(prompt)
    chunks: list[str] = []
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            chunks = [str(item).strip() for item in payload if str(item).strip()]
    except Exception:
        chunks = []

    if len(chunks) <= 1:
        chunks = []

    if not chunks:
        # Fallback: split by paragraphs, then by sentences.
        paragraphs = [p.strip() for p in source_text.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            chunks = paragraphs
        else:
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", source_text.strip())
                if s.strip()
            ]
            if sentences:
                target = max_scenes if max_scenes and max_scenes > 0 else 6
                size = max(1, math.ceil(len(sentences) / target))
                chunks = [" ".join(sentences[i : i + size]) for i in range(0, len(sentences), size)]

    if max_scenes and len(chunks) > max_scenes:
        chunks = chunks[:max_scenes]

    return chunks


def compute_character_profiles(
    source_text: str,
    max_characters: int = 6,
    gemini: GeminiClient | None = None,
) -> list[dict]:
    if not source_text or not source_text.strip():
        raise ValueError("source_text is required for character extraction")

    gemini = gemini or _build_gemini_client()
    prompt = (
        "Extract the main characters from the story. Return ONLY a JSON list of objects.\n"
        "Each object must include: name, role (main or secondary), description, identity_line.\n"
        f"Limit to at most {max_characters} characters. No extra keys.\n\n"
        f"STORY_TEXT:\n{source_text}\n"
    )

    text = gemini.generate_text(prompt)
    characters: list[dict] = []
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                role = str(item.get("role") or "secondary").strip().lower()
                role = role if role in {"main", "secondary"} else "secondary"
                characters.append(
                    {
                        "name": name,
                        "role": role,
                        "description": (item.get("description") or None),
                        "identity_line": (item.get("identity_line") or None),
                    }
                )
    except Exception:
        characters = []

    if not characters:
        # Simple fallback: extract capitalized name-like tokens from the story text.
        candidates = re.findall(r"\b[A-Z][a-z]+(?:-[A-Z][a-z]+)?\b", source_text)
        stopwords = {
            "The",
            "A",
            "An",
            "I",
            "He",
            "She",
            "They",
            "We",
            "You",
            "His",
            "Her",
            "Their",
            "It",
            "This",
            "That",
            "These",
            "Those",
        }
        unique = []
        seen = set()
        for name in candidates:
            if name in stopwords:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(name)

        fallback = []
        for idx, name in enumerate(unique[: max_characters or 6]):
            fallback.append(
                {
                    "name": name,
                    "role": "main" if idx < 2 else "secondary",
                    "description": "Extracted from story text.",
                    "identity_line": None,
                }
            )
        characters = fallback

    if max_characters and len(characters) > max_characters:
        characters = characters[:max_characters]

    return characters
