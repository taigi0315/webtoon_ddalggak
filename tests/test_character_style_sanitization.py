"""Property-based tests for character style sanitization.

Tests that character normalization and migration produce style-neutral descriptions.
"""

import pytest
import re
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings as app_settings
from app.db.models import Character


# Style keywords that should never appear in character descriptions
FORBIDDEN_STYLE_KEYWORDS = [
    "manhwa", "webtoon", "aesthetic", "flower-boy", "k-drama",
    "korean male lead", "romance female lead", "naver webtoon",
    "authentic", "trending", "statuesque", "willowy",
]

# Style phrases that should never appear
FORBIDDEN_STYLE_PATTERNS = [
    r"\bauthent?ic\s+\w+\s+aesthetic\b",
    r"\b\w+\s+male\s+lead\s+aesthetic\b",
    r"\b\w+\s+female\s+lead\s+aesthetic\b",
    r"\bflower-boy\b",
    r"\bK-drama\b",
]


def contains_style_keywords(text: str) -> tuple[bool, list[str]]:
    """Check if text contains forbidden style keywords.
    
    Returns:
        (has_keywords, list_of_found_keywords)
    """
    if not text:
        return False, []
    
    found_keywords = []
    text_lower = text.lower()
    
    # Check for keywords
    for keyword in FORBIDDEN_STYLE_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
            found_keywords.append(keyword)
    
    # Check for patterns
    for pattern in FORBIDDEN_STYLE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found_keywords.append(f"pattern: {pattern}")
    
    return len(found_keywords) > 0, found_keywords


@pytest.fixture(scope="module")
def db_session():
    """Create a database session for testing against production database."""
    engine = create_engine(app_settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.mark.property
class TestCharacterStyleSanitization:
    """Property 8: Migration Style Sanitization
    
    For any character record processed by the migration, stylistic keywords
    should be removed from identity_line and appearance fields while preserving
    morphological information.
    
    Validates: Requirements 8.2, 8.3
    """
    
    def test_all_characters_have_no_style_keywords_in_identity_line(self, db_session):
        """Property: All characters in DB should have style-neutral identity_line."""
        characters = db_session.query(Character).filter(Character.identity_line.isnot(None)).all()
        
        for character in characters:
            has_keywords, found = contains_style_keywords(character.identity_line)
            assert not has_keywords, (
                f"Character '{character.name}' (ID: {character.character_id}) "
                f"has forbidden style keywords in identity_line: {found}\n"
                f"identity_line: {character.identity_line}"
            )
    
    def test_all_characters_have_no_style_keywords_in_appearance(self, db_session):
        """Property: All characters in DB should have style-neutral appearance fields."""
        characters = db_session.query(Character).filter(Character.appearance.isnot(None)).all()
        
        for character in characters:
            if not isinstance(character.appearance, dict):
                continue
            
            for field_name, field_value in character.appearance.items():
                if isinstance(field_value, str):
                    has_keywords, found = contains_style_keywords(field_value)
                    assert not has_keywords, (
                        f"Character '{character.name}' (ID: {character.character_id}) "
                        f"has forbidden style keywords in appearance.{field_name}: {found}\n"
                        f"Value: {field_value}"
                    )
    
    @given(
        identity_line=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Pc")),
            min_size=10,
            max_size=500
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_sanitization_removes_all_style_keywords(self, identity_line):
        """Property: Sanitization function removes all style keywords from any text.
        
        This tests the sanitization logic in isolation.
        """
        # Inject some style keywords into the text
        polluted_text = identity_line + " authentic webtoon aesthetic"
        
        # Apply sanitization (same logic as migration)
        cleaned = polluted_text
        for keyword in FORBIDDEN_STYLE_KEYWORDS:
            pattern = rf"\b{re.escape(keyword)}\b"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        for pattern in FORBIDDEN_STYLE_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        # Clean up whitespace
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = re.sub(r",\s*,", ",", cleaned)
        cleaned = cleaned.strip(" ,")
        
        # Verify no style keywords remain
        has_keywords, found = contains_style_keywords(cleaned)
        assert not has_keywords, f"Sanitization failed to remove keywords: {found}"
    
    @given(
        morphological_info=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
            min_size=20,
            max_size=200
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_sanitization_preserves_morphological_information(self, morphological_info):
        """Property: Sanitization preserves morphological descriptions.
        
        Morphological information like "long black hair", "tall 180cm", "oval face"
        should be preserved after sanitization.
        """
        # Create a description with both morphological and style information
        description = f"{morphological_info}, authentic webtoon aesthetic"
        
        # Apply sanitization
        cleaned = description
        for keyword in FORBIDDEN_STYLE_KEYWORDS:
            pattern = rf"\b{re.escape(keyword)}\b"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = cleaned.strip(" ,")
        
        # Verify morphological info is still present (at least partially)
        # We check that the cleaned text is not empty and contains some original content
        assert len(cleaned) > 0, "Sanitization removed all content"
        
        # Check that at least some words from original morphological info remain
        original_words = set(morphological_info.lower().split())
        cleaned_words = set(cleaned.lower().split())
        
        # At least 50% of original words should remain
        if len(original_words) > 0:
            overlap = len(original_words & cleaned_words) / len(original_words)
            assert overlap >= 0.5, (
                f"Too much morphological information lost during sanitization. "
                f"Overlap: {overlap:.2%}"
            )
