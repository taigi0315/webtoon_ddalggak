from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import loaders
from app.db.models import Character, Scene, StoryCharacter
from app.graphs.nodes.helpers.text import _split_sentences

_ACTION_WORDS = {
    "run",
    "runs",
    "running",
    "rush",
    "rushes",
    "rushing",
    "walk",
    "walks",
    "walking",
    "chase",
    "chases",
    "chasing",
    "fight",
    "fights",
    "fighting",
    "punch",
    "punches",
    "punching",
    "kick",
    "kicks",
    "kicking",
    "grab",
    "grabs",
    "grabbing",
    "push",
    "pushes",
    "pushing",
    "pull",
    "pulls",
    "pulling",
    "hit",
    "hits",
    "hitting",
    "slam",
    "slams",
    "slamming",
    "throw",
    "throws",
    "throwing",
}

_EMOTION_WORDS = {
    "cry",
    "cries",
    "crying",
    "laugh",
    "laughs",
    "laughing",
    "smile",
    "smiles",
    "smiled",
    "angry",
    "furious",
    "sad",
    "heartbroken",
    "shocked",
    "surprised",
    "afraid",
    "terrified",
    "relieved",
}

_DIALOGUE_MARKERS = {"\"", "“", "”"}


def _coerce_scene_id(scene_id: uuid.UUID | str) -> uuid.UUID:
    if isinstance(scene_id, uuid.UUID):
        return scene_id
    return uuid.UUID(str(scene_id))


def _get_scene(db: Session, scene_id: "uuid.UUID" | str) -> Scene:
    scene = db.get(Scene, _coerce_scene_id(scene_id))
    if scene is None:
        raise ValueError(f"scene not found: {scene_id}")
    return scene


def _list_characters(db: Session, story_id: "uuid.UUID") -> list[Character]:
    stmt = (
        select(Character)
        .join(StoryCharacter, StoryCharacter.character_id == Character.character_id)
        .where(StoryCharacter.story_id == story_id)
    )
    return list(db.execute(stmt).scalars().all())


def _extract_setting(text: str) -> str | None:
    for keyword in loaders.load_qc_rules_v1().environment_keywords:
        if keyword in (text or "").lower():
            return keyword
    return None


def _extract_beats(text: str, max_beats: int = 3) -> list[str]:
    sentences = _split_sentences(text)
    beats = [s for s in sentences[:max_beats]]
    return beats


def _choose_mid_grammar(scene_text: str) -> str:
    lower = (scene_text or "").lower()
    if any(word in lower for word in _ACTION_WORDS):
        return "action"
    if any(marker in scene_text for marker in _DIALOGUE_MARKERS) or "said" in lower:
        return "dialogue_medium"
    if any(word in lower for word in _EMOTION_WORDS):
        return "emotion_closeup"
    return "dialogue_medium"
