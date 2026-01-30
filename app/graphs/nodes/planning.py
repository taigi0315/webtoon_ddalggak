"""
Backward-compatible shim for the planning module.

This module has been refactored into separate files under the 'planning/' directory.
All functions are re-exported here for backward compatibility.

See app/graphs/nodes/planning/ for the implementation:
- character.py: Character extraction and normalization
- visual_plan.py: Visual planning and scene chunking
- scene_intent.py: Scene intent extraction
- panel_plan.py: Panel plan generation and layout resolution
- panel_semantics.py: Panel semantics filling
- dialogue.py: Dialogue extraction
- qc.py: Quality control checking
- blind_test.py: Blind test evaluation
"""

from __future__ import annotations

# Re-export everything from the planning package
from .planning import (
    # Character extraction and normalization
    compute_character_profiles,
    compute_character_profiles_llm,
    normalize_character_profiles,
    normalize_character_profiles_llm,
    # Visual planning
    compile_visual_plan_bundle,
    compile_visual_plan_bundle_llm,
    compute_scene_chunker,
    # Scene intent
    run_scene_intent_extractor,
    # Panel planning
    run_panel_plan_generator,
    run_panel_plan_normalizer,
    run_layout_template_resolver,
    # Panel semantics
    run_panel_semantic_filler,
    # Dialogue
    run_dialogue_extractor,
    # QC and evaluation
    run_qc_checker,
    run_blind_test_evaluator,
)

# Also re-export utils for any code that imports from planning
from .utils import *  # noqa: F401, F403

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
