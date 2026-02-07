"""Tests for the QC report generation function."""

import pytest
from unittest.mock import patch, MagicMock

from app.graphs.nodes.utils import _qc_report


@pytest.fixture
def mock_qc_rules():
    """Create mock QC rules with standard thresholds."""
    rules = MagicMock()
    rules.max_words_per_panel = 30
    rules.max_words_per_line = 15
    rules.closeup_ratio_max = 0.5
    rules.dialogue_ratio_max = 0.8
    rules.min_silent_panel_ratio = 0.1
    rules.narration_ratio_max = 0.3
    rules.generic_dialogue_ratio_max = 0.3
    rules.repeated_framing_run_length = 3
    rules.environment_keywords = ["forest", "city", "room"]
    return rules


class TestQcReport:
    def test_no_panels_fails(self, mock_qc_rules):
        with patch("app.graphs.nodes.utils.loaders.load_qc_rules_v1", return_value=mock_qc_rules):
            with patch("app.graphs.nodes.utils.record_qc_issues"):
                result = _qc_report({"panels": []}, None)
        assert result["passed"] is False
        assert "no_panels" in result["issues"]
        assert result["metrics"]["panel_count"] == 0

    def test_clean_plan_passes(self, mock_qc_rules):
        panel_plan = {
            "panels": [
                {"grammar_id": "establishing", "panel_index": 0},
                {"grammar_id": "dialogue_medium", "panel_index": 1},
                {"grammar_id": "emotion_closeup", "panel_index": 2},
            ]
        }
        panel_semantics = {
            "panels": [
                {"panel_index": 0, "dialogue": []},
                {"panel_index": 1, "dialogue": ["Hello!"]},
                {"panel_index": 2, "dialogue": []},
            ]
        }
        with patch("app.graphs.nodes.utils.loaders.load_qc_rules_v1", return_value=mock_qc_rules):
            with patch("app.graphs.nodes.utils.record_qc_issues"):
                result = _qc_report(panel_plan, panel_semantics)
        assert result["passed"] is True
        assert result["issues"] == []

    def test_word_count_violation(self, mock_qc_rules):
        mock_qc_rules.max_words_per_panel = 5
        panel_plan = {
            "panels": [{"grammar_id": "dialogue_medium", "panel_index": 0}]
        }
        panel_semantics = {
            "panels": [
                {"panel_index": 0, "dialogue": ["This is a very long dialogue line that exceeds the word limit"]}
            ]
        }
        with patch("app.graphs.nodes.utils.loaders.load_qc_rules_v1", return_value=mock_qc_rules):
            with patch("app.graphs.nodes.utils.record_qc_issues"):
                result = _qc_report(panel_plan, panel_semantics)
        assert "word_count_violation" in result["issues"]

    def test_too_many_closeups(self, mock_qc_rules):
        mock_qc_rules.closeup_ratio_max = 0.3
        panel_plan = {
            "panels": [
                {"grammar_id": "emotion_closeup", "panel_index": 0},
                {"grammar_id": "emotion_closeup", "panel_index": 1},
            ]
        }
        panel_semantics = {
            "panels": [
                {"panel_index": 0, "dialogue": []},
                {"panel_index": 1, "dialogue": []},
            ]
        }
        with patch("app.graphs.nodes.utils.loaders.load_qc_rules_v1", return_value=mock_qc_rules):
            with patch("app.graphs.nodes.utils.record_qc_issues"):
                result = _qc_report(panel_plan, panel_semantics)
        assert "too_many_closeups" in result["issues"]

    def test_monotonous_layout(self, mock_qc_rules):
        mock_qc_rules.repeated_framing_run_length = 3
        panel_plan = {
            "panels": [
                {"grammar_id": "establishing", "panel_index": i, "panel_hierarchy": {"width_percentage": 100}}
                for i in range(4)
            ]
        }
        panel_semantics = {
            "panels": [
                {"panel_index": i, "dialogue": []}
                for i in range(4)
            ]
        }
        with patch("app.graphs.nodes.utils.loaders.load_qc_rules_v1", return_value=mock_qc_rules):
            with patch("app.graphs.nodes.utils.record_qc_issues"):
                result = _qc_report(panel_plan, panel_semantics)
        assert "monotonous_layout" in result["issues"]

    def test_dialogue_redundancy_detected(self, mock_qc_rules):
        panel_plan = {
            "panels": [{"grammar_id": "dialogue_medium", "panel_index": 0}]
        }
        panel_semantics = {
            "panels": [
                {"panel_index": 0, "dialogue": ["Look at how I am showing you this!"]}
            ]
        }
        with patch("app.graphs.nodes.utils.loaders.load_qc_rules_v1", return_value=mock_qc_rules):
            with patch("app.graphs.nodes.utils.record_qc_issues"):
                result = _qc_report(panel_plan, panel_semantics)
        assert "dialogue_redundancy" in result["issues"]

    def test_metrics_included(self, mock_qc_rules):
        panel_plan = {"panels": [{"grammar_id": "establishing", "panel_index": 0}]}
        panel_semantics = {"panels": [{"panel_index": 0, "dialogue": []}]}
        with patch("app.graphs.nodes.utils.loaders.load_qc_rules_v1", return_value=mock_qc_rules):
            with patch("app.graphs.nodes.utils.record_qc_issues"):
                result = _qc_report(panel_plan, panel_semantics)
        metrics = result["metrics"]
        assert "panel_count" in metrics
        assert "closeup_count" in metrics
        assert "dialogue_count" in metrics
        assert "silent_panel_count" in metrics

    def test_summary_message(self, mock_qc_rules):
        panel_plan = {"panels": [{"grammar_id": "establishing", "panel_index": 0}]}
        panel_semantics = {"panels": [{"panel_index": 0, "dialogue": []}]}
        with patch("app.graphs.nodes.utils.loaders.load_qc_rules_v1", return_value=mock_qc_rules):
            with patch("app.graphs.nodes.utils.record_qc_issues"):
                result = _qc_report(panel_plan, panel_semantics)
        assert "summary" in result
        assert isinstance(result["summary"], str)
