"""Property-based tests for character normalization style neutralization.

Tests that character normalization produces style-neutral output.
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.graphs.nodes.planning.character import (
    _sanitize_character_output,
    FORBIDDEN_STYLE_KEYWORDS,
)


@pytest.mark.property
class TestCharacterStyleNeutralization:
    """Property 1: Character Style Neutralization
    
    For any character output from LLM, the sanitization function should remove
    all forbidden style keywords while preserving morphological information.
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """
    
    @given(
        identity_line=st.text(min_size=10, max_size=200),
        hair=st.text(min_size=5, max_size=50),
        face=st.text(min_size=5, max_size=50),
        build=st.text(min_size=5, max_size=50),
    )
    @settings(max_examples=100, deadline=None)
    def test_sanitization_removes_all_style_keywords(
        self, identity_line, hair, face, build
    ):
        """Property: Sanitization removes all forbidden style keywords."""
        # Create character with potentially contaminated text
        char = {
            "name": "Test Character",
            "identity_line": identity_line,
            "appearance": {
                "hair": hair,
                "face": face,
                "build": build,
            },
            "outfit": "casual clothes",
            "description": "test description",
        }
        
        # Sanitize
        sanitized = _sanitize_character_output(char, "Test Character")
        
        # Verify no forbidden keywords in any field
        fields_to_check = [
            sanitized.get("identity_line", ""),
            sanitized.get("appearance", {}).get("hair", ""),
            sanitized.get("appearance", {}).get("face", ""),
            sanitized.get("appearance", {}).get("build", ""),
            sanitized.get("outfit", ""),
            sanitized.get("description", ""),
        ]
        
        for field_value in fields_to_check:
            if field_value:
                field_lower = field_value.lower()
                for keyword in FORBIDDEN_STYLE_KEYWORDS:
                    assert keyword.lower() not in field_lower, (
                        f"Forbidden keyword '{keyword}' found in sanitized output: {field_value}"
                    )
    
    def test_sanitization_removes_manhwa_keyword(self):
        """Test that 'manhwa' keyword is removed."""
        char = {
            "name": "Alice",
            "identity_line": "young adult female, black hair, Korean manhwa aesthetic",
            "appearance": {
                "hair": "black hair with manhwa style",
                "face": "oval face",
                "build": "slender build",
            },
        }
        
        sanitized = _sanitize_character_output(char, "Alice")
        
        assert "manhwa" not in sanitized["identity_line"].lower()
        assert "manhwa" not in sanitized["appearance"]["hair"].lower()
    
    def test_sanitization_removes_webtoon_keyword(self):
        """Test that 'webtoon' keyword is removed."""
        char = {
            "name": "Bob",
            "identity_line": "young adult male, brown hair, webtoon protagonist style",
            "appearance": {
                "hair": "brown hair",
                "face": "angular face with webtoon features",
                "build": "tall athletic build",
            },
        }
        
        sanitized = _sanitize_character_output(char, "Bob")
        
        assert "webtoon" not in sanitized["identity_line"].lower()
        assert "webtoon" not in sanitized["appearance"]["face"].lower()
    
    def test_sanitization_removes_aesthetic_keyword(self):
        """Test that 'aesthetic' keyword is removed."""
        char = {
            "name": "Charlie",
            "identity_line": "teen male, blonde hair, flower-boy aesthetic",
            "appearance": {
                "hair": "blonde hair",
                "face": "soft features with aesthetic appeal",
                "build": "slender build",
            },
        }
        
        sanitized = _sanitize_character_output(char, "Charlie")
        
        assert "aesthetic" not in sanitized["identity_line"].lower()
        assert "aesthetic" not in sanitized["appearance"]["face"].lower()
    
    def test_sanitization_removes_multiple_keywords(self):
        """Test that multiple keywords are removed from same field."""
        char = {
            "name": "Diana",
            "identity_line": "young adult female, long black hair, statuesque figure, authentic Korean webtoon romance female lead aesthetic",
            "appearance": {
                "hair": "long flowing black hair",
                "face": "delicate features",
                "build": "statuesque willowy figure",
            },
        }
        
        sanitized = _sanitize_character_output(char, "Diana")
        
        # Check identity_line
        identity_lower = sanitized["identity_line"].lower()
        assert "statuesque" not in identity_lower
        assert "authentic" not in identity_lower
        assert "webtoon" not in identity_lower
        assert "romance female lead" not in identity_lower
        assert "aesthetic" not in identity_lower
        
        # Check build
        build_lower = sanitized["appearance"]["build"].lower()
        assert "statuesque" not in build_lower
        assert "willowy" not in build_lower
    
    def test_sanitization_preserves_morphological_info(self):
        """Test that morphological information is preserved."""
        char = {
            "name": "Eve",
            "identity_line": "young adult female, long black hair, 168cm tall, slender build, Korean manhwa style",
            "appearance": {
                "hair": "long black hair with soft waves",
                "face": "oval face with large eyes",
                "build": "slender build, 168cm, long legs",
            },
            "outfit": "cream sweater and jeans",
        }
        
        sanitized = _sanitize_character_output(char, "Eve")
        
        # Verify morphological info is preserved
        assert "long black hair" in sanitized["identity_line"]
        assert "168cm" in sanitized["identity_line"]
        assert "slender build" in sanitized["identity_line"]
        
        assert "long black hair" in sanitized["appearance"]["hair"]
        assert "soft waves" in sanitized["appearance"]["hair"]
        
        assert "oval face" in sanitized["appearance"]["face"]
        assert "large eyes" in sanitized["appearance"]["face"]
        
        assert "slender build" in sanitized["appearance"]["build"]
        assert "168cm" in sanitized["appearance"]["build"]
        assert "long legs" in sanitized["appearance"]["build"]
        
        assert "cream sweater" in sanitized["outfit"]
        assert "jeans" in sanitized["outfit"]
    
    def test_sanitization_handles_case_insensitive(self):
        """Test that keyword removal is case-insensitive."""
        char = {
            "name": "Frank",
            "identity_line": "young adult male, MANHWA style, Webtoon aesthetic, Korean Male Lead",
            "appearance": {
                "hair": "black hair",
                "face": "angular face",
                "build": "tall build",
            },
        }
        
        sanitized = _sanitize_character_output(char, "Frank")
        
        identity_lower = sanitized["identity_line"].lower()
        assert "manhwa" not in identity_lower
        assert "webtoon" not in identity_lower
        assert "korean male lead" not in identity_lower
    
    def test_sanitization_cleans_up_extra_spaces(self):
        """Test that extra spaces are cleaned up after keyword removal."""
        char = {
            "name": "Grace",
            "identity_line": "young adult female, black hair, manhwa style, slender build",
            "appearance": {
                "hair": "black hair with webtoon styling",
                "face": "oval face",
                "build": "slender build",
            },
        }
        
        sanitized = _sanitize_character_output(char, "Grace")
        
        # Verify no double spaces
        assert "  " not in sanitized["identity_line"]
        assert "  " not in sanitized["appearance"]["hair"]
        
        # Verify no leading/trailing commas or spaces
        assert not sanitized["identity_line"].startswith(",")
        assert not sanitized["identity_line"].endswith(",")
        assert not sanitized["identity_line"].startswith(" ")
        assert not sanitized["identity_line"].endswith(" ")
    
    def test_sanitization_handles_none_values(self):
        """Test that None values are handled gracefully."""
        char = {
            "name": "Henry",
            "identity_line": None,
            "appearance": {
                "hair": None,
                "face": "oval face",
                "build": None,
            },
            "outfit": None,
            "description": None,
        }
        
        sanitized = _sanitize_character_output(char, "Henry")
        
        # Verify None values are preserved
        assert sanitized["identity_line"] is None
        assert sanitized["appearance"]["hair"] is None
        assert sanitized["appearance"]["build"] is None
        assert sanitized["outfit"] is None
        assert sanitized["description"] is None
    
    def test_sanitization_handles_empty_strings(self):
        """Test that empty strings are handled gracefully."""
        char = {
            "name": "Iris",
            "identity_line": "",
            "appearance": {
                "hair": "",
                "face": "oval face",
                "build": "",
            },
            "outfit": "",
        }
        
        sanitized = _sanitize_character_output(char, "Iris")
        
        # Verify empty strings are preserved
        assert sanitized["identity_line"] == ""
        assert sanitized["appearance"]["hair"] == ""
        assert sanitized["appearance"]["build"] == ""
        assert sanitized["outfit"] == ""
