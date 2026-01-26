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


def select_template(panel_plan, derived_features: dict | None = None) -> LayoutTemplate:
    derived_features = derived_features or {}

    panel_count = _panel_plan_count(panel_plan)
    if panel_count <= 0:
        raise ValueError("panel_plan must contain at least 1 panel")

    rules = load_layout_selection_rules_v1()
    for rule in rules.rules:
        if rule.panel_count == panel_count:
            return get_layout_template(rule.template_id)

    return get_layout_template(rules.default_template_id)
