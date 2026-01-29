from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class GrammarItem(BaseModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class GrammarLibraryV1(BaseModel):
    version: str
    grammars: list[GrammarItem]


class PanelRect(BaseModel):
    x: float
    y: float
    w: float
    h: float


class LayoutTemplate(BaseModel):
    template_id: str = Field(min_length=1)
    layout_text: str = Field(min_length=1)
    panels: list[PanelRect] = Field(min_length=1)


class LayoutTemplatesV1(BaseModel):
    version: str
    aspect_ratio: str
    templates: list[LayoutTemplate]


class LayoutSelectionRule(BaseModel):
    panel_count: int = Field(ge=1)
    template_id: str = Field(min_length=1)
    # Optional decision-table fields: match if non-empty
    scene_importance: list[str] = Field(default_factory=list)
    pace: list[str] = Field(default_factory=list)
    # Weight-based selectors
    min_large_panels: int = Field(default=0)
    min_max_weight: float = Field(default=0.0)


class LayoutSelectionRulesV1(BaseModel):
    version: str
    rules: list[LayoutSelectionRule]
    default_template_id: str = Field(min_length=1)


class GrammarToPromptMappingV1(BaseModel):
    version: str
    mapping: dict[str, str]


class ContinuityRulesV1(BaseModel):
    version: str
    rules: list[dict]


class QcRulesV1(BaseModel):
    version: str
    closeup_ratio_max: float = Field(ge=0.0, le=1.0)
    dialogue_ratio_max: float = Field(ge=0.0, le=1.0)
    repeated_framing_run_length: int = Field(ge=2)
    require_environment_on_establishing: bool = True
    environment_keywords: list[str] = Field(default_factory=list)


class StyleItem(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    image_url: str | None = None


class StyleLibraryV1(BaseModel):
    version: str
    styles: list[StyleItem]


def _config_dir() -> Path:
    return Path(__file__).resolve().parent


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_grammar_library_v1() -> GrammarLibraryV1:
    data = _read_json(_config_dir() / "panel_grammar_library_v1.json")
    return GrammarLibraryV1.model_validate(data)


@lru_cache(maxsize=1)
def load_layout_templates_9x16_v1() -> LayoutTemplatesV1:
    data = _read_json(_config_dir() / "layout_templates_9x16_v1.json")
    return LayoutTemplatesV1.model_validate(data)


@lru_cache(maxsize=1)
def load_layout_selection_rules_v1() -> LayoutSelectionRulesV1:
    data = _read_json(_config_dir() / "layout_selection_rules_v1.json")
    return LayoutSelectionRulesV1.model_validate(data)


@lru_cache(maxsize=1)
def load_grammar_to_prompt_mapping_v1() -> GrammarToPromptMappingV1:
    data = _read_json(_config_dir() / "grammar_to_prompt_mapping_v1.json")
    return GrammarToPromptMappingV1.model_validate(data)


@lru_cache(maxsize=1)
def load_continuity_rules_v1() -> ContinuityRulesV1:
    data = _read_json(_config_dir() / "continuity_rules_v1.json")
    return ContinuityRulesV1.model_validate(data)


@lru_cache(maxsize=1)
def load_qc_rules_v1() -> QcRulesV1:
    data = _read_json(_config_dir() / "qc_rules_v1.json")
    return QcRulesV1.model_validate(data)


@lru_cache(maxsize=1)
def load_story_styles_v1() -> StyleLibraryV1:
    data = _read_json(_config_dir() / "story_styles.json")
    return StyleLibraryV1.model_validate(data)


@lru_cache(maxsize=1)
def load_image_styles_v1() -> StyleLibraryV1:
    data = _read_json(_config_dir() / "image_styles.json")
    return StyleLibraryV1.model_validate(data)


def get_grammar(grammar_id: str) -> GrammarItem:
    lib = load_grammar_library_v1()
    for g in lib.grammars:
        if g.id == grammar_id:
            return g
    raise KeyError(f"Unknown grammar_id: {grammar_id}")


def get_layout_template(template_id: str) -> LayoutTemplate:
    templates = load_layout_templates_9x16_v1()
    for t in templates.templates:
        if t.template_id == template_id:
            return t
    raise KeyError(f"Unknown template_id: {template_id}")


def has_story_style(style_id: str) -> bool:
    lib = load_story_styles_v1()
    return any(s.id == style_id for s in lib.styles)


def has_image_style(style_id: str) -> bool:
    lib = load_image_styles_v1()
    return any(s.id == style_id for s in lib.styles)


def _panel_plan_count(panel_plan) -> int:
    if panel_plan is None:
        return 0

    if isinstance(panel_plan, list):
        return len(panel_plan)

    if isinstance(panel_plan, dict):
        panels = panel_plan.get("panels")
        if isinstance(panels, list):
            return len(panels)

    raise TypeError("panel_plan must be a list or dict with key 'panels'")


def select_template(panel_plan, derived_features: dict | None = None, excluded_template_ids: list[str] | None = None) -> LayoutTemplate:
    """Select a layout template using the decision-table rules.

    - derived_features: optional dict (e.g., scene_importance, pace)
    - excluded_template_ids: list of template_ids to avoid when selecting (used by guardrails)
    """
    derived_features = derived_features or {}
    excluded_template_ids = excluded_template_ids or []

    panel_count = _panel_plan_count(panel_plan)
    if panel_count <= 0:
        # Allow fallback to default template when panel plan is empty
        rules = load_layout_selection_rules_v1()
        return get_layout_template(rules.default_template_id)

    rules = load_layout_selection_rules_v1()
    for rule in rules.rules:
        # panel_count must match first
        if rule.panel_count != panel_count:
            continue

        # Skip excluded templates
        if rule.template_id in excluded_template_ids:
            continue

        # If rule declares scene_importance values, check derived feature
        if rule.scene_importance:
            sf = derived_features.get("scene_importance")
            if not sf or sf not in rule.scene_importance:
                continue

        # If rule declares pace, check derived feature
        if rule.pace:
            pf = derived_features.get("pace")
            if not pf or pf not in rule.pace:
                continue

        # Weight-based checks
        if rule.min_large_panels and rule.min_large_panels > 0:
            num_large = int(derived_features.get("num_large", 0))
            if num_large < rule.min_large_panels:
                continue

        if rule.min_max_weight and rule.min_max_weight > 0.0:
            max_w = float(derived_features.get("max_weight", 0.0))
            if max_w < float(rule.min_max_weight):
                continue

        # All checks passed for this rule
        return get_layout_template(rule.template_id)

    # No explicit rule matched; try to pick a non-excluded template from the templates list
    templates = load_layout_templates_9x16_v1()
    for t in templates.templates:
        if t.template_id not in excluded_template_ids:
            return t

    # As a final fallback, return the default (even if excluded)
    return get_layout_template(rules.default_template_id)
