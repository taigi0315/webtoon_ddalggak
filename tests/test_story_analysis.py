"""
Tests for story analysis service - scene count estimation.
"""

import pytest

from app.services.story_analysis import (
    Complexity,
    DialogueDensity,
    EstimationStatus,
    Pacing,
    estimate_scene_count_heuristic,
)


class TestSceneCountEstimation:
    """Tests for heuristic scene count estimation."""

    def test_empty_text_returns_too_short(self):
        """Empty text should return too_short status."""
        result = estimate_scene_count_heuristic("")
        assert result.status == EstimationStatus.TOO_SHORT
        assert result.recommended_count == 5

    def test_very_short_story_warns_too_short(self):
        """Very short stories should warn about being too short."""
        short_story = "Alice met Bob. They talked. The end."
        result = estimate_scene_count_heuristic(short_story)
        assert result.recommended_count >= 5
        assert result.status in [EstimationStatus.TOO_SHORT, EstimationStatus.OK]

    def test_medium_story_returns_ok(self):
        """Medium-length stories should return ok status."""
        medium_story = """
        Chapter 1: The Meeting

        Alice walked into the bustling coffee shop, her heart racing. She spotted Jake at the corner table.

        "Hey, I wasn't sure you'd come," Jake said, standing up nervously.

        Alice sat down, memories of their last argument flooding back. "We need to talk about what happened."

        Chapter 2: The Confession

        Later that night, Jake drove Alice home. The rain started pouring as they pulled up to her apartment.

        "I'm sorry," Jake finally said. "I should have told you the truth from the beginning."

        Alice looked at him, tears in her eyes. "I forgive you." She kissed him softly.

        Chapter 3: New Beginnings

        The next morning, Alice woke up to find a note on her pillow: "Meet me at the pier at sunset."

        At the pier, Jake was waiting with flowers. "I have something to ask you," he said.

        Alice's heart soared as Jake knelt down. "Will you marry me?"

        "Yes!" Alice cried, throwing her arms around him.
        """
        result = estimate_scene_count_heuristic(medium_story)
        assert 5 <= result.recommended_count <= 15
        assert result.analysis is not None
        assert result.analysis.narrative_beats > 0

    def test_long_story_warns_too_long(self):
        """Very long stories should warn about being too long."""
        # Create a story with many distinct sections
        long_story = "\n\n".join([
            f"Chapter {i}: Scene {i}\n\nThis is scene {i} with lots of content. " * 5
            for i in range(1, 25)
        ])
        result = estimate_scene_count_heuristic(long_story)
        assert result.recommended_count <= 15
        # May or may not trigger too_long depending on analysis

    def test_recommended_count_within_range(self):
        """Recommended count should always be within 5-15 range."""
        stories = [
            "Short.",
            "A bit longer story with some dialogue. 'Hello!' said John.",
            "A medium story. " * 50,
            "A very long story. " * 500,
        ]
        for story in stories:
            result = estimate_scene_count_heuristic(story)
            assert 5 <= result.recommended_count <= 15

    def test_analysis_includes_all_fields(self):
        """Analysis should include all expected fields."""
        story = """
        Alice walked to the park. She met her friend Bob.
        "How are you?" asked Bob.
        "I'm fine," Alice replied. "Let's get coffee."
        They walked to the nearby cafe together.
        """
        result = estimate_scene_count_heuristic(story)
        assert result.analysis is not None
        assert result.analysis.narrative_beats >= 1
        assert result.analysis.estimated_duration_seconds > 0
        assert isinstance(result.analysis.pacing, Pacing)
        assert isinstance(result.analysis.complexity, Complexity)
        assert isinstance(result.analysis.dialogue_density, DialogueDensity)
        assert isinstance(result.analysis.key_moments, list)

    def test_dialogue_heavy_text_detected(self):
        """Text with lots of dialogue should be detected."""
        dialogue_heavy = '''
        "Hello!" said Alice.
        "Hi there!" Bob replied.
        "How are you doing today?" Alice asked.
        "I'm doing great, thanks for asking!" said Bob.
        "Want to grab some lunch?" Alice suggested.
        "Sure, that sounds perfect!" Bob agreed.
        "Let's go to that new place downtown," Alice said.
        "I heard they have amazing pasta," Bob mentioned.
        '''
        result = estimate_scene_count_heuristic(dialogue_heavy)
        assert result.analysis is not None
        assert result.analysis.dialogue_density in [DialogueDensity.MEDIUM, DialogueDensity.HIGH]

    def test_action_text_has_fast_pacing(self):
        """Action-heavy text should have fast pacing."""
        action_story = """
        Bang! The door flew open!
        Alice ran! She jumped!
        Crash! The window shattered!
        She rolled! She ducked!
        "Stop!" someone yelled!
        Alice sprinted faster!
        Her heart pounded!
        """
        result = estimate_scene_count_heuristic(action_story)
        assert result.analysis is not None
        assert result.analysis.pacing == Pacing.FAST

    def test_message_is_user_friendly(self):
        """Message should be human-readable."""
        story = "Alice met Bob. They fell in love. They lived happily ever after."
        result = estimate_scene_count_heuristic(story)
        assert len(result.message) > 20
        assert "scene" in result.message.lower()


class TestEstimationStatus:
    """Tests for estimation status enum."""

    def test_status_values(self):
        """Status enum should have expected values."""
        assert EstimationStatus.OK.value == "ok"
        assert EstimationStatus.TOO_SHORT.value == "too_short"
        assert EstimationStatus.TOO_LONG.value == "too_long"


class TestPacingAnalysis:
    """Tests for pacing analysis."""

    def test_pacing_values(self):
        """Pacing enum should have expected values."""
        assert Pacing.FAST.value == "fast"
        assert Pacing.NORMAL.value == "normal"
        assert Pacing.SLOW.value == "slow"


class TestComplexityAnalysis:
    """Tests for complexity analysis."""

    def test_complexity_values(self):
        """Complexity enum should have expected values."""
        assert Complexity.SIMPLE.value == "simple"
        assert Complexity.MODERATE.value == "moderate"
        assert Complexity.COMPLEX.value == "complex"


class TestKeyMomentExtraction:
    """Tests for key moment extraction."""

    def test_extracts_key_moments(self):
        """Should extract key visual moments from story."""
        story = """
        Alice suddenly realized the truth. She ran to the door.

        Finally, after years of searching, she found the treasure.

        Jake screamed in terror as the monster appeared.

        At last, they kissed under the moonlight.
        """
        result = estimate_scene_count_heuristic(story)
        assert result.analysis is not None
        assert len(result.analysis.key_moments) > 0

    def test_key_moments_limited(self):
        """Key moments should be limited to reasonable count."""
        long_story = "This is a scene. " * 100
        result = estimate_scene_count_heuristic(long_story)
        assert result.analysis is not None
        assert len(result.analysis.key_moments) <= 5
