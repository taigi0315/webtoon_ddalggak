from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.telemetry import trace_span
from app.db.models import Character, Scene, Story
from app.graphs import nodes
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient


class StoryBuildState(TypedDict, total=False):
    db: Session
    story_id: uuid.UUID
    story_text: str
    max_scenes: int
    max_characters: int
    panel_count: int
    allow_append: bool
    story_style: str | None
    image_style: str | None
    planning_mode: str
    gemini: GeminiClient | None

    scenes: list[dict]
    characters: list[dict]
    scene_ids: list[str]
    character_ids: list[str]
    visual_plan_bundle: list[dict]
    visual_plan_artifact_ids: list[str]
    planning_artifact_ids: list[dict]
    blind_test_report_ids: list[str]
    progress: dict


def _total_steps(planning_mode: str | None) -> int:
    return 8 if planning_mode == "full" else 5


def _persist_progress(state: StoryBuildState, progress: dict) -> None:
    story_id = state.get("story_id")
    if not story_id:
        return
    db: Session = state["db"]
    story = db.get(Story, story_id)
    if story is None:
        return
    payload = dict(progress)
    payload.setdefault("total_steps", _total_steps(state.get("planning_mode")))
    story.progress = payload
    story.generation_status = "running"
    story.generation_error = None
    story.progress_updated_at = datetime.utcnow()
    db.add(story)
    db.commit()


def _node_validate_inputs(state: StoryBuildState) -> dict[str, Any]:
    max_scenes = max(1, min(int(state.get("max_scenes") or 6), 30))
    max_characters = max(1, min(int(state.get("max_characters") or 6), 20))
    panel_count = max(1, min(int(state.get("panel_count") or 3), 12))

    story_style = state.get("story_style")
    image_style = state.get("image_style")

    story_id = state.get("story_id")
    if story_id:
        story = state["db"].get(Story, story_id)
        if story is not None:
            story_style = story_style or story.default_story_style
            image_style = image_style or story.default_image_style

    progress = {
        "max_scenes": max_scenes,
        "max_characters": max_characters,
        "panel_count": panel_count,
        "story_style": story_style,
        "image_style": image_style,
        "progress": {"current_node": "ValidateStoryInputs", "message": "Validating inputs...", "step": 1},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_scene_splitter(state: StoryBuildState) -> dict[str, Any]:
    scenes_text = nodes.compute_scene_chunker(state.get("story_text", ""), max_scenes=state.get("max_scenes", 6))
    scenes: list[dict] = []
    for idx, text in enumerate(scenes_text, start=1):
        summary = _summarize_text(text)
        scenes.append(
            {
                "scene_index": idx,
                "title": f"Scene {idx}",
                "summary": summary,
                "source_text": text,
            }
        )
    progress = {
        "scenes": scenes,
        "progress": {
            "current_node": "SceneSplitter",
            "message": f"Splitting story into scenes ({len(scenes)}/{state.get('max_scenes')})...",
            "step": 2,
        },
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_llm_character_extractor(state: StoryBuildState) -> dict[str, Any]:
    profiles = nodes.compute_character_profiles_llm(
        state.get("story_text", ""),
        max_characters=state.get("max_characters", 6),
        gemini=state.get("gemini"),
    )
    progress = {
        "characters": profiles,
        "progress": {"current_node": "LLMCharacterExtractor", "message": "Extracting characters...", "step": 3},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_llm_character_normalizer(state: StoryBuildState) -> dict[str, Any]:
    profiles = nodes.normalize_character_profiles_llm(
        state.get("characters", []),
        source_text=state.get("story_text", ""),
        gemini=state.get("gemini"),
    )
    progress = {
        "characters": profiles,
        "progress": {"current_node": "LLMCharacterProfileNormalizer", "message": "Normalizing characters...", "step": 4},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_persist_story_bundle(state: StoryBuildState) -> dict[str, Any]:
    db = state["db"]
    story_id = state.get("story_id")
    if story_id is None:
        raise ValueError("story_id is required to persist scenes")

    allow_append = bool(state.get("allow_append"))
    existing_scenes = list(db.execute(select(Scene).where(Scene.story_id == story_id)).scalars().all())
    if existing_scenes and not allow_append:
        raise ValueError("story already has scenes; set allow_append to true to append more")

    existing_chars = list(db.execute(select(Character).where(Character.story_id == story_id)).scalars().all())
    existing_by_name = {c.name.strip().lower(): c for c in existing_chars if c.name}
    existing_codes = {c.canonical_code for c in existing_chars if c.canonical_code}

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

    def _next_character_code() -> str:
        idx = 0
        while True:
            code = _code_from_index(idx)
            if code not in existing_codes:
                existing_codes.add(code)
                return code
            idx += 1

    character_ids: list[str] = []
    for profile in state.get("characters", []):
        name = str(profile.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        appearance = profile.get("appearance") if isinstance(profile.get("appearance"), dict) else None
        hair_description = profile.get("hair_description")
        if hair_description is None and appearance:
            hair_description = appearance.get("hair")
        base_outfit = profile.get("base_outfit") or profile.get("outfit")
        if key in existing_by_name:
            existing_char = existing_by_name[key]
            if not existing_char.canonical_code:
                existing_char.canonical_code = _next_character_code()
            if profile.get("gender") and not existing_char.gender:
                existing_char.gender = profile.get("gender")
            if profile.get("age_range") and not existing_char.age_range:
                existing_char.age_range = profile.get("age_range")
            if appearance and not existing_char.appearance:
                existing_char.appearance = appearance
            if profile.get("identity_line") and not existing_char.identity_line:
                existing_char.identity_line = profile.get("identity_line")
            if hair_description and not existing_char.hair_description:
                existing_char.hair_description = hair_description
            if base_outfit and not existing_char.base_outfit:
                existing_char.base_outfit = base_outfit
            character_ids.append(str(existing_char.character_id))
            continue
        character = Character(
            story_id=story_id,
            canonical_code=_next_character_code(),
            name=name,
            description=profile.get("description"),
            role=profile.get("role") or "secondary",
            gender=profile.get("gender"),
            age_range=profile.get("age_range"),
            appearance=appearance,
            hair_description=hair_description,
            base_outfit=base_outfit,
            identity_line=profile.get("identity_line"),
        )
        db.add(character)
        db.flush()
        character_ids.append(str(character.character_id))

    scene_ids: list[str] = []
    for scene in state.get("scenes", []):
        row = Scene(
            story_id=story_id,
            source_text=scene.get("source_text") or "",
        )
        db.add(row)
        db.flush()
        scene_ids.append(str(row.scene_id))

    db.commit()

    progress = {
        "scene_ids": scene_ids,
        "character_ids": character_ids,
        "progress": {"current_node": "PersistStoryBundle", "message": "Saving story bundle...", "step": 5},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_llm_visual_plan_compiler(state: StoryBuildState) -> dict[str, Any]:
    plans = nodes.compile_visual_plan_bundle_llm(
        scenes=state.get("scenes", []),
        characters=state.get("characters", []),
        story_style=state.get("story_style"),
        gemini=state.get("gemini"),
    )
    db = state["db"]
    svc = ArtifactService(db)
    plan_ids: list[str] = []
    for scene_id, plan in zip(state.get("scene_ids", []), plans, strict=False):
        scene_uuid = uuid.UUID(scene_id)
        artifact = svc.create_artifact(scene_id=scene_uuid, type=nodes.ARTIFACT_VISUAL_PLAN, payload=plan)
        plan_ids.append(str(artifact.artifact_id))
        if isinstance(plan, dict) and plan.get("scene_importance"):
            scene = db.get(Scene, scene_uuid)
            if scene is not None:
                scene.scene_importance = str(plan.get("scene_importance"))

    db.commit()
    progress = {
        "visual_plan_bundle": plans,
        "visual_plan_artifact_ids": plan_ids,
        "progress": {"current_node": "LLMVisualPlanCompiler", "message": "Converting story to visual beats...", "step": 6},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_per_scene_planning_loop(state: StoryBuildState) -> dict[str, Any]:
    planning_artifacts: list[dict] = []
    scene_ids = state.get("scene_ids", [])
    total = len(scene_ids)
    gemini = state.get("gemini")
    for idx, scene_id in enumerate(scene_ids, start=1):
        scene_uuid = uuid.UUID(scene_id)
        planning_artifacts.append(
            {
                "scene_id": scene_id,
                "scene_intent": str(
                    nodes.run_scene_intent_extractor(state["db"], scene_uuid, gemini=gemini).artifact_id
                ),
                "panel_plan": str(
                    nodes.run_panel_plan_generator(
                        state["db"], scene_uuid, panel_count=state.get("panel_count", 3), gemini=gemini
                    ).artifact_id
                ),
                "panel_plan_normalized": str(nodes.run_panel_plan_normalizer(state["db"], scene_uuid).artifact_id),
                "layout_template": str(nodes.run_layout_template_resolver(state["db"], scene_uuid).artifact_id),
                "panel_semantics": str(
                    nodes.run_panel_semantic_filler(state["db"], scene_uuid, gemini=gemini).artifact_id
                ),
                "qc_report": str(nodes.run_qc_checker(state["db"], scene_uuid).artifact_id),
                "dialogue_suggestions": str(nodes.run_dialogue_extractor(state["db"], scene_uuid).artifact_id),
            }
        )
        state["progress"] = {
            "current_node": "PerScenePlanningLoop",
            "message": f"Planning scene {idx}/{total}...",
            "step": 7,
        }
        _persist_progress(state, state["progress"])

    return {"planning_artifact_ids": planning_artifacts}


def _node_blind_test_runner(state: StoryBuildState) -> dict[str, Any]:
    report_ids: list[str] = []
    gemini = state.get("gemini")
    for scene_id in state.get("scene_ids", []):
        artifact = nodes.run_blind_test_evaluator(state["db"], uuid.UUID(scene_id), gemini=gemini)
        report_ids.append(str(artifact.artifact_id))
    progress = {
        "blind_test_report_ids": report_ids,
        "progress": {"current_node": "BlindTestRunner", "message": "Running blind tests...", "step": 8},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _summarize_text(text: str, max_words: int = 32) -> str:
    words = re.findall(r"\w+", text)
    if not words:
        return ""
    return " ".join(words[:max_words])


def build_story_build_graph(planning_mode: str = "full"):
    graph = StateGraph(StoryBuildState)
    graph.add_node("validate_inputs", _node_validate_inputs)
    graph.add_node("scene_splitter", _node_scene_splitter)
    graph.add_node("llm_character_extractor", _node_llm_character_extractor)
    graph.add_node("llm_character_normalizer", _node_llm_character_normalizer)
    graph.add_node("persist_story_bundle", _node_persist_story_bundle)

    graph.set_entry_point("validate_inputs")
    graph.add_edge("validate_inputs", "scene_splitter")
    graph.add_edge("scene_splitter", "llm_character_extractor")
    graph.add_edge("llm_character_extractor", "llm_character_normalizer")
    graph.add_edge("llm_character_normalizer", "persist_story_bundle")

    if planning_mode == "full":
        graph.add_node("llm_visual_plan_compiler", _node_llm_visual_plan_compiler)
        graph.add_node("per_scene_planning", _node_per_scene_planning_loop)
        graph.add_node("blind_test_runner", _node_blind_test_runner)
        graph.add_edge("persist_story_bundle", "llm_visual_plan_compiler")
        graph.add_edge("llm_visual_plan_compiler", "per_scene_planning")
        graph.add_edge("per_scene_planning", "blind_test_runner")
        graph.add_edge("blind_test_runner", END)
    else:
        graph.add_edge("persist_story_bundle", END)

    return graph.compile()


def run_story_build_graph(
    db: Session,
    story_id: uuid.UUID,
    story_text: str,
    max_scenes: int = 6,
    max_characters: int = 6,
    panel_count: int = 3,
    allow_append: bool = False,
    story_style: str | None = None,
    image_style: str | None = None,
    gemini: GeminiClient | None = None,
    planning_mode: str = "full",
) -> StoryBuildState:
    if gemini is None:
        raise ValueError("Gemini client is required for story generation")
    if planning_mode not in {"full", "characters_only"}:
        raise ValueError("planning_mode must be 'full' or 'characters_only'")
    with trace_span("graph.story_build", story_id=str(story_id)):
        app = build_story_build_graph(planning_mode=planning_mode)
        state: StoryBuildState = {
            "db": db,
            "story_id": story_id,
            "story_text": story_text,
            "max_scenes": max_scenes,
            "max_characters": max_characters,
            "panel_count": panel_count,
            "allow_append": allow_append,
            "story_style": story_style,
            "image_style": image_style,
            "planning_mode": planning_mode,
            "gemini": gemini,
        }
        return app.invoke(state)
