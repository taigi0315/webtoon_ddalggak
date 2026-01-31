"""
Property tests for Studio Director style agnosticism.

**Property 5: Studio Director Style Agnosticism**
**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 3.3**

The Studio Director must produce style-agnostic output that focuses on semantic
emotional descriptions (scene_emotion, dramatic_intent) without specifying visual
style characteristics like color palette, lighting, or atmospheric mood.
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.graphs.nodes.planning.studio_director import (
    _detect_style_keywords_in_studio_output,
    FORBIDDEN_STUDIO_DIRECTOR_KEYWORDS,
)


# Test 1: Property test - Studio Director output should not contain style keywords
@settings(max_examples=100)
@given(
    scene_emotion=st.text(min_size=5, max_size=100),
    dramatic_intent=st.text(min_size=5, max_size=100),
    summary=st.text(min_size=5, max_size=100),
)
def test_property_studio_director_no_style_keywords(
    scene_emotion: str, dramatic_intent: str, summary: str
):
    """
    Property: Studio Director output should not contain forbidden style keywords.
    
    This property verifies that when Studio Director output contains forbidden
    style keywords, the detection function correctly identifies them.
    """
    # Create a mock Studio Director response
    response = {
        "action": "proceed",
        "scenes": [
            {
                "scene_index": 1,
                "summary": summary,
                "primary_tone": "Serious",
                "image_style_id": "default",
                "scene_emotion": scene_emotion,
                "dramatic_intent": dramatic_intent,
                "beats": [],
                "source_text": "Test scene",
            }
        ],
    }
    
    # Detect keywords
    detected = _detect_style_keywords_in_studio_output(response)
    
    # Check if any forbidden keywords are in the text
    has_forbidden_keyword = False
    for keyword in FORBIDDEN_STUDIO_DIRECTOR_KEYWORDS:
        if (
            keyword.lower() in scene_emotion.lower()
            or keyword.lower() in dramatic_intent.lower()
            or keyword.lower() in summary.lower()
        ):
            has_forbidden_keyword = True
            break
    
    # If forbidden keyword exists, detection should find it
    if has_forbidden_keyword:
        assert len(detected) > 0, "Detection should find forbidden keywords"
    # If no forbidden keyword, detection should be empty
    else:
        assert len(detected) == 0, f"Detection should be empty but found: {detected}"


# Test 2: Clean output should pass validation
def test_clean_studio_director_output():
    """Test that clean Studio Director output passes validation."""
    response = {
        "action": "proceed",
        "scenes": [
            {
                "scene_index": 1,
                "summary": "Character confronts their past",
                "primary_tone": "Serious",
                "image_style_id": "default",
                "scene_emotion": "Tense and conflicted",
                "dramatic_intent": "Reveal character's hidden motivation",
                "beats": [],
                "source_text": "Test scene",
            }
        ],
    }
    
    detected = _detect_style_keywords_in_studio_output(response)
    assert len(detected) == 0, f"Clean output should have no detected keywords, but found: {detected}"


# Test 3: Output with color palette keywords should be detected
def test_studio_director_color_palette_detection():
    """Test that color palette keywords are detected."""
    response = {
        "action": "proceed",
        "scenes": [
            {
                "scene_index": 1,
                "summary": "A dramatic confrontation",
                "primary_tone": "Serious",
                "image_style_id": "default",
                "scene_emotion": "Tense with warm colors dominating the scene",
                "dramatic_intent": "Create tension",
                "beats": [],
                "source_text": "Test scene",
            }
        ],
    }
    
    detected = _detect_style_keywords_in_studio_output(response)
    assert len(detected) > 0, "Should detect 'warm colors' keyword"
    assert any("warm colors" in d.lower() for d in detected)


# Test 4: Output with lighting keywords should be detected
def test_studio_director_lighting_detection():
    """Test that lighting keywords are detected."""
    response = {
        "action": "proceed",
        "scenes": [
            {
                "scene_index": 1,
                "summary": "A romantic moment",
                "primary_tone": "Romance",
                "image_style_id": "default",
                "scene_emotion": "Romantic",
                "dramatic_intent": "Build intimacy with soft lighting and gentle atmosphere",
                "beats": [],
                "source_text": "Test scene",
            }
        ],
    }
    
    detected = _detect_style_keywords_in_studio_output(response)
    assert len(detected) > 0, "Should detect 'soft lighting' keyword"
    assert any("soft lighting" in d.lower() for d in detected)


# Test 5: Output with atmospheric mood keywords should be detected
def test_studio_director_atmospheric_mood_detection():
    """Test that atmospheric mood keywords are detected."""
    response = {
        "action": "proceed",
        "scenes": [
            {
                "scene_index": 1,
                "summary": "A mysterious encounter with noir atmosphere",
                "primary_tone": "Atmospheric",
                "image_style_id": "default",
                "scene_emotion": "Mysterious",
                "dramatic_intent": "Create suspense",
                "beats": [],
                "source_text": "Test scene",
            }
        ],
    }
    
    detected = _detect_style_keywords_in_studio_output(response)
    assert len(detected) > 0, "Should detect 'noir atmosphere' keyword"
    assert any("noir atmosphere" in d.lower() for d in detected)


# Test 6: Multiple scenes with mixed clean and dirty output
def test_studio_director_multiple_scenes():
    """Test detection across multiple scenes."""
    response = {
        "action": "proceed",
        "scenes": [
            {
                "scene_index": 1,
                "summary": "Clean scene",
                "primary_tone": "Serious",
                "image_style_id": "default",
                "scene_emotion": "Tense",
                "dramatic_intent": "Build suspense",
                "beats": [],
                "source_text": "Test scene 1",
            },
            {
                "scene_index": 2,
                "summary": "Scene with color palette",
                "primary_tone": "Romance",
                "image_style_id": "default",
                "scene_emotion": "Romantic with pastel colors",
                "dramatic_intent": "Create warmth",
                "beats": [],
                "source_text": "Test scene 2",
            },
        ],
    }
    
    detected = _detect_style_keywords_in_studio_output(response)
    assert len(detected) > 0, "Should detect 'pastel colors' keyword in second scene"
    assert any("pastel colors" in d.lower() for d in detected)


# Test 7: Empty response should pass
def test_studio_director_empty_response():
    """Test that empty response passes validation."""
    response = {"action": "proceed", "scenes": []}
    
    detected = _detect_style_keywords_in_studio_output(response)
    assert len(detected) == 0, "Empty response should have no detected keywords"


# Test 8: Case-insensitive detection
def test_studio_director_case_insensitive():
    """Test that keyword detection is case-insensitive."""
    response = {
        "action": "proceed",
        "scenes": [
            {
                "scene_index": 1,
                "summary": "Test",
                "primary_tone": "Serious",
                "image_style_id": "default",
                "scene_emotion": "Tense with WARM COLORS",
                "dramatic_intent": "Create tension",
                "beats": [],
                "source_text": "Test scene",
            }
        ],
    }
    
    detected = _detect_style_keywords_in_studio_output(response)
    assert len(detected) > 0, "Should detect 'WARM COLORS' (case-insensitive)"


# Test 9: Semantic emotional descriptions should pass
def test_studio_director_semantic_emotions():
    """Test that semantic emotional descriptions pass validation."""
    semantic_emotions = [
        "Heartbreaking and sorrowful",
        "Comedic and lighthearted",
        "Tense and suspenseful",
        "Joyful and uplifting",
        "Melancholic and reflective",
        "Angry and confrontational",
        "Peaceful and serene",
        "Chaotic and overwhelming",
    ]
    
    for emotion in semantic_emotions:
        response = {
            "action": "proceed",
            "scenes": [
                {
                    "scene_index": 1,
                    "summary": "Test scene",
                    "primary_tone": "Serious",
                    "image_style_id": "default",
                    "scene_emotion": emotion,
                    "dramatic_intent": "Advance the plot",
                    "beats": [],
                    "source_text": "Test scene",
                }
            ],
        }
        
        detected = _detect_style_keywords_in_studio_output(response)
        assert len(detected) == 0, f"Semantic emotion '{emotion}' should pass validation, but detected: {detected}"


# Test 10: Dramatic intent should be style-agnostic
def test_studio_director_dramatic_intent():
    """Test that dramatic intent descriptions are style-agnostic."""
    valid_intents = [
        "Reveal character's hidden motivation",
        "Build tension before the climax",
        "Provide comic relief",
        "Establish the setting",
        "Deepen the relationship between characters",
        "Create a turning point in the story",
        "Show character growth",
        "Foreshadow future events",
    ]
    
    for intent in valid_intents:
        response = {
            "action": "proceed",
            "scenes": [
                {
                    "scene_index": 1,
                    "summary": "Test scene",
                    "primary_tone": "Serious",
                    "image_style_id": "default",
                    "scene_emotion": "Tense",
                    "dramatic_intent": intent,
                    "beats": [],
                    "source_text": "Test scene",
                }
            ],
        }
        
        detected = _detect_style_keywords_in_studio_output(response)
        assert len(detected) == 0, f"Dramatic intent '{intent}' should pass validation, but detected: {detected}"
