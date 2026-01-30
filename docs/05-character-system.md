# Character System

## Overview

The character system extracts characters from story text, enriches them with visual details for consistent rendering, and manages appearance variations through the Actor library and variant system. Characters are assigned canonical codes (CHAR_A, CHAR_B, etc.) for consistent identification across scenes and stories, with support for outfit changes and global character reuse.

## Character Extraction

**Purpose**: Identify important characters from story text

**Process**:
- LLM-based extraction identifies explicit and implied characters
- Extracts name, role (main/secondary), relationship to protagonist
- Includes evidence quotes from source text
- Falls back to heuristic NER (Named Entity Recognition) if LLM fails

**Heuristic Fallback**:
- Uses regex patterns to extract proper nouns
- Excludes metadata names (author, title, etc.)
- Assigns roles based on mention frequency (first 2 are "main", rest are "secondary")

**Implementation**: `app/graphs/nodes/planning/character.py` - `compute_character_profiles_llm()`

## Character Normalization

**Purpose**: Add visual details for consistent image generation

**Process**:
- LLM adds appearance details: hair, face, build, outfit
- Applies Korean manhwa aesthetic standards via character style map
- Creates identity_line for use in image prompts
- Falls back to basic normalization if LLM fails

**Character Style Map**:
- Age/gender-based styling templates (child, teen, young_adult, adult, middle_aged, elderly)
- Korean manhwa proportions and aesthetics
- Stored in `app/prompts/prompts.yaml` under `character_style_map`

**Visual Details Added**:
- `gender` - male, female, unknown
- `age_range` - child, teen, young_adult, adult, middle_aged, elderly
- `appearance` - JSON with hair, face, build details
- `hair_description` - Detailed hair styling
- `base_outfit` - Default clothing description
- `identity_line` - Compiled description for prompts (e.g., "Alice: young adult female, long black hair, slender build, school uniform")

**Implementation**: `app/graphs/nodes/planning/character.py` - `normalize_character_profiles_llm()`

## Canonical Codes

**Purpose**: Consistent character identification across scenes and stories

**Assignment**:
- Sequential codes: CHAR_A, CHAR_B, CHAR_C, ..., CHAR_Z, CHAR_AA, CHAR_AB, etc.
- Assigned during `persist_story_bundle` node in StoryBuildGraph
- Persists across stories within same project

**Deduplication Logic**:
- Case-insensitive name matching across project
- Merges characters by name: preserves existing data, fills missing fields
- Reuses canonical_code for matched characters
- Links character to new story via StoryCharacter join table

**Example**:
```python
# File: app/graphs/story_build.py

# Character "Alice" in Story 1 gets CHAR_A
# Character "Alice" in Story 2 reuses CHAR_A (same character entity)
# Character "Bob" in Story 2 gets CHAR_B (new character)
```

**Implementation**: `app/graphs/story_build.py` - `_node_persist_story_bundle()`

## Actor System

**Purpose**: Global character library for reuse across projects and stories

**Key Features**:
- Characters with `project_id = NULL` are global actors
- Actors can be "cast" into any project or story
- Approval workflow via `approved` flag
- Profile sheet generation with full-body and expression insets

**Actor Fields**:
- `display_name` - Human-readable name for library browsing
- `default_story_style_id` - Preferred story style
- `default_image_style_id` - Preferred image style
- `is_library_saved` - Whether actor is saved to library
- `approved` - Whether actor is approved for use

**Profile Sheet Generation**:
- 9:16 vertical image with full-body front view (head-to-toe)
- 2-3 expression inset boxes
- Generated via `generate_character_profile_sheet()` in `app/services/casting.py`

**Implementation**: `app/services/casting.py` - Actor generation and management

## Character Variants

**Purpose**: Manage appearance changes while maintaining character identity

**Variant Types**:
- `base` - Default appearance
- `outfit_change` - Different clothing
- `mood_change` - Different expression/styling
- `style_change` - Different art style

**Scoping**:
- **Story-scoped** (`story_id` set): Used within specific story context
- **Global** (`story_id = NULL`): Part of Actor library, reusable across stories

**Variant Fields**:
- `variant_name` - Human-readable name (e.g., "Summer Look", "Battle Mode")
- `traits` - JSON with face, hair, mood, outfit overrides
- `override_attributes` - Additional attribute overrides
- `reference_image_id` - Optional reference image for consistency
- `generated_image_ids` - List of generated image UUIDs
- `is_default` - Whether this is the default variant
- `is_active_for_story` - Whether this variant is currently active for story

**Active Variant Selection**:
- Only one variant can be active per character per story
- Activating a variant deactivates all others for that character/story
- Active variant is used for rendering in that story

**Implementation**: `app/db/models.py` - `CharacterVariant` model, `app/api/v1/character_variants.py` - Variant management endpoints

## Reference Images

**Purpose**: Provide visual consistency for character rendering

**Reference Types**:
- `face` - Close-up face reference
- `full_body` - Full-body reference
- `profile_sheet` - Complete character sheet with expressions

**Reference Fields**:
- `image_url` - URL to reference image
- `ref_type` - Type of reference (face, full_body, profile_sheet)
- `approved` - Whether reference is approved for use
- `is_primary` - Whether this is the primary reference
- `metadata_` - Additional metadata (generation params, traits, etc.)

**Usage**:
- Linked to CharacterVariant via `reference_image_id`
- Used in image generation prompts for consistency
- Can be uploaded manually or generated via profile sheet

**Implementation**: `app/db/models.py` - `CharacterReferenceImage` model

## Key Files

- `app/graphs/nodes/planning/character.py` - Character extraction and normalization
- `app/graphs/story_build.py` - Character deduplication and canonical code assignment
- `app/services/casting.py` - Actor system and profile sheet generation
- `app/services/variant_suggestions.py` - AI-powered variant suggestions
- `app/api/v1/characters.py` - Character CRUD endpoints
- `app/api/v1/character_variants.py` - Variant management endpoints
- `app/db/models.py` - Character, StoryCharacter, CharacterVariant, CharacterReferenceImage models
- `app/prompts/prompts.yaml` - Character style map and normalization prompts

## Debugging Direction

**When character consistency issues occur, check:**

- **Canonical code issues**:
  - Query `Character` table: `SELECT canonical_code, name, project_id FROM characters WHERE project_id = ?`
  - Verify codes are unique within project
  - Check for duplicate names with different codes (deduplication failure)

- **Character extraction failures**:
  - Review `characters` list in StoryBuildState
  - Check logs for LLM extraction failures (falls back to heuristic)
  - Verify `max_characters` limit is not too restrictive

- **Normalization issues**:
  - Check `Character.identity_line` field for compiled descriptions
  - Review `Character.appearance` JSON for visual details
  - Verify `age_range` and `gender` are set correctly
  - Check character style map in `prompts.yaml` for age/gender templates

- **Variant activation issues**:
  - Query active variants: `SELECT * FROM character_variants WHERE story_id = ? AND is_active_for_story = true`
  - Verify only one variant is active per character per story
  - Check `variant_type` and `override_attributes` for correct values

- **Actor system issues**:
  - Query global actors: `SELECT * FROM characters WHERE project_id IS NULL`
  - Check `is_library_saved` and `approved` flags
  - Review `CharacterReferenceImage` table for profile sheets

- **Deduplication issues**:
  - Check `StoryCharacter` join table for character-story links
  - Verify case-insensitive name matching is working
  - Review logs for character merge operations

**Useful queries**:

```sql
-- List all characters with canonical codes
SELECT canonical_code, name, role, gender, age_range, identity_line
FROM characters
WHERE project_id = ?
ORDER BY canonical_code;

-- Check character-story links
SELECT c.name, c.canonical_code, sc.story_id
FROM characters c
JOIN story_characters sc ON c.character_id = sc.character_id
WHERE sc.story_id = ?;

-- Find active variants for a story
SELECT cv.variant_name, cv.variant_type, c.name
FROM character_variants cv
JOIN characters c ON cv.character_id = c.character_id
WHERE cv.story_id = ? AND cv.is_active_for_story = true;

-- List global actors
SELECT display_name, name, approved, is_library_saved
FROM characters
WHERE project_id IS NULL
ORDER BY created_at DESC;

-- Check reference images for a character
SELECT ref_type, approved, is_primary, image_url
FROM character_reference_images
WHERE character_id = ?
ORDER BY created_at DESC;
```

**Key log patterns to search**:
- `character.extraction` - Character extraction traces
- `character.normalization` - Character normalization traces
- `character.deduplication` - Character merge operations
- `variant.activation` - Variant activation events

## See Also

- [Prompt System](03-prompt-system.md) - Character style map and normalization prompts
- [Database Models](04-database-models.md) - Character model relationships
- [LangGraph Architecture](02-langgraph-architecture.md) - Character extraction in StoryBuildGraph
- [Application Workflow](01-application-workflow.md) - Character processing in episode-level workflow
- [SKILLS.md](../SKILLS.md) - Quick reference guide
