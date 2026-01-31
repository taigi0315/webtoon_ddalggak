import pytest
from app.graphs import nodes

def test_run_webtoon_script_writer_mocked():
    class FakeGemini:
        def generate_text(self, prompt, model=None, use_fallback=True):
            # Return a JSON string that matches our schema
            return '{"episode_intent": "Test intent", "visual_beats": [{"beat_index": 1, "visual_action": "Action", "dialogue": "Dialogue", "sfx": "SFX", "characters": []}]}'

    story_text = "Once upon a time..."
    characters = [{"name": "Hero", "identity_line": "A brave hero"}]
    
    result = nodes.run_webtoon_script_writer(
        story_text=story_text,
        characters=characters,
        story_style="Fantasy",
        gemini=FakeGemini()
    )
    
    assert result["episode_intent"] == "Test intent"
    assert len(result["visual_beats"]) == 1
    assert result["visual_beats"][0]["visual_action"] == "Action"

def test_run_webtoon_script_writer_fallback():
    # If gemini is None, it should return a fallback
    result = nodes.run_webtoon_script_writer(
        story_text="Original text",
        characters=[],
        gemini=None
    )
    assert result["visual_beats"][0]["visual_action"] == "Original text"
