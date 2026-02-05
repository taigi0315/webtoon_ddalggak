"""
Planning module for webtoon generation pipeline.

This module contains graph node implementations for:
- Character extraction and normalization
- Scene chunking and visual planning
- Scene intent extraction
- Panel plan generation and normalization
- Panel semantics filling
- Layout template resolution
- Dialogue extraction
- QC checking and blind testing

All functions are re-exported here for backward compatibility.
"""

from __future__ import annotations

# Character extraction and normalization
from .character import (
    compute_character_profiles,
    compute_character_profiles_llm,
    normalize_character_profiles,
    normalize_character_profiles_llm,
)

# Visual planning
from .visual_plan import (
    compile_visual_plan_bundle,
    compile_visual_plan_bundle_llm,
    compute_scene_chunker,
)

# Script writing and optimization
from .story_populator import run_story_populator
from .script_writer import run_webtoon_script_writer
from .studio_director import run_studio_director
from .transition import run_transition_type_classifier
from .closure import run_closure_planner
from .dialogue_minimizer import run_dialogue_minimizer
from .silence import run_silent_panel_classifier
from .rhythm import run_vertical_rhythm_planner
from .metaphor import run_metaphor_recommender
from .presence import run_presence_mapper

# Scene intent
from .scene_intent import run_scene_intent_extractor

# Art direction
from .art_direction import run_art_director

# Panel planning
from .panel_plan import (
    run_panel_plan_generator,
    run_panel_plan_normalizer,
    run_layout_template_resolver,
)

# Panel semantics
from .panel_semantics import run_panel_semantic_filler

# Dialogue extraction
from .dialogue import run_dialogue_extractor

# QC and evaluation
from .qc import run_qc_checker
from .blind_test import run_blind_test_evaluator
from .blind_test_critic import run_blind_test_critic

__all__ = [
    # Character
    "compute_character_profiles",
    "compute_character_profiles_llm",
    "normalize_character_profiles",
    "normalize_character_profiles_llm",
    # Visual plan
    "compile_visual_plan_bundle",
    "compile_visual_plan_bundle_llm",
    "compute_scene_chunker",
    "run_story_populator",
    "run_webtoon_script_writer",
    "run_studio_director",
    "run_transition_type_classifier",
    "run_closure_planner",
    "run_dialogue_minimizer",
    "run_silent_panel_classifier",
    "run_vertical_rhythm_planner",
    "run_metaphor_recommender",
    "run_presence_mapper",
    # Scene intent
    "run_scene_intent_extractor",
    # Art direction
    "run_art_director",
    # Panel plan
    "run_panel_plan_generator",
    "run_panel_plan_normalizer",
    "run_layout_template_resolver",
    # Panel semantics
    "run_panel_semantic_filler",
    # Dialogue
    "run_dialogue_extractor",
    # QC and evaluation
    "run_qc_checker",
    "run_blind_test_evaluator",
    "run_blind_test_critic",
]
