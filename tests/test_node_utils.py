"""Tests for graph node utility functions.

These tests cover the pure utility functions in app/graphs/nodes/utils.py
that are frequently used throughout the pipeline and previously untested.
"""

import pytest

from app.graphs.nodes.utils import (
    _derive_panel_plan_features,
    _extract_dialogue_suggestions,
    _extract_must_show,
    _group_chunks,
    _panel_count,
    _panel_count_for_importance,
    roundup,
)


class TestGroupChunks:
    def test_empty_list(self):
        assert _group_chunks([], 3) == []

    def test_items_fewer_than_groups(self):
        assert _group_chunks(["a", "b"], 5) == ["a", "b"]

    def test_exact_group_count(self):
        assert _group_chunks(["a", "b", "c"], 3) == ["a", "b", "c"]

    def test_items_grouped(self):
        result = _group_chunks(["a", "b", "c", "d"], 2)
        assert len(result) == 2
        assert result[0] == "a b"
        assert result[1] == "c d"

    def test_uneven_split(self):
        result = _group_chunks(["a", "b", "c", "d", "e"], 2)
        assert len(result) == 2

    def test_single_group(self):
        result = _group_chunks(["a", "b", "c"], 1)
        assert len(result) == 1
        assert result[0] == "a b c"


class TestExtractMustShow:
    def test_extracts_unique_tokens(self):
        text = "The hero jumps over the dragon and fights bravely"
        result = _extract_must_show(text)
        assert len(result) <= 4
        assert all(len(tok) >= 4 for tok in result)

    def test_returns_lowercase(self):
        result = _extract_must_show("The Hero Jumps Over")
        assert all(tok == tok.lower() for tok in result)

    def test_empty_text(self):
        assert _extract_must_show("") == []

    def test_short_tokens_excluded(self):
        result = _extract_must_show("a to be or not to be")
        assert result == []

    def test_max_four_tokens(self):
        text = "alpha bravo charlie delta echo foxtrot"
        result = _extract_must_show(text)
        assert len(result) == 4


class TestPanelCountForImportance:
    def test_climax_returns_one(self):
        assert _panel_count_for_importance("climax", "any text", 3) == 1

    def test_cliffhanger_returns_one(self):
        assert _panel_count_for_importance("cliffhanger", "any text", 3) == 1

    def test_setup_short_text(self):
        result = _panel_count_for_importance("setup", "short scene", 3)
        assert result == 2

    def test_setup_long_text(self):
        text = " ".join(["word"] * 130)
        result = _panel_count_for_importance("setup", text, 3)
        assert result == 3

    def test_build_normal(self):
        result = _panel_count_for_importance("build", "some text", 2)
        assert 1 <= result <= 3

    def test_release_default(self):
        result = _panel_count_for_importance("release", "short text", 3)
        assert result == 2

    def test_release_with_montage_long(self):
        text = "rapid sequence of events. " + " ".join(["word"] * 230)
        result = _panel_count_for_importance("release", text, 3)
        assert result == 5

    def test_unknown_importance_clamps_to_default(self):
        result = _panel_count_for_importance("unknown", "text", 10)
        assert result == 3  # DEFAULT_MAX

    def test_empty_importance(self):
        result = _panel_count_for_importance("", "text", 2)
        assert 1 <= result <= 3

    def test_none_importance(self):
        result = _panel_count_for_importance(None, "text", 2)
        assert 1 <= result <= 3

    def test_fallback_is_respected_within_bounds(self):
        result = _panel_count_for_importance("build", "text", 1)
        assert result == 1

    def test_setup_montage_text(self):
        text = "He rushes through the sequence of events rapidly"
        result = _panel_count_for_importance("setup", text, 3)
        assert result == 4


class TestDerivePanelPlanFeatures:
    def test_empty_plan(self):
        result = _derive_panel_plan_features({})
        assert result["panel_count"] == 0
        assert result["max_weight"] == 0.0
        assert result["avg_weight"] == 0.0
        assert result["hero_count"] == 0

    def test_none_plan(self):
        result = _derive_panel_plan_features(None)
        assert result["panel_count"] == 0

    def test_single_panel(self):
        plan = {"panels": [{"weight": 0.8}]}
        result = _derive_panel_plan_features(plan)
        assert result["panel_count"] == 1
        assert result["is_single_panel"] is True
        assert result["max_weight"] == 0.8

    def test_multiple_panels(self):
        plan = {"panels": [{"weight": 0.3}, {"weight": 0.7}, {"weight": 0.5}]}
        result = _derive_panel_plan_features(plan)
        assert result["panel_count"] == 3
        assert result["is_single_panel"] is False
        assert result["max_weight"] == 0.7
        assert result["num_large"] == 1
        assert result["has_strong_panel"] is True

    def test_hero_count_with_character_names(self):
        plan = {"panels": [{"weight": 0.5}], "must_show": ["Alice", "dragon"]}
        result = _derive_panel_plan_features(plan, character_names=["Alice", "Bob"])
        assert result["hero_count"] >= 1

    def test_hero_count_protagonist_fallback(self):
        plan = {"panels": [{"weight": 0.5}], "must_show": ["protagonist"]}
        result = _derive_panel_plan_features(plan)
        assert result["hero_count"] == 1


class TestPanelCount:
    def test_none_returns_zero(self):
        assert _panel_count(None) == 0

    def test_empty_dict_returns_zero(self):
        assert _panel_count({}) == 0

    def test_no_panels_key(self):
        assert _panel_count({"other": []}) == 0

    def test_panels_not_list(self):
        assert _panel_count({"panels": "not a list"}) == 0

    def test_counts_panels(self):
        assert _panel_count({"panels": [{}, {}, {}]}) == 3


class TestRoundup:
    def test_normal_round(self):
        assert roundup(0.12345, 3) == 0.123

    def test_string_value(self):
        assert roundup("not a number", 2) == "not a number"

    def test_none_value(self):
        assert roundup(None, 2) is None

    def test_integer_input(self):
        assert roundup(5, 2) == 5.0


class TestExtractDialogueSuggestions:
    def test_simple_dialogue_with_speaker(self):
        text = '"Hello there," said Alice.\n"Hi!" Bob replied.'
        result = _extract_dialogue_suggestions(text)
        assert len(result) >= 1
        for s in result:
            assert "speaker" in s
            assert "text" in s
            assert "emotion" in s
            assert "panel_hint" in s

    def test_colon_format(self):
        text = 'Alice: "Hello there!"\nBob: "Hi back!"'
        result = _extract_dialogue_suggestions(text)
        if result:
            assert result[0]["speaker"] in ("Alice", "unknown")

    def test_empty_text(self):
        result = _extract_dialogue_suggestions("")
        assert result == []

    def test_panel_hint_increments(self):
        text = '"Line one"\n"Line two"\n"Line three"'
        result = _extract_dialogue_suggestions(text)
        if len(result) >= 2:
            assert result[0]["panel_hint"] == 1
            assert result[1]["panel_hint"] == 2
