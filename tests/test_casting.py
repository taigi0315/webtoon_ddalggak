"""
Tests for Actor/Casting System (Phase 5: Integration Testing).

Tests cover:
- Pydantic schema validation
- API endpoint tests (with mocked image generation)
- Service layer tests
- Full workflow tests
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.schemas import (
    ActorCharacterRead,
    ActorVariantRead,
    CharacterTraitsInput,
    GenerateActorRequest,
    GenerateActorResponse,
    GenerateActorVariantRequest,
    ImportActorRequest,
    SaveActorToLibraryRequest,
)
from app.db.models import (
    Character,
    CharacterReferenceImage,
    CharacterVariant,
    Image,
    Project,
)


# ============================================================================
# Schema Validation Tests
# ============================================================================


class TestCharacterTraitsInputSchema:
    """Tests for CharacterTraitsInput schema."""

    def test_all_fields_optional(self):
        """All trait fields should be optional."""
        traits = CharacterTraitsInput()
        assert traits.gender is None
        assert traits.age_range is None
        assert traits.face_traits is None
        assert traits.hair_traits is None
        assert traits.mood is None
        assert traits.custom_prompt is None

    def test_partial_traits(self):
        """Should accept partial trait specification."""
        traits = CharacterTraitsInput(
            gender="female",
            age_range="young_adult",
        )
        assert traits.gender == "female"
        assert traits.age_range == "young_adult"
        assert traits.face_traits is None

    def test_full_traits(self):
        """Should accept all traits."""
        traits = CharacterTraitsInput(
            gender="male",
            age_range="adult",
            face_traits="Sharp jawline, blue eyes",
            hair_traits="Short black hair",
            mood="Confident",
            custom_prompt="Wearing a business suit",
        )
        assert traits.gender == "male"
        assert traits.custom_prompt == "Wearing a business suit"


class TestGenerateActorRequestSchema:
    """Tests for GenerateActorRequest schema."""

    def test_required_fields(self):
        """Request requires style IDs and traits."""
        req = GenerateActorRequest(
            image_style_id="anime",
            traits=CharacterTraitsInput(gender="female"),
        )
        assert req.image_style_id == "anime"
        assert req.traits.gender == "female"

    def test_empty_traits_allowed(self):
        """Empty traits should be allowed."""
        req = GenerateActorRequest(
            image_style_id="default",
            traits=CharacterTraitsInput(),
        )
        assert req.traits.gender is None


class TestGenerateActorResponseSchema:
    """Tests for GenerateActorResponse schema."""

    def test_response_without_character_id(self):
        """Response should allow None character_id (not saved yet)."""
        resp = GenerateActorResponse(
            character_id=None,
            image_url="http://example.com/image.png",
            image_id=uuid.uuid4(),
            traits_used={"gender": "female"},
            status="generated",
        )
        assert resp.character_id is None
        assert resp.status == "generated"

    def test_response_with_character_id(self):
        """Response can include character_id after save."""
        char_id = uuid.uuid4()
        resp = GenerateActorResponse(
            character_id=char_id,
            image_url="http://example.com/image.png",
            image_id=uuid.uuid4(),
            traits_used={},
            status="saved",
        )
        assert resp.character_id == char_id


class TestSaveActorToLibraryRequestSchema:
    """Tests for SaveActorToLibraryRequest schema."""

    def test_required_fields(self):
        """Request requires image_id, display_name, traits, and styles."""
        req = SaveActorToLibraryRequest(
            image_id=uuid.uuid4(),
            display_name="Hero Character",
            traits=CharacterTraitsInput(gender="male"),
            image_style_id="anime",
        )
        assert req.display_name == "Hero Character"
        assert req.description is None

    def test_display_name_validation(self):
        """Display name must not be empty."""
        with pytest.raises(ValueError):
            SaveActorToLibraryRequest(
                image_id=uuid.uuid4(),
                display_name="",  # Empty not allowed
                traits=CharacterTraitsInput(),
                image_style_id="default",
            )

    def test_optional_description(self):
        """Description is optional."""
        req = SaveActorToLibraryRequest(
            image_id=uuid.uuid4(),
            display_name="Hero",
            description="The main protagonist",
            traits=CharacterTraitsInput(),
            image_style_id="default",
        )
        assert req.description == "The main protagonist"


class TestActorVariantReadSchema:
    """Tests for ActorVariantRead schema."""

    def test_minimal_variant(self):
        """Variant with minimal required fields."""
        data = {
            "variant_id": uuid.uuid4(),
            "character_id": uuid.uuid4(),
            "variant_name": None,
            "variant_type": "base",
            "image_style_id": None,
            "traits": {},
            "is_default": True,
        }
        variant = ActorVariantRead.model_validate(data)
        assert variant.variant_type == "base"
        assert variant.is_default is True

    def test_variant_with_images(self):
        """Variant can include image URLs."""
        data = {
            "variant_id": uuid.uuid4(),
            "character_id": uuid.uuid4(),
            "variant_name": "Summer Outfit",
            "variant_type": "variant",
            "image_style_id": "anime",
            "traits": {"mood": "happy"},
            "is_default": False,
            "reference_image_url": "http://example.com/ref.png",
            "generated_image_urls": ["http://example.com/gen1.png"],
        }
        variant = ActorVariantRead.model_validate(data)
        assert variant.variant_name == "Summer Outfit"
        assert variant.reference_image_url == "http://example.com/ref.png"
        assert len(variant.generated_image_urls) == 1


class TestActorCharacterReadSchema:
    """Tests for ActorCharacterRead schema."""

    def test_character_without_variants(self):
        """Character can have empty variants list."""
        data = {
            "character_id": uuid.uuid4(),
            "project_id": uuid.uuid4(),
            "display_name": "Hero",
            "name": "hero_char",
            "description": None,
            "gender": "male",
            "age_range": "adult",
            "default_image_style_id": None,
            "is_library_saved": True,
            "variants": [],
        }
        char = ActorCharacterRead.model_validate(data)
        assert char.display_name == "Hero"
        assert len(char.variants) == 0

    def test_character_with_variants(self):
        """Character can include variants."""
        variant_data = {
            "variant_id": uuid.uuid4(),
            "character_id": uuid.uuid4(),
            "variant_name": "Default",
            "variant_type": "base",
            "image_style_id": None,
            "traits": {},
            "is_default": True,
        }
        data = {
            "character_id": variant_data["character_id"],
            "project_id": uuid.uuid4(),
            "display_name": "Hero",
            "name": "hero_char",
            "description": "The protagonist",
            "gender": "male",
            "age_range": "adult",
            "default_image_style_id": "anime",
            "is_library_saved": True,
            "variants": [variant_data],
        }
        char = ActorCharacterRead.model_validate(data)
        assert len(char.variants) == 1
        assert char.variants[0].is_default is True


class TestGenerateActorVariantRequestSchema:
    """Tests for GenerateActorVariantRequest schema."""

    def test_required_fields(self):
        """Request requires base_variant_id and trait_changes."""
        req = GenerateActorVariantRequest(
            base_variant_id=uuid.uuid4(),
            trait_changes=CharacterTraitsInput(hair_traits="Pink hair"),
        )
        assert req.variant_name is None

    def test_optional_overrides(self):
        """Can override styles and name."""
        req = GenerateActorVariantRequest(
            base_variant_id=uuid.uuid4(),
            variant_name="Winter Look",
            image_style_id="realistic",
            trait_changes=CharacterTraitsInput(mood="serious"),
        )
        assert req.variant_name == "Winter Look"


class TestImportActorRequestSchema:
    """Tests for ImportActorRequest schema."""

    def test_required_fields(self):
        """Request requires image_url and display_name."""
        req = ImportActorRequest(
            image_url="http://example.com/uploaded.png",
            display_name="Imported Hero",
        )
        assert req.image_url == "http://example.com/uploaded.png"
        assert req.traits is None

    def test_optional_fields(self):
        """All other fields are optional."""
        req = ImportActorRequest(
            image_url="http://example.com/uploaded.png",
            display_name="Imported Hero",
            description="An imported character",
            traits=CharacterTraitsInput(gender="female"),
            image_style_id="anime",
        )
        assert req.description == "An imported character"
        assert req.traits.gender == "female"


# ============================================================================
# Model Tests
# ============================================================================


class TestCharacterModelActorFields:
    """Tests for Character model actor-related fields."""

    def test_character_has_actor_fields(self):
        """Character model should have actor system fields."""
        char = Character(
            project_id=uuid.uuid4(),
            name="Test",
            display_name="Test Character",
            default_image_style_id="anime",
            is_library_saved=True,
        )
        assert char.display_name == "Test Character"
        assert char.default_image_style_id == "anime"
        assert char.is_library_saved is True

    def test_character_actor_field_defaults(self):
        """Actor fields should have sensible defaults."""
        char = Character(
            project_id=uuid.uuid4(),
            name="Test",
            is_library_saved=False,
        )
        assert char.display_name is None
        assert char.default_image_style_id is None
        assert char.is_library_saved is False


class TestCharacterVariantModelActorFields:
    """Tests for CharacterVariant model actor-related fields."""

    def test_variant_can_have_null_story_id(self):
        """Variant should allow null story_id for global/library variants."""
        variant = CharacterVariant(
            character_id=uuid.uuid4(),
            story_id=None,  # Global variant
            variant_type="base",
            variant_name="Default",
            is_default=True,
        )
        assert variant.story_id is None
        assert variant.is_default is True

    def test_variant_has_actor_fields(self):
        """Variant should have actor system fields."""
        variant = CharacterVariant(
            character_id=uuid.uuid4(),
            story_id=None,
            variant_type="variant",
            variant_name="Summer Outfit",
            image_style_id="anime",
            traits={"mood": "happy", "hair_traits": "ponytail"},
            generated_image_ids=["img-1", "img-2"],
            is_default=False,
        )
        assert variant.variant_name == "Summer Outfit"
        assert variant.image_style_id == "anime"
        assert variant.traits["mood"] == "happy"
        assert len(variant.generated_image_ids) == 2


# ============================================================================
# API Endpoint Tests (with mocked image generation)
# ============================================================================


@pytest.fixture
def mock_gemini_client():
    """Mock the Gemini client for image generation."""
    with patch("app.services.casting._build_gemini_client") as mock:
        client = MagicMock()
        # Return fake image bytes and mime type
        client.generate_image.return_value = (b"fake_image_bytes", "image/png")
        mock.return_value = client
        yield client


@pytest.fixture
def mock_storage():
    """Mock the storage service."""
    with patch("app.services.casting._save_image") as mock:
        mock.return_value = "http://mock-storage/image.png"
        yield mock


@pytest.mark.anyio
async def test_casting_generate_endpoint(client, mock_gemini_client, mock_storage):
    """Test POST /v1/casting/projects/{project_id}/generate endpoint."""
    # Create project first
    project_resp = await client.post("/v1/projects", json={"name": "Casting Test"})
    assert project_resp.status_code == 200
    project = project_resp.json()

    # Generate actor
    resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "anime",
            "traits": {
                "gender": "female",
                "age_range": "young_adult",
                "face_traits": "Big eyes, soft features",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "generated"
    assert data["character_id"] is None  # Not saved yet
    assert "image_url" in data
    assert "image_id" in data
    assert data["traits_used"]["gender"] == "female"


@pytest.mark.anyio
async def test_casting_save_endpoint(client, mock_gemini_client, mock_storage):
    """Test POST /v1/casting/projects/{project_id}/save endpoint."""
    # Create project
    project_resp = await client.post("/v1/projects", json={"name": "Casting Test"})
    project = project_resp.json()

    # Generate actor first
    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "default",
            "traits": {"gender": "male"},
        },
    )
    gen_data = gen_resp.json()

    # Save to library
    save_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "Hero Character",
            "description": "The main hero",
            "traits": {"gender": "male", "age_range": "adult"},
            "image_style_id": "default",
        },
    )
    assert save_resp.status_code == 200
    data = save_resp.json()
    assert data["display_name"] == "Hero Character"
    assert data["is_library_saved"] is True
    assert len(data["variants"]) == 1
    assert data["variants"][0]["is_default"] is True


@pytest.mark.anyio
async def test_casting_library_list_endpoint(client, mock_gemini_client, mock_storage):
    """Test GET /v1/casting/projects/{project_id}/library endpoint."""
    # Create project
    project_resp = await client.post("/v1/projects", json={"name": "Library Test"})
    project = project_resp.json()

    # Initially empty
    list_resp = await client.get(f"/v1/casting/projects/{project['project_id']}/library")
    assert list_resp.status_code == 200
    assert list_resp.json() == []

    # Generate and save an actor
    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "default",
            "traits": {"gender": "female"},
        },
    )
    gen_data = gen_resp.json()

    await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "Actress",
            "traits": {"gender": "female"},
            "image_style_id": "default",
        },
    )

    # Now should have one actor
    list_resp = await client.get(f"/v1/casting/projects/{project['project_id']}/library")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["display_name"] == "Actress"


@pytest.mark.anyio
async def test_casting_get_actor_endpoint(client, mock_gemini_client, mock_storage):
    """Test GET /v1/casting/characters/{character_id} endpoint."""
    # Create project and actor
    project_resp = await client.post("/v1/projects", json={"name": "Get Test"})
    project = project_resp.json()

    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "default",
            "traits": {"gender": "male"},
        },
    )
    gen_data = gen_resp.json()

    save_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "Test Actor",
            "traits": {"gender": "male"},
            "image_style_id": "default",
        },
    )
    actor = save_resp.json()

    # Get actor
    get_resp = await client.get(f"/v1/casting/characters/{actor['character_id']}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["character_id"] == actor["character_id"]
    assert data["display_name"] == "Test Actor"


@pytest.mark.anyio
async def test_casting_get_actor_not_found(client):
    """Test GET /v1/casting/characters/{id} returns 404 for unknown ID."""
    resp = await client.get(f"/v1/casting/characters/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_casting_import_endpoint(client):
    """Test POST /v1/casting/projects/{project_id}/import endpoint."""
    # Create project
    project_resp = await client.post("/v1/projects", json={"name": "Import Test"})
    project = project_resp.json()

    # Import from URL
    import_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/import",
        json={
            "image_url": "https://example.com/character.png",
            "display_name": "Imported Hero",
            "description": "A hero imported from external source",
            "traits": {"gender": "female", "age_range": "teen"},
            "image_style_id": "anime",
        },
    )
    assert import_resp.status_code == 200
    data = import_resp.json()
    assert data["display_name"] == "Imported Hero"
    assert data["is_library_saved"] is True
    assert len(data["variants"]) == 1
    assert data["variants"][0]["variant_type"] == "imported"


@pytest.mark.anyio
async def test_casting_delete_actor_endpoint(client, mock_gemini_client, mock_storage):
    """Test DELETE /v1/casting/characters/{character_id} endpoint."""
    # Create project and actor
    project_resp = await client.post("/v1/projects", json={"name": "Delete Test"})
    project = project_resp.json()

    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "default",
            "traits": {},
        },
    )
    gen_data = gen_resp.json()

    save_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "To Delete",
            "traits": {},
            "image_style_id": "default",
        },
    )
    actor = save_resp.json()

    # Delete (soft delete - removes from library)
    del_resp = await client.delete(f"/v1/casting/characters/{actor['character_id']}")
    assert del_resp.status_code == 200
    data = del_resp.json()
    assert data["removed"] is True

    # Should no longer appear in library
    list_resp = await client.get(f"/v1/casting/projects/{project['project_id']}/library")
    assert list_resp.json() == []


@pytest.mark.anyio
async def test_casting_generate_variant_endpoint(client, mock_gemini_client, mock_storage):
    """Test POST /v1/casting/characters/{id}/variants/generate endpoint."""
    # Create project and actor
    project_resp = await client.post("/v1/projects", json={"name": "Variant Test"})
    project = project_resp.json()

    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "default",
            "traits": {"gender": "female", "hair_traits": "Long black hair"},
        },
    )
    gen_data = gen_resp.json()

    save_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "Base Actor",
            "traits": {"gender": "female", "hair_traits": "Long black hair"},
            "image_style_id": "default",
        },
    )
    actor = save_resp.json()
    base_variant_id = actor["variants"][0]["variant_id"]

    # Mock httpx for loading reference image
    with patch("httpx.Client") as mock_httpx:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = b"fake_ref_image"
        mock_resp.headers = {"content-type": "image/png"}
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_httpx.return_value = mock_client

        # Generate variant
        variant_resp = await client.post(
            f"/v1/casting/characters/{actor['character_id']}/variants/generate",
            json={
                "base_variant_id": base_variant_id,
                "variant_name": "Short Hair Variant",
                "trait_changes": {"hair_traits": "Short pink hair"},
            },
        )
        assert variant_resp.status_code == 200
        data = variant_resp.json()
        assert data["variant_name"] == "Short Hair Variant"
        assert data["variant_type"] == "variant"
        assert data["is_default"] is False


@pytest.mark.anyio
async def test_casting_delete_variant_endpoint(client, mock_gemini_client, mock_storage):
    """Test DELETE /v1/casting/variants/{variant_id} endpoint."""
    # Create project and actor with variant
    project_resp = await client.post("/v1/projects", json={"name": "Delete Variant Test"})
    project = project_resp.json()

    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "default",
            "traits": {"gender": "male"},
        },
    )
    gen_data = gen_resp.json()

    save_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "Actor",
            "traits": {"gender": "male"},
            "image_style_id": "default",
        },
    )
    actor = save_resp.json()
    base_variant_id = actor["variants"][0]["variant_id"]

    # Create a non-default variant
    with patch("httpx.Client") as mock_httpx:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = b"fake_ref_image"
        mock_resp.headers = {"content-type": "image/png"}
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_httpx.return_value = mock_client

        variant_resp = await client.post(
            f"/v1/casting/characters/{actor['character_id']}/variants/generate",
            json={
                "base_variant_id": base_variant_id,
                "trait_changes": {"mood": "angry"},
            },
        )
        new_variant = variant_resp.json()

    # Delete non-default variant should succeed
    del_resp = await client.delete(f"/v1/casting/variants/{new_variant['variant_id']}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True


@pytest.mark.anyio
async def test_casting_cannot_delete_default_variant(client, mock_gemini_client, mock_storage):
    """Test that default variant cannot be deleted."""
    # Create project and actor
    project_resp = await client.post("/v1/projects", json={"name": "Cannot Delete Default"})
    project = project_resp.json()

    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "default",
            "traits": {},
        },
    )
    gen_data = gen_resp.json()

    save_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "Actor",
            "traits": {},
            "image_style_id": "default",
        },
    )
    actor = save_resp.json()
    default_variant_id = actor["variants"][0]["variant_id"]

    # Try to delete default variant - should fail
    del_resp = await client.delete(f"/v1/casting/variants/{default_variant_id}")
    assert del_resp.status_code == 400
    assert "default" in del_resp.json()["detail"].lower()


# ============================================================================
# Workflow Integration Tests
# ============================================================================


@pytest.mark.anyio
async def test_full_actor_creation_workflow(client, mock_gemini_client, mock_storage):
    """Test full workflow: generate -> preview -> save -> list."""
    # 1. Create project
    project_resp = await client.post("/v1/projects", json={"name": "Workflow Test"})
    project = project_resp.json()

    # 2. Generate profile sheet (preview)
    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "anime",
            "traits": {
                "gender": "female",
                "age_range": "young_adult",
                "face_traits": "Expressive eyes",
                "hair_traits": "Long flowing hair",
                "mood": "Determined",
            },
        },
    )
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()

    # Verify preview state
    assert gen_data["character_id"] is None
    assert gen_data["status"] == "generated"

    # 3. Save to library
    save_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "Heroine",
            "description": "The determined protagonist",
            "traits": {
                "gender": "female",
                "age_range": "young_adult",
                "face_traits": "Expressive eyes",
                "hair_traits": "Long flowing hair",
                "mood": "Determined",
            },
            "image_style_id": "anime",
        },
    )
    assert save_resp.status_code == 200
    actor = save_resp.json()

    # Verify saved state
    assert actor["display_name"] == "Heroine"
    assert actor["is_library_saved"] is True
    assert len(actor["variants"]) == 1

    # 4. Verify appears in library
    list_resp = await client.get(f"/v1/casting/projects/{project['project_id']}/library")
    library = list_resp.json()
    assert len(library) == 1
    assert library[0]["character_id"] == actor["character_id"]


@pytest.mark.anyio
async def test_variant_creation_preserves_identity(client, mock_gemini_client, mock_storage):
    """Test that variant creation uses base reference for identity."""
    # Setup
    project_resp = await client.post("/v1/projects", json={"name": "Identity Test"})
    project = project_resp.json()

    gen_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/generate",
        json={
            "image_style_id": "default",
            "traits": {"gender": "female"},
        },
    )
    gen_data = gen_resp.json()

    save_resp = await client.post(
        f"/v1/casting/projects/{project['project_id']}/save",
        json={
            "image_id": gen_data["image_id"],
            "display_name": "Identity Actor",
            "traits": {"gender": "female"},
            "image_style_id": "default",
        },
    )
    actor = save_resp.json()
    base_variant = actor["variants"][0]

    # Verify base variant has reference
    assert base_variant["is_default"] is True

    # Create variant with mock
    with patch("httpx.Client") as mock_httpx:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = b"fake_ref_image"
        mock_resp.headers = {"content-type": "image/png"}
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_httpx.return_value = mock_client

        variant_resp = await client.post(
            f"/v1/casting/characters/{actor['character_id']}/variants/generate",
            json={
                "base_variant_id": base_variant["variant_id"],
                "variant_name": "Different Hair",
                "trait_changes": {"hair_traits": "Short red hair"},
            },
        )

    assert variant_resp.status_code == 200
    new_variant = variant_resp.json()

    # Verify new variant
    assert new_variant["variant_name"] == "Different Hair"
    assert new_variant["traits"]["hair_traits"] == "Short red hair"
    # Original traits should be preserved
    assert new_variant["traits"]["gender"] == "female"


@pytest.mark.anyio
async def test_multiple_actors_in_library(client, mock_gemini_client, mock_storage):
    """Test managing multiple actors in library."""
    project_resp = await client.post("/v1/projects", json={"name": "Multi Actor Test"})
    project = project_resp.json()

    # Create 3 actors
    actor_names = ["Hero", "Villain", "Sidekick"]
    created_actors = []

    for name in actor_names:
        gen_resp = await client.post(
            f"/v1/casting/projects/{project['project_id']}/generate",
            json={
                "image_style_id": "default",
                "traits": {"gender": "male" if name != "Sidekick" else "female"},
            },
        )
        gen_data = gen_resp.json()

        save_resp = await client.post(
            f"/v1/casting/projects/{project['project_id']}/save",
            json={
                "image_id": gen_data["image_id"],
                "display_name": name,
                "traits": {},
                "image_style_id": "default",
            },
        )
        created_actors.append(save_resp.json())

    # Verify library has all 3
    list_resp = await client.get(f"/v1/casting/projects/{project['project_id']}/library")
    library = list_resp.json()
    assert len(library) == 3

    # Verify names (order might vary, so check as set)
    library_names = {a["display_name"] for a in library}
    assert library_names == set(actor_names)

    # Delete one actor
    await client.delete(f"/v1/casting/characters/{created_actors[1]['character_id']}")

    # Library should now have 2
    list_resp = await client.get(f"/v1/casting/projects/{project['project_id']}/library")
    library = list_resp.json()
    assert len(library) == 2
