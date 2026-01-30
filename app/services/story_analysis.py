"""
Story analysis service for scene count estimation.

Provides both heuristic-based and LLM-powered analysis for recommending
optimal scene counts targeting webtoon video duration of 60-90 seconds.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from app.prompts.loader import render_prompt

if TYPE_CHECKING:
    from app.services.vertex_gemini import GeminiClient

logger = logging.getLogger(__name__)

# Constants for scene estimation
MIN_SCENES = 5
MAX_SCENES = 15
IDEAL_MIN_SCENES = 7
IDEAL_MAX_SCENES = 12
TARGET_DURATION_SECONDS = 80
SECONDS_PER_SCENE_MIN = 6
SECONDS_PER_SCENE_MAX = 12
SECONDS_PER_SCENE_AVG = 9


class EstimationStatus(str, Enum):
    """Status of scene count estimation."""

    OK = "ok"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"


class Pacing(str, Enum):
    """Story pacing classification."""

    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"


class Complexity(str, Enum):
    """Story complexity classification."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class DialogueDensity(str, Enum):
    """Dialogue density classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SceneAnalysis:
    """Detailed analysis of story for scene estimation."""

    narrative_beats: int
    estimated_duration_seconds: int
    pacing: Pacing
    complexity: Complexity
    dialogue_density: DialogueDensity
    key_moments: list[str] = field(default_factory=list)


@dataclass
class SceneEstimation:
    """Result of scene count estimation."""

    recommended_count: int
    status: EstimationStatus
    message: str
    analysis: SceneAnalysis | None = None


# Heuristic patterns for narrative beat detection
_SCENE_BREAK_PATTERNS = [
    r"\n\n\n+",  # Multiple blank lines
    r"(?:^|\n)#{1,3}\s+",  # Markdown headers
    r"(?:^|\n)\*{3,}(?:\n|$)",  # Horizontal rules
    r"(?:^|\n)---+(?:\n|$)",  # Dashed horizontal rules
    r"(?:^|\n)chapter\s+\d+",  # Chapter markers
    r"(?:^|\n)scene\s+\d+",  # Scene markers
]

_TIME_JUMP_PATTERNS = [
    r"\b(later|the next|that night|morning|evening|hours later|days later)\b",
    r"\b(meanwhile|elsewhere|back at|at the same time)\b",
    r"\b(weeks passed|months later|years later|time flew)\b",
]

_LOCATION_CHANGE_PATTERNS = [
    r"\b(arrived at|walked into|entered|stepped into|went to)\b",
    r"\b(outside|inside|at the|in the|on the)\s+\w+\b",
    r"\b(home|office|school|park|restaurant|hospital|street)\b",
]

_DIALOGUE_PATTERN = re.compile(r'"[^"]{1,500}"', re.MULTILINE)


def _count_pattern_matches(text: str, patterns: list[str]) -> int:
    """Count matches for a list of regex patterns."""
    count = 0
    text_lower = text.lower()
    for pattern in patterns:
        count += len(re.findall(pattern, text_lower, re.IGNORECASE))
    return count


def _estimate_narrative_beats(text: str) -> int:
    """Estimate number of distinct narrative beats in the text."""
    if not text.strip():
        return 0

    # Count explicit scene breaks
    explicit_breaks = sum(
        len(re.findall(pattern, text, re.IGNORECASE | re.MULTILINE))
        for pattern in _SCENE_BREAK_PATTERNS
    )

    # Count time jumps and location changes
    time_jumps = _count_pattern_matches(text, _TIME_JUMP_PATTERNS)
    location_changes = _count_pattern_matches(text, _LOCATION_CHANGE_PATTERNS)

    # Paragraph-based estimation
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs)

    # Sentence-based estimation for very short texts
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)

    # Weighted estimation
    if explicit_breaks > 0:
        # If there are explicit breaks, use them as primary signal
        estimated = explicit_breaks + 1
    elif paragraph_count > 3:
        # Use paragraph structure with time/location signals
        estimated = max(
            paragraph_count // 3,  # Every 3 paragraphs ~ 1 scene
            (time_jumps + location_changes) // 2 + 1,  # Scene changes
        )
    else:
        # Very short text: estimate from sentences
        estimated = max(1, sentence_count // 5)

    return max(1, min(estimated, 20))  # Clamp to reasonable range


def _analyze_pacing(text: str) -> Pacing:
    """Analyze story pacing from text structure."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return Pacing.NORMAL

    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)

    # Count exclamations for action intensity
    exclamation_count = text.count("!")
    exclamation_ratio = exclamation_count / max(len(sentences), 1)

    if avg_sentence_length < 10 or exclamation_ratio > 0.3:
        return Pacing.FAST
    elif avg_sentence_length > 25:
        return Pacing.SLOW
    else:
        return Pacing.NORMAL


def _analyze_complexity(text: str) -> Complexity:
    """Analyze story complexity."""
    word_count = len(text.split())
    paragraph_count = len([p for p in text.split("\n\n") if p.strip()])

    # Count unique character-like words (capitalized, not sentence starts)
    words = text.split()
    potential_characters = set()
    for i, word in enumerate(words):
        if word and word[0].isupper() and i > 0:
            clean_word = re.sub(r"[^a-zA-Z]", "", word)
            if len(clean_word) > 2:
                potential_characters.add(clean_word)

    char_count = len(potential_characters)

    if word_count > 2000 or char_count > 8 or paragraph_count > 15:
        return Complexity.COMPLEX
    elif word_count < 300 or char_count < 3 or paragraph_count < 4:
        return Complexity.SIMPLE
    else:
        return Complexity.MODERATE


def _analyze_dialogue_density(text: str) -> DialogueDensity:
    """Analyze dialogue density in the text."""
    dialogues = _DIALOGUE_PATTERN.findall(text)
    dialogue_chars = sum(len(d) for d in dialogues)
    total_chars = len(text)

    if total_chars == 0:
        return DialogueDensity.LOW

    dialogue_ratio = dialogue_chars / total_chars

    if dialogue_ratio > 0.4:
        return DialogueDensity.HIGH
    elif dialogue_ratio > 0.15:
        return DialogueDensity.MEDIUM
    else:
        return DialogueDensity.LOW


def _extract_key_moments(text: str, max_moments: int = 5) -> list[str]:
    """Extract key visual moments from the text."""
    key_moments = []

    # Look for action verbs and emotional peaks
    action_patterns = [
        r"(?:^|\.\s+)([A-Z][^.!?]{10,60}(?:ran|jumped|screamed|kissed|cried|fought|revealed|discovered)[^.!?]{0,40}[.!?])",
        r"(?:^|\.\s+)([A-Z][^.!?]{10,60}(?:suddenly|finally|at last)[^.!?]{0,60}[.!?])",
    ]

    for pattern in action_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(key_moments) < max_moments:
                moment = match.strip()[:80]
                if moment not in key_moments:
                    key_moments.append(moment)

    # If not enough moments found, use paragraph openings
    if len(key_moments) < 3:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for p in paragraphs[:5]:
            if len(key_moments) >= max_moments:
                break
            first_sentence = re.split(r"[.!?]", p)[0]
            if len(first_sentence) > 10:
                moment = first_sentence.strip()[:80]
                if moment not in key_moments:
                    key_moments.append(moment)

    return key_moments[:max_moments]


def estimate_scene_count_heuristic(source_text: str) -> SceneEstimation:
    """
    Estimate optimal scene count using heuristics (no LLM call).

    Args:
        source_text: The story text to analyze

    Returns:
        SceneEstimation with recommended count and analysis
    """
    text = (source_text or "").strip()

    if not text:
        return SceneEstimation(
            recommended_count=MIN_SCENES,
            status=EstimationStatus.TOO_SHORT,
            message="No story text provided. Please add your story content.",
            analysis=None,
        )

    # Analyze the text
    narrative_beats = _estimate_narrative_beats(text)
    pacing = _analyze_pacing(text)
    complexity = _analyze_complexity(text)
    dialogue_density = _analyze_dialogue_density(text)
    key_moments = _extract_key_moments(text)

    # Calculate recommended scene count
    base_count = narrative_beats

    # Adjust based on pacing
    if pacing == Pacing.FAST:
        base_count = int(base_count * 1.2)  # More scenes for fast pacing
    elif pacing == Pacing.SLOW:
        base_count = int(base_count * 0.8)  # Fewer scenes for slow pacing

    # Adjust based on complexity
    if complexity == Complexity.COMPLEX:
        base_count = max(base_count, IDEAL_MIN_SCENES + 2)
    elif complexity == Complexity.SIMPLE:
        base_count = min(base_count, IDEAL_MAX_SCENES - 2)

    # Adjust based on dialogue
    if dialogue_density == DialogueDensity.HIGH:
        base_count = int(base_count * 0.9)  # Dialogue takes time

    # Clamp to valid range
    recommended_count = max(MIN_SCENES, min(MAX_SCENES, base_count))

    # Determine status and message
    if narrative_beats < MIN_SCENES:
        status = EstimationStatus.TOO_SHORT
        message = (
            f"Your story appears quite short with only {narrative_beats} narrative beats. "
            f"We recommend {recommended_count} scenes, but consider adding more content "
            "for a richer webtoon experience (target: 60-90 second video)."
        )
    elif narrative_beats > MAX_SCENES:
        status = EstimationStatus.TOO_LONG
        message = (
            f"Your story is quite long with {narrative_beats} narrative beats. "
            f"We recommend splitting into multiple episodes. For this episode, "
            f"we suggest {recommended_count} scenes covering the first major story arc."
        )
    else:
        status = EstimationStatus.OK
        estimated_duration = recommended_count * SECONDS_PER_SCENE_AVG
        message = (
            f"Based on your story's {complexity.value} structure and {pacing.value} pacing, "
            f"we recommend {recommended_count} scenes for an estimated {estimated_duration}-second video."
        )

    # Calculate estimated duration
    if pacing == Pacing.FAST:
        seconds_per_scene = SECONDS_PER_SCENE_MIN
    elif pacing == Pacing.SLOW:
        seconds_per_scene = SECONDS_PER_SCENE_MAX
    else:
        seconds_per_scene = SECONDS_PER_SCENE_AVG

    estimated_duration = recommended_count * seconds_per_scene

    analysis = SceneAnalysis(
        narrative_beats=narrative_beats,
        estimated_duration_seconds=estimated_duration,
        pacing=pacing,
        complexity=complexity,
        dialogue_density=dialogue_density,
        key_moments=key_moments,
    )

    return SceneEstimation(
        recommended_count=recommended_count,
        status=status,
        message=message,
        analysis=analysis,
    )


async def estimate_scene_count_llm(
    source_text: str,
    gemini_client: "GeminiClient",
) -> SceneEstimation:
    """
    Estimate optimal scene count using LLM (Gemini).

    Args:
        source_text: The story text to analyze
        gemini_client: Configured Gemini client

    Returns:
        SceneEstimation with recommended count and analysis
    """
    text = (source_text or "").strip()

    if not text:
        return SceneEstimation(
            recommended_count=MIN_SCENES,
            status=EstimationStatus.TOO_SHORT,
            message="No story text provided. Please add your story content.",
            analysis=None,
        )

    # Render the prompt
    prompt = render_prompt("prompt_scene_estimation", source_text=text)

    try:
        # Call Gemini (run blocking call in thread pool)
        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, gemini_client.generate_text, prompt)

        # Parse JSON response
        response_text = response.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
        elif "```" in response_text:
            json_match = re.search(r"```\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)

        data = json.loads(response_text)

        # Extract fields
        recommended_count = int(data.get("recommended_count", IDEAL_MIN_SCENES))
        recommended_count = max(MIN_SCENES, min(MAX_SCENES, recommended_count))

        status_str = data.get("status", "ok").lower()
        try:
            status = EstimationStatus(status_str)
        except ValueError:
            status = EstimationStatus.OK

        message = data.get("message", "")

        # Parse analysis if present
        analysis = None
        if "analysis" in data and isinstance(data["analysis"], dict):
            analysis_data = data["analysis"]
            try:
                analysis = SceneAnalysis(
                    narrative_beats=int(analysis_data.get("narrative_beats", recommended_count)),
                    estimated_duration_seconds=int(
                        analysis_data.get("estimated_duration_seconds", recommended_count * SECONDS_PER_SCENE_AVG)
                    ),
                    pacing=Pacing(analysis_data.get("pacing", "normal").lower()),
                    complexity=Complexity(analysis_data.get("complexity", "moderate").lower()),
                    dialogue_density=DialogueDensity(analysis_data.get("dialogue_density", "medium").lower()),
                    key_moments=analysis_data.get("key_moments", [])[:5],
                )
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse analysis from LLM response: {e}")
                analysis = None

        return SceneEstimation(
            recommended_count=recommended_count,
            status=status,
            message=message,
            analysis=analysis,
        )

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        # Fall back to heuristic
        return estimate_scene_count_heuristic(source_text)

    except Exception as e:
        logger.error(f"LLM scene estimation failed: {e}")
        # Fall back to heuristic
        return estimate_scene_count_heuristic(source_text)
