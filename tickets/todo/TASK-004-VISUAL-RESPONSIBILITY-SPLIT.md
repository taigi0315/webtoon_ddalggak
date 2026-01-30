# TASK-004: Visual Responsibility Split & Style Neutralization

## Context: The "Style Overwriting" Problem

Current analysis shows that the `image_style` parameter (the intended Visual DNA) is being consistently overwritten by hardcoded "Korean Webtoon/Manhwa" anchors and style-polluted character descriptions. This creates a "Vertical Overwriting" effect where the AI defaults to a generic webtoon aesthetic regardless of the user's choice (e.g., Oil Painting, 3D Disney, Noir).

### Root Causes

1. **Style Pollution**: Character descriptions and `identity_line` currently contain stylistic keywords ("Manhwa aesthetic", "Flower-boy") that are stored in the DB and injected into every scene prompt.
2. **Muddled Responsibility**: The `genre_guidelines_v1.json` and various prompts mix "What" (Layout) and "How" (Rendering), creating conflicting instructions for the AI.
3. **Hardcoded Anchors**: Technical requirements in `compile.py` and `rendering.py` contain hardcoded "Korean Webtoon" commands that act as a final, inescapable "filter."

## Objectives

### 1. Style Neutralization (The Clean-up)

- [ ] **Neutralize Character Normalization**: Update `character_normalization.yaml` to focus strictly on **Morphological/Anatomical** descriptions (e.g., "Sharp jawline" instead of "Flower-boy face").
- [ ] **Sanitize Identity Lines**: Ensure the `identity_line` stored in the DB is style-agnostic. Remove all art-style references from the normalization output.
- [ ] **System-wide Scrub**: Delete all hardcoded "Korean Webtoon", "Manhwa", and "Naver Webtoon" strings from `app/graphs/nodes/prompts/compile.py` and `app/graphs/nodes/rendering.py`.

### 2. Deleting Genre Guidelines

- [ ] **Deprecate `genre_guidelines_v1.json`**: Completely remove this file and its associated loader logic.
- [ ] **Redistribute Knowledge**: Move "Genre Wisdom" (e.g., how to shot a Rom-com vs Thriller) into the high-level reasoning of the `Studio Director` node.

### 3. Responsibility Decoupling (Cinematographer vs. Art Director)

Implement a clear split in how prompts are constructed:

- [ ] **Cinematographer (Direction)**: Focuses only on `camera`, `angle`, `composition`, and `shot_type`. **Rule**: No mention of colors, lighting, or art style.
- [ ] **Art Director (Visuals)**: Focuses on `lighting`, `color_palette`, and `atmosphere` based on the `image_style` + `Studio Director's` emotional intent.
- [ ] **Prompt Reconstruction**: Update `compile.py` to assemble the final prompt by layering these distinct outputs: `[Image Style Reference] + [Art Director's Mood] + [Cinematographer's Layout]`.

## Data Hierarchy (The "Vertical" Line)

To prevent overwriting, the prompt must follow this authority hierarchy:

1. **Top Priority**: `image_style_id` (The baseline rendering rule).
2. **Contextual Priority**: `Studio Director's Intent` (The emotional lighting/mood).
3. **Structural Priority**: `Cinematographer's Plan` (The camera/body positioning).
4. **Lowest Priority (Neutral)**: `Character Morphology` (Basic features like hair color/height).

## Acceptance Criteria

- [ ] Character profiles in the DB no longer contain words like "manhwa", "webtoon", or "aesthetic".
- [ ] Applying a `STARK_BLACK_WHITE_NOIR` style results in a pure monochrome image, even if the genre is "Romance".
- [ ] No hardcoded "Korean" keywords appear in the terminal logs when `DEBUG_PROMPT=true` is set.
- [ ] The `Studio Director` successfully manages tone shifts without confusing visual styles.
