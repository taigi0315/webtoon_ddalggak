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
from app.db.models import Character, CharacterReferenceImage, Scene, Story
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

# ---------------------------------------------------------------------------
# System Prompts and Global Constraints for LLM Calls
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_JSON = """You are a strict JSON generator for a webtoon creation pipeline.
Return ONLY valid JSON. No markdown. No commentary.
Use double quotes for all keys and string values.
Do not include trailing commas.
If information is unknown, use null or an empty list.
Follow the output schema exactly."""

GLOBAL_CONSTRAINTS = """Constraints:
- Do NOT invent named characters not present in the input unless clearly implied.
- Keep outputs concise but complete.
- Avoid repetition.
- Respect the requested maximum counts.
- If unsure, prefer conservative outputs."""

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

# ---------------------------------------------------------------------------
# Age-Based Character Visual Prompts (Korean Webtoon Manhwa Style)
# These are production-grade prompts for consistent character rendering
# ---------------------------------------------------------------------------

CHARACTER_STYLE_MALE_KID = """cute little boy, webtoon manhwa art style,
childlike innocent features, large expressive eyes with bright highlights,
round cherubic face, soft pudgy cheeks, small petite stature,
short limbs, playful energetic posture, messy or neat styled hair,
colorful casual children's clothes (t-shirt, shorts, sneakers),
authentic webtoon style character illustration,
chibi-like proportions, head-to-body ratio 1:3, youthful innocence"""

CHARACTER_STYLE_MALE_TEEN = """teenage boy character, soft Korean webtoon manhwa art style,
delicate youthful features, gentle angular face with soft edges,
smooth clear skin, large expressive eyes with gentle gaze,
trendy Korean-style haircut (soft side-swept bangs, layered medium-length, or fluffy textured),
slender graceful build, lean elegant frame without muscle definition,
tall slim proportions with narrow shoulders, willowy silhouette,
long slender limbs, refined gentle posture,
school uniform (neat blazer, crisp white shirt, fitted slacks) or soft casual streetwear,
authentic Korean webtoon style character illustration,
clean gentle features, soft approachable demeanor,
height around 170-178cm with elegant proportions, youthful flower-boy aesthetic"""

CHARACTER_STYLE_MALE_20_30 = """handsome soft masculine features, Korean manhwa male lead aesthetic,
full body shot showing entire elegant figure from head to shoes,
standing gracefully in neutral lighting, visible feet and shoes,
gentle refined jawline (not overly chiseled), soft angular face,
stylish contemporary Korean hairstyle (soft side-part, gentle waves, fluffy layered, or elegant medium-length),
warm gentle expression with kind eyes, serene or subtly confident demeanor,
slender elegant build, graceful narrow shoulders, slim waist,
very tall slender stature 180-188cm, long lean legs, elongated refined torso,
willowy model-like proportions, elegant gentle frame without bulk or excessive muscle,
soft sophisticated silhouette, graceful refined lines,
authentic Korean webtoon manhwa style character illustration,
flawless porcelain-like skin, gentle refined presence, elegant relaxed posture,
soft romantic or professional appearance, flower-boy charm, gentle masculine beauty, approachable refined elegance"""

CHARACTER_STYLE_MALE_40_50 = """distinguished mature male character, soft Korean webtoon manhwa art style,
refined gentle features showing maturity, subtle expression lines adding character,
soft dignified presence, well-groomed elegant appearance,
neat sophisticated hairstyle (possibly subtle grey at temples),
slender maintained build, graceful mature frame,
narrow refined shoulders, elegant slim proportions,
professional refined attire (well-tailored suit, sophisticated casual wear, soft fabrics),
authentic Korean webtoon style character illustration,
graceful composed posture, height around 178-185cm with elegant proportions,
warm approachable expression, wise gentle demeanor,
sophisticated soft masculine presence, refined distinguished charm"""

CHARACTER_STYLE_MALE_60_70 = """elderly distinguished gentleman character, soft Korean webtoon manhwa art style,
aged refined features with gentle wisdom lines, warm expressive eyes,
silver or white hair (neat, dignified styling), kind grandfatherly appearance,
slender elegant elderly frame, graceful aged posture,
comfortable refined clothing (soft cardigan, elegant casual wear, traditional hanbok),
authentic Korean webtoon style character illustration,
gentle dignified stature around 170-175cm, narrow refined shoulders,
warm gentle expression radiating wisdom and kindness,
soft approachable grandfatherly presence, elegant aged grace"""

CHARACTER_STYLE_FEMALE_KID = """cute little girl, webtoon manhwa art style,
childlike innocent features, oversized sparkly eyes with long lashes,
round cherubic face, rosy plump cheeks, button nose, small petite stature,
short limbs, adorable playful posture, cute hairstyle (pigtails, bob, or ponytail with ribbons),
colorful dress, skirt, or casual children's outfit with bright colors,
authentic webtoon style character illustration,
chibi-like proportions, head-to-body ratio 1:3, innocent charming expression"""

CHARACTER_STYLE_FEMALE_TEEN = """teenage girl character, webtoon manhwa art style,
youthful fresh features, large expressive doe eyes with delicate lashes,
smooth clear skin with natural blush, cute button nose,
slender developing figure, long slim legs, petite frame,
authentic webtoon style character illustration,
height around 160-170cm proportions, graceful youthful posture,
bright innocent yet stylish expression, emerging beauty"""

CHARACTER_STYLE_FEMALE_20_30 = """tall elegant stature over 165cm, statuesque supermodel-like figure,
extremely long toned legs (leg length exceeding torso), dramatically elongated graceful proportions,
long elegant torso, perfect upright posture, hourglass silhouette with prominent natural breasts,
full voluptuous bust, narrow defined waist, wide feminine hips, sexy mature curves,
flawless glossy porcelain skin, stunning beautiful facial features,
modern chic fashion highlighting long legs and bust, authentic webtoon style character illustration,
sophisticated powerful presence, in realistic human proportions with no cartoon exaggeration"""

CHARACTER_STYLE_FEMALE_40_50 = """mature elegant female character, webtoon manhwa art style,
refined beautiful features showing graceful aging, subtle fine lines around eyes,
sophisticated appearance, well-maintained figure with feminine curves,
elegant styled hair (shoulder-length bob, soft waves, possible tasteful grey highlights),
motherly warm presence or professional commanding aura,
business professional attire or sophisticated elegant fashion,
authentic Korean webtoon style character illustration,
height around 160-170cm proportions, composed dignified posture,
confident experienced expression, timeless beauty with character,
narrow waist maintained, mature hourglass figure"""

CHARACTER_STYLE_FEMALE_60_70 = """elderly distinguished female character, webtoon manhwa art style,
aged graceful features, visible wrinkles and smile lines showing wisdom,
grey or white hair (elegant updo, short styled, or soft curls),
kind gentle eyes or strict authoritative gaze, grandmotherly presence,
softer rounder figure with dignified bearing, slightly hunched but noble posture,
classic comfortable clothing (traditional hanbok, cardigan sets, or elegant simple dresses),
authentic Korean webtoon style character illustration,
height around 155-165cm proportions, gentle or firm expression,
warm nurturing or strict matriarch aura, face showing life's journey"""

# Mapping for age/gender to style prompt
CHARACTER_STYLE_MAP = {
    ("male", "child"): CHARACTER_STYLE_MALE_KID,
    ("male", "kid"): CHARACTER_STYLE_MALE_KID,
    ("male", "teen"): CHARACTER_STYLE_MALE_TEEN,
    ("male", "young_adult"): CHARACTER_STYLE_MALE_20_30,
    ("male", "adult"): CHARACTER_STYLE_MALE_20_30,
    ("male", "middle_aged"): CHARACTER_STYLE_MALE_40_50,
    ("male", "elderly"): CHARACTER_STYLE_MALE_60_70,
    ("female", "child"): CHARACTER_STYLE_FEMALE_KID,
    ("female", "kid"): CHARACTER_STYLE_FEMALE_KID,
    ("female", "teen"): CHARACTER_STYLE_FEMALE_TEEN,
    ("female", "young_adult"): CHARACTER_STYLE_FEMALE_20_30,
    ("female", "adult"): CHARACTER_STYLE_FEMALE_20_30,
    ("female", "middle_aged"): CHARACTER_STYLE_FEMALE_40_50,
    ("female", "elderly"): CHARACTER_STYLE_FEMALE_60_70,
}


def get_character_style_prompt(gender: str | None, age_range: str | None) -> str:
    """Get the appropriate character style prompt based on gender and age."""
    if not gender or not age_range:
        return ""
    key = (gender.lower(), age_range.lower())
    return CHARACTER_STYLE_MAP.get(key, "")


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


def generate_character_reference_image(
    db: Session,
    character_id: uuid.UUID,
    ref_type: str = "face",
    story_style: str | None = None,
    gemini: GeminiClient | None = None,
) -> CharacterReferenceImage:
    character = db.get(Character, character_id)
    if character is None:
        raise ValueError("character not found")

    if not character.description and not character.identity_line:
        raise ValueError("character needs description or identity_line to generate reference images")

    gemini = gemini or _build_gemini_client()

    style_prompt = get_character_style_prompt(character.gender, character.age_range)
    identity = character.identity_line or character.description or character.name
    story_style_text = story_style or (character.story.default_story_style if character.story else None)

    prompt_parts = [
        "High-quality character reference image for a Korean webtoon.",
        f"Character: {character.name}.",
        f"Identity: {identity}.",
        f"Ref type: {ref_type}.",
    ]
    if story_style_text:
        prompt_parts.append(f"Story style: {story_style_text}.")
    if style_prompt:
        prompt_parts.append(style_prompt)
    prompt_parts.append("Plain background, clean silhouette, full body if possible.")

    prompt = " ".join([part for part in prompt_parts if part])

    image_bytes, mime_type = gemini.generate_image(prompt=prompt)

    store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
    _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

    ref = CharacterReferenceImage(
        character_id=character_id,
        image_url=url,
        ref_type=ref_type,
        approved=False,
        is_primary=False,
        metadata_={
            "mime_type": mime_type,
            "model": getattr(gemini, "last_model", None),
            "request_id": getattr(gemini, "last_request_id", None),
            "usage": getattr(gemini, "last_usage", None),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        },
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


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

# ---------------------------------------------------------------------------
# Visual Prompt Construction Formula
# ---------------------------------------------------------------------------

VISUAL_PROMPT_FORMULA = """Visual Prompt Construction Formula (150-250 words):

{shot_type}, vertical 9:16 webtoon panel, {composition_note},
{environment_with_5+_specific_details} + {style_lighting_description},
{character_placement} + {action_and_expression},
{atmosphere_keywords},
{genre} manhwa style, {rendering_notes}

REQUIRED ELEMENTS:
1. Shot type (establishing/medium/closeup/etc.)
2. 5+ specific environment details (architecture, props, lighting, weather)
3. Character positioning with percentage (e.g., "occupies 40% of frame")
4. Lighting conditions specific to style
5. Atmosphere/mood keywords
6. Color palette notes"""

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


def compute_scene_chunker(source_text: str, max_scenes: int = 6) -> list[str]:
    text = (source_text or "").strip()
    if not text:
        return []

    max_scenes = max(1, int(max_scenes))

    # Prefer explicit scene/section markers when present.
    marker_split = re.split(r"\n(?=\s*(?:Scene|Chapter|Part)\b)", text, flags=re.IGNORECASE)
    marker_chunks = [p.strip() for p in marker_split if p.strip()]
    if len(marker_chunks) >= 2:
        return marker_chunks[:max_scenes]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if len(paragraphs) >= 2:
        return _group_chunks(paragraphs, max_scenes)

    sentences = _split_sentences(text)
    if not sentences:
        return [text]

    return _group_chunks(sentences, max_scenes)


def compute_character_profiles(source_text: str, max_characters: int = 6) -> list[dict]:
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


def run_scene_intent_extractor(
    db: Session,
    scene_id: uuid.UUID,
    genre: str | None = None,
    gemini: GeminiClient | None = None,
):
    with trace_span("graph.scene_intent_extractor", scene_id=str(scene_id), genre=genre):
        scene = _get_scene(db, scene_id)
        story = db.get(Story, scene.story_id)
        characters = _list_characters(db, scene.story_id)
        character_names = [c.name for c in characters]
        summary = _summarize_text(scene.source_text)

        payload = {
            "summary": summary,
            "genre": genre or (story.default_story_style if story else None),
            "setting": _extract_setting(scene.source_text),
            "beats": _extract_beats(scene.source_text, max_beats=3),
            "characters": character_names,
            "logline": None,
            "pacing": "normal",
            "emotional_arc": None,
            "visual_motifs": [],
        }

        if gemini is not None:
            llm = _maybe_json_from_gemini(
                gemini,
                _prompt_scene_intent(scene.source_text, payload["genre"], character_names),
            )
            if isinstance(llm, dict):
                payload = {**payload, **llm}

        return ArtifactService(db).create_artifact(
            scene_id=scene_id, type=ARTIFACT_SCENE_INTENT, payload=payload
        )


def run_panel_plan_generator(
    db: Session,
    scene_id: uuid.UUID,
    panel_count: int = 3,
    gemini: GeminiClient | None = None,
):
    with trace_span(
        "graph.panel_plan_generator",
        scene_id=str(scene_id),
        panel_count=panel_count,
    ):
        svc = ArtifactService(db)
        scene = _get_scene(db, scene_id)
        characters = _list_characters(db, scene.story_id)
        character_names = [c.name for c in characters]
        panel_count = max(1, int(panel_count))
        importance = scene.scene_importance
        if importance:
            panel_count = _panel_count_for_importance(importance, scene.source_text, panel_count)

        # Get scene_intent if available
        scene_intent_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
        scene_intent = scene_intent_artifact.payload if scene_intent_artifact else None

        # Get QC rules for proactive constraints
        qc_rules_obj = loaders.load_qc_rules_v1()
        qc_rules = {
            "closeup_ratio_max": qc_rules_obj.closeup_ratio_max,
            "dialogue_ratio_max": qc_rules_obj.dialogue_ratio_max,
            "repeated_framing_run_length": qc_rules_obj.repeated_framing_run_length,
        }

        plan = _heuristic_panel_plan(scene.source_text, panel_count)

        if gemini is not None:
            llm = _maybe_json_from_gemini(
                gemini,
                _prompt_panel_plan(
                    scene.source_text,
                    panel_count,
                    scene_intent=scene_intent,
                    scene_importance=importance,
                    character_names=character_names,
                    qc_rules=qc_rules,
                ),
            )
            if isinstance(llm, dict) and isinstance(llm.get("panels"), list):
                plan = {"panels": llm["panels"]}

        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_PLAN, payload=plan)


def run_panel_plan_normalizer(db: Session, scene_id: uuid.UUID):
    with trace_span("graph.panel_plan_normalizer", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
        if panel_plan is None:
            raise ValueError("panel_plan artifact not found")
        normalized = _normalize_panel_plan(panel_plan.payload)
        return svc.create_artifact(
            scene_id=scene_id, type=ARTIFACT_PANEL_PLAN_NORMALIZED, payload=normalized
        )


def run_layout_template_resolver(db: Session, scene_id: uuid.UUID):
    with trace_span("graph.layout_template_resolver", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
        if panel_plan is None:
            panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
        if panel_plan is None:
            raise ValueError("panel_plan artifact not found")

        template = loaders.select_template(panel_plan.payload)
        payload = {
            "template_id": template.template_id,
            "layout_text": template.layout_text,
            "panels": [p.model_dump() for p in template.panels],
        }
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_LAYOUT_TEMPLATE, payload=payload)


def run_panel_semantic_filler(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
):
    with trace_span("graph.panel_semantic_filler", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        scene = _get_scene(db, scene_id)
        story = db.get(Story, scene.story_id)
        characters = _list_characters(db, scene.story_id)

        scene_intent_artifact = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
        scene_intent = scene_intent_artifact.payload if scene_intent_artifact else None
        panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
        if panel_plan is None:
            panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
        layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)

        if panel_plan is None or layout is None:
            raise ValueError("panel_plan and layout_template artifacts are required")

        payload = _heuristic_panel_semantics(
            scene_text=scene.source_text,
            panel_plan=panel_plan.payload,
            layout_template=layout.payload,
            characters=characters,
            story_style=(story.default_story_style if story else None),
            scene_intent=scene_intent,
        )

        if gemini is not None:
            llm = _maybe_json_from_gemini(
                gemini,
                _prompt_panel_semantics(
                    scene.source_text,
                    panel_plan.payload,
                    layout.payload,
                    characters,
                    scene_intent=scene_intent,
                    genre=(story.default_story_style if story else None),
                ),
            )
            if isinstance(llm, dict) and isinstance(llm.get("panels"), list):
                payload["panels"] = llm["panels"]

        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_PANEL_SEMANTICS, payload=payload)


def run_qc_checker(db: Session, scene_id: uuid.UUID):
    with trace_span("graph.qc_checker", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN_NORMALIZED)
        if panel_plan is None:
            panel_plan = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_PLAN)
        panel_semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)

        if panel_plan is None:
            raise ValueError("panel_plan artifact not found")

        report = _qc_report(panel_plan.payload, panel_semantics.payload if panel_semantics else None)
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_QC_REPORT, payload=report)


def run_prompt_compiler(
    db: Session,
    scene_id: uuid.UUID,
    style_id: str,
    prompt_override: str | None = None,
):
    with trace_span("graph.prompt_compiler", scene_id=str(scene_id), style_id=style_id):
        svc = ArtifactService(db)
        panel_semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
        layout = svc.get_latest_artifact(scene_id, ARTIFACT_LAYOUT_TEMPLATE)
        if panel_semantics is None or layout is None:
            raise ValueError("panel_semantics and layout_template artifacts are required")

        scene = _get_scene(db, scene_id)
        story = db.get(Story, scene.story_id)
        characters = _list_characters(db, scene.story_id)
        reference_char_ids = _character_ids_with_reference_images(db, scene.story_id)
        panel_count = _panel_count(panel_semantics.payload)
        layout_panels = layout.payload.get("panels")
        layout_count = len(layout_panels) if isinstance(layout_panels, list) else None
        if layout_count is not None and panel_count != layout_count:
            raise ValueError(
                f"Layout/template panel count mismatch: panel_semantics={panel_count} layout={layout_count}"
            )

        prompt = prompt_override
        if not prompt:
            prompt = _compile_prompt(
                panel_semantics=panel_semantics.payload,
                layout_template=layout.payload,
                style_id=style_id,
                characters=characters,
                reference_char_ids=reference_char_ids,
                story_style=(story.default_story_style if story else None),
            )

        payload = {
            "prompt": prompt,
            "style_id": style_id,
            "layout_template_id": layout.payload.get("template_id"),
            "panel_count": panel_count,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_SPEC, payload=payload)


def run_image_renderer(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
    reason: str | None = None,
):
    with trace_span("graph.image_renderer", scene_id=str(scene_id), reason=reason):
        svc = ArtifactService(db)
        render_spec = svc.get_latest_artifact(scene_id, ARTIFACT_RENDER_SPEC)
        if render_spec is None:
            raise ValueError("render_spec artifact not found")

        prompt = render_spec.payload.get("prompt")
        if not prompt:
            raise ValueError("render_spec is missing prompt")

        reference_images = None
        if gemini is not None:
            scene = _get_scene(db, scene_id)
            reference_images = _load_character_reference_images(db, scene.story_id)

        image_bytes, mime_type, metadata = _render_image_from_prompt(
            prompt,
            gemini=gemini,
            reference_images=reference_images,
        )

        store = LocalMediaStore(root_dir=settings.media_root, url_prefix=settings.media_url_prefix)
        _, url = store.save_image_bytes(image_bytes=image_bytes, mime_type=mime_type)

        image = ImageService(db).create_image(
            image_url=url,
            artifact_id=None,
            metadata=metadata,
        )

        payload = {
            "image_id": str(image.image_id),
            "image_url": image.image_url,
            "mime_type": mime_type,
            "model": metadata.get("model"),
            "request_id": metadata.get("request_id"),
            "usage": metadata.get("usage"),
            "prompt_sha256": render_spec.payload.get("prompt_sha256"),
            "prompt": prompt,
            "approved": False,
            "reason": reason,
        }
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_RENDER_RESULT, payload=payload)


def run_blind_test_evaluator(
    db: Session,
    scene_id: uuid.UUID,
    gemini: GeminiClient | None = None,
):
    with trace_span("graph.blind_test_evaluator", scene_id=str(scene_id)):
        svc = ArtifactService(db)
        scene = _get_scene(db, scene_id)
        panel_semantics = svc.get_latest_artifact(scene_id, ARTIFACT_PANEL_SEMANTICS)
        if panel_semantics is None:
            raise ValueError("panel_semantics artifact not found")

        semantics_text = _panel_semantics_text(panel_semantics.payload)
        reconstructed = semantics_text
        score = _rough_similarity(scene.source_text, semantics_text)
        comparison = f"Similarity score: {score:.2f}"
        scores = None
        failure_points = []
        repair_suggestions = []

        if gemini is not None:
            # Try two-stage blind test process
            two_stage_success = False

            # Stage 1: Blind reader reconstructs story
            blind_reading = _maybe_json_from_gemini(
                gemini,
                _prompt_blind_reader(panel_semantics.payload),
            )

            if blind_reading and isinstance(blind_reading, dict):
                reconstructed = blind_reading.get("reconstructed_story", reconstructed)

                # Stage 2: Comparator scores the reconstruction
                comparison_result = _maybe_json_from_gemini(
                    gemini,
                    _prompt_comparator(scene.source_text, blind_reading),
                )

                if comparison_result and isinstance(comparison_result, dict):
                    two_stage_success = True
                    comparison = comparison_result.get("comparison", comparison)
                    scores = comparison_result.get("scores")
                    score = float(comparison_result.get("weighted_score", score))
                    failure_points = comparison_result.get("failure_points", [])
                    repair_suggestions = comparison_result.get("repair_suggestions", [])

            # Fallback to single-prompt if two-stage failed
            if not two_stage_success:
                llm = _maybe_json_from_gemini(
                    gemini,
                    _prompt_blind_test(scene.source_text, panel_semantics.payload),
                )
                if isinstance(llm, dict):
                    reconstructed = llm.get("reconstructed_story", reconstructed)
                    comparison = llm.get("comparison", comparison)
                    score = float(llm.get("score", score))
                    scores = llm.get("scores")
                    failure_points = llm.get("failure_points", [])
                    repair_suggestions = llm.get("repair_suggestions", [])

        payload = {
            "reconstructed_story": reconstructed,
            "comparison": comparison,
            "score": score,
            "passed": score >= 0.25,
            "scores": scores,
            "failure_points": failure_points,
            "repair_suggestions": repair_suggestions,
        }
        return svc.create_artifact(scene_id=scene_id, type=ARTIFACT_BLIND_TEST_REPORT, payload=payload)


def run_dialogue_extractor(db: Session, scene_id: uuid.UUID):
    with trace_span("graph.dialogue_extractor", scene_id=str(scene_id)):
        scene = _get_scene(db, scene_id)
        suggestions = _extract_dialogue_suggestions(scene.source_text)
        payload = {"suggestions": suggestions}
        return ArtifactService(db).create_artifact(
            scene_id=scene_id, type=ARTIFACT_DIALOGUE_SUGGESTIONS, payload=payload
        )


def compile_visual_plan_bundle(
    scenes: list[dict],
    characters: list[dict],
    story_style: str | None = None,
) -> list[dict]:
    plans: list[dict] = []
    total = len(scenes)
    for scene in scenes:
        summary = scene.get("summary") or _summarize_text(scene.get("source_text", ""))
        importance = scene.get("scene_importance")
        if not importance:
            idx = scene.get("scene_index") or 1
            if idx == 1:
                importance = "setup"
            elif total and idx == total:
                importance = "cliffhanger"
            else:
                importance = "build"
        plan = {
            "scene_index": scene.get("scene_index"),
            "summary": summary,
            "beats": _extract_beats(scene.get("source_text", ""), max_beats=3),
            "must_show": _extract_must_show(scene.get("source_text", "")),
            "scene_importance": importance,
            "characters": [c.get("name") for c in characters if c.get("name")],
            "story_style": story_style,
        }
        plans.append(plan)
    return plans


def _get_scene(db: Session, scene_id: uuid.UUID) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError("scene not found")
    return scene


def _list_characters(db: Session, story_id: uuid.UUID) -> list[Character]:
    return list(db.execute(select(Character).where(Character.story_id == story_id)).scalars().all())


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
    )
    panels = panel_semantics.get("panels", []) or []
    panel_count = len(panels)

    # Build concise character lines (reference images provide detailed appearance)
    identity_lines = []
    codes = _character_codes(characters)
    for c in characters:
        code = codes.get(c.character_id)
        role = c.role or "character"
        char_lines = [f"  - {code} ({c.name}) [{role}]"]
        if c.character_id in reference_char_ids:
            if c.base_outfit:
                char_lines.append(f"    Outfit: {c.base_outfit}")
        else:
            if c.base_outfit:
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
    stmt = (
        select(CharacterReferenceImage.character_id)
        .join(Character, CharacterReferenceImage.character_id == Character.character_id)
        .where(
            Character.story_id == story_id,
            CharacterReferenceImage.approved.is_(True),
            CharacterReferenceImage.ref_type == "face",
        )
        .distinct()
    )
    return set(db.execute(stmt).scalars().all())


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
) -> dict:
    if not panel_semantics or not characters:
        return panel_semantics

    codes = _character_codes(characters)
    name_map: dict[str, dict[str, str]] = {}
    for c in characters:
        code = codes.get(c.character_id, "CHAR_X")
        base = f"{code} ({c.name})"
        if c.character_id in reference_char_ids:
            parts = [base, "matching reference image"]
            if c.base_outfit:
                parts.append(f"wearing {c.base_outfit}")
            label = ", ".join(parts)
        else:
            parts = [base]
            if c.base_outfit:
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

    image_bytes, mime_type = gemini.generate_image(prompt=prompt, reference_images=reference_images)
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
    stmt = (
        select(CharacterReferenceImage)
        .join(Character, CharacterReferenceImage.character_id == Character.character_id)
        .where(
            Character.story_id == story_id,
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


def _repair_json_with_llm(gemini: GeminiClient, malformed_text: str, expected_schema: str | None = None) -> dict | None:
    """Attempt to repair malformed JSON using LLM as a last resort."""
    schema_hint = ""
    if expected_schema:
        schema_hint = f"\n\nExpected schema:\n{expected_schema}"

    repair_prompt = f"""{SYSTEM_PROMPT_JSON}

The following text was supposed to be valid JSON but failed to parse.
Fix it and return ONLY the corrected JSON. No explanations.{schema_hint}

Malformed text:
{malformed_text[:2000]}"""

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

    return f"""{GLOBAL_CONSTRAINTS}

Analyze the following scene and extract its narrative intent for webtoon adaptation.

OUTPUT SCHEMA (return exactly this structure):
{{
  "logline": "One sentence describing the core action/conflict of this scene",
  "pacing": "slow_burn|normal|fast|impact",
  "emotional_arc": {{
    "start": "emotion at scene start (e.g., calm, tense, happy)",
    "peak": "strongest emotion in scene",
    "end": "emotion at scene end"
  }},
  "visual_motifs": ["list of 2-4 key visual elements to emphasize"],
  "summary": "2-3 sentence summary of the scene",
  "beats": ["list of 2-4 key story beats in order"],
  "setting": "primary location/environment or null",
  "characters": ["list of characters present in scene"]
}}

PACING GUIDE:
- slow_burn: introspective, atmospheric, lingering on emotion
- normal: standard narrative flow, balanced action and dialogue
- fast: rapid cuts, urgency, action-driven
- impact: dramatic reveals, emotional climax, single powerful moment

WHAT MAKES GOOD BEATS:
- Each beat should be a single discrete visual moment
- Beats should follow cause-and-effect logic
- Include character reactions, not just actions
- Balance dialogue beats with action/reaction beats

Genre: {genre_text}
Known characters: {char_list}

Scene text:
{scene_text}
"""


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
"""

    return f"""{GLOBAL_CONSTRAINTS}

Create a panel plan for a {panel_count}-panel webtoon sequence.
{intent_block}
{importance_block}
Characters: {char_list}
{qc_block}
VALID GRAMMAR IDs (use ONLY these):
1. establishing - Wide shot showing environment and context (REQUIRED for panel 1)
2. dialogue_medium - Two-shot or medium shot for conversation
3. emotion_closeup - Close-up on face for emotional impact (use sparingly)
4. action - Dynamic movement or physical action
5. reaction - Character responding to prior event
6. object_focus - Important object or detail in focus
7. reveal - Dramatic reveal of character, object, or information
8. impact_silence - Dramatic pause with minimal elements, powerful negative space

STORY FUNCTION OPTIONS:
- setup: establishes context or situation
- dialogue: conversation or verbal exchange
- emotion: emotional beat or reaction
- action: physical action or movement
- reaction: response to prior event
- focus: draws attention to important element
- climax: peak dramatic moment
- transition: bridges between scenes or beats

OUTPUT SCHEMA:
{{
  "panels": [
    {{
      "panel_index": 1,
      "grammar_id": "establishing",
      "story_function": "setup",
      "beat_summary": "Brief description of what happens in this panel"
    }}
  ]
}}

Scene text:
{scene_text}
"""


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

    return f"""{GLOBAL_CONSTRAINTS}

Fill in DETAILED visual semantics for each panel. Each description must be 100-150 words minimum.
This will be used for AI image generation - be SPECIFIC, VISUAL, and COMPLETE.
{intent_block}
{genre_block}
CHARACTERS (use these identity_lines for consistency):
{char_section}

PANEL PLAN:
{plan_section}

Layout: {layout_template.get('layout_text', 'vertical scroll')}

**VISUAL PROMPT FORMULA (use this structure for each description):**
[shot_type], vertical 9:16 webtoon panel, [composition with character % of frame],
[environment with 5+ specific details: architecture, furniture, props, weather, background activity],
[lighting conditions: source, quality, color temperature, shadows],
[character placement: position in frame, posture, action, expression],
[atmosphere keywords], Korean manhwa style

**GRAMMAR-SPECIFIC REQUIREMENTS:**
- establishing: Wide shot, characters 20-30% of frame, 5+ environment details, show the WORLD
- dialogue_medium: Medium shot, characters 40-45%, space for speech bubbles, show relationship
- emotion_closeup: Extreme close-up, character 50%+, single face, SPECIFIC emotion with physical tells
- action: Dynamic angle (low/high/dutch), motion blur hint, action verb, 35-40% character
- reaction: Focus on reacting character, clear emotion in eyes/expression, medium shot
- object_focus: Macro or close-up, object centered, minimal background, symbolic lighting
- reveal: High contrast, dramatic single-source lighting, subject entering or being unveiled
- impact_silence: Minimal elements, 70%+ negative space, frozen moment, stark composition

**ENVIRONMENT DETAILS MUST INCLUDE (5+ per panel):**
1. Architecture/space (walls, windows, ceiling, floor material)
2. Furniture/major objects (tables, chairs, counters)
3. Small props (cups, phones, books, bags)
4. Lighting source (natural light, lamps, overhead, neon)
5. Background activity (other people, movement, weather visible through windows)
6. Atmosphere indicators (steam, dust motes, rain, shadows)

**DIALOGUE REQUIREMENTS (CRITICAL - This carries the story):**
Minimum dialogue per panel type:
- Establishing shots: 0-2 lines (can be silent)
- Normal dialogue panels: 5-8 lines MINIMUM (not just 1-2!)
- Key emotional panels: 8-12 lines with reactions and subtext
- Action panels: 2-4 lines for context

**Why rich dialogue matters:**
- Without enough dialogue, the story feels incomplete
- Dialogue shows character dynamics, not just plot points
- Each line must reveal character OR advance plot OR create emotion

**CONVERSATION BUILDING PATTERNS:**
1. Opening Exchange (3-4 lines):
   "Question" → "Response" → "Follow-up" → "Reaction"

2. Building Tension (5-6 lines):
   "Statement" → "Challenge" → "Explanation" → "Disbelief" → "Confirmation"

3. Emotional Peak (7-8 lines):
   "Confession" → "Shock" → "Clarification" → "Emotional response" → "Deeper reveal" → "Processing"

4. Include: pauses, hesitation, interruptions for realism
5. Last line of dialogue should have impact or create anticipation
6. Show distinct character voices (how they speak differently)

VALID CAMERA VALUES: extreme_closeup, closeup, medium_closeup, medium, medium_full, full, wide, establishing
VALID GAZE VALUES: at_other, at_object, down, away, toward_path, camera

OUTPUT SCHEMA:
{{
  "panels": [
    {{
      "panel_index": 1,
      "grammar_id": "establishing",
      "camera": "wide",
      "character_frame_percentage": 25,
      "focus_on": "environment with characters",
      "description": "150+ word detailed visual description following the formula above",
      "characters": [
        {{
          "name": "Character Name",
          "position": "left|center|right|background",
          "frame_position": "lower_third|center|upper_third",
          "gaze": "at_other|at_object|down|away|toward_path|camera",
          "expression": "specific emotion with physical description",
          "action": "specific action verb + body language"
        }}
      ],
      "dialogue": [
        {{"character": "Name", "text": "Dialogue line", "order": 1}},
        {{"character": "Name", "text": "Response", "order": 2}}
      ],
      "environment": {{
        "location": "specific place name",
        "architecture": "walls, windows, ceiling details",
        "furniture": "major objects in space",
        "props": ["list of visible small objects"],
        "background_activity": "what's happening in background"
      }},
      "lighting": {{
        "source": "natural/artificial/mixed",
        "quality": "soft/harsh/dramatic",
        "color_temperature": "warm/cool/neutral",
        "shadows": "description of shadow patterns"
      }},
      "atmosphere_keywords": ["list", "of", "mood", "words"]
    }}
  ]
}}

Scene text:
{scene_text}
"""


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

    return f"""{SYSTEM_PROMPT_JSON}

You are a blind reader who has NEVER seen the original story.
Based ONLY on the panel descriptions below, reconstruct what story is being told.

Panel descriptions:
{chr(10).join(panels_desc)}

OUTPUT SCHEMA:
{{
  "reconstructed_story": "Your reconstruction of the story based only on the panels (2-4 sentences)",
  "identified_characters": ["List of character names you can identify"],
  "plot_points": ["List of plot points you understood"],
  "unclear_elements": ["List of anything confusing or unclear"]
}}
"""


def _prompt_comparator(original_text: str, blind_reading: dict) -> str:
    """Stage 2: Compare blind reading to original for scoring."""
    return f"""{SYSTEM_PROMPT_JSON}

Compare the blind reader's reconstruction to the original story.

ORIGINAL STORY:
{original_text}

BLIND READER'S RECONSTRUCTION:
{blind_reading.get('reconstructed_story', 'N/A')}

IDENTIFIED CHARACTERS: {blind_reading.get('identified_characters', [])}
PLOT POINTS UNDERSTOOD: {blind_reading.get('plot_points', [])}
UNCLEAR ELEMENTS: {blind_reading.get('unclear_elements', [])}

SCORING RUBRIC:
- plot_recall (40%): Did the reader understand the main events?
- emotional_alignment (30%): Did the reader feel the intended emotions?
- character_identifiability (30%): Could the reader identify who is who?

OUTPUT SCHEMA:
{{
  "scores": {{
    "plot_recall": 0.0-1.0,
    "emotional_alignment": 0.0-1.0,
    "character_identifiability": 0.0-1.0
  }},
  "weighted_score": 0.0-1.0,
  "comparison": "Brief comparison of original vs reconstruction",
  "failure_points": ["List specific panels or elements that failed to communicate"],
  "repair_suggestions": ["Specific actionable fixes for failed panels"]
}}
"""


def _prompt_blind_test(scene_text: str, panel_semantics: dict) -> str:
    """Fallback single-prompt blind test (used if two-stage fails)."""
    panels_desc = []
    for p in panel_semantics.get("panels", []):
        desc = f"Panel {p.get('panel_index')}: {p.get('description', '')}"
        dialogue = p.get("dialogue", [])
        if dialogue:
            desc += f" Dialogue: {' '.join(dialogue)}"
        panels_desc.append(desc)

    return f"""{SYSTEM_PROMPT_JSON}
{GLOBAL_CONSTRAINTS}

Evaluate how well the panel descriptions convey the original story.

ORIGINAL STORY:
{scene_text}

PANEL DESCRIPTIONS:
{chr(10).join(panels_desc)}

SCORING RUBRIC:
- plot_recall (40%): Do panels capture main events?
- emotional_alignment (30%): Do panels convey intended emotions?
- character_identifiability (30%): Can characters be identified?

OUTPUT SCHEMA:
{{
  "reconstructed_story": "What story would a reader understand from panels alone (2-4 sentences)",
  "comparison": "How well panels match original",
  "score": 0.0-1.0,
  "scores": {{
    "plot_recall": 0.0-1.0,
    "emotional_alignment": 0.0-1.0,
    "character_identifiability": 0.0-1.0
  }},
  "failure_points": ["Panels or elements that fail to communicate"],
  "repair_suggestions": ["Specific fixes for failed panels"]
}}
"""


# ---------------------------------------------------------------------------
# LLM-Enhanced Character Functions
# ---------------------------------------------------------------------------

def _prompt_character_extraction(source_text: str, max_characters: int) -> str:
    """Prompt for LLM-based character extraction."""
    return f"""{SYSTEM_PROMPT_JSON}
{GLOBAL_CONSTRAINTS}

Extract only the IMPORTANT characters from the following story text.
Include explicitly named characters and implied characters ONLY if they are plot-relevant or recurring.
Do NOT include incidental background roles (e.g., movers, clerks, passersby) unless they directly affect the plot.

Rules:
- Extract up to {max_characters} characters
- Include evidence quotes showing where each character appears
- Assign roles: "main" for central characters (max 2), "secondary" for others
- For implied characters, create a descriptive name (e.g., "Jina's Mother" not just "mom")

OUTPUT SCHEMA:
{{
  "characters": [
    {{
      "name": "Character name",
      "role": "main|secondary",
      "evidence_quotes": ["Quote from text showing this character"],
      "implied": false,
      "relationship_to_main": "relationship if applicable or null"
    }}
  ]
}}

Story text:
{source_text}
"""


def _prompt_character_normalization(characters: list[dict], source_text: str) -> str:
    """Prompt for LLM-based character enrichment with Korean manhwa aesthetics."""
    char_list = json.dumps(characters, indent=2)

    return f"""{SYSTEM_PROMPT_JSON}
{GLOBAL_CONSTRAINTS}

Enrich the following character profiles with DETAILED visual descriptions for Korean webtoon/manhwa rendering.
Use context clues from the story to infer appearance. Apply Korean manhwa aesthetic standards.

**CRITICAL: These descriptions will be used for AI image generation. Be SPECIFIC and VISUAL.**

Current characters:
{char_list}

Story context:
{source_text[:1500]}

**AGE-BASED VISUAL STANDARDS (Korean Manhwa Style):**

MALE CHARACTERS:
- child (under 12): Chibi proportions 1:3, round cherubic face, large expressive eyes, playful posture
- teen (13-19): Soft angular face, slender graceful build, flower-boy aesthetic, 170-178cm, school uniform or streetwear
- young_adult (20-35): Korean male lead aesthetic, refined jawline, tall slender 180-188cm, willowy model proportions, soft side-part hair
- middle_aged (40-55): Distinguished refined features, subtle grey at temples, 178-185cm, professional attire
- elderly (60+): Gentle wisdom lines, silver/white hair, 170-175cm, dignified cardigan or hanbok

FEMALE CHARACTERS:
- child (under 12): Chibi proportions 1:3, oversized sparkly eyes, rosy plump cheeks, cute pigtails/bob
- teen (13-19): Large doe eyes, slender figure, 160-170cm, graceful youthful posture
- young_adult (20-35): Statuesque figure over 165cm, long legs exceeding torso, hourglass silhouette, flawless skin
- middle_aged (40-55): Refined beauty with subtle lines, elegant bob/waves, 160-170cm, professional or sophisticated fashion
- elderly (60+): Smile lines showing wisdom, grey elegant updo, 155-165cm, traditional hanbok or cardigan sets

For each character, provide:
- gender: male|female|unknown
- age_range: child|teen|young_adult|adult|middle_aged|elderly
- appearance:
  - hair: color, style, length (be specific: "soft side-swept black bangs" not just "black hair")
  - face: features, expression tendency (e.g., "gentle angular jawline, warm expressive eyes")
  - build: body type, height, proportions (e.g., "slender elegant build, 180cm, willowy silhouette")
- outfit: typical clothing with detail (e.g., "casual cream sweater, fitted dark jeans, clean white sneakers")
- identity_line: Single comprehensive line for artist (150+ characters)

**IDENTITY LINE FORMAT:**
"[age_range] [ethnicity] [gender], [hair description], [face/expression], [build/height], [typical outfit], [manhwa style note]"

**GOOD EXAMPLE:**
"early_20s Korean female, long flowing black hair with soft waves, large expressive doe eyes with delicate lashes, tall statuesque figure 168cm with elegant long legs, cream knit sweater and high-waisted jeans, authentic webtoon romance female lead aesthetic"

**BAD EXAMPLE (too vague):**
"young woman with dark hair, normal build, casual clothes"

OUTPUT SCHEMA:
{{
  "characters": [
    {{
      "name": "Character name",
      "role": "main|secondary",
      "description": "Brief personality/role description",
      "gender": "male|female|unknown",
      "age_range": "young_adult",
      "appearance": {{
        "hair": "detailed hair description with color, style, length",
        "face": "facial features and typical expression",
        "build": "body type, height in cm, proportions"
      }},
      "outfit": "detailed typical outfit description",
      "identity_line": "Complete 150+ character identity line for artist reference"
    }}
  ]
}}
"""


def compute_character_profiles_llm(
    source_text: str,
    max_characters: int = 6,
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """
    LLM-enhanced character extraction with fallback to heuristic.
    Extracts both explicit and implied characters with evidence.
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
    """
    LLM-enhanced character normalization with appearance details.
    Falls back to heuristic normalization if LLM fails.
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


# ---------------------------------------------------------------------------
# LLM-Enhanced Visual Plan Compiler
# ---------------------------------------------------------------------------

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

    return f"""{SYSTEM_PROMPT_JSON}
{GLOBAL_CONSTRAINTS}

Convert the following scenes into visual beats for webtoon adaptation.
Each scene should have 2-6 visual beats depending on complexity.

Story style: {story_style or 'general'}

Characters:
{chr(10).join(char_identities)}

Scenes:
{chr(10).join(scenes_block)}

For each scene, identify:
1. Visual beats (discrete visual moments that can be drawn)
2. Characters involved in each beat
3. Environment/setting for each beat
4. Key objects that must be shown
5. Emotional tone of each beat
6. Draft dialogue if applicable
7. Scene importance tag (setup|build|climax|release|cliffhanger)

Also extract global_environment_anchors: recurring locations or visual elements for consistency.

OUTPUT SCHEMA:
{{
  "global_environment_anchors": [
    {{
      "name": "location name",
      "description": "visual description for consistency",
      "appears_in_scenes": [1, 2]
    }}
  ],
  "scene_plans": [
    {{
      "scene_index": 1,
      "summary": "scene summary",
      "scene_importance": "setup|build|climax|release|cliffhanger",
      "beats": [
        {{
          "beat_index": 1,
          "what_happens": "description of the visual moment",
          "characters_involved": ["Character Name"],
          "environment": "where this happens",
          "key_objects": ["important objects to show"],
          "emotional_tone": "emotion of this beat",
          "dialogue_draft": ["draft dialogue if any"]
        }}
      ],
      "must_show": ["critical visual elements for this scene"]
    }}
  ]
}}
"""


def compile_visual_plan_bundle_llm(
    scenes: list[dict],
    characters: list[dict],
    story_style: str | None = None,
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """
    LLM-enhanced visual plan compilation with beat extraction.
    Falls back to heuristic compilation if LLM fails.
    """
    if gemini is None:
        return compile_visual_plan_bundle(scenes, characters, story_style)

    prompt = _prompt_visual_plan(scenes, characters, story_style)
    result = _maybe_json_from_gemini(gemini, prompt)

    if result and isinstance(result.get("scene_plans"), list):
        plans = []
        global_anchors = result.get("global_environment_anchors", [])

        for scene_plan in result["scene_plans"]:
            scene_idx = scene_plan.get("scene_index")
            # Find matching input scene
            matching_scene = next((s for s in scenes if s.get("scene_index") == scene_idx), None)

            plan = {
                "scene_index": scene_idx,
                "summary": scene_plan.get("summary", ""),
                "scene_importance": scene_plan.get("scene_importance"),
                "beats": scene_plan.get("beats", []),
                "must_show": scene_plan.get("must_show", []),
                "characters": [c.get("name") for c in characters if c.get("name")],
                "story_style": story_style,
                "global_environment_anchors": global_anchors,
            }

            # Preserve source_text from original scene if available
            if matching_scene:
                plan["source_text"] = matching_scene.get("source_text", "")

            plans.append(plan)

        if plans:
            return plans

    # Fallback to heuristic
    logger.info("Falling back to heuristic visual plan compilation")
    return compile_visual_plan_bundle(scenes, characters, story_style)
