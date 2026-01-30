"""
Enhanced layout template selection service.

Provides improved feature extraction and scoring for layout template selection.
This is designed to work with the existing rule-based system while providing
a foundation for future ML-based selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.config import loaders

if TYPE_CHECKING:
    from app.config.loaders import LayoutTemplate


@dataclass
class LayoutFeatures:
    """Features extracted from panel plan for layout selection."""

    # Basic features
    panel_count: int = 0
    scene_importance: str = "build"  # setup, build, climax, release, cliffhanger
    pacing: str = "normal"  # slow_burn, normal, fast, impact

    # Grammar distribution
    grammar_counts: dict[str, int] = field(default_factory=dict)
    has_establishing: bool = False
    has_closeup: bool = False
    has_action: bool = False
    has_dialogue: bool = False

    # Weight-based features
    weights: list[float] = field(default_factory=list)
    max_weight: float = 0.0
    total_weight: float = 0.0
    num_large_panels: int = 0  # Panels with weight >= 0.3

    # Dialogue features
    dialogue_panel_count: int = 0
    dialogue_ratio: float = 0.0

    # Content features
    character_count: int = 0
    has_hero_panel: bool = False


@dataclass
class LayoutScore:
    """Scoring result for a layout template."""

    template_id: str
    score: float
    match_reasons: list[str] = field(default_factory=list)


def extract_layout_features(
    panel_plan: dict | list,
    scene_importance: str | None = None,
    pacing: str | None = None,
    character_names: list[str] | None = None,
) -> LayoutFeatures:
    """
    Extract features from a panel plan for layout selection.

    Args:
        panel_plan: Panel plan dict or list of panels
        scene_importance: Optional scene importance override
        pacing: Optional pacing override
        character_names: List of known character names

    Returns:
        LayoutFeatures extracted from the panel plan
    """
    features = LayoutFeatures()

    # Handle dict vs list format
    panels = []
    if isinstance(panel_plan, dict):
        panels = panel_plan.get("panels", [])
        features.scene_importance = (
            scene_importance
            or panel_plan.get("scene_importance")
            or panel_plan.get("derived_features", {}).get("scene_importance")
            or "build"
        )
        # Extract from derived_features if available
        derived = panel_plan.get("derived_features", {})
        if derived:
            features.max_weight = derived.get("max_weight", 0.0)
            features.total_weight = derived.get("total_weight", 0.0)
            features.num_large_panels = derived.get("num_large", 0)
            features.has_hero_panel = derived.get("hero_count", 0) > 0
    elif isinstance(panel_plan, list):
        panels = panel_plan

    features.panel_count = len(panels)
    features.pacing = pacing or "normal"

    # Analyze panels
    grammar_counts: dict[str, int] = {}
    weights = []
    dialogue_count = 0
    unique_characters = set()

    for panel in panels:
        if not isinstance(panel, dict):
            continue

        # Grammar analysis
        grammar_id = panel.get("grammar_id", "")
        grammar_counts[grammar_id] = grammar_counts.get(grammar_id, 0) + 1

        # Weight analysis
        weight = panel.get("weight", 0.0)
        if weight:
            weights.append(weight)
            if weight >= 0.3:
                features.num_large_panels += 1

        # Dialogue analysis
        if panel.get("has_dialogue", False):
            dialogue_count += 1

        # Character analysis
        chars = panel.get("characters", [])
        if isinstance(chars, list):
            for c in chars:
                if isinstance(c, dict):
                    unique_characters.add(c.get("name", ""))
                elif isinstance(c, str):
                    unique_characters.add(c)

    features.grammar_counts = grammar_counts
    features.has_establishing = grammar_counts.get("establishing", 0) > 0
    features.has_closeup = grammar_counts.get("emotion_closeup", 0) > 0
    features.has_action = grammar_counts.get("action", 0) > 0
    features.has_dialogue = grammar_counts.get("dialogue_medium", 0) > 0

    if weights:
        features.weights = weights
        features.max_weight = max(weights) if weights else 0.0
        features.total_weight = sum(weights)

    features.dialogue_panel_count = dialogue_count
    features.dialogue_ratio = dialogue_count / max(features.panel_count, 1)
    features.character_count = len(unique_characters - {""})

    return features


def score_template(
    template: "LayoutTemplate",
    features: LayoutFeatures,
) -> LayoutScore:
    """
    Score a layout template against extracted features.

    Args:
        template: Layout template to score
        features: Extracted features from panel plan

    Returns:
        LayoutScore with calculated score and match reasons
    """
    score = 0.0
    reasons = []

    # Panel count match (required)
    template_panel_count = len(template.panels)
    if template_panel_count != features.panel_count:
        return LayoutScore(template_id=template.template_id, score=0.0, match_reasons=["Panel count mismatch"])

    score += 1.0
    reasons.append("Panel count matches")

    # Analyze template panel sizes
    template_areas = [(p.w * p.h) for p in template.panels]
    max_panel_area = max(template_areas) if template_areas else 0
    total_area = sum(template_areas)

    # Large panel emphasis for climax/impact scenes
    if features.scene_importance in ["climax", "cliffhanger"]:
        # Prefer templates with one dominant large panel
        if max_panel_area > 0.4 * total_area:
            score += 0.3
            reasons.append("Has dominant panel for climax")

    # Setup scenes benefit from balanced layouts
    if features.scene_importance == "setup":
        # Check for relatively balanced panel sizes
        size_variance = max(template_areas) - min(template_areas) if template_areas else 0
        if size_variance < 0.3:
            score += 0.2
            reasons.append("Balanced layout for setup")

    # Weight-based matching
    if features.num_large_panels >= 1 and max_panel_area > 0.35 * total_area:
        score += 0.25
        reasons.append("Large panel available for weighted content")

    # Dialogue-heavy scenes benefit from medium-sized panels
    if features.dialogue_ratio > 0.5:
        medium_panels = sum(1 for a in template_areas if 0.15 < a < 0.35)
        if medium_panels >= features.panel_count * 0.5:
            score += 0.2
            reasons.append("Good medium panels for dialogue")

    # Action scenes benefit from dynamic layouts
    if features.has_action:
        # Prefer varied panel sizes
        if len(set(round(a, 2) for a in template_areas)) >= 2:
            score += 0.15
            reasons.append("Varied sizes for action")

    return LayoutScore(
        template_id=template.template_id,
        score=round(score, 2),
        match_reasons=reasons,
    )


def select_best_template(
    panel_plan: dict | list,
    scene_importance: str | None = None,
    pacing: str | None = None,
    excluded_template_ids: list[str] | None = None,
) -> tuple["LayoutTemplate", LayoutScore]:
    """
    Select the best layout template for a panel plan.

    Args:
        panel_plan: Panel plan dict or list of panels
        scene_importance: Optional scene importance override
        pacing: Optional pacing override
        excluded_template_ids: Template IDs to exclude from selection

    Returns:
        Tuple of (selected template, scoring details)
    """
    excluded_template_ids = excluded_template_ids or []

    # Extract features
    features = extract_layout_features(
        panel_plan,
        scene_importance=scene_importance,
        pacing=pacing,
    )

    # Get all templates
    templates = loaders.load_layout_templates_9x16_v1()

    # Score each template
    scored_templates: list[tuple["LayoutTemplate", LayoutScore]] = []

    for template in templates.templates:
        if template.template_id in excluded_template_ids:
            continue

        template_score = score_template(template, features)
        if template_score.score > 0:
            scored_templates.append((template, template_score))

    # Sort by score descending
    scored_templates.sort(key=lambda x: x[1].score, reverse=True)

    if scored_templates:
        return scored_templates[0]

    # Fallback to existing selection logic
    rules = loaders.load_layout_selection_rules_v1()
    fallback = loaders.get_layout_template(rules.default_template_id)
    return fallback, LayoutScore(
        template_id=fallback.template_id,
        score=0.5,
        match_reasons=["Fallback to default template"],
    )


def get_template_recommendations(
    panel_plan: dict | list,
    scene_importance: str | None = None,
    top_n: int = 3,
) -> list[tuple["LayoutTemplate", LayoutScore]]:
    """
    Get top N template recommendations for a panel plan.

    Useful for showing alternatives to the user.
    """
    features = extract_layout_features(panel_plan, scene_importance=scene_importance)
    templates = loaders.load_layout_templates_9x16_v1()

    scored = []
    for template in templates.templates:
        template_score = score_template(template, features)
        if template_score.score > 0:
            scored.append((template, template_score))

    scored.sort(key=lambda x: x[1].score, reverse=True)
    return scored[:top_n]
