import pytest

from app.config.loaders import (
    get_grammar,
    load_grammar_library_v1,
    load_grammar_to_prompt_mapping_v1,
    load_layout_selection_rules_v1,
    select_template,
)


def test_can_load_and_validate_schema():
    lib = load_grammar_library_v1()
    assert lib.version == "v1"
    assert len(lib.grammars) >= 1


def test_get_grammar():
    g = get_grammar("establishing")
    assert g.id == "establishing"


def test_select_template_deterministic_for_known_case():
    t = select_template([{"grammar_id": "establishing"}])
    assert t.template_id == "9x16_1"


def test_select_template_respects_scene_importance():
    panel_plan = {"panels": [{}, {}, {}]}
    t = select_template(panel_plan, derived_features={"scene_importance": "cliffhanger"})
    assert t.template_id == "9x16_1"


def test_select_template_respects_pace_dialogue():
    panel_plan = {"panels": [{}, {}]}
    t = select_template(panel_plan, derived_features={"pace": "dialogue"})
    assert t.template_id == "9x16_2_70_30"


def test_select_template_excludes_templates():
    panel_plan = {"panels": [{}, {}, {}]}
    t = select_template(panel_plan, excluded_template_ids=["9x16_3_vertical"])
    # Should choose first non-excluded template (exists in templates list)
    assert t.template_id != "9x16_3_vertical"


def test_grammar_mapping_exists_for_all_grammar_ids():
    lib = load_grammar_library_v1()
    mapping = load_grammar_to_prompt_mapping_v1().mapping

    missing = [g.id for g in lib.grammars if g.id not in mapping]
    assert missing == []


def test_select_template_requires_panel_plan():
    # Empty panel plan should return default template
    t = select_template({"panels": []})
    assert t.template_id == load_layout_selection_rules_v1().default_template_id
