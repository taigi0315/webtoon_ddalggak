from __future__ import annotations

import re
import uuid
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

    return {
        "max_scenes": max_scenes,
        "max_characters": max_characters,
        "panel_count": panel_count,
        "story_style": story_style,
        "image_style": image_style,
        "progress": {"current_node": "ValidateStoryInputs", "message": "Validating inputs...", "step": 1},
    }


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
    return {
        "scenes": scenes,
        "progress": {
            "current_node": "SceneSplitter",
            "message": f"Splitting story into scenes ({len(scenes)}/{state.get('max_scenes')})...",
            "step": 2,
        },
    }


def _node_character_extractor(state: StoryBuildState) -> dict[str, Any]:
    profiles = nodes.compute_character_profiles_llm(
        state.get("story_text", ""),
        max_characters=state.get("max_characters", 6),
        gemini=state.get("gemini"),
    )
    return {
        "characters": profiles,
        "progress": {"current_node": "CharacterExtractor", "message": "Extracting characters...", "step": 3},
    }


def _node_character_normalizer(state: StoryBuildState) -> dict[str, Any]:
    profiles = nodes.normalize_character_profiles_llm(
        state.get("characters", []),
        source_text=state.get("story_text", ""),
        gemini=state.get("gemini"),
    )
    return {
        "characters": profiles,
        "progress": {"current_node": "CharacterProfileNormalizer", "message": "Normalizing characters...", "step": 4},
    }


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

    character_ids: list[str] = []
    for profile in state.get("characters", []):
        name = str(profile.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in existing_by_name:
            existing_char = existing_by_name[key]
            if profile.get("gender") and not existing_char.gender:
                existing_char.gender = profile.get("gender")
            if profile.get("age_range") and not existing_char.age_range:
                existing_char.age_range = profile.get("age_range")
            if profile.get("appearance") and not existing_char.appearance:
                existing_char.appearance = profile.get("appearance")
            if profile.get("identity_line") and not existing_char.identity_line:
                existing_char.identity_line = profile.get("identity_line")
            character_ids.append(str(existing_char.character_id))
            continue
        character = Character(
            story_id=story_id,
            name=name,
            description=profile.get("description"),
            role=profile.get("role") or "secondary",
            gender=profile.get("gender"),
            age_range=profile.get("age_range"),
            appearance=profile.get("appearance"),
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

    return {
        "scene_ids": scene_ids,
        "character_ids": character_ids,
        "progress": {"current_node": "PersistStoryBundle", "message": "Saving story bundle...", "step": 5},
    }


def _node_visual_plan_compiler(state: StoryBuildState) -> dict[str, Any]:
    plans = nodes.compile_visual_plan_bundle_llm(
        scenes=state.get("scenes", []),
        characters=state.get("characters", []),
        story_style=state.get("story_style"),
        gemini=state.get("gemini"),
    )
    svc = ArtifactService(state["db"])
    plan_ids: list[str] = []
    for scene_id, plan in zip(state.get("scene_ids", []), plans, strict=False):
        artifact = svc.create_artifact(scene_id=uuid.UUID(scene_id), type=nodes.ARTIFACT_VISUAL_PLAN, payload=plan)
        plan_ids.append(str(artifact.artifact_id))
    return {
        "visual_plan_bundle": plans,
        "visual_plan_artifact_ids": plan_ids,
        "progress": {"current_node": "StoryToVisualPlanCompiler", "message": "Converting story to visual beats...", "step": 6},
    }


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

    return {"planning_artifact_ids": planning_artifacts}


def _node_blind_test_runner(state: StoryBuildState) -> dict[str, Any]:
    report_ids: list[str] = []
    gemini = state.get("gemini")
    for scene_id in state.get("scene_ids", []):
        artifact = nodes.run_blind_test_evaluator(state["db"], uuid.UUID(scene_id), gemini=gemini)
        report_ids.append(str(artifact.artifact_id))
    return {
        "blind_test_report_ids": report_ids,
        "progress": {"current_node": "BlindTestRunner", "message": "Running blind tests...", "step": 8},
    }


def _summarize_text(text: str, max_words: int = 32) -> str:
    words = re.findall(r"\w+", text)
    if not words:
        return ""
    return " ".join(words[:max_words])


def build_story_build_graph():
    graph = StateGraph(StoryBuildState)
    graph.add_node("validate_inputs", _node_validate_inputs)
    graph.add_node("scene_splitter", _node_scene_splitter)
    graph.add_node("character_extractor", _node_character_extractor)
    graph.add_node("character_normalizer", _node_character_normalizer)
    graph.add_node("persist_story_bundle", _node_persist_story_bundle)
    graph.add_node("visual_plan_compiler", _node_visual_plan_compiler)
    graph.add_node("per_scene_planning", _node_per_scene_planning_loop)
    graph.add_node("blind_test_runner", _node_blind_test_runner)

    graph.set_entry_point("validate_inputs")
    graph.add_edge("validate_inputs", "scene_splitter")
    graph.add_edge("scene_splitter", "character_extractor")
    graph.add_edge("character_extractor", "character_normalizer")
    graph.add_edge("character_normalizer", "persist_story_bundle")
    graph.add_edge("persist_story_bundle", "visual_plan_compiler")
    graph.add_edge("visual_plan_compiler", "per_scene_planning")
    graph.add_edge("per_scene_planning", "blind_test_runner")
    graph.add_edge("blind_test_runner", END)
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
) -> StoryBuildState:
    if gemini is None:
        raise ValueError("Gemini client is required for story generation")
    with trace_span("graph.story_build", story_id=str(story_id)):
        app = build_story_build_graph()
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
            "gemini": gemini,
        }
        return app.invoke(state)
