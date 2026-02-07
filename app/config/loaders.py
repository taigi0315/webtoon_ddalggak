from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

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
    narration_ratio_max: float = Field(default=0.35, ge=0.0, le=1.0)
    generic_dialogue_ratio_max: float = Field(default=0.4, ge=0.0, le=1.0)
    min_silent_panel_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    max_words_per_panel: int = Field(default=25, ge=1)
    max_words_per_line: int = Field(default=15, ge=1)
    repeated_framing_run_length: int = Field(ge=2)
    require_environment_on_establishing: bool = True
    environment_keywords: list[str] = Field(default_factory=list)


class StyleItem(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(default="")
    image_url: str | None = None


class ImageStylesV1(BaseModel):
    version: str
    styles: list[StyleItem]


# Global config version counter (incremented on cache clear)
_config_version = 0
_WEBTOON_STYLE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "example_webtoon"
_STYLE_GUIDE_FILENAME = "STYLE_GUIDE.md"
_CHARACTER_STYLE_FILENAME = "CHARACTER_STYLE.md"


def _strip_forbidden_style_anchors(text: str) -> str:
    if not text:
        return text
    anchors = [
        "korean webtoon",
        "korean manhwa",
        "naver webtoon",
        "manhwa art style",
        "webtoon art style",
        "manhwa aesthetic",
        "webtoon aesthetic",
        "korean webtoon style",
        "korean manhwa style",
    ]
    cleaned = text
    for anchor in anchors:
        cleaned = re.sub(rf"(?i)\\b{re.escape(anchor)}\\b", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def clear_config_cache():
    """Clear all cached config data. Call this to force config reload."""
    global _config_version
    _config_version += 1
    load_grammar_library_v1.cache_clear()
    load_layout_templates_9x16_v1.cache_clear()
    load_layout_selection_rules_v1.cache_clear()
    load_grammar_to_prompt_mapping_v1.cache_clear()
    load_continuity_rules_v1.cache_clear()
    load_qc_rules_v1.cache_clear()
    load_image_styles_v1.cache_clear()
    load_style_guide_text.cache_clear()
    load_character_style_text.cache_clear()


def get_config_version() -> int:
    """Get current config version (incremented on each cache clear)."""
    return _config_version


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


def has_image_style(style_id: str) -> bool:
    lib = load_image_styles_v1()
    return any(s.id == style_id for s in lib.styles)


def _style_dir_label(dir_name: str) -> str:
    return dir_name.replace("-", " ").replace("_", " ").title()


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _extract_summary(text: str, max_chars: int = 200) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # Prefer the first non-header line
    for line in lines:
        if not line.startswith("#"):
            return (line[: max_chars - 1] + "…") if len(line) > max_chars else line
    # Fallback to first header or truncated raw
    raw = lines[0] if lines else text
    return (raw[: max_chars - 1] + "…") if len(raw) > max_chars else raw


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


# ============================================================================
# Config Loaders
# ============================================================================

_CONFIG_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def load_grammar_library_v1() -> GrammarLibraryV1:
    """Load panel grammar library."""
    path = _CONFIG_DIR / "panel_grammar_library_v1.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return GrammarLibraryV1.model_validate(data)


@lru_cache(maxsize=1)
def load_layout_templates_9x16_v1() -> LayoutTemplatesV1:
    """Load 9:16 layout templates."""
    path = _CONFIG_DIR / "layout_templates_9x16_v1.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return LayoutTemplatesV1.model_validate(data)


@lru_cache(maxsize=1)
def load_layout_selection_rules_v1() -> LayoutSelectionRulesV1:
    """Load layout selection rules."""
    path = _CONFIG_DIR / "layout_selection_rules_v1.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return LayoutSelectionRulesV1.model_validate(data)


@lru_cache(maxsize=1)
def load_grammar_to_prompt_mapping_v1() -> GrammarToPromptMappingV1:
    """Load grammar to prompt mapping."""
    path = _CONFIG_DIR / "grammar_to_prompt_mapping_v1.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return GrammarToPromptMappingV1.model_validate(data)


@lru_cache(maxsize=1)
def load_continuity_rules_v1() -> ContinuityRulesV1:
    """Load continuity rules."""
    path = _CONFIG_DIR / "continuity_rules_v1.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ContinuityRulesV1.model_validate(data)


@lru_cache(maxsize=1)
def load_qc_rules_v1() -> QcRulesV1:
    """Load QC rules."""
    path = _CONFIG_DIR / "qc_rules_v1.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return QcRulesV1.model_validate(data)


@lru_cache(maxsize=1)
def load_image_styles_v1() -> ImageStylesV1:
    """Load image styles."""
    styles: list[StyleItem] = []
    if _WEBTOON_STYLE_ROOT.exists():
        for style_dir in sorted(p for p in _WEBTOON_STYLE_ROOT.iterdir() if p.is_dir()):
            guide_path = style_dir / _STYLE_GUIDE_FILENAME
            if not guide_path.exists():
                continue
            guide_text = _read_text_file(guide_path)
            styles.append(
                StyleItem(
                    id=style_dir.name,
                    label=_style_dir_label(style_dir.name),
                    description=_extract_summary(guide_text),
                    image_url=None,
                )
            )
        if styles:
            return ImageStylesV1(version="webtoon_styles_v1", styles=styles)

    path = _CONFIG_DIR / "image_styles.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ImageStylesV1.model_validate(data)


@lru_cache(maxsize=128)
def load_style_guide_text(style_id: str) -> Optional[str]:
    if not style_id:
        return None
    if not _WEBTOON_STYLE_ROOT.exists():
        return None
    path = _WEBTOON_STYLE_ROOT / style_id / _STYLE_GUIDE_FILENAME
    text = _read_text_file(path)
    if not text:
        return None
    return _strip_forbidden_style_anchors(text)


@lru_cache(maxsize=128)
def load_character_style_text(style_id: str) -> Optional[str]:
    if not style_id:
        return None
    if not _WEBTOON_STYLE_ROOT.exists():
        return None
    path = _WEBTOON_STYLE_ROOT / style_id / _CHARACTER_STYLE_FILENAME
    text = _read_text_file(path)
    if not text:
        return None
    return _strip_forbidden_style_anchors(text)
