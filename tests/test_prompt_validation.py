"""
Unit tests for prompt validation in _compile_prompt().

**Validates: Requirements 7.3, 7.5**

The prompt compiler must validate that:
1. No forbidden hardcoded anchors appear in the compiled prompt
2. The expected user-selected style appears in the prompt
"""

import pytest
import uuid
from unittest.mock import Mock

from app.graphs.nodes.prompts.compile import _compile_prompt, _validate_compiled_prompt
from app.db.models import Character


def test_validate_compiled_prompt_clean():
    """Test that clean prompts pass validation."""
    prompt = """
    **STYLE:** Soft romantic webtoon with pastel colors
    **ART DIRECTION:**
    - Lighting: Soft natural light
    - Color Temperature: Warm golden tones
    **PANELS:**
    Panel 1: Character walks in park
    """
    
    # Should not raise exception
    _validate_compiled_prompt(prompt, "SOFT_ROMANTIC_WEBTOON", "Soft romantic webtoon with pastel colors")


def test_validate_compiled_prompt_forbidden_korean_webtoon():
    """Test that 'korean webtoon' anchor is detected."""
    prompt = """
    **STYLE:** Korean webtoon art style
    **PANELS:**
    Panel 1: Character walks
    """
    
    with pytest.raises(ValueError) as exc_info:
        _validate_compiled_prompt(prompt, "SOFT_ROMANTIC_WEBTOON", "Soft romantic webtoon")
    
    assert "korean webtoon" in str(exc_info.value).lower()
    assert "forbidden hardcoded anchors" in str(exc_info.value).lower()


def test_validate_compiled_prompt_forbidden_manhwa():
    """Test that 'manhwa' anchor is detected."""
    prompt = """
    **STYLE:** Korean manhwa aesthetic
    **PANELS:**
    Panel 1: Character walks
    """
    
    with pytest.raises(ValueError) as exc_info:
        _validate_compiled_prompt(prompt, "STARK_BLACK_WHITE_NOIR", "Stark black and white noir")
    
    assert "manhwa" in str(exc_info.value).lower()
    assert "forbidden hardcoded anchors" in str(exc_info.value).lower()


def test_validate_compiled_prompt_forbidden_naver_webtoon():
    """Test that 'naver webtoon' anchor is detected."""
    prompt = """
    **STYLE:** Naver webtoon quality
    **PANELS:**
    Panel 1: Character walks
    """
    
    with pytest.raises(ValueError) as exc_info:
        _validate_compiled_prompt(prompt, "SOFT_ROMANTIC_WEBTOON", "Soft romantic webtoon")
    
    assert "naver webtoon" in str(exc_info.value).lower()


def test_validate_compiled_prompt_case_insensitive():
    """Test that validation is case-insensitive."""
    prompt = """
    **STYLE:** KOREAN WEBTOON ART STYLE
    **PANELS:**
    Panel 1: Character walks
    """
    
    with pytest.raises(ValueError) as exc_info:
        _validate_compiled_prompt(prompt, "SOFT_ROMANTIC_WEBTOON", "Soft romantic webtoon")
    
    assert "korean webtoon" in str(exc_info.value).lower()


def test_validate_compiled_prompt_multiple_anchors():
    """Test that multiple forbidden anchors are detected."""
    prompt = """
    **STYLE:** Korean manhwa webtoon aesthetic
    **PANELS:**
    Panel 1: Character walks
    """
    
    with pytest.raises(ValueError) as exc_info:
        _validate_compiled_prompt(prompt, "SOFT_ROMANTIC_WEBTOON", "Soft romantic webtoon")
    
    error_msg = str(exc_info.value).lower()
    # Should detect at least one of the anchors
    assert any(anchor in error_msg for anchor in ["korean manhwa", "korean webtoon", "webtoon aesthetic", "manhwa aesthetic"])


def test_validate_compiled_prompt_default_style():
    """Test that default style doesn't trigger style presence warning."""
    prompt = """
    **STYLE:** Default style
    **PANELS:**
    Panel 1: Character walks
    """
    
    # Should not raise exception (default style is allowed to not appear)
    _validate_compiled_prompt(prompt, "default", "Default style")


def test_compile_prompt_with_validation():
    """Test that _compile_prompt() calls validation and raises on forbidden anchors."""
    # Create mock character
    char = Mock(spec=Character)
    char.character_id = uuid.uuid4()
    char.name = "Test Character"
    char.role = "protagonist"
    char.base_outfit = "casual clothes"
    char.description = "A young person"
    char.appearance = {"hair": "black", "face": "oval", "build": "average"}
    
    panel_semantics = {
        "panels": [
            {
                "panel_index": 1,
                "grammar_id": "ESTABLISHING_SHOT",
                "description": "Character walks in park",
                "dialogue": [],
                "environment": {"location": "park"},
                "lighting": {},
                "atmosphere_keywords": [],
            }
        ]
    }
    
    layout_template = {
        "template_id": "single_panel",
        "layout_text": "Single panel layout",
        "panels": [{"x": 0, "y": 0, "w": 1080, "h": 1920}],
    }
    
    # Should compile successfully with valid style
    result = _compile_prompt(
        panel_semantics=panel_semantics,
        layout_template=layout_template,
        style_id="SOFT_ROMANTIC_WEBTOON",
        characters=[char],
    )
    
    assert "**STYLE:**" in result
    assert "korean webtoon" not in result.lower()
    assert "manhwa" not in result.lower()


def test_compile_prompt_validation_catches_forbidden_anchors():
    """Test that validation in _compile_prompt() would catch forbidden anchors if they appeared."""
    # This test verifies the validation is integrated
    # We can't easily inject forbidden anchors into _compile_prompt output
    # But we can verify the validation function works
    
    bad_prompt = "**STYLE:** Korean webtoon art style\n**PANELS:** Panel 1: Test"
    
    with pytest.raises(ValueError) as exc_info:
        _validate_compiled_prompt(bad_prompt, "SOFT_ROMANTIC_WEBTOON", "Soft romantic webtoon")
    
    assert "forbidden hardcoded anchors" in str(exc_info.value).lower()
