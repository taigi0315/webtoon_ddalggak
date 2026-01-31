"""Property-based tests for prompt layering hierarchy.

Tests that compiled prompts follow the correct layering order.
"""

import pytest
import re
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock
import uuid

from app.graphs.nodes.prompts.compile import _compile_prompt
from app.db.models import Character


@pytest.mark.property
class TestPromptLayering:
    """Property 4: Prompt Layering Order
    
    For any compiled prompt, the sections should appear in the correct order:
    1. STYLE (highest priority)
    2. ART DIRECTION (if provided)
    3. ASPECT RATIO & FORMAT
    4. REFERENCE IMAGE AUTHORITY
    5. PANEL COMPOSITION RULES
    6. CHARACTERS
    7. PANELS
    8. TECHNICAL REQUIREMENTS
    9. NEGATIVE (lowest priority)
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
    """
    
    @given(
        style_id=st.sampled_from([
            "SOFT_ROMANTIC_WEBTOON",
            "CINEMATIC_MODERN_MANHWA",
            "VIBRANT_FANTASY_WEBTOON",
            "default",
        ]),
        panel_count=st.integers(min_value=1, max_value=6),
        include_art_direction=st.booleans(),
    )
    @settings(max_examples=100, deadline=None)
    def test_prompt_sections_in_correct_order(self, style_id, panel_count, include_art_direction):
        """Property: Prompt sections must appear in the correct hierarchical order."""
        # Create mock data
        panel_semantics = {
            "panels": [
                {
                    "panel_index": i + 1,
                    "grammar_id": "SINGLE_FOCUS",
                    "description": f"Panel {i + 1} description",
                }
                for i in range(panel_count)
            ]
        }
        
        layout_template = {"layout_text": f"{panel_count} panels, vertical flow"}
        
        character = Mock(spec=Character)
        character.character_id = uuid.uuid4()
        character.name = "Test Character"
        character.role = "protagonist"
        character.identity_line = "young adult, black hair"
        character.base_outfit = "casual"
        character.appearance = {"hair": "black", "face": "oval", "build": "average"}
        character.description = None
        
        art_direction = None
        if include_art_direction:
            art_direction = {
                "lighting": "soft natural light",
                "color_temperature": "warm",
                "atmosphere_keywords": ["calm", "peaceful"],
            }
        
        # Compile prompt
        prompt = _compile_prompt(
            panel_semantics=panel_semantics,
            layout_template=layout_template,
            style_id=style_id,
            characters=[character],
            art_direction=art_direction,
        )
        
        # Find section positions
        sections = {
            "STYLE": self._find_section_position(prompt, r"\*\*STYLE:\*\*"),
            "ART_DIRECTION": self._find_section_position(prompt, r"\*\*ART DIRECTION:\*\*"),
            "FORMAT": self._find_section_position(prompt, r"\*\*ASPECT RATIO & FORMAT:\*\*"),
            "REFERENCE": self._find_section_position(prompt, r"\*\*REFERENCE IMAGE AUTHORITY:\*\*"),
            "COMPOSITION": self._find_section_position(prompt, r"\*\*PANEL COMPOSITION RULES:\*\*"),
            "CHARACTERS": self._find_section_position(prompt, r"\*\*CHARACTERS"),
            "PANELS": self._find_section_position(prompt, r"\*\*PANELS"),
            "TECHNICAL": self._find_section_position(prompt, r"\*\*TECHNICAL REQUIREMENTS:\*\*"),
            "NEGATIVE": self._find_section_position(prompt, r"\*\*NEGATIVE:\*\*"),
        }
        
        # Verify STYLE is first (must exist)
        assert sections["STYLE"] is not None, "STYLE section missing"
        assert sections["STYLE"] == 0, f"STYLE must be first, found at position {sections['STYLE']}"
        
        # Verify required sections exist
        required_sections = ["FORMAT", "REFERENCE", "COMPOSITION", "PANELS", "TECHNICAL", "NEGATIVE"]
        for section in required_sections:
            assert sections[section] is not None, f"{section} section missing"
        
        # Verify order: STYLE < FORMAT < REFERENCE < COMPOSITION < PANELS < TECHNICAL < NEGATIVE
        assert sections["STYLE"] < sections["FORMAT"], "STYLE must come before FORMAT"
        assert sections["FORMAT"] < sections["REFERENCE"], "FORMAT must come before REFERENCE"
        assert sections["REFERENCE"] < sections["COMPOSITION"], "REFERENCE must come before COMPOSITION"
        assert sections["COMPOSITION"] < sections["PANELS"], "COMPOSITION must come before PANELS"
        assert sections["PANELS"] < sections["TECHNICAL"], "PANELS must come before TECHNICAL"
        assert sections["TECHNICAL"] < sections["NEGATIVE"], "TECHNICAL must come before NEGATIVE"
        
        # If ART_DIRECTION exists, verify it comes after STYLE and before FORMAT
        if include_art_direction:
            assert sections["ART_DIRECTION"] is not None, "ART_DIRECTION section missing when provided"
            assert sections["STYLE"] < sections["ART_DIRECTION"], "STYLE must come before ART_DIRECTION"
            assert sections["ART_DIRECTION"] < sections["FORMAT"], "ART_DIRECTION must come before FORMAT"
        else:
            # ART_DIRECTION should not exist if not provided
            assert sections["ART_DIRECTION"] is None, "ART_DIRECTION should not exist when not provided"
        
        # If CHARACTERS exist, verify they come after COMPOSITION and before PANELS
        if sections["CHARACTERS"] is not None:
            assert sections["COMPOSITION"] < sections["CHARACTERS"], "COMPOSITION must come before CHARACTERS"
            assert sections["CHARACTERS"] < sections["PANELS"], "CHARACTERS must come before PANELS"
    
    def test_art_direction_layer_format(self):
        """Test that ART DIRECTION layer has correct format when provided."""
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
        character.identity_line = "test"
        character.base_outfit = "casual"
        character.appearance = {}
        character.description = None
        
        art_direction = {
            "lighting": "dramatic low-key lighting",
            "color_temperature": "cool blue tones",
            "atmosphere_keywords": ["tense", "mysterious", "noir"],
        }
        
        prompt = _compile_prompt(
            panel_semantics=panel_semantics,
            layout_template=layout_template,
            style_id="default",
            characters=[character],
            art_direction=art_direction,
        )
        
        # Verify ART DIRECTION section exists
        assert "**ART DIRECTION:**" in prompt, "ART DIRECTION section missing"
        
        # Verify lighting is included
        assert "Lighting: dramatic low-key lighting" in prompt, "Lighting not in ART DIRECTION"
        
        # Verify color temperature is included
        assert "Color Temperature: cool blue tones" in prompt, "Color temperature not in ART DIRECTION"
        
        # Verify atmosphere keywords are included
        assert "Atmosphere: tense, mysterious, noir" in prompt, "Atmosphere keywords not in ART DIRECTION"
    
    def test_art_direction_monochrome_handling(self):
        """Test that monochrome styles (N/A color temperature) are handled correctly."""
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
        character.identity_line = "test"
        character.base_outfit = "casual"
        character.appearance = {}
        character.description = None
        
        art_direction = {
            "lighting": "dramatic high-contrast lighting",
            "color_temperature": "N/A (monochrome)",
            "atmosphere_keywords": ["noir", "shadowy"],
        }
        
        prompt = _compile_prompt(
            panel_semantics=panel_semantics,
            layout_template=layout_template,
            style_id="default",
            characters=[character],
            art_direction=art_direction,
        )
        
        # Verify ART DIRECTION section exists
        assert "**ART DIRECTION:**" in prompt, "ART DIRECTION section missing"
        
        # Verify lighting is included
        assert "Lighting: dramatic high-contrast lighting" in prompt, "Lighting not in ART DIRECTION"
        
        # Verify color temperature is NOT included (N/A should be filtered out)
        assert "Color Temperature:" not in prompt, "Color temperature should not appear for monochrome (N/A)"
        
        # Verify atmosphere keywords are included
        assert "Atmosphere: noir, shadowy" in prompt, "Atmosphere keywords not in ART DIRECTION"
    
    def test_style_layer_always_first(self):
        """Test that STYLE layer is always the first section."""
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
        
        for style_id in ["SOFT_ROMANTIC_WEBTOON", "CINEMATIC_MODERN_MANHWA", "default"]:
            prompt = _compile_prompt(
                panel_semantics=panel_semantics,
                layout_template=layout_template,
                style_id=style_id,
                characters=[character],
            )
            
            # Find first section
            first_section_match = re.search(r"\*\*([A-Z\s&:]+)\*\*", prompt)
            assert first_section_match, f"No sections found in prompt for {style_id}"
            
            first_section = first_section_match.group(1)
            assert first_section == "STYLE:", f"First section should be STYLE, found {first_section} for {style_id}"
    
    def _find_section_position(self, prompt: str, pattern: str) -> int | None:
        """Find the position of a section in the prompt.
        
        Returns:
            Position index (0-based) or None if not found
        """
        match = re.search(pattern, prompt)
        if match:
            return match.start()
        return None
