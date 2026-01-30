# Task: Remove Story Style Concept

## Context

The current "Story Style" (e.g., Romance, Horror, Action) overlaps significantly with "Image Style" (lighting, color) and interferes with the "Panel Planning" logic (camera angles).

- **Redundancy:** Lighting/Color is already handled by `Image Style`.
- **Interference:** Global camera preferences (e.g., "Romance uses close-ups") override specific dramatic needs determined by the scene planner.
- **Goal:** Simplify the pipeline. Let `Panel Plan` drive camera/layout based on narrative beat, and `Image Style` drive the visual look.

## Objectives

Remove "Story Style" from the entire stack: Frontend, Backend, Database, and Prompts.

### 1. Database & Models

- [ ] Remove `default_story_style_id` from `Story` model.
- [ ] Remove `story_style_override` from `Scene` model.
- [ ] Remove `default_story_style_id` from `Character` model (and `Actor` logic).
- [ ] Remove `story_style_id` from `CharacterVariant` table.
- [ ] Migration: Drop columns and clean up `style_presets` table if it was used for story styles.

### 2. Backend Logic & Services

- [ ] **Casting Service (`app/services/casting.py`)**: Remove `story_style_id` arguments from:
  - `generate_character_profile_sheet`
  - `save_actor_to_library`
  - `generate_variant_from_reference`
  - `import_actor_from_image`
  - `import_actor_from_local_file`
- [ ] **Prompt Context**: Stop passing `story_style` to prompts.
- [ ] **Genre Guidelines**: Remove `app/graphs/nodes/genre_guidelines.py` or strip it down if used for other things (e.g., intent analysis).
- [ ] **Graph Nodes**:
  - Update `panel_semantics.py` to stop injecting genre-based visual guidelines (`genre_block`).
  - Update `visual_plan.py` to remove story style dependency.

### 3. API & Schemas

- [ ] Update `StoryCreate`/`StoryUpdate` schemas to remove `story_style`.
- [ ] Update `CharacterCreate`/`update` schemas.
- [ ] Update `SceneUpdate` schemas.
- [ ] Remove `StoryStyle` enum/literals.

### 4. Frontend

- [ ] **Project Creation/Settings**: Remove "Select Story Genre/Style" dropdowns.
- [ ] **Character Studio**: Remove "Story Style" selection when creating/editing characters.
- [ ] **Scene Editor**: Remove "Story Style Override" option.
- [ ] **Casting Page**: Remove "Story Style" from the Import/Create forms.

### 5. Config/Resources

- [ ] Delete `app/config/story_styles.json`.
- [ ] Update `app/config/loaders.py` to stop loading story styles.

## Acceptance Criteria

- [ ] Application starts without errors.
- [ ] Creating a project/story no longer asks for Story Style.
- [ ] Image generation relies solely on `Image Style` + `Panel Plan` instructions.
- [ ] Database migration applied successfully.
