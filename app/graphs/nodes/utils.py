from __future__ import annotations

import hashlib
import json
import logging
import math
import mimetypes
import os
import re
import uuid
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import loaders
from app.core.telemetry import trace_span
from app.core.settings import settings
from app.db.models import Character, CharacterReferenceImage, CharacterVariant, Scene, Story, StoryCharacter
from app.prompts.loader import get_prompt, get_prompt_data, render_prompt
from app.services.artifacts import ArtifactService
from app.services.images import ImageService
from app.services.storage import LocalMediaStore
from app.services.vertex_gemini import GeminiClient

logger = logging.getLogger(__name__)

ARTIFACT_SCENE_INTENT = "scene_intent"
ARTIFACT_PANEL_PLAN = "panel_plan"
ARTIFACT_PANEL_PLAN_NORMALIZED = "panel_plan_normalized"
ARTIFACT_LAYOUT_TEMPLATE = "layout_template"
ARTIFACT_PANEL_SEMANTICS = "panel_semantics"
ARTIFACT_RENDER_SPEC = "render_spec"
ARTIFACT_RENDER_RESULT = "render_result"
ARTIFACT_QC_REPORT = "qc_report"
ARTIFACT_BLIND_TEST_REPORT = "blind_test_report"
ARTIFACT_DIALOGUE_SUGGESTIONS = "dialogue_suggestions"
ARTIFACT_VISUAL_PLAN = "visual_plan"

SYSTEM_PROMPT_JSON = get_prompt("system_prompt_json")
GLOBAL_CONSTRAINTS = get_prompt("global_constraints")
VISUAL_PROMPT_FORMULA = get_prompt("visual_prompt_formula")

# ---------------------------------------------------------------------------
# Valid Grammar IDs (must match panel_grammar_library_v1.json)
# ---------------------------------------------------------------------------

VALID_GRAMMAR_IDS = frozenset([
    "establishing",
    "dialogue_medium",
    "emotion_closeup",
    "action",
    "reaction",
    "object_focus",
    "reveal",
    "impact_silence",
])

# ---------------------------------------------------------------------------
# Valid Gaze Directions for Panel Semantics
# ---------------------------------------------------------------------------

VALID_GAZE_VALUES = frozenset([
    "at_other",
    "at_object",
    "down",
    "away",
    "toward_path",
    "camera",
])

# ---------------------------------------------------------------------------
# Pacing Options for Scene Intent
# ---------------------------------------------------------------------------

PACING_OPTIONS = frozenset([
    "slow_burn",
    "normal",
    "fast",
    "impact",
])

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


def _build_gemini_client() -> GeminiClient:
    if not settings.google_cloud_project and not settings.gemini_api_key:
        raise RuntimeError("Gemini is not configured")

    return GeminiClient(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        api_key=settings.gemini_api_key,
        text_model=settings.gemini_text_model,
        image_model=settings.gemini_image_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
        initial_backoff_seconds=settings.gemini_initial_backoff_seconds,
    )


# ---------------------------------------------------------------------------
# Genre-Specific Visual Guidelines for Webtoon Panels
# ---------------------------------------------------------------------------

GENRE_VISUAL_GUIDELINES = {
    "romance": {
        "shot_preferences": "Medium close-ups (40-45% character), two-shots, over-shoulder",
        "composition": "Characters occupy 40-45% frame, intimate framing",
        "camera": "Eye-level for intimacy, slight low-angle for vulnerability",
        "lighting": "warm ambient, soft glow, golden hour, intimate atmosphere, soft diffused natural light",
        "props": "Coffee cups, phones with messages, tissues, meaningful objects, flowers",
        "atmosphere": "ethereal, dreamy, soft bokeh, light-filled, gentle, pastel-tinted",
        "color_palette": "warm peachy tones, soft blues and lavenders, creamy neutrals",
    },
    "drama": {
        "shot_preferences": "Medium close-ups (40-45% character), emotional focus shots",
        "composition": "Characters 40-45%, room for emotional expression",
        "camera": "Eye-level, occasional low-angle for vulnerability moments",
        "lighting": "dramatic but natural, contrast for emotional beats, rim lighting",
        "props": "Personal items, letters, photos, meaningful objects that tell story",
        "atmosphere": "tense, emotional, atmospheric, moody, contemplative",
        "color_palette": "muted tones with emotional accents, natural colors",
    },
    "thriller": {
        "shot_preferences": "Wide shots (25-30% character), Dutch angles, high angles for paranoia",
        "composition": "Characters 25-35%, environment dominates and tells story",
        "camera": "Off-kilter angles, overhead for vulnerability, low-angle for threat",
        "lighting": "harsh shadows, dim lighting, single light source, ominous glow",
        "props": "Hidden details, suspicious background elements, foreshadowing objects",
        "atmosphere": "tense, ominous, foreboding, isolating, unsettling, dark",
        "color_palette": "desaturated, cold blue tones, muted with dark accents",
    },
    "comedy": {
        "shot_preferences": "Medium full shots (body language), reaction close-ups",
        "composition": "Characters 35-40%, room for visual gags in environment",
        "camera": "Slight exaggeration in angles, reaction-focused framing",
        "lighting": "bright clear lighting, vibrant, energetic, even illumination",
        "props": "Comedy props (spilled items, tangled objects, mishap aftermath)",
        "atmosphere": "playful, bright, energetic, exaggerated, fun",
        "color_palette": "saturated bright colors, cheerful tones",
    },
    "slice_of_life": {
        "shot_preferences": "Wide establishing shots (20-30% character), medium shots",
        "composition": "Characters 20-35%, world and environment is the story",
        "camera": "Observational, pulled back, natural everyday angles",
        "lighting": "natural daylight, realistic ambient, ordinary comfortable",
        "props": "Everyday items (grocery bags, transit cards, textbooks, meals)",
        "atmosphere": "calm, peaceful, mundane beauty, contemplative, cozy",
        "color_palette": "natural realistic colors, warm everyday tones",
    },
    "fantasy": {
        "shot_preferences": "Mix of wide (show magical world) and dramatic close-ups",
        "composition": "Balanced 30-40% character, space for magical effects",
        "camera": "Dynamic dramatic angles, awe-inspiring perspectives",
        "lighting": "magical glow, ethereal light, mystical illumination, enchanted",
        "props": "Fantasy elements, glowing objects, supernatural manifestations",
        "atmosphere": "mystical, enchanted, magical, otherworldly, wondrous",
        "color_palette": "jewel tones, ethereal pastels, magical highlights",
    },
}

# ---------------------------------------------------------------------------
# Shot Type Distribution by Genre
# ---------------------------------------------------------------------------

SHOT_DISTRIBUTION_BY_GENRE = {
    "romance": {"establishing": 2, "medium": "5-6", "closeup": "2-3", "dynamic": "1-2"},
    "drama": {"establishing": 2, "medium": "5-6", "closeup": "2-3", "dynamic": "1-2"},
    "thriller": {"establishing": "3-4", "medium": "3-4", "closeup": "1-2", "dynamic": "2-3"},
    "comedy": {"establishing": 2, "medium": "4-5", "closeup": "2-3", "dynamic": "1-2"},
    "slice_of_life": {"establishing": "3-4", "medium": "4-5", "closeup": "0-1", "dynamic": "1-2"},
    "fantasy": {"establishing": "2-3", "medium": "4-5", "closeup": "1-2", "dynamic": "2-3"},
}

_NAME_STOPWORDS = {
    "The",
    "A",
    "An",
    "He",
    "She",
    "They",
    "It",
    "I",
    "We",
    "You",
    "His",
    "Her",
    "Their",
    "Our",
    "In",
    "On",
    "At",
    "After",
    "Before",
    "Later",
    "Then",
    "When",
    "While",
    "Because",
}

_ACTION_WORDS = {
    "run",
    "runs",
    "ran",
    "fight",
    "fights",
    "fought",
    "slam",
    "slams",
    "slammed",
    "jump",
    "jumps",
    "jumped",
    "crash",
    "crashes",
    "crashed",
    "explode",
    "explodes",
    "exploded",
    "chase",
    "chases",
    "chased",
}

_EMOTION_WORDS = {
    "cry",
    "cries",
    "cried",
    "tear",
    "tears",
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

_BLANK_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff"
    b"?\x03\x00\x08\xfc\x02\xfe\xd2\xf3j\xf5\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _get_scene(db: Session, scene_id: uuid.UUID) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")
    return scene


def _list_characters(db: Session, story_id: uuid.UUID) -> list[Character]:
    stmt = (
        select(Character)
        .join(StoryCharacter, StoryCharacter.character_id == Character.character_id)
        .where(StoryCharacter.story_id == story_id)
    )
    return list(db.execute(stmt).scalars().all())


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _group_chunks(items: list[str], max_groups: int) -> list[str]:
    if not items:
        return []
    if len(items) <= max_groups:
        return items

    group_size = math.ceil(len(items) / max_groups)
    chunks: list[str] = []
    for i in range(0, len(items), group_size):
        chunk = " ".join(items[i : i + group_size]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks[:max_groups]


def _extract_names(text: str, excluded: set[str] | None = None) -> list[str]:
    excluded = excluded or set()
    candidates = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", text or "")
    names: list[str] = []
    for candidate in candidates:
        if candidate in _NAME_STOPWORDS:
            continue
        if candidate in excluded:
            continue
        if candidate not in names:
            names.append(candidate)
    return names


def _extract_metadata_names(text: str) -> set[str]:
    excluded: set[str] = set()
    for line in (text or "").splitlines()[:20]:
        stripped = line.strip()
        lower = stripped.lower()
        if ":" in line:
            label, rest = line.split(":", 1)
            label_key = label.strip().lower()
            if label_key in {"title", "episode", "story", "genre", "style"}:
                for candidate in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", rest):
                    excluded.add(candidate)
        elif any(lower.startswith(prefix) for prefix in ("title", "episode", "story", "genre", "style")):
            for candidate in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", stripped):
                excluded.add(candidate)
    return excluded


def _summarize_text(text: str, max_words: int = 32) -> str:
    words = re.findall(r"\w+", text)
    if not words:
        return ""
    return " ".join(words[:max_words])


def _extract_setting(text: str) -> str | None:
    for keyword in loaders.load_qc_rules_v1().environment_keywords:
        if keyword in (text or "").lower():
            return keyword
    return None


def _extract_beats(text: str, max_beats: int = 3) -> list[str]:
    sentences = _split_sentences(text)
    beats = [s for s in sentences[:max_beats]]
    return beats


def _extract_must_show(text: str) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z]{4,}\b", text)
    common = []
    for token in tokens:
        key = token.lower()
        if key not in common:
            common.append(key)
        if len(common) >= 4:
            break
    return common


def _panel_count_for_importance(
    scene_importance: str,
    scene_text: str,
    fallback: int,
) -> int:
    importance = (scene_importance or "").lower()
    word_count = len(re.findall(r"\w+", scene_text or ""))
    if importance in {"climax", "cliffhanger"}:
        return 1
    if importance == "release":
        return 3 if word_count >= 120 else 2
    if importance == "setup":
        return 4 if word_count >= 120 else 3
    if importance == "build":
        if word_count >= 160:
            return 5
        if word_count >= 90:
            return 4
        return 3
    return max(1, int(fallback))


def _heuristic_panel_plan(scene_text: str, panel_count: int) -> dict:
    panels: list[dict] = []
    for idx in range(panel_count):
        if idx == 0:
            grammar_id = "establishing"
        elif idx == panel_count - 1:
            grammar_id = "reaction"
        else:
            grammar_id = _choose_mid_grammar(scene_text)
        panels.append(
            {
                "panel_index": idx + 1,
                "grammar_id": grammar_id,
                "story_function": _grammar_story_function(grammar_id),
            }
        )
    return {"panels": panels}


def _choose_mid_grammar(scene_text: str) -> str:
    lower = (scene_text or "").lower()
    if any(word in lower for word in _ACTION_WORDS):
        return "action"
    if any(marker in scene_text for marker in _DIALOGUE_MARKERS) or "said" in lower:
        return "dialogue_medium"
    if any(word in lower for word in _EMOTION_WORDS):
        return "emotion_closeup"
    return "dialogue_medium"


def _grammar_story_function(grammar_id: str) -> str:
    mapping = {
        "establishing": "setup",
        "dialogue_medium": "dialogue",
        "emotion_closeup": "emotion",
        "action": "action",
        "reaction": "reaction",
        "object_focus": "focus",
        "reveal": "climax",
        "impact_silence": "climax",
    }
    return mapping.get(grammar_id, "beat")


def _normalize_panel_plan(panel_plan: dict) -> dict:
    panels = list(panel_plan.get("panels") or [])
    if not panels:
        return {"panels": []}

    # Validate grammar_ids and replace invalid ones
    for panel in panels:
        grammar_id = panel.get("grammar_id")
        if grammar_id not in VALID_GRAMMAR_IDS:
            panel["grammar_id"] = "dialogue_medium"
            panel["story_function"] = _grammar_story_function("dialogue_medium")

    if len(panels) == 1:
        panels[0]["grammar_id"] = "establishing"
        panels[0]["story_function"] = _grammar_story_function("establishing")
        return {"panels": panels}

    # First panel must be establishing
    if panels[0].get("grammar_id") != "establishing":
        panels[0]["grammar_id"] = "establishing"
        panels[0]["story_function"] = _grammar_story_function("establishing")

    # Last panel should be a closing grammar (reaction, reveal, or impact_silence)
    valid_endings = {"reaction", "reveal", "impact_silence"}
    if panels[-1].get("grammar_id") not in valid_endings:
        panels[-1]["grammar_id"] = "reaction"
        panels[-1]["story_function"] = _grammar_story_function("reaction")

    # Limit closeups to max 50% of panels
    closeups = [p for p in panels if p.get("grammar_id") == "emotion_closeup"]
    max_closeups = max(1, math.floor(len(panels) * 0.5))
    if len(closeups) > max_closeups:
        for p in closeups[max_closeups:]:
            p["grammar_id"] = "reaction"
            p["story_function"] = _grammar_story_function("reaction")

    # Prevent 3+ consecutive identical grammar_ids
    run_len = 1
    for idx in range(1, len(panels)):
        if panels[idx].get("grammar_id") == panels[idx - 1].get("grammar_id"):
            run_len += 1
            if run_len >= 3:
                panels[idx]["grammar_id"] = "reaction"
                panels[idx]["story_function"] = _grammar_story_function("reaction")
                run_len = 1
        else:
            run_len = 1

    return {"panels": panels}


def _panel_purpose_from(panel: dict) -> str:
    grammar_id = panel.get("grammar_id")
    story_function = panel.get("story_function")
    if story_function:
        return str(story_function)
    mapping = {
        "dialogue_medium": "dialogue",
        "emotion_closeup": "reaction",
        "reaction": "reaction",
        "action": "action",
        "object_focus": "reveal",
        "reveal": "reveal",
        "impact_silence": "silent_beat",
        "establishing": "establishing",
    }
    return mapping.get(grammar_id, "dialogue")


def _annotate_panel_utility(panel: dict) -> dict:
    panel_role = panel.get("panel_role")
    if panel_role not in {"main", "inset"}:
        panel_role = "main"
    panel["panel_role"] = panel_role

    panel_purpose = panel.get("panel_purpose")
    if panel_purpose not in {
        "dialogue",
        "reaction",
        "reveal",
        "action",
        "establishing",
        "silent_beat",
    }:
        panel_purpose = _panel_purpose_from(panel)
    panel["panel_purpose"] = panel_purpose

    has_dialogue = panel.get("has_dialogue")
    if not isinstance(has_dialogue, bool):
        has_dialogue = panel.get("grammar_id") == "dialogue_medium" or panel_purpose == "dialogue"
    panel["has_dialogue"] = has_dialogue

    if has_dialogue:
        utility = 1.0
    elif panel_purpose in {"reveal", "reaction", "action"}:
        utility = 0.7
    elif panel_purpose == "silent_beat":
        utility = 0.4
    elif panel_purpose == "establishing":
        utility = 0.5
    else:
        utility = 0.3
    panel["utility_score"] = float(panel.get("utility_score", utility))
    return panel


def _evaluate_and_prune_panel_plan(panel_plan: dict) -> dict:
    panels = list(panel_plan.get("panels") or [])
    if not panels:
        return {"panels": []}

    annotated = [_annotate_panel_utility(dict(panel)) for panel in panels]

    meaningful = {"reveal", "reaction", "action", "silent_beat"}
    pruned = []
    inset_panels = []
    for panel in annotated:
        is_inset = panel.get("panel_role") == "inset"
        if is_inset and not panel.get("has_dialogue") and panel.get("panel_purpose") not in meaningful:
            continue
        if is_inset:
            inset_panels.append(panel)
        pruned.append(panel)

    if len(inset_panels) > 2:
        inset_panels_sorted = sorted(inset_panels, key=lambda p: p.get("utility_score", 0))
        to_drop = {p.get("panel_index") for p in inset_panels_sorted[:-2]}
        pruned = [p for p in pruned if p.get("panel_index") not in to_drop]

    for idx, panel in enumerate(pruned, start=1):
        panel["panel_index"] = idx

    return {"panels": pruned}


def _heuristic_panel_semantics(
    scene_text: str,
    panel_plan: dict,
    layout_template: dict,
    characters: list[Character],
    story_style: str | None = None,
    scene_intent: dict | None = None,
) -> dict:
    panels = []
    grammar_lib = {g.id: g.description for g in loaders.load_grammar_library_v1().grammars}
    dialogue_lines = _extract_dialogue_lines(scene_text)
    dialogue_iter = iter(dialogue_lines)
    names = [c.name for c in characters]
    setting_hint = _extract_setting(scene_text) or "room"
    environment_keywords = loaders.load_qc_rules_v1().environment_keywords

    for panel in panel_plan.get("panels", []):
        grammar_id = panel.get("grammar_id")
        description = grammar_lib.get(grammar_id, "Panel")
        if scene_intent and scene_intent.get("summary"):
            description = f"{description} {scene_intent['summary']}"
        if grammar_id == "establishing":
            lowered = description.lower()
            if not any(word in lowered for word in environment_keywords):
                description = f"{description} {setting_hint}"

        dialogue: list[str] = []
        if grammar_id in {"dialogue_medium", "emotion_closeup"}:
            line = next(dialogue_iter, None)
            if line:
                dialogue.append(line)

        panels.append(
            {
                "panel_index": panel.get("panel_index"),
                "grammar_id": grammar_id,
                "description": description.strip(),
                "characters": names,
                "dialogue": dialogue,
                "layout_hint": layout_template.get("layout_text"),
                "story_style": story_style,
            }
        )

    return {"panels": panels}


def _extract_dialogue_lines(text: str) -> list[str]:
    lines = []
    for match in re.findall(r"“([^”]+)”", text):
        lines.append(match.strip())
    for match in re.findall(r"\"([^\"]+)\"", text):
        line = match.strip()
        if line and line not in lines:
            lines.append(line)
    return lines


def _panel_count(panel_semantics: dict | None) -> int:
    if not panel_semantics:
        return 0
    panels = panel_semantics.get("panels")
    if isinstance(panels, list):
        return len(panels)
    return 0


def _qc_report(panel_plan: dict, panel_semantics: dict | None) -> dict:
    rules = loaders.load_qc_rules_v1()
    panels = list(panel_plan.get("panels") or [])
    total = len(panels)
    if total == 0:
        return {
            "passed": False,
            "issues": ["no_panels"],
            "issue_details": [
                {
                    "code": "no_panels",
                    "message": "No panels found in the panel plan.",
                    "hint": "Regenerate the panel plan or reduce strict constraints.",
                }
            ],
            "metrics": {"panel_count": 0},
            "summary": "QC failed: no panels detected.",
        }

    closeups = [p for p in panels if p.get("grammar_id") == "emotion_closeup"]
    closeup_count = len(closeups)
    closeup_ratio = closeup_count / total

    dialogue_ratio = 0.0
    dialogue_count = 0
    if panel_semantics and isinstance(panel_semantics.get("panels"), list):
        dialogue_panels = [p for p in panel_semantics["panels"] if p.get("dialogue")]
        dialogue_count = len(dialogue_panels)
        dialogue_ratio = dialogue_count / total

    run_len = 1
    max_run = 1
    for idx in range(1, total):
        if panels[idx].get("grammar_id") == panels[idx - 1].get("grammar_id"):
            run_len += 1
            max_run = max(max_run, run_len)
        else:
            run_len = 1

    issues: list[str] = []
    if closeup_ratio > rules.closeup_ratio_max:
        issues.append("too_many_closeups")
    if dialogue_ratio > rules.dialogue_ratio_max:
        issues.append("too_much_dialogue")
    if max_run >= rules.repeated_framing_run_length:
        issues.append("repeated_framing")

    if rules.require_environment_on_establishing:
        first = panels[0].get("grammar_id")
        if first == "establishing" and panel_semantics and panel_semantics.get("panels"):
            desc = panel_semantics["panels"][0].get("description", "").lower()
            if not any(word in desc for word in rules.environment_keywords):
                issues.append("missing_environment_on_establishing")

    issue_details: list[dict[str, str]] = []
    for code in issues:
        if code == "too_many_closeups":
            allowed = max(1, int(total * rules.closeup_ratio_max))
            issue_details.append(
                {
                    "code": code,
                    "message": f"Too many close-up panels ({closeup_count}/{total}). Max {allowed}.",
                    "hint": "Reduce close-ups or mix in wider shots to balance framing.",
                }
            )
        elif code == "too_much_dialogue":
            allowed = max(1, int(total * rules.dialogue_ratio_max))
            issue_details.append(
                {
                    "code": code,
                    "message": f"Too many dialogue panels ({dialogue_count}/{total}). Max {allowed}.",
                    "hint": "Move some dialogue to narration or spread it across fewer panels.",
                }
            )
        elif code == "repeated_framing":
            issue_details.append(
                {
                    "code": code,
                    "message": f"Repeated framing detected ({max_run} panels in a row).",
                    "hint": "Vary camera distance or angle between adjacent panels.",
                }
            )
        elif code == "missing_environment_on_establishing":
            examples = ", ".join(rules.environment_keywords[:6])
            issue_details.append(
                {
                    "code": code,
                    "message": "Establishing panel lacks clear environment cues.",
                    "hint": f"Add location details (e.g., {examples}).",
                }
            )
        else:
            issue_details.append(
                {
                    "code": code,
                    "message": "QC rule failed.",
                    "hint": "Regenerate the panel plan or adjust scene semantics.",
                }
            )

    return {
        "passed": not issues,
        "issues": issues,
        "issue_details": issue_details,
        "metrics": {
            "panel_count": total,
            "closeup_count": closeup_count,
            "closeup_ratio": closeup_ratio,
            "dialogue_count": dialogue_count,
            "dialogue_ratio": dialogue_ratio,
            "max_repeated_framing": max_run,
        },
        "summary": "QC passed." if not issues else f"QC failed: {len(issues)} issue(s).",
    }


def _compile_prompt(
    panel_semantics: dict,
    layout_template: dict,
    style_id: str,
    characters: list[Character],
    reference_char_ids: set[uuid.UUID] | None = None,
    story_style: str | None = None,
    variants_by_character: dict[uuid.UUID, CharacterVariant] | None = None,
) -> str:
    """Compile a production-grade image generation prompt with rich visual details."""
    style_desc = _style_description(style_id)
    story_desc = _story_style_description(story_style)
    layout_text = layout_template.get("layout_text", "")
    reference_char_ids = reference_char_ids or set()
    panel_semantics = _inject_character_identities(
        panel_semantics=panel_semantics,
        characters=characters,
        reference_char_ids=reference_char_ids,
        variants_by_character=variants_by_character,
    )
    panels = panel_semantics.get("panels", []) or []
    panel_count = len(panels)

    # Build concise character lines (reference images provide detailed appearance)
    identity_lines = []
    codes = _character_codes(characters)
    for c in characters:
        code = codes.get(c.character_id)
        role = c.role or "character"
        variant = variants_by_character.get(c.character_id) if variants_by_character else None
        variant_outfit = None
        if variant and isinstance(variant.override_attributes, dict):
            variant_outfit = variant.override_attributes.get("outfit") or variant.override_attributes.get("clothing")
        char_lines = [f"  - {code} ({c.name}) [{role}]"]
        if c.character_id in reference_char_ids:
            if variant_outfit:
                char_lines.append(f"    Outfit: {variant_outfit}")
            elif c.base_outfit:
                char_lines.append(f"    Outfit: {c.base_outfit}")
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

    # Get genre-specific visual guidelines
    genre_key = (story_style or "drama").lower().replace("-", "_").replace(" ", "_")
    genre_guide = GENRE_VISUAL_GUIDELINES.get(genre_key, GENRE_VISUAL_GUIDELINES.get("drama", {}))

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
        f"**STYLE & GENRE:** {style_desc} | {story_desc}",
        "",
        "**PANEL COMPOSITION RULES:**",
        f"- Layout: {layout_text or f'{panel_count} panels, vertical flow'}",
        f"- Panel count: {panel_count} (do not add or remove panels)",
        "- Panels do NOT need equal sizes or grid alignment.",
        "- You may use one dominant panel with smaller inset panels.",
        "- Panels can vary in size and position if reading order is clear (top to bottom).",
        "- If there is a reveal/impact/emotional peak, make that panel dominant.",
        "",
        f"**GENRE VISUAL GUIDELINES ({genre_key}):**",
        f"- Lighting: {genre_guide.get('lighting', 'natural ambient')}",
        f"- Atmosphere: {genre_guide.get('atmosphere', 'appropriate to mood')}",
        f"- Color palette: {genre_guide.get('color_palette', 'natural tones')}",
        "",
    ]

    if identity_lines:
        lines.append("**CHARACTERS (reference images provided; keep appearance consistent):**")
        lines.extend(identity_lines)
        lines.append("")

    lines.append("**PANELS (action/emotion/environment only; no text in image):**")
    for panel in panels:
        grammar_id = panel.get("grammar_id")
        grammar_hint = mapping.get(grammar_id, "")
        desc = panel.get("description", "")

        # Extract environment and lighting if available
        environment = panel.get("environment", {})
        lighting = panel.get("lighting", {})
        atmosphere = panel.get("atmosphere_keywords", [])

        # Build detailed panel description
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

        # Handle dialogue
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

    lines.extend([
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
        "low quality, blurry, amateur, inconsistent character design"
    ])

    return "\n".join([line for line in lines if line is not None])


def _style_description(style_id: str) -> str:
    styles = loaders.load_image_styles_v1().styles
    for style in styles:
        if style.id == style_id:
            return f"{style.label}: {style.description}"
    return style_id


def _story_style_description(style_id: str | None) -> str:
    if not style_id:
        return "default"
    styles = loaders.load_story_styles_v1().styles
    for style in styles:
        if style.id == style_id:
            return f"{style.label}: {style.description}"
    return style_id


def _panel_semantics_text(panel_semantics: dict) -> str:
    parts = []
    for panel in panel_semantics.get("panels", []):
        desc = panel.get("description")
        if desc:
            parts.append(str(desc))
        for line in panel.get("dialogue") or []:
            parts.append(str(line))
    return " ".join(parts)


def _character_ids_with_reference_images(db: Session, story_id: uuid.UUID) -> set[uuid.UUID]:
    variant_ids = _active_variant_reference_images(db, story_id).keys()
    stmt = (
        select(CharacterReferenceImage.character_id)
        .join(StoryCharacter, CharacterReferenceImage.character_id == StoryCharacter.character_id)
        .where(
            StoryCharacter.story_id == story_id,
            CharacterReferenceImage.approved.is_(True),
            CharacterReferenceImage.ref_type == "face",
        )
        .distinct()
    )
    return set(db.execute(stmt).scalars().all()).union(set(variant_ids))


def _active_variant_reference_images(
    db: Session,
    story_id: uuid.UUID,
) -> dict[uuid.UUID, CharacterReferenceImage]:
    variants = _active_variants_by_character(db, story_id).values()
    if not variants:
        return {}
    ref_ids = {v.reference_image_id for v in variants if v.reference_image_id}
    if not ref_ids:
        return {}
    ref_lookup = {
        ref.reference_image_id: ref
        for ref in db.execute(
            select(CharacterReferenceImage).where(CharacterReferenceImage.reference_image_id.in_(ref_ids))
        )
        .scalars()
        .all()
    }
    results: dict[uuid.UUID, CharacterReferenceImage] = {}
    for variant in variants:
        ref = ref_lookup.get(variant.reference_image_id)
        if ref is None:
            continue
        results[variant.character_id] = ref
    return results


def _active_variants_by_character(
    db: Session,
    story_id: uuid.UUID,
) -> dict[uuid.UUID, CharacterVariant]:
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
    return {variant.character_id: variant for variant in variants}


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
    variants_by_character: dict[uuid.UUID, CharacterVariant] | None = None,
) -> dict:
    if not panel_semantics or not characters:
        return panel_semantics

    codes = _character_codes(characters)
    name_map: dict[str, dict[str, str]] = {}
    variants_by_character = variants_by_character or {}
    for c in characters:
        code = codes.get(c.character_id, "CHAR_X")
        base = f"{code} ({c.name})"
        variant = variants_by_character.get(c.character_id)
        variant_outfit = None
        if variant and isinstance(variant.override_attributes, dict):
            variant_outfit = variant.override_attributes.get("outfit") or variant.override_attributes.get("clothing")
        if c.character_id in reference_char_ids:
            parts = [base, "matching reference image"]
            if variant_outfit:
                parts.append(f"wearing {variant_outfit}")
            elif c.base_outfit:
                parts.append(f"wearing {c.base_outfit}")
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
        name_map[c.name.lower()] = {"label": label, "code": base}

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

    def _replace_text(text: str) -> str:
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
                return f"{payload['label']}{suffix}"

            updated = pattern.sub(_repl, updated)
        if matched_reference:
            updated = _strip_forbidden_descriptors(updated)
        return updated

    cloned = dict(panel_semantics)
    panels = []
    for panel in panel_semantics.get("panels", []) or []:
        updated_panel = dict(panel)
        if updated_panel.get("description"):
            updated_panel["description"] = _replace_text(str(updated_panel["description"]))
        if updated_panel.get("dialogue"):
            updated_dialogue = []
            for line in updated_panel["dialogue"]:
                if isinstance(line, dict):
                    char_name = str(line.get("character") or "")
                    key = char_name.lower()
                    if key in name_map:
                        updated_line = dict(line)
                        updated_line["character"] = name_map[key]["label"]
                        updated_dialogue.append(updated_line)
                    else:
                        updated_dialogue.append(line)
                else:
                    updated_dialogue.append(_replace_text(str(line)))
            updated_panel["dialogue"] = updated_dialogue
        panels.append(updated_panel)
    cloned["panels"] = panels
    return cloned


def _rough_similarity(text_a: str, text_b: str) -> float:
    tokens_a = set(re.findall(r"\w+", text_a.lower()))
    tokens_b = set(re.findall(r"\w+", text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / max(1, len(union))


def _render_image_from_prompt(
    prompt: str,
    gemini: GeminiClient | None = None,
    reference_images: list[tuple[bytes, str]] | None = None,
) -> tuple[bytes, str, dict]:
    if gemini is None:
        raise RuntimeError("Gemini is not configured")

    try:
        image_bytes, mime_type = gemini.generate_image(prompt=prompt, reference_images=reference_images)
    except TypeError:
        image_bytes, mime_type = gemini.generate_image(prompt=prompt)
    metadata = {
        "model": getattr(gemini, "last_model", None),
        "request_id": getattr(gemini, "last_request_id", None),
        "usage": getattr(gemini, "last_usage", None),
    }
    return image_bytes, mime_type, metadata


def _resolve_media_path(image_url: str) -> str:
    prefix = settings.media_url_prefix.rstrip("/")
    if image_url.startswith(f"{prefix}/"):
        return os.path.join(settings.media_root, image_url[len(prefix) + 1 :])
    if image_url.startswith("/media/"):
        return os.path.join(settings.media_root, image_url[len("/media/") :])
    if image_url.startswith("media/"):
        return os.path.join(settings.media_root, image_url[len("media/") :])
    if os.path.isabs(image_url):
        return image_url
    return os.path.join(settings.media_root, image_url)


def _load_character_reference_images(
    db: Session,
    story_id: uuid.UUID,
    max_images: int = 6,
) -> list[tuple[bytes, str]]:
    variant_refs = _active_variant_reference_images(db, story_id)
    stmt = (
        select(CharacterReferenceImage)
        .join(StoryCharacter, CharacterReferenceImage.character_id == StoryCharacter.character_id)
        .where(
            StoryCharacter.story_id == story_id,
            CharacterReferenceImage.approved.is_(True),
            CharacterReferenceImage.ref_type == "face",
        )
        .order_by(
            CharacterReferenceImage.character_id.asc(),
            CharacterReferenceImage.is_primary.desc(),
            CharacterReferenceImage.created_at.desc(),
        )
    )

    refs = list(db.execute(stmt).scalars().all())
    picked: dict[uuid.UUID, CharacterReferenceImage] = {}
    for character_id, ref in variant_refs.items():
        picked[character_id] = ref
        if len(picked) >= max_images:
            break
    for ref in refs:
        if ref.character_id in picked:
            continue
        picked[ref.character_id] = ref
        if len(picked) >= max_images:
            break

    results: list[tuple[bytes, str]] = []
    for ref in picked.values():
        try:
            path = _resolve_media_path(ref.image_url)
            with open(path, "rb") as handle:
                data = handle.read()
            mime_type = mimetypes.guess_type(path)[0] or "image/png"
            results.append((data, mime_type))
        except OSError as exc:
            logger.warning("reference image load failed ref_id=%s error=%s", ref.reference_image_id, exc)
            continue

    return results


def _extract_dialogue_suggestions(text: str) -> list[dict]:
    suggestions: list[dict] = []
    for idx, line in enumerate(_extract_dialogue_lines(text)):
        speaker = "unknown"
        cleaned = line.strip()
        if ":" in cleaned:
            possible_speaker, remainder = cleaned.split(":", 1)
            if 0 < len(possible_speaker) <= 24 and remainder.strip():
                speaker = possible_speaker.strip().strip('"')
                cleaned = remainder.strip().strip('"')
        elif " - " in cleaned:
            possible_speaker, remainder = cleaned.split(" - ", 1)
            if 0 < len(possible_speaker) <= 24 and remainder.strip():
                speaker = possible_speaker.strip().strip('"')
                cleaned = remainder.strip().strip('"')

        suggestions.append(
            {
                "speaker": speaker,
                "text": cleaned,
                "emotion": "neutral",
                "panel_hint": idx + 1,
            }
        )
    return suggestions


def _dialogue_panel_ids(panel_semantics: dict) -> list[int]:
    panels = panel_semantics.get("panels") if isinstance(panel_semantics, dict) else None
    if not isinstance(panels, list) or not panels:
        return []
    panel_ids: list[int] = []
    for idx, panel in enumerate(panels):
        if isinstance(panel, dict):
            panel_id = panel.get("panel_index") or panel.get("panel_id")
            if isinstance(panel_id, int):
                panel_ids.append(panel_id)
                continue
        panel_ids.append(idx + 1)
    return panel_ids


def _normalize_dialogue_script(raw: dict | None, panel_ids: list[int]) -> dict:
    normalized = {"scene_id": None, "dialogue_by_panel": []}
    if isinstance(raw, dict):
        normalized["scene_id"] = raw.get("scene_id")
        raw_panels = raw.get("dialogue_by_panel")
        if isinstance(raw_panels, list):
            normalized["dialogue_by_panel"] = raw_panels

    panel_map = {p.get("panel_id"): p for p in normalized.get("dialogue_by_panel", []) if isinstance(p, dict)}
    result_panels = []
    def _is_narration_like(text: str) -> bool:
        lowered = text.lower()
        return any(
            phrase in lowered
            for phrase in (
                " he says",
                " she says",
                " he whispers",
                " she whispers",
                " he thinks",
                " she thinks",
                " he stares",
                " she stares",
                " he looks",
                " she looks",
                " he walks",
                " she walks",
                " he steps",
                " she steps",
            )
        )

    for panel_id in panel_ids:
        panel = panel_map.get(panel_id, {"panel_id": panel_id, "lines": [], "notes": None})
        lines = panel.get("lines")
        cleaned_lines = []
        caption_used = False
        if isinstance(lines, list):
            for line in lines:
                if not isinstance(line, dict):
                    continue
                text = str(line.get("text") or "").strip()
                if not text:
                    continue
                speaker = str(line.get("speaker") or "unknown").strip() or "unknown"
                line_type = str(line.get("type") or "speech").strip().lower()
                if line_type not in {"speech", "thought", "caption", "sfx"}:
                    line_type = "speech"
                if _is_narration_like(text) and line_type in {"speech", "thought"}:
                    continue
                if line_type == "caption":
                    if caption_used:
                        continue
                    caption_used = True
                cleaned_lines.append({"speaker": speaker, "type": line_type, "text": text})
                if len(cleaned_lines) >= 3:
                    break
        result_panels.append(
            {
                "panel_id": panel_id,
                "lines": cleaned_lines,
                "notes": panel.get("notes"),
            }
        )
    normalized["dialogue_by_panel"] = result_panels
    return normalized


def _fallback_dialogue_script(scene_text: str, panel_ids: list[int]) -> dict:
    dialogue_lines = _extract_dialogue_lines(scene_text)
    lines_iter = iter(dialogue_lines)
    panels = []
    for panel_id in panel_ids:
        panel_lines = []
        for _ in range(3):
            line = next(lines_iter, None)
            if not line:
                break
            panel_lines.append({"speaker": "unknown", "type": "speech", "text": line})
        panels.append({"panel_id": panel_id, "lines": panel_lines, "notes": None})
    return {"scene_id": None, "dialogue_by_panel": panels}


def _prompt_dialogue_script(
    scene_id: uuid.UUID,
    scene_text: str,
    panel_semantics: dict,
    character_names: list[str],
) -> str:
    panel_ids = _dialogue_panel_ids(panel_semantics)
    panels = panel_semantics.get("panels") if isinstance(panel_semantics, dict) else []
    panel_lines = []
    for panel in panels or []:
        if not isinstance(panel, dict):
            continue
        pid = panel.get("panel_index") or panel.get("panel_id")
        desc = panel.get("description") or ""
        panel_lines.append(f"- Panel {pid}: {desc}")
    panel_lines_text = "\n".join(panel_lines) if panel_lines else "No panel descriptions available."
    char_list = ", ".join(character_names) if character_names else "Unknown"

    return render_prompt(
        "prompt_dialogue_script",
        scene_id=scene_id,
        scene_text=scene_text,
        panel_lines_text=panel_lines_text,
        char_list=char_list,
    )


def _generate_dialogue_script(
    scene_id: uuid.UUID,
    scene_text: str,
    panel_semantics: dict,
    character_names: list[str],
    gemini: GeminiClient | None = None,
) -> dict:
    panel_ids = _dialogue_panel_ids(panel_semantics)
    if not panel_ids:
        panel_ids = list(range(1, 5))

    if gemini is None:
        return _fallback_dialogue_script(scene_text, panel_ids)

    prompt = _prompt_dialogue_script(scene_id, scene_text, panel_semantics, character_names)
    expected_schema = "{ scene_id: string, dialogue_by_panel: [{ panel_id: number, lines: [{ speaker: string, type: string, text: string }], notes: string|null }] }"
    raw = _maybe_json_from_gemini(gemini, prompt, expected_schema=expected_schema)
    if not isinstance(raw, dict):
        return _fallback_dialogue_script(scene_text, panel_ids)
    return _normalize_dialogue_script(raw, panel_ids)


def _prompt_variant_suggestions(
    story_id: uuid.UUID,
    story_title: str,
    scene_text: str,
    character_names: list[str],
) -> str:
    char_list = ", ".join(character_names) if character_names else "Unknown"
    return render_prompt(
        "prompt_variant_suggestions",
        story_id=story_id,
        story_title=story_title,
        scene_text=scene_text,
        char_list=char_list,
    )


def _repair_json_with_llm(gemini: GeminiClient, malformed_text: str, expected_schema: str | None = None) -> dict | None:
    """Attempt to repair malformed JSON using LLM as a last resort."""
    schema_hint = ""
    if expected_schema:
        schema_hint = f"\n\nExpected schema:\n{expected_schema}"

    repair_prompt = render_prompt(
        "prompt_repair_json",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        schema_hint=schema_hint,
        malformed_text=malformed_text[:2000],
    )

    try:
        repaired = gemini.generate_text(prompt=repair_prompt)
        return json.loads(repaired)
    except (json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
        logger.warning("JSON repair failed: %s", exc)
        return None


def _maybe_json_from_gemini(
    gemini: GeminiClient,
    prompt: str,
    expected_schema: str | None = None,
) -> dict | None:
    """
    Three-tier JSON extraction:
    1. Direct parse
    2. Regex extract JSON block
    3. LLM-based repair
    """
    full_prompt = f"{SYSTEM_PROMPT_JSON}\n\n{prompt}"

    try:
        text = gemini.generate_text(prompt=full_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("gemini prompt failed: %s", exc)
        return None

    # Tier 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tier 2: Regex extract JSON block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Tier 3: LLM-based repair
    return _repair_json_with_llm(gemini, text, expected_schema)


# ---------------------------------------------------------------------------
# Production-Grade LLM Prompts
# ---------------------------------------------------------------------------

def _prompt_scene_intent(scene_text: str, genre: str | None, character_names: list[str] | None = None) -> str:
    """Production-grade scene intent extraction prompt."""
    genre_text = genre or "general"
    char_list = ", ".join(character_names) if character_names else "unknown"

    return render_prompt(
        "prompt_scene_intent",
        global_constraints=GLOBAL_CONSTRAINTS,
        genre_text=genre_text,
        char_list=char_list,
        scene_text=scene_text,
    )


def _prompt_panel_plan(
    scene_text: str,
    panel_count: int,
    scene_intent: dict | None = None,
    scene_importance: str | None = None,
    character_names: list[str] | None = None,
    qc_rules: dict | None = None,
) -> str:
    """Production-grade panel plan generation prompt."""
    intent_block = ""
    if scene_intent:
        intent_block = f"""
Scene Intent:
- Logline: {scene_intent.get('logline', 'N/A')}
- Pacing: {scene_intent.get('pacing', 'normal')}
- Emotional arc: {scene_intent.get('emotional_arc', {})}
"""
    importance_block = ""
    if scene_importance:
        importance_block = f"\nScene importance: {scene_importance}\n"

    char_list = ", ".join(character_names) if character_names else "unknown characters"

    qc_block = ""
    if qc_rules:
        qc_block = f"""
QC HARD CONSTRAINTS (you MUST follow these):
- Max closeup ratio: {qc_rules.get('closeup_ratio_max', 0.5)} (no more than {int(panel_count * qc_rules.get('closeup_ratio_max', 0.5))} emotion_closeup panels)
- No more than 2 consecutive panels with the same grammar_id
- First panel MUST be 'establishing'
- Last panel SHOULD be 'reaction' or 'reveal' for closure
- Inset panels must be meaningful (dialogue, reveal, reaction, action, or intentional silent beat)
- Max inset panels: 2
"""

    return render_prompt(
        "prompt_panel_plan",
        global_constraints=GLOBAL_CONSTRAINTS,
        panel_count=panel_count,
        intent_block=intent_block.strip(),
        importance_block=importance_block.strip(),
        char_list=char_list,
        qc_block=qc_block.strip(),
        scene_text=scene_text,
    )


def _prompt_panel_semantics(
    scene_text: str,
    panel_plan: dict,
    layout_template: dict,
    characters: list[Character],
    scene_intent: dict | None = None,
    genre: str | None = None,
) -> str:
    """Production-grade panel semantics prompt with grammar constraints and visual guidelines."""
    char_blocks = []
    for c in characters:
        identity = c.identity_line or f"{c.name}: {c.role or 'character'}"
        char_block = f"  - {identity}"

        # Add age-based style prompt for visual consistency
        gender = getattr(c, "gender", None)
        age_range = getattr(c, "age_range", None)
        if gender and age_range:
            char_style = get_character_style_prompt(gender, age_range)
            if char_style:
                char_block += f"\n    [Age/Style reference: {char_style[:300]}]"

        # Add appearance details if available
        appearance = getattr(c, "appearance", None)
        if isinstance(appearance, dict):
            appearance_parts = []
            if appearance.get("hair"):
                appearance_parts.append(f"hair: {appearance['hair']}")
            if appearance.get("build"):
                appearance_parts.append(f"build: {appearance['build']}")
            if appearance_parts:
                char_block += f"\n    [Visual: {', '.join(appearance_parts)}]"

        char_blocks.append(char_block)
    char_section = "\n".join(char_blocks) if char_blocks else "  - No specific characters"

    panels_summary = []
    for p in panel_plan.get("panels", []):
        panels_summary.append(f"  Panel {p.get('panel_index')}: {p.get('grammar_id')} - {p.get('beat_summary', p.get('story_function', ''))}")
    plan_section = "\n".join(panels_summary)

    intent_block = ""
    if scene_intent:
        intent_block = f"""
Scene Context:
- Logline: {scene_intent.get('logline', 'N/A')}
- Pacing: {scene_intent.get('pacing', 'normal')}
- Visual motifs to include: {scene_intent.get('visual_motifs', [])}
"""

    # Get genre-specific guidelines
    genre_key = (genre or "drama").lower().replace("-", "_").replace(" ", "_")
    genre_guide = GENRE_VISUAL_GUIDELINES.get(genre_key, GENRE_VISUAL_GUIDELINES.get("drama", {}))

    genre_block = f"""
GENRE-SPECIFIC VISUAL GUIDELINES ({genre_key}):
- Shot preferences: {genre_guide.get('shot_preferences', 'Medium shots with emotional focus')}
- Composition: {genre_guide.get('composition', 'Characters 40% of frame')}
- Camera angles: {genre_guide.get('camera', 'Eye-level, natural angles')}
- Lighting style: {genre_guide.get('lighting', 'Natural ambient lighting')}
- Atmosphere: {genre_guide.get('atmosphere', 'Appropriate to scene mood')}
- Color palette: {genre_guide.get('color_palette', 'Natural tones')}
- Props to include: {genre_guide.get('props', 'Scene-appropriate objects')}
"""

    return render_prompt(
        "prompt_panel_semantics",
        global_constraints=GLOBAL_CONSTRAINTS,
        intent_block=intent_block.strip(),
        genre_block=genre_block.strip(),
        char_section=char_section,
        plan_section=plan_section,
        layout_text=layout_template.get("layout_text", "vertical scroll"),
        scene_text=scene_text,
    )


def _prompt_blind_reader(panel_semantics: dict) -> str:
    """Stage 1: Blind reader reconstructs story from panel semantics only."""
    panels_desc = []
    for p in panel_semantics.get("panels", []):
        desc = f"Panel {p.get('panel_index')}: {p.get('description', '')}"
        dialogue = p.get("dialogue", [])
        if dialogue:
            dialogue_texts: list[str] = []
            if isinstance(dialogue, list):
                for item in dialogue:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if text:
                            dialogue_texts.append(str(text))
                    else:
                        dialogue_texts.append(str(item))
            else:
                dialogue_texts.append(str(dialogue))
            if dialogue_texts:
                desc += f" Dialogue: {' '.join(dialogue_texts)}"
        chars = p.get("characters", [])
        if isinstance(chars, list) and chars:
            if isinstance(chars[0], dict):
                char_names = [c.get("name", "someone") for c in chars]
            else:
                char_names = chars
            desc += f" Characters: {', '.join(char_names)}"
        panels_desc.append(desc)

    return render_prompt(
        "prompt_blind_reader",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        panel_descriptions="\n".join(panels_desc),
    )


def _prompt_comparator(original_text: str, blind_reading: dict) -> str:
    """Stage 2: Compare blind reading to original for scoring."""
    return render_prompt(
        "prompt_comparator",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        original_text=original_text,
        reconstructed_story=blind_reading.get("reconstructed_story", "N/A"),
        identified_characters=blind_reading.get("identified_characters", []),
        plot_points=blind_reading.get("plot_points", []),
        unclear_elements=blind_reading.get("unclear_elements", []),
    )


def _prompt_blind_test(scene_text: str, panel_semantics: dict) -> str:
    """Fallback single-prompt blind test (used if two-stage fails)."""
    panels_desc = []
    for p in panel_semantics.get("panels", []):
        desc = f"Panel {p.get('panel_index')}: {p.get('description', '')}"
        dialogue = p.get("dialogue", [])
        if dialogue:
            desc += f" Dialogue: {' '.join(dialogue)}"
        panels_desc.append(desc)

    return render_prompt(
        "prompt_blind_test",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        global_constraints=GLOBAL_CONSTRAINTS,
        scene_text=scene_text,
        panel_descriptions="\n".join(panels_desc),
    )


# ---------------------------------------------------------------------------
# LLM-Enhanced Character Functions
# ---------------------------------------------------------------------------

def _prompt_character_extraction(source_text: str, max_characters: int) -> str:
    """Prompt for LLM-based character extraction."""
    return render_prompt(
        "prompt_character_extraction",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        global_constraints=GLOBAL_CONSTRAINTS,
        max_characters=max_characters,
        source_text=source_text,
    )


def _prompt_character_normalization(characters: list[dict], source_text: str) -> str:
    """Prompt for LLM-based character enrichment with Korean manhwa aesthetics."""
    char_list = json.dumps(characters, indent=2)

    return render_prompt(
        "prompt_character_normalization",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        global_constraints=GLOBAL_CONSTRAINTS,
        characters_json=char_list,
        story_context=source_text[:1500],
    )


def _prompt_visual_plan(
    scenes: list[dict],
    characters: list[dict],
    story_style: str | None,
) -> str:
    """Prompt for LLM-based visual plan compilation."""
    char_names = [c.get("name", "Unknown") for c in characters]
    char_identities = []
    for c in characters:
        identity = c.get("identity_line") or f"{c.get('name', 'Unknown')}: {c.get('role', 'character')}"
        char_identities.append(f"  - {identity}")

    scenes_block = []
    for s in scenes:
        scenes_block.append(f"Scene {s.get('scene_index', '?')}:\n{s.get('source_text', s.get('summary', ''))[:500]}")

    return render_prompt(
        "prompt_visual_plan",
        system_prompt_json=SYSTEM_PROMPT_JSON,
        global_constraints=GLOBAL_CONSTRAINTS,
        story_style=story_style or "general",
        character_identities="\n".join(char_identities),
        scenes_block="\n".join(scenes_block),
    )

__all__ = [name for name in globals() if not name.startswith("__")]
