# TASK-002: Character Library & Reuse System

**Type:** Feature / Frontend & Backend
**Priority:** High
**Status:** Open
**Created:** 2026-01-29
**Related Epic:** WEBTOON-CHAR-REUSE

## Description

Implement a comprehensive "Character Library" workflow allowing users to explicitly save characters, load them into new stories as options, and generate variants using existing references ("Generate with Reference").

## Requirements

### 1. Feature: Save Character to Library

- **Context:** User views a generated character they like.
- **Action:** "Save" button on the character card.
- **Behavior:**
  - Persists the character to a **Project-Level Library** (making it available across stories).
  - **Data to Persist:**
    - Full Visual Profile (Hair, Face, Body, Outfit, etc.).
    - original Text Prompt used for generation.
    - Canonical Reference Image.
    - General Description.
- **Backend:** Ensure `Character` model supports `is_saved_to_library` flag or similar project-scope visibility.

### 2. Feature: Generate with Reference (Variant Creation)

- **Context:** User is adding a character to a new story.
- **Action:** "Generate with Reference" button/option.
- **UI Interaction:**
  - Opens a **Library Popup/Modal**.
  - Displays list of "Saved Characters" (with images and names) from the project.
  - User selects one character.
- **Generation Logic:**
  - Calls generation endpoint using the **Selected Image** as the visual anchor.
  - Combines with the _current_ story's context/prompt (e.g., "wearing a spacesuit").
  - **Crucial:** Resulting image must retain facial identity of selected character but adopt new attributes.

### 3. Feature: Load Character (Direct Reuse)

- **Context:** User wants to reuse an exact image for a character in a new story.
- **Action:** "Load Character" button.
- **UI Interaction:**
  - Same Library Popup as above.
  - User selects a character.
- **Behavior:**
  - Directly links the **Selected Image** to the current story's character entry.
  - It appears as a selected option (alongside any potential new generations).
  - **Capabilities:**
    - User can select it as the active image.
    - User can delete/remove it from this story.
    - User can trigger "Generate Variants" from it (invoking Feature #2 logic).

## Implementation Plan

1.  **Backend:**
    - Update `Character` and `CharacterReferenceImage` models/endpoints to support proper project-level scoping and "Library" status.
    - Implement `save_character` endpoint.
    - Ensure `generate_character_variant` accepts an external `reference_image_id` from the library.
2.  **Frontend:**
    - Build "Character Library Modal" component.
    - Add "Save" button to Character Card.
    - Add "Generate with Ref" and "Load" buttons to Story Character interface.

## Acceptance Criteria

- User can save a character in Story A and see it in the Library in Story B.
- "Generate with Reference" successfully creates a variant of the selected library character in the new story context.
- "Load Character" brings the exact image ID into the current story context without re-generation.
