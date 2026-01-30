"""
Scene importance auto-detection service.

Analyzes scene text to determine narrative importance for layout decisions.
Uses both heuristic analysis and optional LLM enhancement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class SceneImportance(str, Enum):
    """Scene importance levels affecting layout selection."""

    SETUP = "setup"  # Introduction, establishing context
    BUILD = "build"  # Rising action, normal progression
    CLIMAX = "climax"  # Peak dramatic moment
    RELEASE = "release"  # Resolution, aftermath
    CLIFFHANGER = "cliffhanger"  # Suspenseful ending


@dataclass
class ImportanceAnalysis:
    """Result of scene importance analysis."""

    importance: SceneImportance
    confidence: float  # 0.0 to 1.0
    reasoning: str
    signals: dict[str, float]  # Signal type -> strength


# Keywords indicating different importance types
_CLIMAX_KEYWORDS = [
    r"\b(finally|at last|reveal|truth|discover|realize|shock|gasp)\b",
    r"\b(confront|face|challenge|fight|clash|battle)\b",
    r"\b(confession|admit|truth comes out|secret)\b",
    r"\b(death|dies?|killed?|murder)\b",
    r"\b(kiss|embrace|i love you|marry)\b",
    r"\b(betray|lies?|lied|deceive)\b",
]

_CLIFFHANGER_KEYWORDS = [
    r"\b(suddenly|without warning|out of nowhere)\b",
    r"\b(to be continued|next time|what will happen)\b",
    r"\b(disappeared|vanished|gone)\b",
    r"\b(scream|yell|shout)\b",
    r"\.\.\.$",  # Trailing ellipsis
    r"\?!|\?$",  # Question ending
]

_SETUP_KEYWORDS = [
    r"\b(once upon a time|it all began|years ago)\b",
    r"\b(introduce|first time|meet|meeting)\b",
    r"\b(arrive|arrival|entering|stepped into)\b",
    r"\b(ordinary|normal|everyday|typical)\b",
    r"\b(new job|new school|new home|moved to)\b",
]

_RELEASE_KEYWORDS = [
    r"\b(finally|at peace|resolved|over)\b",
    r"\b(forgive|forgave|reconcile|make up)\b",
    r"\b(happy ending|lived|ever after)\b",
    r"\b(goodbye|farewell|leaving|departure)\b",
    r"\b(calm|quiet|peaceful|relief)\b",
]

# Emotion indicators for intensity
_HIGH_EMOTION_KEYWORDS = [
    r"\b(tears|crying|sobbing|weeping)\b",
    r"\b(angry|furious|rage|hatred)\b",
    r"\b(terrified|horrified|panic|fear)\b",
    r"\b(ecstatic|overjoyed|thrilled|elated)\b",
    r"\b(heartbroken|devastated|crushed|despair)\b",
    r"!{2,}",  # Multiple exclamation marks
]

# Dialogue intensity
_DIALOGUE_PATTERN = re.compile(r'"[^"]{1,200}"', re.MULTILINE)


def _count_pattern_matches(text: str, patterns: list[str]) -> int:
    """Count matches for a list of regex patterns."""
    count = 0
    text_lower = text.lower()
    for pattern in patterns:
        count += len(re.findall(pattern, text_lower, re.IGNORECASE))
    return count


def _analyze_dialogue_intensity(text: str) -> float:
    """Analyze dialogue for emotional intensity (0.0-1.0)."""
    dialogues = _DIALOGUE_PATTERN.findall(text)
    if not dialogues:
        return 0.0

    total_intensity = 0.0
    for dialogue in dialogues:
        # Check for exclamations
        if "!" in dialogue:
            total_intensity += 0.3
        # Check for questions
        if "?" in dialogue:
            total_intensity += 0.1
        # Check for emotional keywords in dialogue
        total_intensity += _count_pattern_matches(dialogue, _HIGH_EMOTION_KEYWORDS) * 0.2

    return min(1.0, total_intensity / max(len(dialogues), 1))


def _analyze_pacing(text: str) -> str:
    """Analyze narrative pacing from text structure."""
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]

    if not sentences:
        return "normal"

    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)

    # Short sentences = fast pacing
    if avg_sentence_length < 8:
        return "fast"
    # Long sentences = slow pacing
    elif avg_sentence_length > 20:
        return "slow_burn"
    # Many paragraphs in short text = impact moments
    elif len(paragraphs) > 5 and len(text) < 500:
        return "impact"
    else:
        return "normal"


def analyze_scene_importance(
    text: str,
    scene_index: int | None = None,
    total_scenes: int | None = None,
) -> ImportanceAnalysis:
    """
    Analyze scene text to determine narrative importance.

    Args:
        text: The scene text to analyze
        scene_index: Optional position of scene (1-indexed)
        total_scenes: Optional total number of scenes

    Returns:
        ImportanceAnalysis with detected importance level
    """
    text = (text or "").strip()
    if not text:
        return ImportanceAnalysis(
            importance=SceneImportance.BUILD,
            confidence=0.5,
            reasoning="Empty or minimal text",
            signals={},
        )

    # Calculate signal strengths
    signals = {
        "climax": _count_pattern_matches(text, _CLIMAX_KEYWORDS),
        "cliffhanger": _count_pattern_matches(text, _CLIFFHANGER_KEYWORDS),
        "setup": _count_pattern_matches(text, _SETUP_KEYWORDS),
        "release": _count_pattern_matches(text, _RELEASE_KEYWORDS),
        "emotion": _count_pattern_matches(text, _HIGH_EMOTION_KEYWORDS),
        "dialogue_intensity": _analyze_dialogue_intensity(text),
    }

    # Normalize signals relative to text length
    word_count = len(text.split())
    normalization_factor = max(100, word_count) / 100

    normalized_signals = {
        k: v / normalization_factor if isinstance(v, int) else v for k, v in signals.items()
    }

    # Determine importance based on signals
    reasoning_parts = []
    importance = SceneImportance.BUILD
    confidence = 0.6

    # Position-based heuristics
    if scene_index is not None and total_scenes is not None:
        if scene_index == 1:
            normalized_signals["position_setup"] = 0.5
            reasoning_parts.append("First scene suggests setup")
        elif scene_index == total_scenes:
            normalized_signals["position_ending"] = 0.5
            reasoning_parts.append("Final scene suggests climax/cliffhanger")

    # Signal-based determination
    max_signal = max(normalized_signals.values())
    signal_type = max(normalized_signals, key=normalized_signals.get)

    if normalized_signals.get("climax", 0) >= 2.0:
        importance = SceneImportance.CLIMAX
        confidence = min(0.95, 0.7 + normalized_signals["climax"] * 0.05)
        reasoning_parts.append(f"High climax signals ({int(signals['climax'])} matches)")

    elif normalized_signals.get("cliffhanger", 0) >= 1.5:
        importance = SceneImportance.CLIFFHANGER
        confidence = min(0.9, 0.65 + normalized_signals["cliffhanger"] * 0.05)
        reasoning_parts.append(f"Cliffhanger indicators ({int(signals['cliffhanger'])} matches)")

    elif normalized_signals.get("setup", 0) >= 1.5 or (
        scene_index == 1 and normalized_signals.get("setup", 0) >= 0.5
    ):
        importance = SceneImportance.SETUP
        confidence = min(0.85, 0.6 + normalized_signals["setup"] * 0.05)
        reasoning_parts.append(f"Setup indicators ({int(signals['setup'])} matches)")

    elif normalized_signals.get("release", 0) >= 1.5:
        importance = SceneImportance.RELEASE
        confidence = min(0.85, 0.6 + normalized_signals["release"] * 0.05)
        reasoning_parts.append(f"Resolution indicators ({int(signals['release'])} matches)")

    else:
        # Check for emotional intensity to boost to climax
        if signals["emotion"] >= 3 or signals["dialogue_intensity"] >= 0.6:
            importance = SceneImportance.CLIMAX
            confidence = 0.65
            reasoning_parts.append("High emotional intensity")
        else:
            importance = SceneImportance.BUILD
            confidence = 0.7
            reasoning_parts.append("Standard narrative progression")

    # Adjust confidence based on pacing
    pacing = _analyze_pacing(text)
    if pacing == "impact" and importance == SceneImportance.BUILD:
        importance = SceneImportance.CLIMAX
        confidence = 0.6
        reasoning_parts.append("Impact pacing detected")

    reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Default build scene"

    return ImportanceAnalysis(
        importance=importance,
        confidence=confidence,
        reasoning=reasoning,
        signals={k: round(v, 2) for k, v in normalized_signals.items()},
    )


def suggest_importance_llm_prompt(text: str, character_names: list[str] | None = None) -> str:
    """
    Generate a prompt for LLM-based importance analysis.

    Returns a prompt string to send to Gemini for more accurate analysis.
    """
    char_context = ""
    if character_names:
        char_context = f"\nCharacters: {', '.join(character_names)}"

    return f"""Analyze this scene's narrative importance for a webtoon adaptation.

Scene text:
{text}
{char_context}

Determine the scene's importance level:
- setup: Introduction, establishing context, meeting characters
- build: Rising action, normal story progression
- climax: Peak dramatic moment, major revelation, confrontation
- release: Resolution, aftermath, calming down
- cliffhanger: Suspenseful ending, unresolved tension

OUTPUT SCHEMA:
{{
  "importance": "setup|build|climax|release|cliffhanger",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why this importance level",
  "emotional_peak": "Description of the strongest emotional moment if any",
  "key_story_beat": "The main narrative beat of this scene"
}}"""
