import pytest
from app.graphs.nodes.utils import _maybe_json_from_gemini


class TestGeminiRepairSuccess:
    def __init__(self):
        self.calls = 0

    def generate_text(self, prompt: str, model=None) -> str:
        # First call simulates malformed LLM output
        self.calls += 1
        if self.calls == 1:
            return 'MALFORMED: {panels: [{grammar_id: establishing}}'  # intentionally malformed
        # Repair call returns valid JSON
        return '{"panels": [{"grammar_id": "establishing"}]}'


def test_maybe_json_repair_success():
    gem = TestGeminiRepairSuccess()
    res = _maybe_json_from_gemini(gem, "Generate a panel plan")
    assert isinstance(res, dict)
    assert isinstance(res.get("panels"), list)
    assert res["panels"][0]["grammar_id"] == "establishing"


class TestGeminiRepairFail:
    def __init__(self):
        self.calls = 0

    def generate_text(self, prompt: str, model=None) -> str:
        self.calls += 1
        if self.calls == 1:
            return 'MALFORMED: {panels: [ }'  # malformed
        # Repair call returns another invalid response
        return 'still not json'


def test_maybe_json_repair_fails():
    gem = TestGeminiRepairFail()
    res = _maybe_json_from_gemini(gem, "Generate a panel plan")
    assert res is None


class TestGeminiRegex:
    def generate_text(self, prompt: str, model=None) -> str:
        return 'Here is the plan:\n{"panels": [{"grammar_id": "establishing"}]}\nThanks'


def test_maybe_json_regex_extracts():
    gem = TestGeminiRegex()
    res = _maybe_json_from_gemini(gem, "Generate a panel plan")
    assert isinstance(res, dict)
    assert res["panels"][0]["grammar_id"] == "establishing"
