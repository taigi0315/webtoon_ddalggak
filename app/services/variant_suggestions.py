"""
Character variant suggestions auto-generation service.

Analyzes story text to detect when characters need outfit or appearance changes
and suggests appropriate variants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class VariantTrigger(str, Enum):
    """Reasons for suggesting a character variant."""

    TIME_JUMP = "time_jump"  # Story skips forward in time
    LOCATION_CHANGE = "location_change"  # Moving to a new type of location
    SPECIAL_EVENT = "special_event"  # Party, wedding, funeral, etc.
    WEATHER_CHANGE = "weather_change"  # Seasonal or weather-based change
    ACTIVITY_CHANGE = "activity_change"  # Work, exercise, sleep, etc.
    EMOTIONAL_SHIFT = "emotional_shift"  # Major character development


@dataclass
class VariantSuggestion:
    """A suggested character variant."""

    character_name: str
    variant_type: str  # e.g., "outfit_change", "appearance_change"
    trigger: VariantTrigger
    description: str
    override_attributes: dict = field(default_factory=dict)
    confidence: float = 0.7


# Time jump indicators
_TIME_JUMP_PATTERNS = [
    r"\b(\d+)\s*(years?|months?|weeks?|days?)\s*(later|passed|went by)\b",
    r"\b(next\s+)?(morning|evening|day|week|month|year)\b",
    r"\b(the following|a few|several)\s*(days?|weeks?|months?)\b",
    r"\b(time\s+)?(flew|passed|skipped)\b",
    r"\b(seasons?\s+)?(changed?|passed)\b",
]

# Location type indicators
_LOCATION_PATTERNS = {
    "work_office": [r"\b(office|workplace|company|meeting room|conference)\b"],
    "home_casual": [r"\b(home|apartment|house|bedroom|living room|kitchen)\b"],
    "school": [r"\b(school|classroom|campus|university|college|library)\b"],
    "outdoor_casual": [r"\b(park|street|cafe|restaurant|mall|shop)\b"],
    "formal_event": [r"\b(wedding|party|gala|ceremony|reception|banquet)\b"],
    "athletic": [r"\b(gym|pool|beach|hiking|running|sports|exercise)\b"],
    "nightlife": [r"\b(bar|club|nightclub|pub|lounge)\b"],
    "medical": [r"\b(hospital|clinic|doctor|medical)\b"],
}

# Special event keywords
_SPECIAL_EVENT_PATTERNS = {
    "wedding": [r"\b(wedding|bride|groom|ceremony|vows)\b"],
    "funeral": [r"\b(funeral|memorial|mourning|burial)\b"],
    "party": [r"\b(party|celebration|birthday|anniversary)\b"],
    "interview": [r"\b(interview|meeting|presentation|pitch)\b"],
    "date": [r"\b(date|romantic dinner|anniversary)\b"],
    "graduation": [r"\b(graduation|commencement|diploma)\b"],
}

# Weather/season indicators
_WEATHER_PATTERNS = {
    "winter": [r"\b(winter|snow|cold|freezing|coat|jacket)\b"],
    "summer": [r"\b(summer|hot|heat|sweating|beach|swimsuit)\b"],
    "rain": [r"\b(rain|raining|umbrella|wet|storm)\b"],
}

# Activity change patterns
_ACTIVITY_PATTERNS = {
    "sleep": [r"\b(sleep|bed|pajamas|woke up|morning)\b"],
    "exercise": [r"\b(gym|workout|running|yoga|sports|exercise)\b"],
    "swim": [r"\b(pool|beach|swimming|swimsuit|swim)\b"],
    "work": [r"\b(work|office|job|meeting|business)\b"],
}

# Outfit suggestions by context
_OUTFIT_SUGGESTIONS = {
    "work_office": "professional business attire, formal shirt and slacks or blouse and skirt",
    "home_casual": "comfortable casual wear, relaxed t-shirt and sweatpants or loungewear",
    "school": "school uniform or casual student attire with backpack",
    "outdoor_casual": "casual streetwear, jeans and comfortable top",
    "formal_event": "elegant formal wear, suit or dress with accessories",
    "athletic": "athletic wear, sports clothing with sneakers",
    "nightlife": "stylish evening wear, fashionable outfit for going out",
    "medical": "simple comfortable clothing or hospital gown if patient",
    "wedding": "formal wedding guest attire or traditional ceremony dress",
    "funeral": "dark formal mourning attire, black or navy",
    "party": "festive party outfit, dressy casual",
    "interview": "sharp professional interview attire",
    "date": "attractive date night outfit, well-groomed appearance",
    "graduation": "graduation gown or formal celebration attire",
    "winter": "warm winter clothing, coat, scarf, layers",
    "summer": "light summer clothing, shorts, sleeveless, breathable fabrics",
    "rain": "rain-appropriate clothing with jacket or umbrella",
    "sleep": "sleepwear, pajamas, comfortable night clothes",
    "exercise": "workout clothes, athletic wear, sports bra and leggings",
    "swim": "swimwear, bathing suit, beach attire",
}


def _find_pattern_matches(text: str, patterns: list[str]) -> list[tuple[int, str]]:
    """Find all pattern matches with their positions."""
    matches = []
    text_lower = text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            matches.append((match.start(), match.group()))
    return sorted(matches, key=lambda x: x[0])


def _detect_time_jumps(text: str) -> list[dict]:
    """Detect time jumps in text."""
    jumps = []
    for pattern in _TIME_JUMP_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            jumps.append(
                {
                    "position": match.start(),
                    "match": match.group(),
                    "type": "time_jump",
                }
            )
    return jumps


def _detect_location_contexts(text: str) -> list[dict]:
    """Detect different location contexts in text."""
    contexts = []
    for location_type, patterns in _LOCATION_PATTERNS.items():
        matches = _find_pattern_matches(text, patterns)
        if matches:
            contexts.append(
                {
                    "location_type": location_type,
                    "count": len(matches),
                    "first_position": matches[0][0],
                }
            )
    return sorted(contexts, key=lambda x: x["first_position"])


def _detect_special_events(text: str) -> list[dict]:
    """Detect special events in text."""
    events = []
    for event_type, patterns in _SPECIAL_EVENT_PATTERNS.items():
        matches = _find_pattern_matches(text, patterns)
        if matches:
            events.append(
                {
                    "event_type": event_type,
                    "count": len(matches),
                    "first_position": matches[0][0],
                }
            )
    return events


def _detect_weather_changes(text: str) -> list[dict]:
    """Detect weather/season indicators in text."""
    changes = []
    for weather_type, patterns in _WEATHER_PATTERNS.items():
        matches = _find_pattern_matches(text, patterns)
        if matches:
            changes.append(
                {
                    "weather_type": weather_type,
                    "count": len(matches),
                }
            )
    return changes


def _detect_activity_changes(text: str) -> list[dict]:
    """Detect activity changes in text."""
    activities = []
    for activity_type, patterns in _ACTIVITY_PATTERNS.items():
        matches = _find_pattern_matches(text, patterns)
        if matches:
            activities.append(
                {
                    "activity_type": activity_type,
                    "count": len(matches),
                }
            )
    return activities


def suggest_character_variants(
    story_text: str,
    character_names: list[str],
    existing_variants: list[str] | None = None,
) -> list[VariantSuggestion]:
    """
    Analyze story text and suggest character variants.

    Args:
        story_text: The full story or scene text
        character_names: List of character names in the story
        existing_variants: List of already-defined variant descriptions

    Returns:
        List of suggested character variants
    """
    suggestions = []
    existing_variants = existing_variants or []
    text = (story_text or "").strip()

    if not text or not character_names:
        return suggestions

    # Detect various triggers
    time_jumps = _detect_time_jumps(text)
    locations = _detect_location_contexts(text)
    events = _detect_special_events(text)
    weather = _detect_weather_changes(text)
    activities = _detect_activity_changes(text)

    # Track which contexts we've suggested
    suggested_contexts = set()

    # Generate suggestions based on detections
    for char_name in character_names:
        char_lower = char_name.lower()

        # Check if character is mentioned in text
        if char_lower not in text.lower():
            continue

        # Location-based suggestions
        for loc in locations:
            loc_type = loc["location_type"]
            if loc_type in suggested_contexts:
                continue

            outfit = _OUTFIT_SUGGESTIONS.get(loc_type)
            if outfit:
                suggestions.append(
                    VariantSuggestion(
                        character_name=char_name,
                        variant_type="outfit_change",
                        trigger=VariantTrigger.LOCATION_CHANGE,
                        description=f"{char_name} in {loc_type.replace('_', ' ')} setting",
                        override_attributes={"outfit": outfit},
                        confidence=0.7,
                    )
                )
                suggested_contexts.add(loc_type)

        # Event-based suggestions
        for event in events:
            event_type = event["event_type"]
            if event_type in suggested_contexts:
                continue

            outfit = _OUTFIT_SUGGESTIONS.get(event_type)
            if outfit:
                suggestions.append(
                    VariantSuggestion(
                        character_name=char_name,
                        variant_type="outfit_change",
                        trigger=VariantTrigger.SPECIAL_EVENT,
                        description=f"{char_name} at {event_type}",
                        override_attributes={"outfit": outfit},
                        confidence=0.8,
                    )
                )
                suggested_contexts.add(event_type)

        # Weather-based suggestions
        for w in weather:
            weather_type = w["weather_type"]
            if weather_type in suggested_contexts:
                continue

            outfit = _OUTFIT_SUGGESTIONS.get(weather_type)
            if outfit:
                suggestions.append(
                    VariantSuggestion(
                        character_name=char_name,
                        variant_type="outfit_change",
                        trigger=VariantTrigger.WEATHER_CHANGE,
                        description=f"{char_name} in {weather_type} weather",
                        override_attributes={"outfit": outfit},
                        confidence=0.75,
                    )
                )
                suggested_contexts.add(weather_type)

        # Activity-based suggestions
        for act in activities:
            activity_type = act["activity_type"]
            if activity_type in suggested_contexts:
                continue

            outfit = _OUTFIT_SUGGESTIONS.get(activity_type)
            if outfit:
                suggestions.append(
                    VariantSuggestion(
                        character_name=char_name,
                        variant_type="outfit_change",
                        trigger=VariantTrigger.ACTIVITY_CHANGE,
                        description=f"{char_name} during {activity_type}",
                        override_attributes={"outfit": outfit},
                        confidence=0.7,
                    )
                )
                suggested_contexts.add(activity_type)

        # Time jump suggestion (appearance change)
        if time_jumps and "time_jump" not in suggested_contexts:
            suggestions.append(
                VariantSuggestion(
                    character_name=char_name,
                    variant_type="appearance_change",
                    trigger=VariantTrigger.TIME_JUMP,
                    description=f"{char_name} after time passage",
                    override_attributes={"appearance_note": "Updated appearance reflecting time passage"},
                    confidence=0.65,
                )
            )
            suggested_contexts.add("time_jump")

    # Filter out suggestions that match existing variants
    if existing_variants:
        existing_lower = {v.lower() for v in existing_variants}
        suggestions = [
            s for s in suggestions if s.description.lower() not in existing_lower
        ]

    # Sort by confidence
    suggestions.sort(key=lambda x: x.confidence, reverse=True)

    return suggestions


def detect_outfit_context(text: str) -> tuple[str | None, str | None]:
    """Detect a dramatic outfit context from text.

    Returns:
        (outfit_description, trigger_type)
    """
    text = (text or "").strip()
    if not text:
        return None, None

    events = _detect_special_events(text)
    if events:
        event_type = events[0]["event_type"]
        outfit = _OUTFIT_SUGGESTIONS.get(event_type)
        if outfit:
            return outfit, "special_event"

    activities = _detect_activity_changes(text)
    if activities:
        activity_type = activities[0]["activity_type"]
        outfit = _OUTFIT_SUGGESTIONS.get(activity_type)
        if outfit:
            return outfit, "activity_change"

    return None, None


def build_variant_plan_for_scenes(
    scenes: list[dict],
    character_names: list[str],
) -> list[dict]:
    """Build a scene-range variant plan based on dramatic outfit changes.

    Each plan item includes character_name, outfit, scene_ids, and scene_range.
    """
    if not scenes or not character_names:
        return []

    plans: list[dict] = []
    for name in character_names:
        current_outfit: str | None = None
        current_scene_ids: list[str] = []
        current_range_start: int | None = None

        for idx, scene in enumerate(scenes, start=1):
            scene_text = str(scene.get("source_text") or "")
            if name.lower() not in scene_text.lower():
                continue

            outfit, trigger = detect_outfit_context(scene_text)
            if not outfit:
                if current_outfit and current_scene_ids:
                    plans.append(
                        {
                            "character_name": name,
                            "variant_type": "outfit_change",
                            "override_attributes": {"outfit": current_outfit},
                            "scene_ids": list(current_scene_ids),
                            "scene_range": f"{current_range_start}-{idx - 1}",
                            "trigger": trigger or "revert_to_base",
                        }
                    )
                current_outfit = None
                current_scene_ids = []
                current_range_start = None
                continue

            if outfit != current_outfit:
                if current_outfit and current_scene_ids:
                    plans.append(
                        {
                            "character_name": name,
                            "variant_type": "outfit_change",
                            "override_attributes": {"outfit": current_outfit},
                            "scene_ids": list(current_scene_ids),
                            "scene_range": f"{current_range_start}-{idx - 1}",
                            "trigger": trigger or "change",
                        }
                    )
                current_outfit = outfit
                current_scene_ids = []
                current_range_start = idx

            if scene.get("scene_id"):
                current_scene_ids.append(str(scene["scene_id"]))

        if current_outfit and current_scene_ids:
            plans.append(
                {
                    "character_name": name,
                    "variant_type": "outfit_change",
                    "override_attributes": {"outfit": current_outfit},
                    "scene_ids": list(current_scene_ids),
                    "scene_range": f"{current_range_start}-{len(scenes)}",
                    "trigger": "end",
                }
            )

    return plans


def suggest_variants_llm_prompt(
    story_text: str,
    character_names: list[str],
) -> str:
    """
    Generate a prompt for LLM-based variant suggestion.

    Returns a prompt string to send to Gemini for more nuanced suggestions.
    """
    char_list = ", ".join(character_names)

    return f"""Analyze this story and suggest character outfit/appearance variants.

Story text:
{story_text}

Characters: {char_list}

For each character, identify if they need different outfits or appearances for:
- Different scenes (home vs work vs social)
- Special events (weddings, parties, funerals)
- Weather/season changes
- Activity changes (sleep, exercise, swimming)
- Time jumps (significant time passing)

OUTPUT SCHEMA:
{{
  "suggestions": [
    {{
      "character_name": "Name",
      "variant_type": "outfit_change|appearance_change",
      "trigger": "location_change|special_event|weather_change|activity_change|time_jump",
      "description": "Short description",
      "outfit": "Detailed outfit description for image generation"
    }}
  ],
  "reasoning": "Why these variants are needed"
}}

Only suggest variants that are clearly needed based on the story context.
Return empty suggestions list if no variants are needed."""
