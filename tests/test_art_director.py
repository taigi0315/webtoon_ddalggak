"""Property-based and unit tests for Art Director node.

Tests that Art Director generates style-compatible art direction.
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.graphs.nodes.planning.art_direction import (
    _validate_art_direction,
    _is_monochrome_style,
    _fallback_art_direction,
)


@pytest.mark.property
class TestArtDirectorStyleCompatibility:
    """Property 6: Art Director Style Compatibility
    
    For any art direction output, the validation function should ensure
    compatibility with the selected image style, especially for monochrome styles.
    
    Validates: Requirements 5.2, 5.4
    """
    
    @given(
        lighting=st.text(min_size=10, max_size=100),
        color_temp=st.sampled_from([
            "warm", "cool", "neutral", "warm golden", "cool blue",
            "N/A", "N/A (monochrome)", ""
        ]),
        atmosphere=st.lists(
            st.sampled_from([
                "tense", "mysterious", "noir", "shadowy", "dramatic",
                "warm", "cool", "golden", "blue", "colorful", "vibrant"
            ]),
            min_size=1,
            max_size=5
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_monochrome_style_removes_color_references(
        self, lighting, color_temp, atmosphere
    ):
        """Property: Monochrome styles should have N/A color temperature and no color keywords."""
        monochrome_styles = [
            "STARK_BLACK_WHITE_NOIR",
            "BLACK_WHITE_NOIR",
            "MONOCHROME_STYLE",
        ]
        
        for style_id in monochrome_styles:
            art_direction = {
                "lighting": lighting,
                "color_temperature": color_temp,
                "atmosphere_keywords": atmosphere,
            }
            
            validated = _validate_art_direction(art_direction, style_id)
            
            # Verify color temperature is N/A
            assert validated["color_temperature"].upper().startswith("N/A"), (
                f"Monochrome style {style_id} should have N/A color temperature, "
                f"got: {validated['color_temperature']}"
            )
            
            # Verify no color keywords in atmosphere
            color_keywords = [
                "warm", "cool", "golden", "blue", "red", "green", "yellow",
                "orange", "purple", "pink", "pastel", "vibrant", "colorful",
            ]
            
            atmosphere_lower = " ".join(validated["atmosphere_keywords"]).lower()
            for color_kw in color_keywords:
                assert color_kw not in atmosphere_lower, (
                    f"Monochrome style {style_id} should not have color keyword '{color_kw}' "
                    f"in atmosphere: {validated['atmosphere_keywords']}"
                )


class TestArtDirectorMonochromeHandling:
    """Unit tests for monochrome style handling.
    
    Validates: Requirements 5.5
    """
    
    def test_stark_black_white_noir_produces_na_color_temperature(self):
        """Test STARK_BLACK_WHITE_NOIR produces N/A color temperature."""
        art_direction = {
            "lighting": "dramatic low-key lighting",
            "color_temperature": "cool blue tones",
            "atmosphere_keywords": ["tense", "noir", "shadowy"],
        }
        
        validated = _validate_art_direction(art_direction, "STARK_BLACK_WHITE_NOIR")
        
        assert validated["color_temperature"] == "N/A (monochrome)"
    
    def test_monochrome_style_removes_color_keywords_from_atmosphere(self):
        """Test no color keywords in atmosphere for monochrome styles."""
        art_direction = {
            "lighting": "dramatic lighting",
            "color_temperature": "warm golden",
            "atmosphere_keywords": ["tense", "warm", "golden", "noir", "blue"],
        }
        
        validated = _validate_art_direction(art_direction, "BLACK_WHITE_NOIR")
        
        # Verify color keywords removed
        atmosphere_lower = " ".join(validated["atmosphere_keywords"]).lower()
        assert "warm" not in atmosphere_lower
        assert "golden" not in atmosphere_lower
        assert "blue" not in atmosphere_lower
        
        # Verify non-color keywords preserved
        assert "tense" in validated["atmosphere_keywords"]
        assert "noir" in validated["atmosphere_keywords"]
    
    def test_is_monochrome_style_detection(self):
        """Test monochrome style detection."""
        # Monochrome styles
        assert _is_monochrome_style("STARK_BLACK_WHITE_NOIR")
        assert _is_monochrome_style("BLACK_WHITE_NOIR")
        assert _is_monochrome_style("MONOCHROME")
        assert _is_monochrome_style("NOIR_STYLE")
        
        # Non-monochrome styles
        assert not _is_monochrome_style("SOFT_ROMANTIC_WEBTOON")
        assert not _is_monochrome_style("VIBRANT_FANTASY_WEBTOON")
        assert not _is_monochrome_style("CINEMATIC_MODERN_MANHWA")
        assert not _is_monochrome_style("default")
    
    def test_fallback_art_direction_for_monochrome(self):
        """Test fallback art direction for monochrome styles."""
        fallback = _fallback_art_direction("STARK_BLACK_WHITE_NOIR")
        
        assert fallback["color_temperature"] == "N/A (monochrome)"
        assert fallback["lighting"] == "balanced natural lighting"
        assert isinstance(fallback["atmosphere_keywords"], list)
        assert fallback["compatible_with_style"] is True
    
    def test_fallback_art_direction_for_color_style(self):
        """Test fallback art direction for color styles."""
        fallback = _fallback_art_direction("SOFT_ROMANTIC_WEBTOON")
        
        assert fallback["color_temperature"] == "neutral"
        assert fallback["lighting"] == "balanced natural lighting"
        assert isinstance(fallback["atmosphere_keywords"], list)
        assert fallback["compatible_with_style"] is True
    
    def test_validation_preserves_na_color_temperature(self):
        """Test that N/A color temperature is preserved."""
        art_direction = {
            "lighting": "dramatic lighting",
            "color_temperature": "N/A (monochrome)",
            "atmosphere_keywords": ["tense", "noir"],
        }
        
        validated = _validate_art_direction(art_direction, "STARK_BLACK_WHITE_NOIR")
        
        assert validated["color_temperature"] == "N/A (monochrome)"
    
    def test_validation_sets_compatible_flag(self):
        """Test that validation sets compatible_with_style flag."""
        art_direction = {
            "lighting": "soft lighting",
            "color_temperature": "warm",
            "atmosphere_keywords": ["romantic", "dreamy"],
        }
        
        validated = _validate_art_direction(art_direction, "SOFT_ROMANTIC_WEBTOON")
        
        assert validated["compatible_with_style"] is True
    
    def test_validation_handles_empty_atmosphere(self):
        """Test that validation handles empty atmosphere keywords."""
        art_direction = {
            "lighting": "balanced lighting",
            "color_temperature": "neutral",
            "atmosphere_keywords": [],
        }
        
        validated = _validate_art_direction(art_direction, "default")
        
        assert validated["atmosphere_keywords"] == []
        assert validated["compatible_with_style"] is True
    
    def test_validation_handles_none_atmosphere(self):
        """Test that validation handles None atmosphere keywords."""
        art_direction = {
            "lighting": "balanced lighting",
            "color_temperature": "neutral",
            "atmosphere_keywords": None,
        }
        
        validated = _validate_art_direction(art_direction, "default")
        
        # Should not crash, atmosphere_keywords should be handled gracefully
        assert validated["compatible_with_style"] is True
    
    def test_color_style_preserves_color_temperature(self):
        """Test that color styles preserve color temperature."""
        art_direction = {
            "lighting": "soft golden-hour lighting",
            "color_temperature": "warm (golden hour bias)",
            "atmosphere_keywords": ["romantic", "dreamy", "warm"],
        }
        
        validated = _validate_art_direction(art_direction, "SOFT_ROMANTIC_WEBTOON")
        
        assert validated["color_temperature"] == "warm (golden hour bias)"
        assert "warm" in validated["atmosphere_keywords"]
