from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from functools import partial
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.telemetry import trace_span
from app.core.request_context import log_context
from app.db.session import session_scope
from app.db.models import Character, Scene, Story, StoryCharacter
from app.graphs import nodes
from app.graphs.nodes.constants import GENRE_PROFILES
from app.services.artifacts import ArtifactService
from app.services.vertex_gemini import GeminiClient

logger = logging.getLogger(__name__)


class StoryBuildState(TypedDict, total=False):
    story_id: uuid.UUID
    story_text: str
    max_scenes: int
    max_characters: int
    panel_count: int
    allow_append: bool
    story_style: str | None
    image_style: str | None
    planning_mode: str

    scenes: list[dict]
    characters: list[dict]
    scene_ids: list[str]
    character_ids: list[str]
    visual_plan_bundle: list[dict]
    visual_plan_artifact_ids: list[str]
    planning_artifact_ids: list[dict]
    blind_test_report_ids: list[str]
    progress: dict
    require_hero_single: bool
    webtoon_script: dict | None
    story_profile: dict | None
    character_hints: list[dict]
    feedback: list[str]
    script_drafts: list[dict]
    tone_analysis: dict | None
    genre_profile: dict | None
    quality_signals: dict | None
    optimized: bool
    retry_count: int
    max_retries: int


def _total_steps(planning_mode: str | None) -> int:
    return 11 if planning_mode == "full" else 7


def _persist_progress(state: StoryBuildState, progress: dict) -> None:
    story_id = state.get("story_id")
    if not story_id:
        return
    with session_scope() as db:
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
    panel_count = max(1, min(int(state.get("panel_count") or 3), 3))

    story_style = state.get("story_style")
    image_style = state.get("image_style")

    story_id = state.get("story_id")
    if story_id:
        with session_scope() as db:
            story = db.get(Story, story_id)
            if story is not None:
                image_style = image_style or story.default_image_style

    # Genre-aware constraints (Task 6.1)
    primary_genre = (story_style or "drama").lower().split(",")[0].strip()
    genre_profile = GENRE_PROFILES.get(primary_genre, GENRE_PROFILES["drama"])
    
    # If panel_count wasn't explicitly provided, use genre defaults or state logic
    # (Note: panel_count in our system is panels per scene image, not per episode)
    if not state.get("panel_count"):
        if primary_genre == "action":
            panel_count = 4 # Action webtoons prefer higher density
        elif primary_genre == "comedy":
            panel_count = 2 # Comedy prefers tight timing

    progress = {
        "max_scenes": max_scenes,
        "max_characters": max_characters,
        "panel_count": panel_count,
        "story_style": story_style,
        "image_style": image_style,
        "genre_profile": genre_profile,
        "progress": {"current_node": "ValidateStoryInputs", "message": "Validating inputs...", "step": 1},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_scene_splitter(state: StoryBuildState) -> dict[str, Any]:
    script = state.get("webtoon_script")
    max_scenes = state.get("max_scenes", 6)
    
    if script and script.get("visual_beats"):
        # Group beats into scenes
        beats = script["visual_beats"]
        total_beats = len(beats)
        beats_per_scene = max(1, (total_beats + max_scenes - 1) // max_scenes)
        
        scenes: list[dict] = []
        for i in range(0, total_beats, beats_per_scene):
            batch = beats[i : i + beats_per_scene]
            idx = len(scenes) + 1
            
            # Format batch as source_text - use narrative format without explicit
            # BEAT markers to avoid LLM interpreting each beat as a separate panel
            text_parts = []
            for b in batch:
                # Format as natural narrative text instead of structured BEAT markers
                action = b.get('visual_action', '')
                dialogue = b.get('dialogue', '')
                sfx = b.get('sfx', '')

                # Build natural sentence/paragraph
                part = action
                if dialogue:
                    # Integrate dialogue naturally
                    part += f' "{dialogue}"'
                if sfx:
                    part += f" ({sfx})"
                text_parts.append(part)

            # Join with single newlines for continuity (not double newlines that suggest separation)
            source_text = " ".join(text_parts)
            summary = batch[0].get("visual_action", "")[:100] # Use first beat as summary base
            
            scenes.append(
                {
                    "scene_index": idx,
                    "title": f"Scene {idx}",
                    "summary": summary,
                    "source_text": source_text,
                    "beats": batch, # Store original beats for downstream use
                }
            )
            if len(scenes) >= max_scenes:
                break
    else:
        # Fallback to old behavior if script writing failed
        scenes_text = nodes.compute_scene_chunker(state.get("story_text", ""), max_scenes=max_scenes)
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
            "message": f"Splitting story into scenes ({len(scenes)}/{max_scenes})...",
            "step": 6,
        },
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_story_populator(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    with log_context(node_name="story_populator"):
        _persist_progress(
            state,
            {
                "current_node": "StoryPopulator",
                "message": "Expanding story seed into webtoon-ready structure...",
                "step": 2,
            },
        )
        profile = nodes.run_story_populator(
            story_text=state.get("story_text", ""),
            target_scene_count=state.get("max_scenes", 6),
            max_characters=min(4, int(state.get("max_characters", 6))),
            story_style=state.get("story_style"),
            gemini=gemini,
        )
        expanded_story = profile.get("expanded_story_text") or state.get("story_text", "")
        hints = profile.get("character_plan") if isinstance(profile.get("character_plan"), list) else []
        recommended = int(profile.get("max_characters_recommended") or state.get("max_characters", 6))
        recommended = max(1, min(recommended, 4))
        progress = {
            "story_profile": profile,
            "story_text": expanded_story,
            "character_hints": hints,
            "max_characters": recommended,
            "progress": {
                "current_node": "StoryPopulator",
                "message": "Story seed expanded and character plan prepared.",
                "step": 2,
            },
        }
        _persist_progress(state, progress["progress"])
        return progress


def _node_llm_character_extractor(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    with log_context(node_name="llm_character_extractor"):
        _persist_progress(
            state,
            {
                "current_node": "LLMCharacterExtractor",
                "message": "Extracting characters with Gemini...",
                "step": 3,
            },
        )
        logger.info(
            "story_build character extraction started (story_id=%s, max_characters=%s)",
            state.get("story_id"),
            state.get("max_characters", 6),
        )
        try:
            profiles = nodes.compute_character_profiles_llm(
                state.get("story_text", ""),
                max_characters=state.get("max_characters", 6),
                character_hints=state.get("character_hints", []),
                gemini=gemini,
            )
        except Exception:
            logger.exception(
                "story_build character extraction failed (story_id=%s, max_characters=%s)",
                state.get("story_id"),
                state.get("max_characters", 6),
            )
            raise
        progress = {
            "characters": profiles,
            "progress": {"current_node": "LLMCharacterExtractor", "message": "Extracting characters...", "step": 3},
        }
        logger.info(
            "story_build character extraction completed (story_id=%s, extracted=%s)",
            state.get("story_id"),
            len(profiles),
        )
        _persist_progress(state, progress["progress"])
        return progress


def _node_llm_character_normalizer(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    with log_context(node_name="llm_character_normalizer"):
        _persist_progress(
            state,
            {
                "current_node": "LLMCharacterProfileNormalizer",
                "message": "Normalizing characters with Gemini...",
                "step": 4,
            },
        )
        logger.info(
            "story_build character normalization started (story_id=%s, input_characters=%s)",
            state.get("story_id"),
            len(state.get("characters", [])),
        )
        try:
            profiles = nodes.normalize_character_profiles_llm(
                state.get("characters", []),
                source_text=state.get("story_text", ""),
                style_id=state.get("image_style"),
                gemini=gemini,
            )
        except Exception:
            logger.exception(
                "story_build character normalization failed (story_id=%s, character_count=%s)",
                state.get("story_id"),
                len(state.get("characters", [])),
            )
            raise
        progress = {
            "characters": profiles,
            "progress": {"current_node": "LLMCharacterProfileNormalizer", "message": "Normalizing characters...", "step": 4},
        }
        logger.info(
            "story_build character normalization completed (story_id=%s, normalized=%s)",
            state.get("story_id"),
            len(profiles),
        )
        _persist_progress(state, progress["progress"])
        return progress


def _node_webtoon_script_writer(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    with log_context(node_name="webtoon_script_writer"):
        logger.info(
            "story_build script writer started (story_id=%s, retry_count=%s)",
            state.get("story_id"),
            state.get("retry_count", 0),
        )
        script = nodes.run_webtoon_script_writer(
            story_text=state.get("story_text", ""),
            characters=state.get("characters", []),
            target_scene_count=state.get("max_scenes", 6),
            story_style=state.get("story_style"),
            story_profile=state.get("story_profile"),
            feedback=state.get("feedback"),
            history=state.get("script_drafts"),
            gemini=gemini,
        )

        drafts = state.get("script_drafts", [])
        drafts.append(script)

        progress = {
            "webtoon_script": script,
            "script_drafts": drafts,
            "progress": {"current_node": "WebtoonScriptWriter", "message": "Writing webtoon script...", "step": 5},
        }
        _persist_progress(state, progress["progress"])
        logger.info(
            "story_build script writer completed (story_id=%s, beats=%s)",
            state.get("story_id"),
            len(script.get("visual_beats", [])) if isinstance(script, dict) else 0,
        )
        return progress


def _node_dialogue_minimizer(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    script = state.get("webtoon_script")
    if not script or "visual_beats" not in script:
        return {}
    
    with session_scope() as db:
        minimized_beats = nodes.run_dialogue_minimizer(
            db=db,
            scene_id=state.get("story_id"),
            visual_beats=script["visual_beats"],
            gemini=gemini,
        )
    
    script["visual_beats"] = minimized_beats
    return {"webtoon_script": script}


def _node_silent_panel_classifier(state: StoryBuildState) -> dict[str, Any]:
    script = state.get("webtoon_script")
    if not script or "visual_beats" not in script:
        return {}
    
    beats = nodes.run_silent_panel_classifier(script["visual_beats"])
    script["visual_beats"] = beats
    return {"webtoon_script": script}


def _node_studio_director(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    with log_context(node_name="studio_director"):
        result = nodes.run_studio_director(
            script=state.get("webtoon_script"),
            max_scenes=state.get("max_scenes", 6),
            gemini=gemini,
        )

        # If optimization requires a script rewrite (feedback loop)
        if result.get("action") == "rewrite":
            feedback = state.get("feedback", [])
            feedback.append(result.get("feedback", "Please optimize the script for better pacing."))
            next_retry = state.get("retry_count", 0) + 1
            logger.info(
                "story_build studio_director requested rewrite (story_id=%s, retry_count=%s)",
                state.get("story_id"),
                next_retry,
            )
            return {
                "feedback": feedback,
                "retry_count": next_retry,
                "optimized": False,
            }

        progress = {
            "scenes": result.get("scenes"),
            "progress": {"current_node": "StudioDirector", "message": "Unified planning and budget optimization...", "step": 6},
        }
        _persist_progress(state, progress["progress"])
        logger.info(
            "story_build studio_director completed (story_id=%s, scenes=%s)",
            state.get("story_id"),
            len(result.get("scenes", [])) if isinstance(result, dict) else 0,
        )
        return progress


def _router_optimization(state: StoryBuildState) -> str:
    """Decide whether to loop back for script rewrite or proceed."""
    feedback = state.get("feedback")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    # If we have feedback but no scenes yet, and haven't exceeded retries
    if feedback and retry_count < max_retries and not state.get("scenes"):
        return "webtoon_script_writer"
    return "persist_story_bundle"


def _node_blind_test_critic(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    quality_signals = state.get("quality_signals") or {}
    if quality_signals and not quality_signals.get("quality_gate_passed", True):
        feedback = state.get("feedback", [])
        feedback.append(
            "Visual rhythm/emotional clarity is weak. Increase silence/reaction beats, diversify gutter pacing, "
            "and reduce explanatory dialogue."
        )
        return {
            "feedback": feedback,
            "retry_count": state.get("retry_count", 0) + 1,
            "optimized": False,
            "scene_ids": [],
        }

    with session_scope() as db:
        result = nodes.run_blind_test_critic(
            db=db,
            story_text=state.get("story_text", ""),
            script=state.get("webtoon_script"),
            scene_ids=state.get("scene_ids", []),
            tone_analysis=state.get("tone_analysis"),
            quality_signals=quality_signals,
            gemini=gemini,
        )
    
    if result.get("action") == "rewrite":
        feedback = state.get("feedback", [])
        feedback.append(result.get("feedback", "Narrative gaps detected in blind test."))
        return {
            "feedback": feedback,
            "retry_count": state.get("retry_count", 0) + 1,
            "optimized": False, # Signal for router
            "scene_ids": [], # Clear scene_ids if we decide to rewrite
        }

    progress = {
        "optimized": True,
        "progress": {"current_node": "BlindTestCritic", "message": "Analyzing blind test results...", "step": 11},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _router_blind_test(state: StoryBuildState) -> str:
    """Decide whether to loop back after blind test critic."""
    feedback = state.get("feedback")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    # Check if a rewrite was requested and we have budget for retries
    if feedback and retry_count < max_retries and not state.get("optimized", True):
        # We need to loop back to the beginning of script writing
        return "webtoon_script_writer"
    
    return END


def _node_persist_story_bundle(state: StoryBuildState) -> dict[str, Any]:
    story_id = state.get("story_id")
    if story_id is None:
        raise ValueError("story_id is required to persist scenes")
    with log_context(node_name="persist_story_bundle"):
        logger.info(
            "story_build persist bundle started (story_id=%s, scenes=%s, characters=%s)",
            story_id,
            len(state.get("scenes", [])),
            len(state.get("characters", [])),
        )

        with session_scope() as db:
            allow_append = bool(state.get("allow_append"))
            existing_scenes = list(db.execute(select(Scene).where(Scene.story_id == story_id)).scalars().all())
            if existing_scenes and not allow_append:
                if state.get("retry_count", 0) > 0:
                    for scene in existing_scenes:
                        db.delete(scene)
                    db.flush()
                else:
                    raise ValueError("story already has scenes; set allow_append to true to append more")

            story = db.get(Story, story_id)
            if story is None:
                raise ValueError("story not found")

            existing_chars = list(
                db.execute(select(Character).where(Character.project_id == story.project_id)).scalars().all()
            )
            existing_by_name = {c.name.strip().lower(): c for c in existing_chars if c.name}
            existing_codes = {c.canonical_code for c in existing_chars if c.canonical_code}
            existing_story_links = {
                row[0]
                for row in db.execute(
                    select(StoryCharacter.character_id).where(StoryCharacter.story_id == story_id)
                ).all()
            }

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
                    if existing_char.character_id not in existing_story_links:
                        db.add(
                            StoryCharacter(
                                story_id=story_id,
                                character_id=existing_char.character_id,
                                narrative_description=profile.get("description"),
                            )
                        )
                        existing_story_links.add(existing_char.character_id)
                    character_ids.append(str(existing_char.character_id))
                    continue
                character = Character(
                    project_id=story.project_id,
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
                db.add(
                    StoryCharacter(
                        story_id=story_id,
                        character_id=character.character_id,
                        narrative_description=profile.get("description"),
                    )
                )
                existing_story_links.add(character.character_id)
                character_ids.append(str(character.character_id))

            scene_ids: list[str] = []
            for scene in state.get("scenes", []):
                row = Scene(
                    story_id=story_id,
                    source_text=scene.get("source_text") or "",
                    image_style_override=scene.get("image_style_id"),
                )
                db.add(row)
                db.flush()
                scene_ids.append(str(row.scene_id))

            db.commit()

        progress = {
            "scene_ids": scene_ids,
            "character_ids": character_ids,
            "progress": {"current_node": "PersistStoryBundle", "message": "Saving story bundle...", "step": 7},
        }
        _persist_progress(state, progress["progress"])
        logger.info(
            "story_build persist bundle completed (story_id=%s, saved_scenes=%s, saved_characters=%s)",
            story_id,
            len(scene_ids),
            len(character_ids),
        )
        return progress


def _node_llm_visual_plan_compiler(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    plans = nodes.compile_visual_plan_bundle_llm(
        scenes=state.get("scenes", []),
        characters=state.get("characters", []),
        story_style=state.get("story_style"),
        gemini=gemini,
    )
    with session_scope() as db:
        svc = ArtifactService(db)
        plan_ids: list[str] = []
        for scene_id, plan in zip(state.get("scene_ids", []), plans, strict=False):
            scene_uuid = uuid.UUID(scene_id)
            artifact = svc.create_artifact(scene_id=scene_uuid, type=nodes.ARTIFACT_VISUAL_PLAN, payload=plan)
            plan_ids.append(str(artifact.artifact_id))
            
            # Phase 1: Core Narrative Grammar
            if isinstance(plan, dict) and plan.get("beats"):
                # Transition Type Classification
                nodes.run_transition_type_classifier(
                    db=db,
                    scene_id=scene_uuid,
                    visual_beats=plan["beats"],
                    gemini=gemini
                )
                # Closure Planning
                nodes.run_closure_planner(
                    db=db,
                    scene_id=scene_uuid,
                    gemini=gemini
                )

            if isinstance(plan, dict) and plan.get("scene_importance"):
                scene = db.get(Scene, scene_uuid)
                if scene is not None:
                    scene.scene_importance = str(plan.get("scene_importance"))

        db.commit()
    progress = {
        "visual_plan_bundle": plans,
        "visual_plan_artifact_ids": plan_ids,
        "progress": {"current_node": "LLMVisualPlanCompiler", "message": "Converting story to visual beats...", "step": 8},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _node_per_scene_planning_loop(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    planning_artifacts: list[dict] = []
    scene_ids = state.get("scene_ids", [])
    total = len(scene_ids)
    # Episode-level guardrail state
    recent_templates: list[str] = []
    hero_count = 0
    
    # Get image_style from state
    image_style = state.get("image_style", "default")

    with session_scope() as db:
        for idx, scene_id in enumerate(scene_ids, start=1):
            scene_uuid = uuid.UUID(scene_id)

            # Run intent, art direction, panel plan, normalize
            scene_intent_id = nodes.run_scene_intent_extractor(db, scene_uuid, gemini=gemini).artifact_id
            art_direction_id = nodes.run_art_director(db, scene_uuid, image_style_id=image_style, gemini=gemini).artifact_id
            panel_plan_id = nodes.run_panel_plan_generator(db, scene_uuid, panel_count=state.get("panel_count", 3), gemini=gemini).artifact_id
            panel_plan_normalized_id = nodes.run_panel_plan_normalizer(db, scene_uuid).artifact_id

            # Attempt to resolve a layout template; if it would create a 3rd identical in a row, exclude that template and try again
            artifact = nodes.run_layout_template_resolver(db, scene_uuid)
            template_id = artifact.payload.get("template_id")

            if len(recent_templates) >= 2 and template_id == recent_templates[-1] == recent_templates[-2]:
                # Exclude the repeated template and re-resolve
                artifact = nodes.run_layout_template_resolver(db, scene_uuid, excluded_template_ids=[template_id])
                template_id = artifact.payload.get("template_id")

            if template_id == "9x16_1":
                hero_count += 1

            panel_semantics_id = nodes.run_panel_semantic_filler(db, scene_uuid, gemini=gemini).artifact_id
            qc_report_id = nodes.run_qc_checker(db, scene_uuid).artifact_id
            dialogue_suggestions_id = nodes.run_dialogue_extractor(db, scene_uuid).artifact_id
            
            # Phase 2: Vertical Rhythm Planning
            rhythm_artifact = nodes.run_vertical_rhythm_planner(db, scene_uuid, gemini=gemini)
            rhythm_id = rhythm_artifact.artifact_id if rhythm_artifact else None

            planning_artifacts.append(
                {
                    "scene_id": scene_id,
                    "scene_intent": str(scene_intent_id),
                    "art_direction": str(art_direction_id),
                    "panel_plan": str(panel_plan_id),
                    "panel_plan_normalized": str(panel_plan_normalized_id),
                    "layout_template": str(artifact.artifact_id),
                    "panel_semantics": str(panel_semantics_id),
                    "qc_report": str(qc_report_id),
                    "dialogue_suggestions": str(dialogue_suggestions_id),
                    "vertical_rhythm": str(rhythm_id) if rhythm_id else None,
                }
            )
            
            # Phase 3: Visual Metaphor Recommendation
            metaphor_artifact = nodes.run_metaphor_recommender(db, scene_uuid, gemini=gemini)
            if metaphor_artifact:
                # Add to the last planning item
                planning_artifacts[-1]["metaphor_directions"] = str(metaphor_artifact.artifact_id)

            # Phase 4: Presence Logic
            presence_artifact = nodes.run_presence_mapper(db, scene_uuid, gemini=gemini)
            if presence_artifact:
                planning_artifacts[-1]["presence_map"] = str(presence_artifact.artifact_id)

            recent_templates.append(template_id)

            # Keep only last 3 for simplicity
            if len(recent_templates) > 3:
                recent_templates.pop(0)

            state["progress"] = {
                "current_node": "PerScenePlanningLoop",
                "message": f"Planning scene {idx}/{total}...",
                "step": 9,
            }
            _persist_progress(state, state["progress"])

    # After loop: enforce at least one hero single-panel scene if requested
    if state.get("require_hero_single"):
        if hero_count == 0:
            # Prefer a cliffhanger scene to convert; else choose the last scene
            chosen_scene_id = None
            with session_scope() as db:
                svc = ArtifactService(db)
                for sid in reversed(scene_ids):
                    vis_art = svc.get_latest_artifact(uuid.UUID(sid), nodes.ARTIFACT_VISUAL_PLAN)
                    if vis_art and isinstance(vis_art.payload, dict):
                        scene_importance = vis_art.payload.get("scene_importance")
                        if scene_importance == "cliffhanger":
                            chosen_scene_id = sid
                            break
                if chosen_scene_id is None:
                    chosen_scene_id = scene_ids[-1]

            # Re-run the scene with a single-panel plan
            scene_uuid = uuid.UUID(chosen_scene_id)
            nodes.run_panel_plan_generator(db, scene_uuid, panel_count=1, gemini=gemini)
            nodes.run_panel_plan_normalizer(db, scene_uuid)
            nodes.run_layout_template_resolver(db, scene_uuid)
            nodes.run_panel_semantic_filler(db, scene_uuid, gemini=gemini)
            nodes.run_qc_checker(db, scene_uuid)

            # Note: For simplicity we don't retroactively update the stored planning_artifacts list;
            # the guardrail ensures an output single-panel scene exists in the persisted artifacts.

    return {"planning_artifact_ids": planning_artifacts}


def _node_blind_test_runner(state: StoryBuildState, gemini: GeminiClient | None) -> dict[str, Any]:
    report_ids: list[str] = []
    blind_scores: list[float] = []
    rhythm_diversities: list[float] = []
    scene_thumb_stops = 0
    total_silent_panels = 0
    total_panels = 0

    def _safe_float(val: Any, fallback: float = 0.0) -> float:
        try:
            return float(val)
        except (TypeError, ValueError):
            return fallback

    with session_scope() as db:
        svc = ArtifactService(db)
        for scene_id in state.get("scene_ids", []):
            scene_uuid = uuid.UUID(scene_id)
            artifact = nodes.run_blind_test_evaluator(db, scene_uuid, gemini=gemini)
            report_ids.append(str(artifact.artifact_id))
            blind_scores.append(_safe_float((artifact.payload or {}).get("score"), 0.0))

            rhythm_art = svc.get_latest_artifact(scene_uuid, nodes.ARTIFACT_VERTICAL_RHYTHM)
            if rhythm_art and isinstance(rhythm_art.payload, dict):
                rhythm_map = list(rhythm_art.payload.get("rhythm_map") or [])
                if rhythm_map:
                    spacings = [
                        int(item.get("gutter_spacing_px"))
                        for item in rhythm_map
                        if isinstance(item, dict) and item.get("gutter_spacing_px") is not None
                    ]
                    if spacings:
                        rhythm_diversities.append(len(set(spacings)) / max(1, len(spacings)))
                    if any(bool(item.get("is_thumb_stop")) for item in rhythm_map if isinstance(item, dict)):
                        scene_thumb_stops += 1

            semantics_art = svc.get_latest_artifact(scene_uuid, nodes.ARTIFACT_PANEL_SEMANTICS)
            if semantics_art and isinstance(semantics_art.payload, dict):
                sem_panels = list(semantics_art.payload.get("panels") or [])
                total_panels += len(sem_panels)
                for panel in sem_panels:
                    if not isinstance(panel, dict):
                        continue
                    dialogue = panel.get("dialogue")
                    is_silent = False
                    if dialogue is None:
                        is_silent = True
                    elif isinstance(dialogue, str):
                        is_silent = not dialogue.strip()
                    elif isinstance(dialogue, list):
                        is_silent = len([d for d in dialogue if str(d).strip()]) == 0
                    else:
                        is_silent = True
                    if is_silent:
                        total_silent_panels += 1

    avg_blind_score = (sum(blind_scores) / len(blind_scores)) if blind_scores else 0.0
    avg_rhythm_diversity = (sum(rhythm_diversities) / len(rhythm_diversities)) if rhythm_diversities else 0.0
    silent_ratio = (total_silent_panels / total_panels) if total_panels else 0.0
    thumb_stop_ratio = (scene_thumb_stops / len(state.get("scene_ids", []))) if state.get("scene_ids") else 0.0
    # Best around 0.25 silent ratio, but allow a wide practical range.
    silence_balance_score = max(0.0, 1.0 - min(1.0, abs(silent_ratio - 0.25) / 0.25))
    rhythm_score = avg_rhythm_diversity if rhythm_diversities else 0.5
    silence_score = silence_balance_score if total_panels else 0.5
    quality_composite = (
        (avg_blind_score * 0.5)
        + (rhythm_score * 0.2)
        + (silence_score * 0.2)
        + (thumb_stop_ratio * 0.1)
    )
    blind_ok = avg_blind_score >= 0.3 if blind_scores else True
    rhythm_ok = avg_rhythm_diversity >= 0.2 if rhythm_diversities else True
    silence_ok = silent_ratio >= 0.1 if total_panels else True
    quality_signals = {
        "avg_blind_score": round(avg_blind_score, 3),
        "avg_rhythm_diversity": round(avg_rhythm_diversity, 3),
        "silent_panel_ratio": round(silent_ratio, 3),
        "thumb_stop_scene_ratio": round(thumb_stop_ratio, 3),
        "silence_balance_score": round(silence_balance_score, 3),
        "quality_composite": round(quality_composite, 3),
        "quality_gate_passed": bool(
            blind_ok
            and quality_composite >= 0.35
            and silence_ok
            and rhythm_ok
        ),
    }

    progress = {
        "blind_test_report_ids": report_ids,
        "quality_signals": quality_signals,
        "progress": {"current_node": "BlindTestRunner", "message": "Running blind tests...", "step": 10},
    }
    _persist_progress(state, progress["progress"])
    return progress


def _summarize_text(text: str, max_words: int = 32) -> str:
    words = re.findall(r"\w+", text)
    if not words:
        return ""
    return " ".join(words[:max_words])


def build_story_build_graph(planning_mode: str = "full", gemini: GeminiClient | None = None):
    graph = StateGraph(StoryBuildState)
    graph.add_node("validate_inputs", _node_validate_inputs)
    graph.add_node("story_populator", partial(_node_story_populator, gemini=gemini))
    graph.add_node("llm_character_extractor", partial(_node_llm_character_extractor, gemini=gemini))
    graph.add_node("llm_character_normalizer", partial(_node_llm_character_normalizer, gemini=gemini))
    graph.add_node("webtoon_script_writer", partial(_node_webtoon_script_writer, gemini=gemini))
    graph.add_node("scene_splitter", _node_scene_splitter)
    graph.add_node("dialogue_minimizer", partial(_node_dialogue_minimizer, gemini=gemini))
    graph.add_node("silent_panel_classifier", _node_silent_panel_classifier)
    graph.add_node("studio_director", partial(_node_studio_director, gemini=gemini))
    graph.add_node("persist_story_bundle", _node_persist_story_bundle)

    graph.set_entry_point("validate_inputs")
    graph.add_edge("validate_inputs", "story_populator")
    graph.add_edge("story_populator", "llm_character_extractor")
    graph.add_edge("llm_character_extractor", "llm_character_normalizer")
    graph.add_edge("llm_character_normalizer", "webtoon_script_writer")

    if planning_mode == "full":
        graph.add_edge("webtoon_script_writer", "dialogue_minimizer")
        graph.add_edge("dialogue_minimizer", "silent_panel_classifier")
        graph.add_edge("silent_panel_classifier", "studio_director")
        graph.add_edge("studio_director", "persist_story_bundle")
        graph.add_conditional_edges(
            "studio_director",
            _router_optimization,
            {
                "webtoon_script_writer": "webtoon_script_writer",
                "persist_story_bundle": "persist_story_bundle",
            },
        )
    else:
        # Fast path for story blueprint: avoid extra LLM optimization loops.
        graph.add_edge("webtoon_script_writer", "scene_splitter")
        graph.add_edge("scene_splitter", "persist_story_bundle")

    graph.add_edge("persist_story_bundle", "llm_visual_plan_compiler") if planning_mode == "full" else graph.add_edge("persist_story_bundle", END)

    if planning_mode == "full":
        graph.add_node("llm_visual_plan_compiler", partial(_node_llm_visual_plan_compiler, gemini=gemini))
        graph.add_node("per_scene_planning", partial(_node_per_scene_planning_loop, gemini=gemini))
        graph.add_node("blind_test_runner", partial(_node_blind_test_runner, gemini=gemini))
        graph.add_node("blind_test_critic", partial(_node_blind_test_critic, gemini=gemini))
        
        graph.add_edge("persist_story_bundle", "llm_visual_plan_compiler")
        graph.add_edge("llm_visual_plan_compiler", "per_scene_planning")
        graph.add_edge("per_scene_planning", "blind_test_runner")
        graph.add_edge("blind_test_runner", "blind_test_critic")
        
        graph.add_conditional_edges(
            "blind_test_critic",
            _router_blind_test,
            {
                "webtoon_script_writer": "webtoon_script_writer",
                "END": END,
            },
        )
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
    require_hero_single: bool = False,
) -> StoryBuildState:
    if gemini is None:
        raise ValueError("Gemini client is required for story generation")
    if planning_mode not in {"full", "characters_only"}:
        raise ValueError("planning_mode must be 'full' or 'characters_only'")
    with trace_span("graph.story_build", story_id=str(story_id)):
        app = build_story_build_graph(planning_mode=planning_mode, gemini=gemini)
        state: StoryBuildState = {
            "story_id": story_id,
            "story_text": story_text,
            "max_scenes": max_scenes,
            "max_characters": max_characters,
            "panel_count": panel_count,
            "allow_append": allow_append,
            "story_style": story_style,
            "image_style": image_style,
            "planning_mode": planning_mode,
            "require_hero_single": require_hero_single,
            "retry_count": 0,
            "max_retries": 3,
            "feedback": [],
            "script_drafts": [],
        }
        return app.invoke(state)
