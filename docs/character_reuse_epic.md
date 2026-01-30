# Epic: Project-Level Character Reuse & Variant Generation

**Epic ID:** WEBTOON-CHAR-REUSE
**Priority:** P0
**Status:** Open

## Intent
Characters must be **project-level reusable entities**, not story-level throwaways. When a new story (episode) is created inside the same project and references an existing character, the system must **reuse the existing canonical character reference image** and optionally generate a **story-specific variant** (e.g., outfit change) using that reference image. The variant becomes the **active reference for that story**, while the base character remains unchanged.

---

## TASK 1 — Introduce Project-Level Character Entity (Blocking)
**Status:** In progress
**Type:** Backend / Data Model
**Priority:** P0

### Description
Create a **project-level Character entity** that persists independently of stories. Characters live at the **project level** and can be reused by multiple stories.

### Requirements
Each `Character` must include:
- `character_id` (stable across project)
- `project_id`
- `canonical_name`
- `base_profile` (gender, age range, body profile, etc.)
- `base_reference_image_id` (canonical identity image)
- `variants[]` (list of character variants, see Task 2)
- metadata (`created_at`, `updated_at`)

### Acceptance Criteria
- Characters are no longer duplicated per story
- A character created in Story 1 is visible and reusable in Story 2 (same project)

---

## TASK 2 — Add Character Variant Model (Outfit / Appearance Changes)
**Status:** In progress
**Type:** Backend / Domain Logic
**Priority:** P0

### Description
Introduce a **CharacterVariant** entity to support outfit or appearance changes per story.

### Fields
- `variant_id`
- `character_id` (parent)
- `story_id`
- `variant_type` (e.g. `outfit_change`, `hair_change`, `time_skip`)
- `override_attributes` (e.g. outfit, accessories)
- `reference_image_id` (generated using base reference)
- `is_active_for_story` (boolean)

### Rules
- Variant generation MUST use:
  - `base_reference_image_id` as image reference
  - variant overrides (e.g. outfit)
- Variant reference image becomes the **active reference for that story**
- Base character reference remains unchanged

### Acceptance Criteria
- Story 2 can create a new variant of an existing character
- Variant does NOT overwrite base character
- Variant is used consistently throughout that story

---

## TASK 3 — Character Resolution Logic During Story Generation
**Type:** LangGraph / Orchestration
**Priority:** P0

### Description
When generating a story inside a project, resolve characters using the following priority:

### Resolution Rules
1. If character exists in project → reuse existing `Character`
2. If story specifies appearance changes → generate `CharacterVariant` using base reference + overrides
3. If no variant needed → use base reference image directly
4. If character does NOT exist in project → create new character + base reference image

### Acceptance Criteria
- Story generation never creates duplicate characters for same identity
- Variants are created only when needed

---

## TASK 4 — Update Character Generation Prompt (Reference-First)
**Type:** Prompt Compiler
**Priority:** P0

### Description
Never regenerate an existing character from text alone.

### Prompt Rules
- If `base_reference_image` exists:
  - ALWAYS include it as image reference
  - Include Reference Image Authority block
- Text prompt should only describe:
  - outfit changes
  - accessories
  - mood (if needed)
- Facial features/body proportions must come from the reference image

### Acceptance Criteria
- Character variants visually match base character identity
- Outfit changes apply cleanly without face/body drift

---

## TASK 5 — Update Scene Image Generation to Use Active Variant
**Type:** Prompt Compiler / Scene Rendering
**Priority:** P0

### Description
Ensure scene image generation uses the **correct reference image**:

### Rules
- For each character in a scene:
  - If a variant exists for the story → use variant reference
  - Else → use base reference
- Never mix base + variant references in the same story

### Acceptance Criteria
- All scenes in Story 2 consistently use Story 2 character variant
- No regression to base outfit mid-story

---

## TASK 6 — Frontend: Character Reuse UX
**Type:** Frontend
**Priority:** P1

### Description
Expose character reuse clearly to the user.

### UI Requirements
- Project-level character list
- When creating a new story:
  - Show existing characters
  - Indicate “Reuse existing character”
- If story introduces appearance change:
  - Prompt user: “New outfit / appearance?”
  - Generate variant preview
- Allow user to:
  - Accept variant
  - Regenerate variant
  - Keep base character

### Acceptance Criteria
- Users understand characters persist across stories
- Variant creation is explicit and visible

---

## TASK 7 — Data Persistence & Navigation Safety
**Type:** Backend / State Management
**Priority:** P0

### Description
Ensure characters and variants persist across:
- tab switches
- story edits
- regeneration

### Acceptance Criteria
- Navigating between Story 1 and Story 2 does not lose character data
- Regenerating a story does not delete existing characters or variants unless explicitly requested

---

## Non-Goals
- Do NOT auto-merge variants back into base character
- Do NOT allow silent character overwrites
- Do NOT regenerate base character if reference already exists
