"""Property-based and unit tests for Cinematographer layout focus.

Tests that Cinematographer focuses on layout/composition and avoids style keywords.
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.graphs.nodes.planning.panel_semantics import (
    _detect_style_keywords_in_panel_semantics,
    FORBIDDEN_CINEMATOGRAPHER_KEYWORDS,
)


@pytest.mark.property
class TestCinematographerLayoutFocus:
    """Property 3: Cinematographer Layout Focus
    
    For any panel semantics output, the Cinematographer should focus on
    layout and composition, avoiding lighting/color/mood keywords.
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4
    """
    
    @given(
        description=st.text(min_size=50, max_size=200),
    )
    @settings(max_examples=100, deadline=None)
    def test_panel_descriptions_without_style_keywords_pass_validation(self, description):
        """Property: Panel descriptions without style keywords should pass validation."""
        # Create panel semantics without forbidden keywords
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "description": description,
                    "camera": "medium",
                }
            ]
        }
        
        # If description doesn't contain forbidden keywords, should pass
        has_forbidden = any(
            keyword.lower() in description.lower()
            for keyword in FORBIDDEN_CINEMATOGRAPHER_KEYWORDS
        )
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        if has_forbidden:
            # Should detect the keywords
            assert len(detected) > 0, (
                f"Should detect forbidden keywords in description: {description}"
            )
        else:
            # Should not detect any keywords
            assert len(detected) == 0, (
                f"Should not detect keywords in clean description: {description}, "
                f"but detected: {detected}"
            )


class TestCinematographerStyleKeywordDetection:
    """Unit tests for style keyword detection in Cinematographer output.
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4
    """
    
    def test_detects_lighting_keywords(self):
        """Test that lighting keywords are detected."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "description": "A medium shot with soft lighting illuminating the character's face.",
                }
            ]
        }
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        assert len(detected) > 0
        assert any("soft lighting" in d.lower() for d in detected)
    
    def test_detects_color_temperature_keywords(self):
        """Test that color temperature keywords are detected."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "description": "A wide shot with warm golden tones filling the scene.",
                }
            ]
        }
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        assert len(detected) > 0
        assert any("warm" in d.lower() or "golden" in d.lower() for d in detected)
    
    def test_detects_atmospheric_mood_keywords(self):
        """Test that atmospheric mood keywords are detected."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "description": "A tense closeup with mysterious shadows.",
                }
            ]
        }
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        assert len(detected) > 0
        assert any("tense" in d.lower() or "mysterious" in d.lower() for d in detected)
    
    def test_detects_lighting_field_presence(self):
        """Test that presence of 'lighting' field is detected."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "description": "A medium shot of the character.",
                    "lighting": {
                        "source": "natural",
                        "quality": "soft",
                    }
                }
            ]
        }
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        assert len(detected) > 0
        assert any("lighting" in d.lower() and "field present" in d.lower() for d in detected)
    
    def test_detects_atmosphere_keywords_field_presence(self):
        """Test that presence of 'atmosphere_keywords' field is detected."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "description": "A medium shot of the character.",
                    "atmosphere_keywords": ["tense", "dramatic"],
                }
            ]
        }
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        assert len(detected) > 0
        assert any("atmosphere_keywords" in d.lower() and "field present" in d.lower() for d in detected)
    
    def test_clean_layout_description_passes(self):
        """Test that clean layout-focused description passes validation."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "description": (
                        "Medium shot, vertical 9:16 panel. Character positioned center frame, "
                        "standing in modern office with glass walls, wooden desk, laptop, "
                        "coffee mug. Background shows city skyline through windows. "
                        "Character facing camera, arms crossed, confident posture."
                    ),
                    "camera": "medium",
                    "environment": {
                        "location": "modern office",
                        "architecture": "glass walls, wooden floor",
                        "furniture": "desk, chair",
                        "props": ["laptop", "coffee mug"],
                    }
                }
            ]
        }
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        assert len(detected) == 0, f"Clean layout description should pass, but detected: {detected}"
    
    def test_multiple_panels_with_mixed_content(self):
        """Test detection across multiple panels with mixed content."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "description": "Wide shot of city street with buildings and pedestrians.",
                },
                {
                    "panel_index": 2,
                    "description": "Close-up with dramatic lighting and tense atmosphere.",
                },
                {
                    "panel_index": 3,
                    "description": "Medium shot of character at desk with computer.",
                }
            ]
        }
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        # Should detect keywords in panel 2 only
        assert len(detected) > 0
        assert any("Panel 2" in d for d in detected)
        assert not any("Panel 1" in d for d in detected)
        assert not any("Panel 3" in d for d in detected)
    
    def test_handles_empty_panels_list(self):
        """Test that empty panels list is handled gracefully."""
        panel_semantics = {"panels": []}
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        assert len(detected) == 0
    
    def test_handles_missing_panels_key(self):
        """Test that missing 'panels' key is handled gracefully."""
        panel_semantics = {}
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        assert len(detected) == 0
    
    def test_handles_non_dict_panel_items(self):
        """Test that non-dict panel items are handled gracefully."""
        panel_semantics = {
            "panels": [
                "invalid panel",
                {"panel_index": 2, "description": "Valid panel"},
            ]
        }
        
        detected = _detect_style_keywords_in_panel_semantics(panel_semantics)
        
        # Should not crash, should process valid panel
        assert isinstance(detected, list)
