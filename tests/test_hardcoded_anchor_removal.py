"""Property-based tests for hardcoded style anchor removal.

Tests that compiled prompts do not contain hardcoded style anchors.
"""

import pytest
import re
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, MagicMock
import uuid

from app.graphs.nodes.prompts.compile import _compile_prompt
from app.db.models import Character


# Forbidden hardcoded strings that should never appear in prompts
FORBIDDEN_HARDCODED_STRINGS = [
    "Korean webtoon/manhwa art style",
    "Naver webtoon quality",
    "Vertical 9:16 webtoon/manhwa image",
    "Korean webtoon",
    "manhwa art style",
]


def contains_hardcoded_anchors(text: str) -> tuple[bool, list[str]]:
    """Check if text contains forbidden hardcoded style anchors.
    
    Returns:
        (has_anchors, list_of_found_anchors)
    """
    if not text:
        return False, []
    
    found_anchors = []
    text_lower = text.lower()
    
    for anchor in FORBIDDEN_HARDCODED_STRINGS:
        if anchor.lower() in text_lower:
            found_anchors.append(anchor)
    
    return len(found_anchors) > 0, found_anchors


@pytest.mark.property
class TestHardcodedAnchorRemoval:
    """Property 2: Hardcoded Anchor Removal
    
    For any compiled prompt, the prompt text should not contain hardcoded style
    anchors and should instead use dynamic references to the user-selected image_style_id.
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.5
    """
    
    @given(
        style_id=st.sampled_from([
            "SOFT_ROMANTIC_WEBTOON",
            "STARK_BLACK_WHITE_NOIR",
            "CINEMATIC_MODERN_MANHWA",
            "VIBRANT_FANTASY_WEBTOON",
            "default",
        ]),
        panel_count=st.integers(min_value=1, max_value=6),
    )
    @settings(max_examples=50, deadline=None)
    def test_compiled_prompt_has_no_hardcoded_anchors(self, style_id, panel_count):
        """Property: Compiled prompts should not contain hardcoded style anchors."""
        # Create mock data
        panel_semantics = {
            "panels": [
                {
                    "panel_index": i + 1,
                    "grammar_id": "SINGLE_FOCUS",
                    "description": f"Panel {i + 1} description",
                    "environment": {"location": "room"},
                    "lighting": {"source": "window", "quality": "soft"},
                    "atmosphere_keywords": ["calm"],
                }
                for i in range(panel_count)
            ]
        }
        
        layout_template = {
            "layout_text": f"{panel_count} panels, vertical flow"
        }
        
        # Create mock character
        character = Mock(spec=Character)
        character.character_id = uuid.uuid4()
        character.name = "Test Character"
        character.role = "protagonist"
        character.identity_line = "young adult, black hair, casual outfit"
        character.base_outfit = "casual shirt and jeans"
        character.appearance = {
            "hair": "black hair",
            "face": "oval face",
            "build": "average build"
        }
        character.description = None
        
        # Compile prompt
        prompt = _compile_prompt(
            panel_semantics=panel_semantics,
            layout_template=layout_template,
            style_id=style_id,
            characters=[character],
        )
        
        # Verify no hardcoded anchors
        has_anchors, found = contains_hardcoded_anchors(prompt)
        assert not has_anchors, (
            f"Compiled prompt contains forbidden hardcoded anchors: {found}\n"
            f"Style ID: {style_id}\n"
            f"Prompt excerpt: {prompt[:500]}..."
        )
    
    def test_prompt_uses_dynamic_style_reference(self):
        """Test that prompt uses dynamic style reference from style_id parameter."""
        # Create minimal mock data
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "grammar_id": "SINGLE_FOCUS",
                    "description": "Test panel",
                }
            ]
        }
        
        layout_template = {"layout_text": "1 panel"}
        
        character = Mock(spec=Character)
        character.character_id = uuid.uuid4()
        character.name = "Test"
        character.role = "protagonist"
        character.identity_line = "test character"
        character.base_outfit = "casual"
        character.appearance = {}
        character.description = None
        
        # Test with different styles
        for style_id in ["SOFT_ROMANTIC_WEBTOON", "STARK_BLACK_WHITE_NOIR"]:
            prompt = _compile_prompt(
                panel_semantics=panel_semantics,
                layout_template=layout_template,
                style_id=style_id,
                characters=[character],
            )
            
            # Verify style section exists
            assert "**STYLE:**" in prompt, f"Prompt missing STYLE section for {style_id}"
            
            # Verify no hardcoded anchors
            has_anchors, found = contains_hardcoded_anchors(prompt)
            assert not has_anchors, (
                f"Prompt for {style_id} contains hardcoded anchors: {found}"
            )
    
    def test_format_section_has_no_style_references(self):
        """Test that ASPECT RATIO & FORMAT section has no style-specific references."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "grammar_id": "SINGLE_FOCUS",
                    "description": "Test",
                }
            ]
        }
        
        layout_template = {"layout_text": "1 panel"}
        
        character = Mock(spec=Character)
        character.character_id = uuid.uuid4()
        character.name = "Test"
        character.role = "protagonist"
        character.identity_line = "test"
        character.base_outfit = "casual"
        character.appearance = {}
        character.description = None
        
        prompt = _compile_prompt(
            panel_semantics=panel_semantics,
            layout_template=layout_template,
            style_id="default",
            characters=[character],
        )
        
        # Extract FORMAT section
        format_match = re.search(
            r"\*\*ASPECT RATIO & FORMAT:\*\*(.*?)\*\*",
            prompt,
            re.DOTALL
        )
        
        assert format_match, "FORMAT section not found in prompt"
        format_section = format_match.group(1)
        
        # Verify no style keywords in format section
        style_keywords = ["webtoon", "manhwa", "korean", "naver"]
        for keyword in style_keywords:
            assert keyword.lower() not in format_section.lower(), (
                f"FORMAT section contains style keyword '{keyword}': {format_section}"
            )
    
    def test_technical_requirements_has_no_hardcoded_style(self):
        """Test that TECHNICAL REQUIREMENTS section has no hardcoded style anchors."""
        panel_semantics = {
            "panels": [
                {
                    "panel_index": 1,
                    "grammar_id": "SINGLE_FOCUS",
                    "description": "Test",
                }
            ]
        }
        
        layout_template = {"layout_text": "1 panel"}
        
        character = Mock(spec=Character)
        character.character_id = uuid.uuid4()
        character.name = "Test"
        character.role = "protagonist"
        character.identity_line = "test"
        character.base_outfit = "casual"
        character.appearance = {}
        character.description = None
        
        prompt = _compile_prompt(
            panel_semantics=panel_semantics,
            layout_template=layout_template,
            style_id="default",
            characters=[character],
        )
        
        # Extract TECHNICAL REQUIREMENTS section
        tech_match = re.search(
            r"\*\*TECHNICAL REQUIREMENTS:\*\*(.*?)\*\*NEGATIVE:",
            prompt,
            re.DOTALL
        )
        
        assert tech_match, "TECHNICAL REQUIREMENTS section not found in prompt"
        tech_section = tech_match.group(1)
        
        # Verify no hardcoded style anchors
        has_anchors, found = contains_hardcoded_anchors(tech_section)
        assert not has_anchors, (
            f"TECHNICAL REQUIREMENTS contains hardcoded anchors: {found}\n"
            f"Section: {tech_section}"
        )
