from __future__ import annotations

import logging
import math
import re
import uuid
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import loaders
from app.core.telemetry import trace_span
from app.core.settings import settings
from app.db.models import Character, CharacterReferenceImage, Scene, Story, StoryCharacter
from app.prompts.loader import render_prompt
from app.services.artifacts import ArtifactService
from app.services.images import ImageService
from app.services.storage import LocalMediaStore
from app.services.vertex_gemini import GeminiClient
from app.graphs.nodes.constants import (
    ARTIFACT_ART_DIRECTION,
    ARTIFACT_BLIND_TEST_REPORT,
    ARTIFACT_DIALOGUE_SUGGESTIONS,
    ARTIFACT_LAYOUT_TEMPLATE,
    ARTIFACT_PANEL_PLAN,
    ARTIFACT_PANEL_PLAN_NORMALIZED,
    ARTIFACT_PANEL_SEMANTICS,
    ARTIFACT_QC_REPORT,
    ARTIFACT_RENDER_RESULT,
    ARTIFACT_RENDER_SPEC,
    ARTIFACT_SCENE_INTENT,
    ARTIFACT_VISUAL_PLAN,
    GLOBAL_CONSTRAINTS,
    PACING_OPTIONS,
    SYSTEM_PROMPT_JSON,
    VALID_GAZE_VALUES,
    VALID_GRAMMAR_IDS,
    VISUAL_PROMPT_FORMULA,
)
from app.graphs.nodes.helpers.character import (
    CHARACTER_STYLE_MAP,
    _active_variant_reference_images,
    _active_variants_by_character,
    _character_codes,
    _inject_character_identities,
    get_character_style_prompt,
)
from app.core.metrics import record_qc_issues
from app.graphs.nodes.helpers.dialogue import (
    _dialogue_panel_ids,
    _extract_dialogue_lines,
    _normalize_dialogue_script,
)
from app.graphs.nodes.helpers.media import _load_character_reference_images, _resolve_media_path
from app.graphs.nodes.helpers.panel import (
    _assign_panel_weights,
    _evaluate_and_prune_panel_plan,
    _heuristic_panel_plan,
    _normalize_panel_plan,
)
from app.graphs.nodes.helpers.scene import (
    _choose_mid_grammar,
    _extract_beats,
    _extract_setting,
    _get_scene,
    _list_characters,
)
from app.graphs.nodes.helpers.similarity import _rough_similarity
from app.graphs.nodes.helpers.text import _extract_metadata_names, _extract_names, _split_sentences, _summarize_text
from app.graphs.nodes.json_parser import (
    _clean_json_text,
    _extract_json_array,
    _extract_json_object,
    _maybe_json_from_gemini,
    _repair_json_with_llm,
    _strip_markdown_fences,
)
from app.graphs.nodes.prompts.builders import (
    _prompt_blind_reader,
    _prompt_blind_test,
    _prompt_character_extraction,
    _prompt_character_normalization,
    _prompt_comparator,
    _prompt_dialogue_script,
    _prompt_panel_plan,
    _prompt_panel_semantics,
    _prompt_scene_intent,
    _prompt_variant_suggestions,
    _prompt_visual_plan,
)
from app.graphs.nodes.prompts.compile import _compile_prompt, _panel_semantics_text

logger = logging.getLogger(__name__)



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
        fallback_text_model=settings.gemini_fallback_text_model,
        fallback_image_model=settings.gemini_fallback_image_model,
        circuit_breaker_threshold=settings.gemini_circuit_breaker_threshold,
        circuit_breaker_timeout=settings.gemini_circuit_breaker_timeout,
    )


_BLANK_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff"
    b"?\x03\x00\x08\xfc\x02\xfe\xd2\xf3j\xf5\x00\x00\x00\x00IEND\xaeB`\x82"
)
def _list_characters(db: Session, story_id: uuid.UUID) -> list[Character]:
    stmt = (
        select(Character)
        .join(StoryCharacter, StoryCharacter.character_id == Character.character_id)
        .where(StoryCharacter.story_id == story_id)
    )
    return list(db.execute(stmt).scalars().all())


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
    """Determine panel count based on scene importance.

    Returns a value between 1-5 (hard limit for panel count per scene).
    """
    importance = (scene_importance or "").lower()
    word_count = len(re.findall(r"\w+", scene_text or ""))

    # Maximum 5 panels per scene image
    MAX_PANELS = 5

    if importance in {"climax", "cliffhanger"}:
        # Impact moments: single powerful panel
        return 1
    if importance == "release":
        # Resolution scenes: allow longer decompression beats.
        if word_count >= 220:
            return 5
        if word_count >= 120:
            return 4
        return 2
    if importance == "setup":
        # Setup scenes: use more panels for spatial/emotional context.
        return MAX_PANELS
    if importance == "build":
        # Build scenes: scale with content length for pacing flexibility.
        if word_count >= 220:
            return 5
        if word_count >= 120:
            return 4
        return max(2, min(int(fallback), MAX_PANELS))

    return max(1, min(int(fallback), MAX_PANELS))


def _derive_panel_plan_features(panel_plan: dict, character_names: list[str] | None = None) -> dict:
    """Compute aggregated features from a panel_plan.

    Returns dict with keys: panel_count, max_weight, avg_weight, num_large, has_strong_panel, is_single_panel, hero_count
    hero_count is derived from `must_show` tokens and `character_names` (if provided).
    """
    panels = list((panel_plan or {}).get("panels") or [])
    panel_count = len(panels)
    weights = [float(p.get("weight", 0.0)) for p in panels]
    max_weight = max(weights) if weights else 0.0
    avg_weight = sum(weights) / len(weights) if weights else 0.0
    num_large = sum(1 for w in weights if w >= 0.7)
    has_strong_panel = num_large > 0
    is_single_panel = panel_count == 1

    # hero_count: count of tokens in `must_show` that match primary character name (case-insensitive)
    must_show = (panel_plan or {}).get("must_show") or []
    hero_count = 0
    if character_names and must_show:
        primary = character_names[0].lower() if character_names else None
        for token in must_show:
            if not token:
                continue
            t = str(token).lower()
            if primary and primary in t:
                hero_count += 1
    # else fallback: if any must_show contains 'protagonist' or 'hero'
    if hero_count == 0 and must_show:
        for token in must_show:
            if str(token).lower() in {"protagonist", "hero"}:
                hero_count += 1

    return {
        "panel_count": panel_count,
        "max_weight": round(float(max_weight), 3),
        "avg_weight": round(float(avg_weight), 3),
        "num_large": int(num_large),
        "has_strong_panel": bool(has_strong_panel),
        "is_single_panel": bool(is_single_panel),
        "hero_count": int(hero_count),
    }


def _apply_weights_to_template(panel_plan: dict, template: "loaders.LayoutTemplate") -> "loaders.LayoutTemplate":
    """Return a new LayoutTemplate (as a simple dict-like object) where vertical stacked templates
    have panel heights assigned proportionally to panel weights. For asymmetric templates, try
    to map `must_be_large` panels to the largest template rect where applicable.
    """
    # Copy template to avoid mutating original
    tpl = template.model_copy() if hasattr(template, "model_copy") else template
    panels_tpl = [dict(p.model_dump()) for p in tpl.panels]
    plan_panels = list(panel_plan.get("panels") or [])
    if not plan_panels:
        return tpl

    # Simple stacked full-width detection
    is_full_width_stack = all((abs(p.get("x", 0.0)) < 1e-6 and abs(p.get("w", 1.0) - 1.0) < 1e-6) for p in panels_tpl)

    if is_full_width_stack and len(panels_tpl) == len(plan_panels):
        # Allocate vertical heights proportional to weights
        weights = [float(p.get("weight", 0.3)) for p in plan_panels]
        total = sum(weights)
        total = total or len(weights)
        min_h = 0.12
        gutters = 0.02 * (len(weights) - 1)
        available = max(0.0, 1.0 - gutters)
        heights = []
        for w in weights:
            h = max(min_h, (w / total) * available)
            heights.append(h)

        # If we overshot available due to mins, rescale
        sum_h = sum(heights)
        if sum_h > available:
            heights = [h * (available / sum_h) for h in heights]

        # Build new panels with y offsets
        y = 0.0
        new_panels = []
        for h in heights:
            new_panels.append({"x": 0.0, "y": round(y, 4), "w": 1.0, "h": round(h, 4)})
            y += h + 0.02

        # Return a lightweight LayoutTemplate-like object
        tpl.panels = [loaders.PanelRect.model_validate(p) for p in new_panels]
        return tpl

    # For asymmetrical templates: if any must_be_large exists, try to map it to the largest rect
    must_indices = [i for i, p in enumerate(plan_panels) if p.get("must_be_large")]
    if must_indices and len(panels_tpl) == len(plan_panels):
        # Find largest rect by area
        areas = [pt.get("w", 1.0) * pt.get("h", 1.0) for pt in panels_tpl]
        largest_idx = int(max(range(len(areas)), key=lambda i: areas[i]))
        # If there is a single must_be_large, swap its geometry with the largest rect
        if len(must_indices) == 1:
            m = must_indices[0]
            if m != largest_idx:
                panels_tpl[m], panels_tpl[largest_idx] = panels_tpl[largest_idx], panels_tpl[m]
                tpl.panels = [loaders.PanelRect.model_validate(p) for p in panels_tpl]
                return tpl
    # Default: return original template unchanged
    return tpl


def _heuristic_panel_semantics(
    scene_text: str,
    panel_plan: dict,
    layout_template: dict,
    characters: list[Character],
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
            }
        )

    return {"panels": panels}


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

    issues: list[str] = []
    issue_details: list[dict[str, str]] = []

    def _line_texts(dialogue_val: object) -> list[str]:
        if isinstance(dialogue_val, str):
            t = dialogue_val.strip()
            return [t] if t else []
        if not isinstance(dialogue_val, list):
            return []
        out: list[str] = []
        for item in dialogue_val:
            if isinstance(item, dict):
                txt = str(item.get("text") or "").strip()
            else:
                txt = str(item).strip()
            if txt:
                out.append(txt)
        return out

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
                " as you know",
                " meanwhile",
                " suddenly",
            )
        )

    def _is_generic_dialogue(text: str) -> bool:
        lowered = text.lower()
        return any(
            pat in lowered
            for pat in (
                "let me explain",
                "in other words",
                "this changes everything",
                "i cannot believe this is happening",
                "we need to",
                "i have a bad feeling",
            )
        )

    word_count_violations: list[int] = []
    line_word_violations: list[int] = []
    silent_panels = 0
    dialogue_panels = 0
    total_word_count = 0
    total_dialogue_lines = 0
    narration_like_lines = 0
    generic_lines = 0
    semantics_panels = list(panel_semantics.get("panels") or []) if panel_semantics else []

    for p_sem in semantics_panels:
        lines = _line_texts(p_sem.get("dialogue"))
        panel_words = sum(len(line.split()) for line in lines)
        total_word_count += panel_words
        total_dialogue_lines += len(lines)

        panel_id = p_sem.get("panel_index")
        if lines:
            dialogue_panels += 1
        else:
            silent_panels += 1

        if panel_words > rules.max_words_per_panel and isinstance(panel_id, int):
            word_count_violations.append(panel_id)

        if any(len(line.split()) > rules.max_words_per_line for line in lines) and isinstance(panel_id, int):
            line_word_violations.append(panel_id)

        for line in lines:
            if _is_narration_like(line):
                narration_like_lines += 1
            if _is_generic_dialogue(line):
                generic_lines += 1

    if word_count_violations:
        issues.append("word_count_violation")
        issue_details.append(
            {
                "code": "word_count_violation",
                "message": f"Panels {word_count_violations} exceed the panel word limit ({rules.max_words_per_panel}).",
                "hint": "Cut exposition and let action/expression carry meaning.",
            }
        )

    if line_word_violations:
        issues.append("line_too_long")
        issue_details.append(
            {
                "code": "line_too_long",
                "message": f"Panels {line_word_violations} include dialogue lines longer than {rules.max_words_per_line} words.",
                "hint": "Split into shorter, natural bursts or replace with silent reaction.",
            }
        )

    # 2. Layout Monotony check (Task 7.1)
    widths = [p.get("panel_hierarchy", {}).get("width_percentage") for p in panels]
    monotony_run = 1
    max_monotony = 1
    for idx in range(1, len(widths)):
        if widths[idx] == widths[idx-1] and widths[idx] is not None:
            monotony_run += 1
            max_monotony = max(max_monotony, monotony_run)
        else:
            monotony_run = 1
    
    if max_monotony >= rules.repeated_framing_run_length:
        issues.append("monotonous_layout")
        issue_details.append({
            "code": "monotonous_layout",
            "message": f"Redundant layout width found ({max_monotony} consecutive panels).",
            "hint": "Vary panel widths (100%, 80%, 60%) to improve rhythm."
        })

    # 3. Show-Don't-Tell / Dialogue Redundancy
    redundant_panels: list[int] = []
    for p_sem in semantics_panels:
        panel_id = p_sem.get("panel_index")
        dialogue_joined = " ".join(_line_texts(p_sem.get("dialogue"))).lower()
        if any(key in dialogue_joined for key in ["i am showing", "look at", "see how i", "as you can see"]):
            if isinstance(panel_id, int):
                redundant_panels.append(panel_id)

    if redundant_panels:
        issues.append("dialogue_redundancy")
        issue_details.append({
            "code": "dialogue_redundancy",
            "message": f"Redundant 'Show' statements in dialogue for panels {redundant_panels}.",
            "hint": "Let the art show the action; remove self-descriptive dialogue."
        })

    # Existing closeup and dialogue ratio checks
    closeups = [p for p in panels if p.get("grammar_id") == "emotion_closeup"]
    closeup_count = len(closeups)
    closeup_ratio = closeup_count / total

    if closeup_ratio > rules.closeup_ratio_max:
        issues.append("too_many_closeups")
        issue_details.append(
            {
                "code": "too_many_closeups",
                "message": f"Close-up ratio too high ({roundup(closeup_ratio, 3)}).",
                "hint": "Mix in establishing/reaction/object shots to restore visual rhythm.",
            }
        )

    dialogue_count = dialogue_panels
    dialogue_ratio = dialogue_count / total if total > 0 else 0.0
    silent_ratio = (silent_panels / total) if total > 0 else 0.0
    narration_ratio = (narration_like_lines / total_dialogue_lines) if total_dialogue_lines else 0.0
    generic_ratio = (generic_lines / total_dialogue_lines) if total_dialogue_lines else 0.0

    if dialogue_ratio > rules.dialogue_ratio_max:
        issues.append("too_much_dialogue")
        allowed = max(1, int(total * rules.dialogue_ratio_max))
        issue_details.append({
            "code": "too_much_dialogue",
            "message": f"Too many dialogue panels ({dialogue_count}/{total}). Max {allowed}.",
            "hint": "Strategically use silent panels for emotional impact."
        })

    if silent_ratio < rules.min_silent_panel_ratio:
        issues.append("not_enough_silence")
        issue_details.append(
            {
                "code": "not_enough_silence",
                "message": f"Silent panel ratio too low ({roundup(silent_ratio, 3)}).",
                "hint": "Add reaction/hold panels with no text to improve emotional pacing.",
            }
        )

    if narration_ratio > rules.narration_ratio_max:
        issues.append("narration_like_dialogue")
        issue_details.append(
            {
                "code": "narration_like_dialogue",
                "message": f"Narration-like dialogue ratio too high ({roundup(narration_ratio, 3)}).",
                "hint": "Convert descriptive lines into visual action or captions.",
            }
        )

    if generic_ratio > rules.generic_dialogue_ratio_max:
        issues.append("generic_dialogue")
        issue_details.append(
            {
                "code": "generic_dialogue",
                "message": f"Generic dialogue ratio too high ({roundup(generic_ratio, 3)}).",
                "hint": "Use character-specific voice and subtext instead of stock phrases.",
            }
        )

    record_qc_issues(issues)
    return {
        "passed": not issues,
        "issues": issues,
        "issue_details": issue_details,
        "metrics": {
            "panel_count": total,
            "closeup_count": closeup_count,
            "closeup_ratio": roundup(closeup_ratio, 3),
            "dialogue_count": dialogue_count,
            "dialogue_ratio": roundup(dialogue_ratio, 3),
            "silent_panel_count": silent_panels,
            "silent_panel_ratio": roundup(silent_ratio, 3),
            "narration_like_ratio": roundup(narration_ratio, 3),
            "generic_dialogue_ratio": roundup(generic_ratio, 3),
            "max_monotony": max_monotony,
            "total_word_count": total_word_count,
            "total_dialogue_lines": total_dialogue_lines,
        },
        "summary": "QC passed." if not issues else f"QC failed: {len(issues)} issue(s).",
    }


def roundup(val, digits):
    try:
        return round(float(val), digits)
    except (ValueError, TypeError):
        return val


def _character_ids_with_reference_images(db: Session, story_id: uuid.UUID) -> set[uuid.UUID]:
    variant_mapping = _active_variant_reference_images(db, story_id)
    variant_char_ids = {cid for (cid, vtype) in variant_mapping.keys()}
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
    return set(db.execute(stmt).scalars().all()).union(variant_char_ids)


def _render_image_from_prompt(
    prompt: str,
    gemini: GeminiClient | None = None,
    reference_images: list[tuple[bytes, str]] | None = None,
) -> tuple[bytes, str, dict]:
    if gemini is None:
        raise RuntimeError("Gemini is not configured")

    try:
        if reference_images:
            total_size = sum(len(img) for img, _ in reference_images)
            logger.info(
                "Gemini image gen: sending prompt + %d reference images (total img size: %.2f MB)",
                len(reference_images),
                total_size / (1024 * 1024),
            )
        image_bytes, mime_type = gemini.generate_image(prompt=prompt, reference_images=reference_images)
    except TypeError:
        image_bytes, mime_type = gemini.generate_image(prompt=prompt)
    metadata = {
        "model": getattr(gemini, "last_model", None),
        "request_id": getattr(gemini, "last_request_id", None),
        "usage": getattr(gemini, "last_usage", None),
    }
    return image_bytes, mime_type, metadata


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


def _generate_dialogue_script(
    scene_id: uuid.UUID,
    scene_text: str,
    panel_semantics: dict,
    character_names: list[str],
    gemini: GeminiClient | None = None,
) -> dict:
    panel_ids = _dialogue_panel_ids(panel_semantics)
    if not panel_ids:
        logger.error(
            "dialogue_writer fail-fast: no panel ids (scene_id=%s, panel_semantics_keys=%s)",
            scene_id,
            list(panel_semantics.keys()) if isinstance(panel_semantics, dict) else type(panel_semantics).__name__,
        )
        raise ValueError("dialogue_writer failed: no valid panel ids in panel_semantics")

    if gemini is None:
        logger.error(
            "dialogue_writer fail-fast: missing Gemini client (scene_id=%s, panel_count=%d)",
            scene_id,
            len(panel_ids),
        )
        raise RuntimeError("Gemini client is required for dialogue generation (fail-fast mode)")

    prompt = _prompt_dialogue_script(scene_id, scene_text, panel_semantics, character_names)
    expected_schema = "{ scene_id: string, dialogue_by_panel: [{ panel_id: number, lines: [{ speaker: string, type: string, text: string }], notes: string|null }] }"
    raw = _maybe_json_from_gemini(gemini, prompt, expected_schema=expected_schema)
    if not isinstance(raw, dict):
        logger.error(
            "dialogue_writer generation failed: invalid Gemini JSON (scene_id=%s, panel_count=%d)",
            scene_id,
            len(panel_ids),
        )
        raise RuntimeError("dialogue_writer failed: Gemini returned invalid JSON")
    normalized = _normalize_dialogue_script(raw, panel_ids)
    dialogue_by_panel = normalized.get("dialogue_by_panel")
    if not isinstance(dialogue_by_panel, list):
        logger.error(
            "dialogue_writer normalization failed: missing dialogue_by_panel list (scene_id=%s)",
            scene_id,
        )
        raise RuntimeError("dialogue_writer failed: normalized output missing dialogue_by_panel")
    return normalized


__all__ = [name for name in globals() if not name.startswith("__")]
