# Prompt System

## Overview

The system uses Jinja2-templated prompts stored in `app/prompts/prompts.yaml` to guide LLM behavior throughout the pipeline. Prompts are loaded via `app/prompts/loader.py` and compiled with runtime context (characters, scenes, styles) before being sent to the Gemini API. The system includes automatic JSON repair for malformed LLM outputs.

## Prompt Loading Mechanism

**Storage**: Prompts are stored in a versioned directory structure under `app/prompts/v1/`, organized by domain:

- `shared/`: System prompts, constraints, and style maps.
- `story_build/`: Script writing and character normalization.
- `scene_planning/`: Scene intent and panel-level planning.
- `evaluation/`: Blind test and criticism prompts.
- `dialogue/`: Dialogue generation and variant suggestions.
- `utility/`: JSON repair.

**Loading**: `app/prompts/loader.py` manages loading and Jinja2 compilation, with versioned prompts taking precedence over the legacy `prompts.yaml`.

**Key Features**:

- **Automatic JSON Repair**: Integrated logic to fix malformed LLM outputs.
- **Syntax Validation**: Built-in Jinja2 parsing checks to catch errors at load time.
- **Context Management**: Auto-inclusion of global constraints and system rules.

## Key Prompt Templates

### Episode Planning & Optimization (Story Build)

- **prompt_character_normalization**: Adds visual details and narrative descriptions to extracted characters using style-agnostic morphological standards (no hardcoded style keywords).
- **prompt_script_writer**: Translates raw story text into a visual multi-beat script.
- **prompt_tone_auditor**: Detects mood shifts (Action, Gag, Emotional) and assigns importance weights to narrative beats.
- **prompt_scene_optimizer**: Merges low-weight beats into high-weight scenes to stay within budget (`max_scenes`) while assigning appropriate image styles.

### Scene Planning & Semantics

- **prompt_scene_intent**: Extracts narrative intent, visual motifs, and required transitions.
- **prompt_panel_plan**: Generates a panel-by-panel breakdown using standard webtoon shot types (grammar IDs).
- **prompt_panel_semantics**: Fills exhaustive visual descriptions (100-150 words) for each panel to ensure AI generation consistency.

### Validation & Criticism

- **prompt_blind_test**: Reconstructs the story from panel descriptions to verify visual storytelling coherence.
- **prompt_blind_test_critic**: Analyzes blind test reports for narrative gaps or logical inconsistencies and triggers necessary rewrites.

### Dialogue Domain

- **prompt_dialogue_script** - Convert scene into panel-aligned dialogue (0-3 lines per panel)
- **prompt_variant_suggestions** - Suggest character outfit/appearance changes based on story context

### Utility Domain

- **prompt_repair_json** - Fix malformed JSON output from LLM (removes markdown, fixes trailing commas)

## Character Style Map

**Purpose**: Age and gender-based styling templates for style-agnostic morphological standards

**Structure**: Nested dictionary with `gender` → `age_range` → `style_template`

**Age Ranges**:

- `child` / `kid` - Chibi proportions (1:3), round cherubic face, large expressive eyes
- `teen` - Slender graceful build, large doe eyes
- `young_adult` / `adult` - Tall proportions (180-188cm male, 165cm+ female), slender build
- `middle_aged` - Distinguished refined features, professional attire
- `elderly` - Gentle wisdom lines, silver/white hair, dignified presence

**Important Note**: As of migration `83f5330535c1_sanitize_character_style_keywords`, all style-specific keywords (manhwa, webtoon, aesthetic, flower-boy, K-drama, etc.) have been removed from character descriptions to ensure style neutrality. Character normalization now focuses on objective morphological descriptions only.

**Usage**: Applied during character normalization to ensure consistent visual descriptions without imposing specific art styles

**Location**: `app/prompts/prompts.yaml` under `character_style_map` key

## Visual Prompt Formula

**Purpose**: 150-250 word structure for AI image generation prompts

**Required Elements**:

1. **Shot type** - establishing, medium, closeup, action, etc.
2. **Environment details** - 5+ specific details (architecture, props, lighting, weather)
3. **Character placement** - Position in frame with percentage (e.g., "occupies 40% of frame")
4. **Lighting conditions** - Source, quality, color temperature, shadows
5. **Atmosphere keywords** - Mood descriptors
6. **Style notes** - Korean manhwa style, rendering notes

**Format Template**:

```
{shot_type}, vertical 9:16 format for vertical scrolling, {composition_note},
{environment_with_5+_specific_details} + {style_lighting_description},
{character_placement} + {action_and_expression},
{atmosphere_keywords},
{rendering_notes}
```

**Important Note**: As of Task 2 (Hardcoded Anchor Removal), all hardcoded style anchors like "Korean webtoon/manhwa art style" and "Naver webtoon quality" have been removed from prompt compilation. Image style is now dynamically referenced from the user-selected `image_style_id` parameter.

**Grammar-Specific Requirements**:

- `establishing` - Wide shot, characters 20-30% of frame, show the WORLD
- `dialogue_medium` - Medium shot, characters 40-45%, space for speech bubbles
- `emotion_closeup` - Extreme close-up, character 50%+, specific emotion with physical tells
- `action` - Dynamic angle, motion blur hint, 35-40% character
- `reaction` - Focus on reacting character, clear emotion in eyes/expression
- `object_focus` - Macro/close-up, object centered, minimal background
- `reveal` - High contrast, dramatic lighting, subject entering or unveiled
- `impact_silence` - Minimal elements, 70%+ negative space, frozen moment

## Prompt Compilation with Runtime Context

**Compilation Process**:

1. Load template from `prompts.yaml`
2. Gather runtime context (scene text, character list, genre, etc.)
3. Render template with Jinja2 using context variables
4. Send compiled prompt to Gemini API

**Prompt Layering Hierarchy** (as of Task 3 - Visual Responsibility Split):

The `_compile_prompt()` function now uses a 9-layer hierarchy to ensure proper separation of concerns:

1. **Image Style** (highest priority) - User-selected style from `image_style_id`
2. **Art Direction** (optional) - Mood & atmosphere from Art Director node
3. **Format & Composition** - Technical format requirements (9:16 vertical)
4. **Reference Image Authority** - Character consistency rules
5. **Panel Composition** - Cinematographer's layout rules
6. **Characters** - Morphology-only descriptions (style-neutral)
7. **Panels** - Scene-specific visual descriptions
8. **Technical Requirements** - Style-agnostic quality standards
9. **Negative Prompt** (lowest priority) - What to avoid

This layering ensures that user-selected image styles are never overridden by hardcoded anchors or conflicting instructions.

**Common Context Variables**:

- `scene_text` - Raw scene text input
- `char_list` - Comma-separated character names
- `genre_text` - Genre for style guidance
- `panel_count` - Number of panels to generate
- `intent_block` - Formatted scene intent from prior node
- `plan_section` - Formatted panel plan from prior node
- `char_section` - Character identity lines for consistency

**Example Compilation**:

```python
# File: app/graphs/nodes/prompts/builders.py

prompt = render_prompt(
    "prompt_scene_intent",
    scene_text=scene.source_text,
    char_list="Alice, Bob, Charlie",
    genre_text="romance"
)
```

## JSON Repair Mechanism

**Purpose**: Fix malformed JSON output from LLM responses

**Common Issues Fixed**:

- Markdown code fences (` ```json ... ``` `)
- Trailing commas before closing brackets
- Commentary before/after JSON
- Missing brackets

**Repair Process**:

1. Strip markdown fences with regex
2. Find outermost JSON object using bracket matching
3. Remove trailing commas
4. Attempt to parse with `json.loads()`
5. If still fails, send to LLM with `prompt_repair_json` (max 2 attempts)

**Implementation**: `app/graphs/nodes/json_parser.py`

**Functions**:

- `_strip_markdown_fences()` - Remove markdown code blocks
- `_clean_json_text()` - Fix common formatting issues
- `_extract_json_object()` - Extract JSON using bracket matching
- `parse_json_with_repair()` - Main repair function with LLM fallback

## Key Files

- `app/prompts/prompts.yaml` - All prompt templates and character style map
- `app/prompts/loader.py` - Prompt loading and Jinja2 compilation
- `app/graphs/nodes/prompts/builders.py` - Prompt compilation functions for each node
- `app/graphs/nodes/prompts/compile.py` - Main prompt compiler with 9-layer hierarchy and style-neutral formatting
- `app/graphs/nodes/json_parser.py` - JSON repair mechanism
- `app/graphs/nodes/constants.py` - Shared prompt constants (SYSTEM_PROMPT_JSON, GLOBAL_CONSTRAINTS)
- `app/core/character_styles.py` - Character style examples (reference only)
- `app/core/image_styles.py` - Image style profiles with prompts and metadata
- `app/db/migrations/versions/83f5330535c1_sanitize_character_style_keywords.py` - Character style sanitization migration
- `tests/test_hardcoded_anchor_removal.py` - Property tests for hardcoded anchor removal
- `tests/test_prompt_layering.py` - Property tests for prompt layering hierarchy

## Debugging Direction

**When prompts produce unexpected results, check:**

- **Prompt compilation**:
  - Review artifact payloads to see compiled prompts sent to LLM
  - Check `render_spec` artifact for final image generation prompts
  - Verify all required context variables are provided

- **LLM responses**:
  - Check logs for raw LLM output before JSON parsing
  - Review `generation_error` field in Story/Scene for error messages
  - Inspect artifact.payload for node outputs

- **JSON repair failures**:
  - Check logs for `json_parse_failure` metrics
  - Review malformed JSON text in logs
  - Verify `prompt_repair_json` is working correctly

- **Character style issues**:
  - Check `Character.identity_line` field for compiled character descriptions
  - Review `character_style_map` in prompts.yaml for age/gender templates
  - Verify `age_range` and `gender` are set correctly during normalization

- **Visual prompt issues**:
  - Check `panel_semantics` artifact for compiled visual descriptions
  - Verify grammar_id matches expected shot type
  - Ensure environment details include 5+ specific elements
  - Check character_frame_percentage matches grammar requirements

**Useful queries**:

```sql
-- Check character identity lines
SELECT name, gender, age_range, identity_line
FROM characters WHERE project_id = ?;

-- Review panel semantics
SELECT payload
FROM artifacts
WHERE scene_id = ? AND type = 'panel_semantics'
ORDER BY version DESC LIMIT 1;

-- Check render spec prompts
SELECT payload
FROM artifacts
WHERE scene_id = ? AND type = 'render_spec'
ORDER BY version DESC LIMIT 1;
```

**Key log patterns to search**:

- `prompt.compilation` - Prompt rendering traces
- `json_parse_failure` - JSON repair attempts
- `gemini.request` - Raw prompts sent to API
- `gemini.response` - Raw LLM outputs

## See Also

- [LangGraph Architecture](02-langgraph-architecture.md) - How prompts are used in graph nodes
- [Character System](05-character-system.md) - Character extraction and normalization
- [Database Models](04-database-models.md) - Artifact storage for compiled prompts
- [Error Handling & Observability](09-error-handling-observability.md) - Debugging LLM failures
- [SKILLS.md](../SKILLS.md) - Quick reference guide
