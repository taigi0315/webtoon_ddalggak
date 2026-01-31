# Implementation Plan: Visual Responsibility Split

## Overview

This implementation plan refactors the webtoon generation system to eliminate style overwriting by establishing clear separation of concerns between layout (cinematography), mood (art direction), and rendering style (image style). The implementation follows a phased approach: first sanitizing existing data and removing hardcoded anchors, then implementing the new Art Director node, and finally refactoring existing nodes to respect the new responsibility boundaries.

## Tasks

- [x] 1. Database Migration for Character Style Sanitization
  - Create Alembic migration script to sanitize existing character data
  - Remove stylistic keywords from `identity_line` and `appearance` fields
  - Preserve morphological information (hair color, height, facial features)
  - Add audit logging for all character updates
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 1.1 Write property test for migration sanitization
  - **Property 8: Migration Style Sanitization**
  - **Validates: Requirements 8.2, 8.3**

- [x] 2. Remove Hardcoded Style Anchors from Prompt Compiler
  - [x] 2.1 Refactor `_compile_prompt()` in `app/graphs/nodes/prompts/compile.py`
    - Remove hardcoded "Korean webtoon/manhwa art style (Naver webtoon quality)" string
    - Remove hardcoded "Vertical 9:16 webtoon/manhwa image" string
    - Replace with dynamic image style reference from `style_id` parameter
    - _Requirements: 2.1, 2.2, 2.5_
  
  - [x] 2.2 Refactor character reference image generation functions
    - Update `generate_character_reference_image()` in `app/graphs/nodes/rendering.py`
    - Update `generate_character_variant_reference_image()` in `app/graphs/nodes/rendering.py`
    - Remove "Korean webtoon" strings from prompts
    - _Requirements: 2.3_
  
  - [x] 2.3 Write property test for hardcoded anchor removal
    - **Property 2: Hardcoded Anchor Removal**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.5**

- [x] 3. Implement Prompt Layering Hierarchy
  - [x] 3.1 Restructure `_compile_prompt()` to implement layering
    - Layer 1: Image Style (highest priority)
    - Layer 2: Art Direction (mood & atmosphere)
    - Layer 3: Format & Composition
    - Layer 4: Reference Image Authority
    - Layer 5: Panel Composition (cinematographer)
    - Layer 6: Characters (morphology only)
    - Layer 7: Panels (scene-specific)
    - Layer 8: Technical Requirements (style-agnostic)
    - Layer 9: Negative Prompt
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [x] 3.2 Add `art_direction` parameter to `_compile_prompt()` signature
    - Update function signature to accept art direction data
    - Integrate art direction into Layer 2 of prompt
    - _Requirements: 6.1_
  
  - [x] 3.3 Write property test for prompt layering order
    - **Property 4: Prompt Layering Order**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Refactor Character Normalization Prompt
  - [x] 5.1 Update `app/prompts/v1/story_build/character_normalization.yaml`
    - Remove "Apply Korean manhwa aesthetic standards" instruction
    - Remove "AGE-BASED VISUAL STANDARDS (Korean Manhwa Style)" section
    - Replace with "AGE-BASED PHYSICAL STANDARDS (Style-Agnostic)"
    - Remove style keywords from identity_line format examples
    - Add explicit constraint: "Focus on objective morphological descriptions only"
    - _Requirements: 1.5_
  
  - [x] 5.2 Add post-processing filter to `normalize_character_profiles_llm()`
    - Implement `_sanitize_character_output()` function
    - Detect and remove style keywords from LLM output
    - Log warnings when keywords are detected
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [x] 5.3 Write property test for character style neutralization
    - **Property 1: Character Style Neutralization**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

- [x] 6. Implement Art Director Node
  - [x] 6.1 Create `app/graphs/nodes/planning/art_direction.py`
    - Implement `run_art_director()` function
    - Accept `scene_id`, `image_style_id`, and `gemini` parameters
    - Return artifact with type `ARTIFACT_ART_DIRECTION`
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 6.2 Create Art Director prompt template
    - Create `app/prompts/v1/scene_planning/art_direction.yaml`
    - Include image style context and constraints
    - Generate lighting, color temperature, atmosphere keywords
    - Ensure compatibility with selected image style
    - _Requirements: 5.2, 5.4_
  
  - [x] 6.3 Add validation for Art Director output
    - Implement `_validate_art_direction()` function
    - Enforce monochrome constraints for noir styles
    - Remove color keywords from atmosphere for monochrome styles
    - Log validation warnings
    - _Requirements: 5.4, 5.5_
  
  - [x] 6.4 Register Art Director node in workflow
    - Add `ARTIFACT_ART_DIRECTION` constant to `app/graphs/nodes/planning/__init__.py`
    - Export `run_art_director` function
    - _Requirements: 5.1_
  
  - [x] 6.5 Write property test for Art Director style compatibility
    - **Property 6: Art Director Style Compatibility**
    - **Validates: Requirements 5.2, 5.4**
  
  - [x] 6.6 Write unit test for monochrome style handling
    - Test STARK_BLACK_WHITE_NOIR produces color_temperature="N/A"
    - Test no color keywords in atmosphere for monochrome styles
    - _Requirements: 5.5_

- [x] 7. Integrate Art Director into LangGraph Workflow
  - [x] 7.1 Update `_node_per_scene_planning_loop()` in `app/graphs/story_build.py`
    - Add Art Director call after scene intent extraction
    - Pass `image_style` from state to Art Director
    - Store art direction artifact ID
    - _Requirements: 5.1_
  
  - [x] 7.2 Update `run_prompt_compiler()` to load art direction
    - Load art direction artifact from database
    - Pass art direction data to `_compile_prompt()`
    - _Requirements: 6.1_
  
  - [x] 7.3 Write integration test for Art Director in workflow
    - Test Art Director node is called in correct order
    - Test art direction artifact is created
    - _Requirements: 5.1_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Refactor Cinematographer to Focus on Layout
  - [x] 9.1 Update Cinematographer prompt in `app/prompts/v1/scene_planning/panel_semantics.yaml`
    - Add explicit constraint: "Focus on LAYOUT and COMPOSITION only"
    - List allowed elements: camera angle, shot type, composition, body positioning
    - List forbidden elements: color palette, lighting quality, atmospheric mood
    - _Requirements: 4.5_
  
  - [x] 9.2 Add post-processing filter to `run_panel_semantic_filler()`
    - Implement filter to detect color/lighting keywords in panel descriptions
    - Log warnings when style keywords are detected
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [x] 9.3 Write property test for Cinematographer layout focus
    - **Property 3: Cinematographer Layout Focus**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 10. Refactor Studio Director for Style Agnosticism
  - [x] 10.1 Update Studio Director prompt (if exists)
    - Remove any color palette or lighting setup instructions
    - Focus on semantic emotional descriptions
    - Ensure output is compatible with any image style
    - _Requirements: 9.3, 9.4_
  
  - [x] 10.2 Add validation for Studio Director output
    - Detect color/lighting keywords in scene intent
    - Log warnings if style-specific keywords found
    - _Requirements: 9.3, 9.4_
  
  - [x] 10.3 Write property test for Studio Director style agnosticism
    - **Property 5: Studio Director Style Agnosticism**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 3.3**

- [x] 11. Deprecate Genre Guidelines
  - [x] 11.1 Remove genre guidelines loading code
    - Remove `load_genre_guidelines_v1()` from `app/config/loaders.py`
    - Remove any references to genre guidelines in codebase
    - _Requirements: 3.2, 3.4_
  
  - [x] 11.2 Delete genre guidelines configuration file
    - Delete `app/config/genre_guidelines_v1.json` if it exists
    - _Requirements: 3.5_
  
  - [x] 11.3 Write unit test verifying genre guidelines not loaded
    - Test that genre guidelines file is not loaded
    - Test that Studio Director doesn't reference genre guidelines
    - _Requirements: 3.1_

- [x] 12. Add Validation and Error Handling
  - [x] 12.1 Implement prompt validation in `_compile_prompt()`
    - Add `_validate_compiled_prompt()` function
    - Check for forbidden hardcoded anchors
    - Verify expected style appears in prompt
    - Raise exception if validation fails
    - _Requirements: 7.3, 7.5_
  
  - [x] 12.2 Add error handling for character normalization
    - Implement retry logic if style keywords detected
    - Fallback to basic morphological template if retries fail
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [x] 12.3 Add error handling for Art Director
    - Validate output against image style constraints
    - Correct monochrome violations automatically
    - Log all corrections
    - _Requirements: 5.4, 5.5_

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Write Comprehensive Test Suite
  - [x] 14.1 Write property test for image style authority
    - **Property 7: Image Style Authority**
    - **Validates: Requirements 7.3, 7.5**
  
  - [x] 14.2 Write property test for genre guidelines deprecation
    - **Property 9: Genre Guidelines Deprecation**
    - **Validates: Requirements 3.1, 3.3**
  
  - [x] 14.3 Write integration test for end-to-end style preservation
    - Test STARK_BLACK_WHITE_NOIR style through full pipeline
    - Verify no color keywords in final prompt
    - Verify no hardcoded style anchors
    - _Requirements: 7.1, 7.2, 7.3, 7.5_
  
  - [x] 14.4 Write unit test for SOFT_ROMANTIC_WEBTOON style
    - Test that pastel colors and soft lighting appear in prompt
    - Test that style characteristics are preserved
    - _Requirements: 7.2_

- [x] 15. Update Documentation
  - [x] 15.1 Update `docs/02-langgraph-architecture.md`
    - Document new Art Director node
    - Update workflow diagram with Art Director
    - Document prompt layering hierarchy
    - _Requirements: All_
  
  - [x] 15.2 Update `docs/03-prompt-system.md`
    - Document style-neutral character normalization
    - Document prompt layering approach
    - Document Art Director prompt template
    - _Requirements: 1.1-1.5, 5.1-5.5, 6.1-6.5_
  
  - [x] 15.3 Update `docs/AGENTS.md`
    - Add Art Director agent patterns
    - Document style compatibility validation
    - _Requirements: 5.1-5.5_
  
  - [x] 15.4 Update `SKILLS.md`
    - Add new file locations (art_direction.py, updated prompts)
    - Document style neutralization patterns
    - _Requirements: All_

- [x] 16. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- Documentation updates ensure the system remains maintainable
