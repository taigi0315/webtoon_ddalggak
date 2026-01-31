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
    _fallback_dialogue_script,
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

    record_qc_issues(issues)
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
        panel_ids = list(range(1, 5))

    if gemini is None:
        return _fallback_dialogue_script(scene_text, panel_ids)

    prompt = _prompt_dialogue_script(scene_id, scene_text, panel_semantics, character_names)
    expected_schema = "{ scene_id: string, dialogue_by_panel: [{ panel_id: number, lines: [{ speaker: string, type: string, text: string }], notes: string|null }] }"
    raw = _maybe_json_from_gemini(gemini, prompt, expected_schema=expected_schema)
    if not isinstance(raw, dict):
        return _fallback_dialogue_script(scene_text, panel_ids)
    return _normalize_dialogue_script(raw, panel_ids)


__all__ = [name for name in globals() if not name.startswith("__")]
