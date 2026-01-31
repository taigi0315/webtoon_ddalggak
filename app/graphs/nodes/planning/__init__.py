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

# Script writing
from .script_writer import run_webtoon_script_writer

# Scene intent
from .scene_intent import run_scene_intent_extractor

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
    "run_webtoon_script_writer",
    # Scene intent
    "run_scene_intent_extractor",
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
]
