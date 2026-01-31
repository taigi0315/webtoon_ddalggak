# Prompt System

## Overview

The system uses Jinja2-templated prompts stored in `app/prompts/prompts.yaml` to guide LLM behavior throughout the pipeline. Prompts are loaded via `app/prompts/loader.py` and compiled with runtime context (characters, scenes, styles) before being sent to the Gemini API. The system includes automatic JSON repair for malformed LLM outputs.

## Prompt Loading Mechanism

**Storage**: All prompt templates are stored in `app/prompts/prompts.yaml` as YAML key-value pairs

**Loading**: `app/prompts/loader.py` provides:

- `get_prompt(name)` - Get raw template string
- `render_prompt(name, **context)` - Compile template with Jinja2 variables
- `get_prompt_data(name)` - Get non-string data (e.g., character_style_map)

**Compilation**: Prompts use Jinja2 syntax for variable substitution:

- `{{ variable }}` - Insert variable value
- `{% if condition %}...{% endif %}` - Conditional blocks
- Auto-includes shared prompts (`system_prompt_json`, `global_constraints`)

**Caching**: Prompts are cached with `@lru_cache` for performance

## Key Prompt Templates

### System and Constraints

- **system_prompt_json** - JSON generation rules (strict format, no markdown, no commentary)
- **global_constraints** - Universal rules (don't invent characters, keep outputs concise, respect limits)

### Story Build Domain

- **prompt_character_extraction** - Extract important characters from story text with evidence quotes
- **prompt_character_normalization** - Add visual details (hair, face, build, outfit) using Korean manhwa aesthetics
- **prompt_script_writer** - Translate raw story into a visual webtoon script with beats, dialogue, and SFX
- **prompt_visual_plan** - Convert scenes into visual beats with importance ratings

### Scene Planning Domain

- **prompt_scene_intent** - Extract narrative intent (mood, pacing, emotional arc, visual motifs)
- **prompt_panel_plan** - Generate panel breakdown with shot types (grammar IDs) and story functions
- **prompt_panel_semantics** - Fill detailed 100-150 word visual descriptions for each panel

### Evaluation Domain

- **prompt_blind_test** - Evaluate narrative coherence by reconstructing story from panel descriptions only

### Dialogue Domain

- **prompt_dialogue_script** - Convert scene into panel-aligned dialogue (0-3 lines per panel)
- **prompt_variant_suggestions** - Suggest character outfit/appearance changes based on story context

### Utility Domain

- **prompt_repair_json** - Fix malformed JSON output from LLM (removes markdown, fixes trailing commas)

## Character Style Map

**Purpose**: Age and gender-based styling templates for Korean manhwa aesthetic standards

**Structure**: Nested dictionary with `gender` → `age_range` → `style_template`

**Age Ranges**:

- `child` / `kid` - Chibi proportions (1:3), round cherubic face, large expressive eyes
- `teen` - Slender graceful build, flower-boy aesthetic (male), large doe eyes (female)
- `young_adult` / `adult` - Korean male lead aesthetic (180-188cm, willowy proportions), statuesque figure (female, 165cm+)
- `middle_aged` - Distinguished refined features, professional attire
- `elderly` - Gentle wisdom lines, silver/white hair, dignified presence

**Usage**: Applied during character normalization to ensure consistent visual style

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
{shot_type}, vertical 9:16 webtoon panel, {composition_note},
{environment_with_5+_specific_details} + {style_lighting_description},
{character_placement} + {action_and_expression},
{atmosphere_keywords},
{genre} manhwa style, {rendering_notes}
```

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
- `app/graphs/nodes/json_parser.py` - JSON repair mechanism
- `app/graphs/nodes/constants.py` - Shared prompt constants (SYSTEM_PROMPT_JSON, GLOBAL_CONSTRAINTS)
- `app/core/character_styles.py` - Character style examples (reference only)

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
