Below is a clean **EPIC ticket** (with scope, UX, data model, APIs, prompts, and acceptance criteria) that matches exactly what you described. You can paste this into Jira/Linear as-is.

---

# EPIC: Character Library & Casting Tab (Actors + Variants)

**Epic ID:** WEBTOON-CASTING-LIBRARY
**Priority:** P0 (Foundational for reuse & organization)
**Type:** Frontend + Backend + Prompting + Data Model
**Goal:** Add a standalone “Character Generate / Casting” tab where users can generate, import, save, and manage reusable actor-style characters and their variants across projects/stories.

---

## Background / Problem

Current character system is story-scoped and static (e.g., one “Ji-hoon” with one variant image). This breaks the desired workflow where characters should behave like **actors**:

- Users generate attractive characters independent of any story
- Save them into a reusable **Character Library**
- Create **variants** (hair changes, mood changes, style changes) as needed
- Reuse those variants in different stories/projects

We need a dedicated UI and a restructured database model to support:

- **Character = stable entity (primary key is character_id)**
- **CharacterVariant = multiple looks of the same character**
- **Import/upload existing character images**
- **Reference-first generation for consistency**

---

## User Story

As a user, I want a separate **Character Generate** tab (not tied to story creation) where I can:

1. Choose **Story Style** and **Image Style**
2. Enter character details (face/hair/mood + optional custom prompt)
3. Generate a **character profile sheet** (full-body + headshots/expressions)
4. Regenerate until I like it
5. Save the character into my **Character Library** with a name
6. Later, load a character and create **variants** using the saved reference image(s)
7. Use a saved character/variant in any story as “casting”

---

# Scope

## In-Scope (Phase 1)

### A) New Left-Side Tab: “Character Library” / “Casting”

- New navigation entry in the UI
- Fully independent flow from story creation

### B) Character Generation UI

Inputs:

- Story Style (dropdown / chips)
- Image Style (dropdown / chips)
- Character fields:
  - gender (optional)
  - age range (optional)
  - face traits (short)
  - hair traits (short)
  - mood (short)

- Custom prompt free-text (optional)

Buttons:

- Generate
- Regenerate
- Save to Library (opens “Name character” modal)

Output:

- Character profile sheet style image:
  - Full body front view (head-to-toe)
  - One or more facial close-ups / expression insets

### C) Character Variant Creation from a Base Character

On a saved character page:

- Select an existing variant
- “Create Variant” button:
  - Use selected variant/base as **reference image**
  - Allow changes (hair, mood, _optionally_ style/story style)
  - Generate new profile sheet
  - Save variant under the same character_id

### D) Import / Upload Existing Character (Create Actor Profile)

- “Import Character” button
- Upload image(s) and enter same character fields
- Save into Character Library as new character entity (new character_id)
- Uploaded image becomes a reference variant

### E) Data Model Refactor (Primary Key = character_id)

Replace “name-based single character” with stable IDs and variant lists.

---

## Out-of-Scope (Phase 1)

- Casting characters directly into stories (can be Phase 2, but include minimal API hooks)
- Advanced search, tagging, similarity search (optional Phase 2)
- Multi-user sharing marketplace

---

# Functional Requirements

## 1) Character Generation Prompt Requirements (Profile Sheet)

Generated output must:

- be vertical (9:16)
- include:
  - full-body front view (head-to-toe)
  - neutral pose
  - clean background or simple gradient
  - 2–3 inset headshots showing expressions (optional but preferred)

- no text, no speech bubbles, no watermark

If generating a **variant** using a reference:

- Reference image is primary authority for identity

## 2) Save & Organize

When user clicks “Save to Library”:

- Modal asks for:
  - character_name (required)
  - short description (optional)

- System creates:
  - Character entity (if new)
  - Variant entity linked to that character_id

## 3) Variant Rules

A character can have multiple variants:

- different hair style
- different mood
- different outfit (optional later)
- different story/image style (allowed if user selects)

All variants are grouped under the same character_id.

---

# Data Model (Required Change)

## New Tables / Collections

### Character (Actor)

- `character_id` (UUID, PK)
- `display_name`
- `description`
- `created_at`, `updated_at`
- `default_story_style_id` (optional)
- `default_image_style_id` (optional)

### CharacterVariant (Looks)

- `variant_id` (UUID, PK)
- `character_id` (FK)
- `image_style_id`
- `story_style_id`
- `traits` (json: face/hair/mood etc.)
- `reference_image_ids` (list)
- `generated_image_ids` (list; includes profile sheet)
- `created_at`
- `is_default` (bool)

### Optional: ImportedReference

- store original uploads as assets tied to variant

**Key rule:**
**The primary key is `character_id`, not the name.**
Names can collide; IDs must not.

---

# API Requirements

## Character Library API

- `POST /characters` → create actor profile
- `GET /characters` → list actors
- `GET /characters/{character_id}` → actor + variants
- `POST /characters/{character_id}/variants` → generate variant (ref-first)
- `POST /characters/import` → create actor from uploads
- `DELETE /variants/{variant_id}` (optional)

---

# LangGraph / Backend Flow Requirements

## Flow A: Generate New Character (no reference)

Nodes:

1. `StyleResolver` (story_style + image_style)
2. `CharacterPromptBuilder` (build profile sheet prompt)
3. `ImageGenerator` (generate sheet)
4. `AssetSaver` (store)
5. `ReturnResult`

## Flow B: Generate Variant (reference-first)

Nodes:

1. `LoadCharacterVariantRef` (get chosen ref image)
2. `StyleResolver`
3. `VariantPromptBuilder` (**includes reference authority block**)
4. `ImageGenerator` (image+text)
5. `AssetSaver` (store)
6. `ReturnResult`

---

# Prompt Work (Required)

## Character Sheet Prompt Builder must enforce:

- 9:16
- full-body front view
- clean simple background
- inset expressions
- no text

## Variant Prompt Builder must enforce:

- “reference image authority”
- only describe changes (hair/mood/style), not identity

---

# UX Requirements

## Character Library Tab Layout

Left: list/grid of saved characters
Middle: character details + variant selector + generate variant
Right: preview of generated images (latest) + actions

Buttons:

- Generate new character
- Import/upload character
- Save to Library
- Create Variant
- Regenerate

---

# Acceptance Criteria

### Core

- User can generate a character sheet using selected styles + prompt fields
- User can regenerate and then save as a new Character with unique `character_id`
- User can open saved character and see its variants
- User can generate a new variant using reference image and save it under same character_id
- User can import an uploaded character image and save as a library character
- Database stores characters by ID and supports multiple variants per character

### Quality

- Character sheet output consistently includes full body + inset headshots
- Variant outputs maintain identity similarity better than text-only generation

### Non-regression

- Existing story-scoped character system continues to function (until migrated)
- No breaking changes in story generation endpoints; casting integration can come later

---

# Migration Notes (Important)

- Existing characters created through story pipeline should be migrated into:
  - Character (actor)
  - Variant (look)

- If migration is too risky now, keep old table but add:
  - a one-time “promote to library” operation

---

If you want, I can also write the **subtasks breakdown** (frontend tickets vs backend tickets vs prompt tickets) so your agent can implement in a clean order.
