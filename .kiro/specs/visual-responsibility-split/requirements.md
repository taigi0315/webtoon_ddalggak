# Requirements Document

## Introduction

The webtoon generation system currently suffers from a "style overwriting" problem where the user-selected `image_style` parameter is systematically overridden by hardcoded "Korean Webtoon/Manhwa" anchors and style-polluted character descriptions stored in the database. This creates a vertical overwriting effect where the AI defaults to a generic webtoon aesthetic regardless of the user's explicit style choice.

This feature implements a comprehensive visual responsibility split and style neutralization to ensure that user-selected image styles are respected throughout the rendering pipeline, while maintaining clear separation of concerns between layout (cinematography), mood (art direction), and rendering style (image style).

## Glossary

- **System**: The webtoon generation system including LangGraph nodes, prompt compilation, and image rendering
- **Image_Style**: User-selected visual rendering style (e.g., STARK_BLACK_WHITE_NOIR, SOFT_ROMANTIC_WEBTOON)
- **Character_Normalization**: LLM-based process that enriches character profiles with visual descriptions
- **Identity_Line**: Single comprehensive character description stored in database and injected into prompts
- **Style_Pollution**: Presence of stylistic keywords (e.g., "Manhwa aesthetic", "Flower-boy") in morphological descriptions
- **Cinematographer**: LangGraph node responsible for camera, angle, composition, shot type
- **Art_Director**: LangGraph node responsible for lighting, color palette, atmosphere based on emotional intent
- **Studio_Director**: LangGraph node responsible for high-level scene planning and emotional intent
- **Prompt_Compiler**: Function that assembles final image generation prompts from multiple sources
- **Genre_Guidelines**: JSON configuration file containing genre-specific layout and style instructions (deprecated)
- **Technical_Requirements**: Hardcoded prompt section containing rendering instructions

## Requirements

### Requirement 1: Character Description Style Neutralization

**User Story:** As a system architect, I want character descriptions to be style-agnostic, so that user-selected image styles are not overridden by character data.

#### Acceptance Criteria

1. WHEN the Character_Normalization process generates character descriptions, THE System SHALL produce morphological and anatomical descriptions only
2. WHEN generating identity_line fields, THE System SHALL exclude all stylistic keywords including "manhwa", "webtoon", "aesthetic", "flower-boy", "K-drama", and similar terms
3. WHEN generating appearance fields, THE System SHALL focus on objective physical attributes (hair color/length, facial structure, body proportions, height) without style references
4. WHEN generating outfit fields, THE System SHALL describe clothing items and colors without referencing art styles or cultural aesthetics
5. THE Character_Normalization prompt SHALL NOT contain instructions to "Apply Korean manhwa aesthetic standards" or similar style-specific guidance

### Requirement 2: Hardcoded Style Anchor Removal

**User Story:** As a developer, I want to remove all hardcoded style anchors from the codebase, so that the rendering pipeline respects user-selected styles.

#### Acceptance Criteria

1. THE Prompt_Compiler SHALL NOT include the string "Korean webtoon/manhwa art style (Naver webtoon quality)" in Technical_Requirements
2. THE Prompt_Compiler SHALL NOT include the string "Vertical 9:16 webtoon/manhwa image" in format descriptions
3. THE Character reference image generation functions SHALL NOT include "Korean webtoon" in their prompts
4. WHEN searching the codebase for "Korean webtoon", "Manhwa", or "Naver webtoon" strings, THE System SHALL return zero matches in prompt-related code
5. THE System SHALL replace hardcoded style references with dynamic references to the user-selected Image_Style

### Requirement 3: Genre Guidelines Deprecation

**User Story:** As a system architect, I want to remove genre-specific style guidelines, so that genre wisdom is handled at the reasoning level rather than through configuration.

#### Acceptance Criteria

1. THE System SHALL NOT load or reference `genre_guidelines_v1.json` configuration file
2. THE System SHALL remove all code that reads from or applies genre guidelines
3. WHEN a scene is planned, THE Studio_Director SHALL incorporate genre wisdom through high-level reasoning without explicit style instructions
4. THE System SHALL remove the `load_genre_guidelines_v1()` function from config loaders
5. THE System SHALL delete the `genre_guidelines_v1.json` file from the codebase

### Requirement 4: Cinematographer Responsibility Decoupling

**User Story:** As a system architect, I want the Cinematographer to focus solely on layout and composition, so that visual style decisions are separated from structural decisions.

#### Acceptance Criteria

1. WHEN the Cinematographer node generates panel descriptions, THE System SHALL include only camera angle, shot type, composition, and body positioning
2. THE Cinematographer output SHALL NOT include color palette, lighting quality, or atmospheric mood keywords
3. THE Cinematographer output SHALL NOT reference art styles or rendering techniques
4. WHEN generating environment descriptions, THE Cinematographer SHALL describe spatial layout and architecture without lighting or color information
5. THE Cinematographer prompt SHALL explicitly instruct to avoid color, lighting, and style keywords

### Requirement 5: Art Director Responsibility Definition

**User Story:** As a system architect, I want a dedicated Art Director node to handle mood and atmosphere, so that emotional intent is translated to visual elements without conflicting with image style.

#### Acceptance Criteria

1. THE System SHALL create an Art_Director node in the LangGraph workflow
2. WHEN the Art_Director processes a scene, THE System SHALL generate lighting quality, color temperature, and atmospheric keywords based on emotional intent
3. THE Art_Director SHALL receive the user-selected Image_Style as context
4. THE Art_Director output SHALL complement the Image_Style without overriding its core characteristics
5. WHEN the Image_Style is STARK_BLACK_WHITE_NOIR, THE Art_Director SHALL generate lighting and mood keywords compatible with monochrome rendering

### Requirement 6: Prompt Layering Hierarchy

**User Story:** As a system architect, I want a clear prompt layering hierarchy, so that user-selected styles take precedence over contextual and structural information.

#### Acceptance Criteria

1. WHEN the Prompt_Compiler assembles the final prompt, THE System SHALL layer prompts in this order: [Image_Style Reference] → [Art_Director Mood] → [Cinematographer Layout] → [Character Morphology]
2. THE Image_Style prompt SHALL appear first in the compiled prompt to establish baseline rendering rules
3. THE Art_Director mood keywords SHALL appear before Cinematographer layout to establish atmosphere
4. THE Character morphology SHALL appear last as the lowest priority information
5. THE System SHALL NOT allow later prompt sections to override earlier style declarations

### Requirement 7: Image Style Authority

**User Story:** As a user, I want my selected image style to be respected throughout rendering, so that I get the visual aesthetic I explicitly chose.

#### Acceptance Criteria

1. WHEN a user selects STARK_BLACK_WHITE_NOIR style, THE System SHALL produce pure monochrome images regardless of genre
2. WHEN a user selects SOFT_ROMANTIC_WEBTOON style, THE System SHALL apply pastel colors and soft lighting regardless of character descriptions
3. THE System SHALL use the `image_style_id` parameter as the highest priority visual directive
4. WHEN debugging with `DEBUG_PROMPT=true`, THE System SHALL log the effective image style at the start of prompt compilation
5. THE System SHALL NOT allow genre, character data, or scene context to override the user-selected Image_Style

### Requirement 8: Database Migration for Character Data

**User Story:** As a developer, I want to sanitize existing character data, so that legacy style-polluted descriptions don't affect new renders.

#### Acceptance Criteria

1. THE System SHALL provide a database migration script to sanitize existing character identity_line fields
2. WHEN the migration runs, THE System SHALL remove stylistic keywords from all character records
3. THE migration SHALL preserve morphological information (hair color, height, facial features) while removing style references
4. THE migration SHALL log the number of characters updated and keywords removed
5. THE System SHALL provide a rollback mechanism for the migration

### Requirement 9: Studio Director High-Level Reasoning

**User Story:** As a system architect, I want the Studio Director to manage tone and pacing at a high level, so that genre wisdom is applied through reasoning rather than hardcoded rules.

#### Acceptance Criteria

1. WHEN the Studio_Director plans a scene, THE System SHALL reason about emotional tone, pacing, and narrative importance
2. THE Studio_Director SHALL communicate intent to the Art_Director through semantic descriptions (e.g., "tense confrontation", "romantic intimacy")
3. THE Studio_Director SHALL NOT generate specific color palettes, lighting setups, or art style directives
4. THE Studio_Director output SHALL be style-agnostic and compatible with any Image_Style
5. WHEN a Romance genre scene is planned, THE Studio_Director SHALL focus on emotional beats without assuming pastel colors or soft lighting

### Requirement 10: Prompt Compilation Testing

**User Story:** As a developer, I want comprehensive tests for prompt compilation, so that style overwriting bugs are caught before production.

#### Acceptance Criteria

1. THE System SHALL provide unit tests that verify Image_Style appears first in compiled prompts
2. THE System SHALL provide tests that verify no hardcoded "Korean webtoon" strings appear in prompts
3. WHEN testing with STARK_BLACK_WHITE_NOIR style, THE tests SHALL verify no color keywords appear in the final prompt
4. THE System SHALL provide tests that verify character identity_line fields contain no style keywords
5. THE System SHALL provide integration tests that verify end-to-end style preservation from user selection to final prompt
