"""Visual planning functions for story-to-scene conversion."""

from __future__ import annotations

import re

from ..utils import (
    logger,
    _summarize_text,
    _extract_beats,
    _extract_must_show,
    _split_sentences,
    _group_chunks,
    _maybe_json_from_gemini,
    _prompt_visual_plan,
    GeminiClient,
)


def compile_visual_plan_bundle(
    scenes: list[dict],
    characters: list[dict],
) -> list[dict]:
    """Compile visual plan bundle using heuristics.

    Args:
        scenes: List of scene dicts with source_text
        characters: List of character dicts

    Returns:
        List of visual plan dicts for each scene
    """
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
        }
        plans.append(plan)

    return plans


def compile_visual_plan_bundle_llm(
    scenes: list[dict],
    characters: list[dict],
    gemini: GeminiClient | None = None,
) -> list[dict]:
    """LLM-enhanced visual plan compilation with beat extraction.

    Args:
        scenes: List of scene dicts with source_text
        characters: List of character dicts
        gemini: Optional GeminiClient for LLM-based compilation

    Returns:
        List of visual plan dicts for each scene
    """
    if gemini is None:
        logger.error("visual_plan_compiler fail-fast: Gemini client missing")
        raise RuntimeError("visual_plan_compiler requires Gemini client (fallback disabled)")

    prompt = _prompt_visual_plan(scenes, characters)
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
                "global_environment_anchors": global_anchors,
            }

            # Preserve source_text from original scene if available
            if matching_scene:
                plan["source_text"] = matching_scene.get("source_text", "")

            plans.append(plan)

        if plans:
            return plans

    logger.error("visual_plan_compiler generation failed: invalid/empty Gemini JSON")
    raise RuntimeError("visual_plan_compiler failed: Gemini returned invalid JSON")


def compute_scene_chunker(source_text: str, max_scenes: int = 6) -> list[str]:
    """Split story text into scene chunks.

    Uses markers (Scene/Chapter/Part), paragraphs, or sentences.

    Args:
        source_text: Story text to split
        max_scenes: Maximum number of scenes to create

    Returns:
        List of scene text chunks
    """
    text = (source_text or "").strip()
    if not text:
        return []

    max_scenes = max(1, int(max_scenes))

    # Prefer explicit scene/section markers when present
    marker_split = re.split(r"\n(?=\s*(?:Scene|Chapter|Part)\b)", text, flags=re.IGNORECASE)
    marker_chunks = [p.strip() for p in marker_split if p.strip()]
    if len(marker_chunks) >= 2:
        return marker_chunks[:max_scenes]

    # Fall back to paragraph splitting
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if len(paragraphs) >= 2:
        return _group_chunks(paragraphs, max_scenes)

    # Fall back to sentence splitting
    sentences = _split_sentences(text)
    if not sentences:
        return [text]

    return _group_chunks(sentences, max_scenes)
