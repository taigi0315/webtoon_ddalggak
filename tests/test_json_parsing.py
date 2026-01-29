"""Tests for JSON parsing utilities with self-repair."""

import pytest

from app.graphs.nodes.utils import (
    _strip_markdown_fences,
    _clean_json_text,
    _extract_json_object,
    _extract_json_array,
)


class TestStripMarkdownFences:
    """Tests for _strip_markdown_fences function."""

    def test_strips_json_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_strips_plain_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_handles_no_fence(self):
        text = '{"key": "value"}'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_handles_fence_with_extra_text(self):
        text = 'Here is the JSON:\n```json\n{"key": "value"}\n```\nDone!'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_case_insensitive(self):
        text = '```JSON\n{"key": "value"}\n```'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'


class TestCleanJsonText:
    """Tests for _clean_json_text function."""

    def test_removes_trailing_commas(self):
        text = '{"items": [1, 2, 3,], "name": "test",}'
        result = _clean_json_text(text)
        assert result == '{"items": [1, 2, 3], "name": "test"}'

    def test_removes_leading_prose(self):
        text = 'Here is the JSON output:\n{"key": "value"}'
        result = _clean_json_text(text)
        assert result == '{"key": "value"}'

    def test_removes_trailing_prose(self):
        text = '{"key": "value"}\n\nI hope this helps!'
        result = _clean_json_text(text)
        assert result == '{"key": "value"}'

    def test_handles_array(self):
        text = 'Output:\n[1, 2, 3,]\nEnd'
        result = _clean_json_text(text)
        assert result == '[1, 2, 3]'

    def test_combined_cleaning(self):
        text = '```json\n{"items": [1, 2,],}\n```\nDone!'
        result = _clean_json_text(text)
        assert result == '{"items": [1, 2]}'


class TestExtractJsonObject:
    """Tests for _extract_json_object function."""

    def test_extracts_simple_object(self):
        text = '{"key": "value"}'
        result = _extract_json_object(text)
        assert result == '{"key": "value"}'

    def test_extracts_nested_object(self):
        text = '{"outer": {"inner": "value"}}'
        result = _extract_json_object(text)
        assert result == '{"outer": {"inner": "value"}}'

    def test_extracts_from_prose(self):
        text = 'Here is the result: {"key": "value"} and more text'
        result = _extract_json_object(text)
        assert result == '{"key": "value"}'

    def test_handles_strings_with_braces(self):
        text = '{"text": "Hello {world}"}'
        result = _extract_json_object(text)
        assert result == '{"text": "Hello {world}"}'

    def test_handles_escaped_quotes(self):
        text = '{"text": "He said \\"hello\\""}'
        result = _extract_json_object(text)
        assert result == '{"text": "He said \\"hello\\""}'

    def test_returns_none_for_no_object(self):
        text = 'No JSON here'
        result = _extract_json_object(text)
        assert result is None

    def test_handles_complex_nested(self):
        text = '{"a": {"b": {"c": "d"}}, "e": [1, 2, {"f": "g"}]}'
        result = _extract_json_object(text)
        assert result == '{"a": {"b": {"c": "d"}}, "e": [1, 2, {"f": "g"}]}'


class TestExtractJsonArray:
    """Tests for _extract_json_array function."""

    def test_extracts_simple_array(self):
        text = '[1, 2, 3]'
        result = _extract_json_array(text)
        assert result == '[1, 2, 3]'

    def test_extracts_nested_array(self):
        text = '[[1, 2], [3, 4]]'
        result = _extract_json_array(text)
        assert result == '[[1, 2], [3, 4]]'

    def test_extracts_from_prose(self):
        text = 'The result is: [1, 2, 3] as expected'
        result = _extract_json_array(text)
        assert result == '[1, 2, 3]'

    def test_handles_strings_with_brackets(self):
        text = '["text with [brackets]"]'
        result = _extract_json_array(text)
        assert result == '["text with [brackets]"]'

    def test_returns_none_for_no_array(self):
        text = 'No array here'
        result = _extract_json_array(text)
        assert result is None

    def test_handles_array_of_objects(self):
        text = '[{"a": 1}, {"b": 2}]'
        result = _extract_json_array(text)
        assert result == '[{"a": 1}, {"b": 2}]'


class TestJsonParsingIntegration:
    """Integration tests for JSON parsing scenarios."""

    def test_llm_output_with_explanation(self):
        """Test typical LLM output with explanation before JSON."""
        text = """Based on the scene, here is the panel plan:

```json
{
  "panels": [
    {"panel_index": 1, "grammar_id": "establishing"},
    {"panel_index": 2, "grammar_id": "dialogue_medium"},
  ]
}
```

This plan creates a good flow for the scene."""

        cleaned = _clean_json_text(text)
        obj = _extract_json_object(cleaned)
        assert obj is not None
        assert '"panels"' in obj

    def test_malformed_trailing_comma(self):
        """Test JSON with trailing commas gets cleaned."""
        text = '{"items": ["a", "b", "c",], "count": 3,}'
        cleaned = _clean_json_text(text)
        import json
        result = json.loads(cleaned)
        assert result["items"] == ["a", "b", "c"]
        assert result["count"] == 3
