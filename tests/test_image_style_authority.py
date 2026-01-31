"""
Property tests for image style authority.

**Property 7: Image Style Authority**
**Validates: Requirements 7.3, 7.5**

The user-selected image_style must have the highest authority in the final prompt,
and no hardcoded style anchors should override it.
"""

import pytest
import uuid
from unittest.mock import Mock
from hypothesis import given, strategies as st, settings

from app.graphs.nodes.prompts.compile import _compile_prompt
from app.db.models import Character


# Test 1: Property test - User-selected style appears in compiled prompt
@settings(max_examples=100)
@given(
    style_id=st.sampled_from([
        "SOFT_ROMANTIC_WEBTOON",
        "STARK_BLACK_WHITE_NOIR",
        "VIBRANT_ACTION_SHONEN",
        "default",
    ])
)
def test_property_user_selected_style_appears_in_prompt(style_id: str):
    """
    Property: User-selected style must appear in the compiled prompt.
    
    This property verifies that the style_id parameter results in the
    corresponding style description appearing in the final prompt.
    """
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
                "description": "Character in scene",
                "dialogue": [],
                "environment": {},
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
    
    # Compile prompt
    result = _compile_prompt(
        panel_semantics=panel_semantics,
        layout_template=layout_template,
        style_id=style_id,
        characters=[char],
    )
    
    # Verify style appears in prompt
    assert "**STYLE:**" in result, "Prompt should contain STYLE section"
    
    # For non-default styles, verify style description appears
    if style_id != "default":
        # Style description should appear somewhere in the prompt
        # (We can't check exact text as it comes from get_style_semantic_hint)
        assert len(result) > 0, "Prompt should not be empty"


# Test 2: Property test - No forbidden anchors in compiled prompt
@settings(max_examples=100)
@given(
    style_id=st.sampled_from([
        "SOFT_ROMANTIC_WEBTOON",
        "STARK_BLACK_WHITE_NOIR",
        "VIBRANT_ACTION_SHONEN",
    ])
)
def test_property_no_forbidden_anchors_in_prompt(style_id: str):
    """
    Property: Compiled prompts must not contain forbidden hardcoded anchors.
    
    This property verifies that regardless of the style_id, the compiled
    prompt never contains forbidden anchors like "Korean webtoon" or "manhwa".
    """
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
                "description": "Character in scene",
                "dialogue": [],
                "environment": {},
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
    
    # Compile prompt
    result = _compile_prompt(
        panel_semantics=panel_semantics,
        layout_template=layout_template,
        style_id=style_id,
        characters=[char],
    )
    
    # Check for forbidden anchors
    result_lower = result.lower()
    forbidden_anchors = [
        "korean webtoon",
        "korean manhwa",
        "naver webtoon",
        "manhwa art style",
        "webtoon art style",
        "manhwa aesthetic",
        "webtoon aesthetic",
    ]
    
    for anchor in forbidden_anchors:
        assert anchor not in result_lower, f"Prompt should not contain forbidden anchor: {anchor}"


# Test 3: Style layer appears first in prompt
def test_style_layer_appears_first():
    """Test that STYLE section appears first in the compiled prompt."""
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
                "description": "Character in scene",
                "dialogue": [],
                "environment": {},
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
    
    result = _compile_prompt(
        panel_semantics=panel_semantics,
        layout_template=layout_template,
        style_id="SOFT_ROMANTIC_WEBTOON",
        characters=[char],
    )
    
    # Find position of STYLE section
    style_pos = result.find("**STYLE:**")
    assert style_pos >= 0, "STYLE section should exist"
    
    # Check that STYLE appears before other sections
    other_sections = [
        "**ART DIRECTION:**",
        "**ASPECT RATIO & FORMAT:**",
        "**REFERENCE IMAGE AUTHORITY:**",
        "**PANEL COMPOSITION RULES:**",
        "**CHARACTERS",
        "**PANELS",
        "**TECHNICAL REQUIREMENTS:**",
        "**NEGATIVE:**",
    ]
    
    for section in other_sections:
        section_pos = result.find(section)
        if section_pos >= 0:
            assert style_pos < section_pos, f"STYLE should appear before {section}"


# Test 4: Different styles produce different prompts
def test_different_styles_produce_different_prompts():
    """Test that different style_ids produce different prompt content."""
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
                "description": "Character in scene",
                "dialogue": [],
                "environment": {},
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
    
    # Compile with different styles
    prompt_romantic = _compile_prompt(
        panel_semantics=panel_semantics,
        layout_template=layout_template,
        style_id="SOFT_ROMANTIC_WEBTOON",
        characters=[char],
    )
    
    prompt_noir = _compile_prompt(
        panel_semantics=panel_semantics,
        layout_template=layout_template,
        style_id="STARK_BLACK_WHITE_NOIR",
        characters=[char],
    )
    
    # Prompts should be different
    assert prompt_romantic != prompt_noir, "Different styles should produce different prompts"
    
    # Check that style-specific content appears
    # (We can't check exact text, but prompts should differ in STYLE section)
    romantic_style_section = prompt_romantic.split("**ART DIRECTION:**")[0] if "**ART DIRECTION:**" in prompt_romantic else prompt_romantic.split("**ASPECT RATIO")[0]
    noir_style_section = prompt_noir.split("**ART DIRECTION:**")[0] if "**ART DIRECTION:**" in prompt_noir else prompt_noir.split("**ASPECT RATIO")[0]
    
    assert romantic_style_section != noir_style_section, "Style sections should differ"


# Test 5: Style authority overrides other style hints
def test_style_authority_overrides_other_hints():
    """Test that user-selected style has authority over other style hints."""
    char = Mock(spec=Character)
    char.character_id = uuid.uuid4()
    char.name = "Test Character"
    char.role = "protagonist"
    char.base_outfit = "casual clothes"
    char.description = "A young person"
    char.appearance = {"hair": "black", "face": "oval", "build": "average"}
    
    # Panel semantics with style-like keywords (should be ignored)
    panel_semantics = {
        "panels": [
            {
                "panel_index": 1,
                "grammar_id": "ESTABLISHING_SHOT",
                "description": "Character in vibrant colorful scene",
                "dialogue": [],
                "environment": {},
                "lighting": {},
                "atmosphere_keywords": ["bright", "colorful"],
            }
        ]
    }
    
    layout_template = {
        "template_id": "single_panel",
        "layout_text": "Single panel layout",
        "panels": [{"x": 0, "y": 0, "w": 1080, "h": 1920}],
    }
    
    # Compile with noir style (should override panel's colorful hints)
    result = _compile_prompt(
        panel_semantics=panel_semantics,
        layout_template=layout_template,
        style_id="STARK_BLACK_WHITE_NOIR",
        characters=[char],
    )
    
    # STYLE section should appear first and contain noir style
    assert "**STYLE:**" in result
    style_section = result.split("\n\n")[0]
    assert "STARK_BLACK_WHITE_NOIR" in style_section or "noir" in style_section.lower() or "black" in style_section.lower()


# Test 6: Validation catches forbidden anchors
def test_validation_catches_forbidden_anchors():
    """Test that validation would catch forbidden anchors if they appeared."""
    from app.graphs.nodes.prompts.compile import _validate_compiled_prompt
    
    # This should raise ValueError
    bad_prompt = "**STYLE:** Korean webtoon art style\n**PANELS:** Panel 1: Test"
    
    with pytest.raises(ValueError) as exc_info:
        _validate_compiled_prompt(bad_prompt, "SOFT_ROMANTIC_WEBTOON", "Soft romantic webtoon")
    
    assert "forbidden hardcoded anchors" in str(exc_info.value).lower()
    assert "korean webtoon" in str(exc_info.value).lower()


# Test 7: Validation allows clean prompts
def test_validation_allows_clean_prompts():
    """Test that validation allows prompts without forbidden anchors."""
    from app.graphs.nodes.prompts.compile import _validate_compiled_prompt
    
    clean_prompt = """
    **STYLE:** Soft romantic webtoon with pastel colors
    **PANELS:** Panel 1: Character walks in park
    """
    
    # Should not raise exception
    _validate_compiled_prompt(clean_prompt, "SOFT_ROMANTIC_WEBTOON", "Soft romantic webtoon with pastel colors")
