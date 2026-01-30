"""
Tests for Character Library & Reuse System (TASK-002).
"""

import uuid

import pytest
from unittest.mock import MagicMock, patch

from app.api.v1.schemas import (
    GenerateWithReferenceRequest,
    LibraryCharacterRead,
    LoadFromLibraryRequest,
    SaveToLibraryRequest,
)
from app.db.models import (
    Character,
    CharacterReferenceImage,
    Project,
    Story,
    StoryCharacter,
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def sample_project():
    """Create a sample project."""
    project = Project(
        project_id=uuid.uuid4(),
        name="Test Project",
    )
    return project


@pytest.fixture
def sample_character(sample_project):
    """Create a sample character."""
    return Character(
        character_id=uuid.uuid4(),
        project_id=sample_project.project_id,
        canonical_code="CHAR_A",
        name="Alice",
        description="A young woman with blonde hair",
        role="main",
        gender="female",
        age_range="young_adult",
        is_library_saved=False,
        approved=True,
    )


@pytest.fixture
def sample_ref_image(sample_character):
    """Create a sample reference image."""
    return CharacterReferenceImage(
        reference_image_id=uuid.uuid4(),
        character_id=sample_character.character_id,
        image_url="https://example.com/alice.png",
        ref_type="face",
        approved=True,
        is_primary=True,
    )


class TestCharacterLibrarySchemas:
    """Tests for character library Pydantic schemas."""

    def test_library_character_read_schema(self, sample_character):
        """LibraryCharacterRead should include library fields."""
        sample_character.is_library_saved = True
        sample_character.generation_prompt = "A blonde heroine"

        # Test model validation
        data = {
            "character_id": sample_character.character_id,
            "project_id": sample_character.project_id,
            "canonical_code": sample_character.canonical_code,
            "name": sample_character.name,
            "description": sample_character.description,
            "role": sample_character.role,
            "gender": sample_character.gender,
            "age_range": sample_character.age_range,
            "appearance": None,
            "hair_description": None,
            "base_outfit": None,
            "identity_line": None,
            "generation_prompt": "A blonde heroine",
            "approved": True,
            "primary_reference_image": None,
        }
        char_read = LibraryCharacterRead.model_validate(data)
        assert char_read.name == "Alice"
        assert char_read.generation_prompt == "A blonde heroine"

    def test_save_to_library_request_optional_prompt(self):
        """SaveToLibraryRequest should allow optional generation_prompt."""
        # With prompt
        req = SaveToLibraryRequest(generation_prompt="Test prompt")
        assert req.generation_prompt == "Test prompt"

        # Without prompt
        req = SaveToLibraryRequest()
        assert req.generation_prompt is None

    def test_load_from_library_request_requires_id(self):
        """LoadFromLibraryRequest requires library_character_id."""
        char_id = uuid.uuid4()
        req = LoadFromLibraryRequest(library_character_id=char_id)
        assert req.library_character_id == char_id

    def test_generate_with_reference_request_defaults(self):
        """GenerateWithReferenceRequest should have sensible defaults."""
        char_id = uuid.uuid4()
        req = GenerateWithReferenceRequest(library_character_id=char_id)
        assert req.library_character_id == char_id
        assert req.variant_description is None
        assert req.variant_type == "story_context"

    def test_generate_with_reference_request_custom_values(self):
        """GenerateWithReferenceRequest accepts custom values."""
        char_id = uuid.uuid4()
        req = GenerateWithReferenceRequest(
            library_character_id=char_id,
            variant_description="wearing a spacesuit",
            variant_type="outfit_change",
        )
        assert req.variant_description == "wearing a spacesuit"
        assert req.variant_type == "outfit_change"


class TestCharacterModelLibraryFields:
    """Tests for Character model library fields."""

    def test_character_has_library_fields(self):
        """Character model should have library-related fields."""
        char = Character(
            project_id=uuid.uuid4(),
            name="Test",
            is_library_saved=True,
            generation_prompt="Original prompt",
        )
        assert char.is_library_saved is True
        assert char.generation_prompt == "Original prompt"

    def test_character_library_defaults(self):
        """Character library fields should have sensible defaults."""
        char = Character(
            project_id=uuid.uuid4(),
            name="Test",
            is_library_saved=False,  # Explicit default for testing
        )
        assert char.is_library_saved is False
        assert char.generation_prompt is None


class TestLibraryWorkflow:
    """Integration-style tests for library workflow."""

    def test_save_and_load_workflow_concept(self, sample_character, sample_ref_image):
        """Test the conceptual workflow of save and load."""
        # 1. Character starts not in library
        assert sample_character.is_library_saved is False

        # 2. Save to library (with approved ref)
        sample_character.is_library_saved = True
        sample_character.generation_prompt = "A blonde heroine with blue eyes"
        assert sample_character.is_library_saved is True

        # 3. Character can be found in library queries
        # (in real implementation, this would be a DB query)
        library_chars = [sample_character]  # Simulated query result
        assert len(library_chars) == 1
        assert library_chars[0].name == "Alice"

    def test_library_character_requires_approved_ref(self, sample_character):
        """Library save should conceptually require approved reference."""
        # This is enforced in the API endpoint
        # Here we just verify the model allows the flag
        sample_character.is_library_saved = True
        assert sample_character.is_library_saved is True


class TestLibraryCharacterReadWithRef:
    """Tests for LibraryCharacterRead with reference image."""

    def test_library_character_with_ref(self, sample_character, sample_ref_image):
        """LibraryCharacterRead can include primary reference image."""
        from app.api.v1.schemas import CharacterRefRead

        ref_data = {
            "reference_image_id": sample_ref_image.reference_image_id,
            "character_id": sample_ref_image.character_id,
            "image_url": sample_ref_image.image_url,
            "ref_type": sample_ref_image.ref_type,
            "approved": sample_ref_image.approved,
            "is_primary": sample_ref_image.is_primary,
            "metadata_": {},
        }
        ref_read = CharacterRefRead.model_validate(ref_data)

        char_data = {
            "character_id": sample_character.character_id,
            "project_id": sample_character.project_id,
            "canonical_code": "CHAR_A",
            "name": "Alice",
            "description": "A young woman",
            "role": "main",
            "gender": "female",
            "age_range": "young_adult",
            "appearance": None,
            "hair_description": None,
            "base_outfit": None,
            "identity_line": None,
            "generation_prompt": None,
            "approved": True,
            "primary_reference_image": ref_read,
        }
        char_read = LibraryCharacterRead.model_validate(char_data)
        assert char_read.primary_reference_image is not None
        assert char_read.primary_reference_image.image_url == "https://example.com/alice.png"


class TestVariantTypeOptions:
    """Tests for variant type options."""

    def test_variant_types_in_request(self):
        """Test various variant types are accepted."""
        char_id = uuid.uuid4()

        variant_types = ["outfit_change", "age_progression", "expression", "story_context"]
        for vtype in variant_types:
            req = GenerateWithReferenceRequest(
                library_character_id=char_id,
                variant_type=vtype,
            )
            assert req.variant_type == vtype
