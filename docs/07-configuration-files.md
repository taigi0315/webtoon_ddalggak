# Configuration Files

## Overview

The system uses JSON configuration files to define panel shot types, layout templates, quality control rules, genre-specific visual guidelines, and style presets. These files enable behavior modification without code changes and support hot-reload for rapid iteration.

## Configuration Files Overview

The system uses the following configuration files:

- **`panel_grammar_library_v1.json`** - Valid shot types (grammar IDs) for panel planning
- **`layout_templates_9x16_v1.json`** - Panel geometry templates for 9:16 vertical format
- **`layout_selection_rules_v1.json`** - Decision rules for template matching
- **`qc_rules_v1.json`** - Quality control thresholds and validation rules
- **`image_styles.json`** - Image-level style presets (visual rendering styles)
- **`grammar_to_prompt_mapping_v1.json`** - Maps grammar IDs to prompt templates
- **`continuity_rules_v1.json`** - Character and environment continuity rules

## Panel Grammar Library

**File**: `app/config/panel_grammar_library_v1.json`

Defines valid shot types (grammar IDs) used in panel planning. Each grammar represents a specific visual storytelling pattern.

**Valid Grammar IDs:**

- `establishing` - Establish the setting and context
- `dialogue_medium` - Two characters speaking in a medium shot
- `emotion_closeup` - Close-up on a character's emotion
- `action` - Dynamic action moment
- `reaction` - Reaction shot to prior event
- `object_focus` - Focus on an important object
- `reveal` - Dramatic reveal of character, object, or information
- `impact_silence` - Dramatic pause with minimal elements, strong composition

**Usage**: Panel plans must use valid grammar IDs. The system validates grammar IDs during panel plan creation and normalization.

## Layout Templates

**File**: `app/config/layout_templates_9x16_v1.json`

Defines panel geometry templates for 9:16 vertical webtoon format. Each template specifies panel positions using normalized coordinates (0.0 to 1.0).

**Template Structure:**

```json
{
  "template_id": "9x16_3_vertical",
  "layout_text": "Three stacked vertical panels",
  "panels": [
    {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.33},
    {"x": 0.0, "y": 0.33, "w": 1.0, "h": 0.34},
    {"x": 0.0, "y": 0.67, "w": 1.0, "h": 0.33}
  ]
}
```

**Available Templates:**

- `9x16_1` - Single full-height panel
- `9x16_2_70_30` - Two panels with 70/30 vertical split (dialogue emphasis)
- `9x16_2_asym` - One dominant panel with smaller inset panel
- `9x16_3_vertical` - Three stacked vertical panels
- `9x16_4_asym` - Dominant panel with two stacked right panels and wide bottom panel
- `9x16_5_asym` - Dominant panel with clustered smaller panels
- `9x16_stacked_weighted_3` - One large panel and two smaller panels stacked beneath

**Coordinate System**: All coordinates are normalized (0.0 to 1.0) where:
- `x`, `y` - Top-left corner position
- `w`, `h` - Width and height
- Origin (0, 0) is top-left corner

## Layout Selection Rules

**File**: `app/config/layout_selection_rules_v1.json`

Defines decision rules for selecting layout templates based on panel count and scene features.

**Rule Structure:**

```json
{
  "panel_count": 3,
  "scene_importance": ["cliffhanger"],
  "pace": ["dialogue"],
  "min_large_panels": 1,
  "min_max_weight": 0.75,
  "template_id": "9x16_stacked_weighted_3"
}
```

**Selection Logic:**

1. Match `panel_count` first (required)
2. Check optional filters: `scene_importance`, `pace`
3. Check weight-based filters: `min_large_panels`, `min_max_weight`
4. Return first matching template
5. Fall back to `default_template_id` if no match

**Usage**: The `select_template()` function in `app/config/loaders.py` applies these rules during layout assignment.

## QC Rules

**File**: `app/config/qc_rules_v1.json`

Defines quality control thresholds and validation rules for panel plans.

**Key Thresholds:**

- `closeup_ratio_max: 0.5` - Maximum ratio of closeup shots (prevents visual monotony)
- `dialogue_ratio_max: 0.6` - Maximum ratio of dialogue shots (ensures visual variety)
- `repeated_framing_run_length: 3` - Maximum consecutive panels with same grammar
- `require_environment_on_establishing: true` - Establishing shots must include environment description

**Environment Keywords**: List of valid environment types (room, street, cafe, school, office, park, etc.)

**Usage**: QC validation runs after panel plan creation. Failures generate warnings but don't block workflow.

## Style Presets

### Image Styles

**File**: `app/config/image_styles.json`

Defines image-level style presets that affect visual rendering style.

**Available Styles:**

- `default` / `NO_STYLE` - Neutral baseline rendering
- `soft_webtoon` / `SOFT_ROMANTIC_WEBTOON` - Soft pastel shading, gentle lineart, warm romantic mood
- `VIBRANT_FANTASY_WEBTOON` - Magical glow, clean lineart, airy fantasy palette
- `DRAMATIC_HISTORICAL_WEBTOON` - Cinematic candlelight, rich shadows, historical depth
- `BRIGHT_YOUTHFUL_WEBTOON` - Clean friendly lineart, cheerful daylight palette
- `DREAMY_ISEKAI_WEBTOON` - Ethereal glow, jewel accents, fantasy romance polish

**Usage**: Image styles are applied during render spec generation and influence image generation prompts.

## Configuration Loading

**File**: `app/config/loaders.py`

Configuration files are loaded using Pydantic models with validation and caching.

**Loading Functions:**

- `load_grammar_library_v1()` - Load panel grammar library
- `load_layout_templates_9x16_v1()` - Load layout templates
- `load_layout_selection_rules_v1()` - Load layout selection rules
- `load_qc_rules_v1()` - Load QC rules
- `load_image_styles_v1()` - Load image styles

**Caching**: All loaders use `@lru_cache(maxsize=1)` for performance. Call `clear_config_cache()` to force reload.

**Helper Functions:**

- `get_grammar(grammar_id)` - Get specific grammar by ID
- `get_layout_template(template_id)` - Get specific template by ID
- `select_template(panel_plan, derived_features, excluded_template_ids)` - Select template using decision rules

## Hot-Reload Support

**File**: `app/services/config_watcher.py`

The config watcher service monitors configuration files for changes and automatically reloads them.

**How It Works:**

1. Polls config directory every 2 seconds (configurable)
2. Detects file modification time changes
3. Clears config cache and reloads all configs
4. Runs registered callbacks for additional reload logic
5. Logs reload events for debugging

**Usage:**

```python
# File: app/main.py

from app.services.config_watcher import start_watcher, stop_watcher

# Start watching during app startup
start_watcher()

# Stop watching during app shutdown
stop_watcher()
```

**Benefits**: Enables rapid iteration on config files without restarting the application.

## Key Files

- `app/config/*.json` - All configuration files
- `app/config/loaders.py` - Configuration loading and caching
- `app/services/config_watcher.py` - Hot-reload service
- `app/services/layout_selection.py` - Layout template selection logic
- `app/graphs/nodes/planning/qc.py` - QC validation implementation

## Debugging Direction

**When things go wrong, check:**

- **Invalid grammar ID errors**:
  - Verify grammar ID exists in `panel_grammar_library_v1.json`
  - Check panel plan artifact for malformed grammar IDs
  - Review LLM output for grammar ID generation

- **Layout selection issues**:
  - Check `layout_selection_rules_v1.json` for matching rules
  - Verify panel count matches available templates
  - Review derived features (scene_importance, pace) in panel plan
  - Check excluded_template_ids in guardrail logic

- **QC validation failures**:
  - Review `qc_rules_v1.json` thresholds
  - Check `qc_report` artifact for specific violations
  - Verify panel plan grammar distribution
  - Check environment descriptions in establishing shots

- **Config changes not taking effect**:
  - Check if config watcher is running (`is_watching()`)
  - Verify file modification time changed
  - Review logs for reload events
  - Manually call `clear_config_cache()` if needed

**Useful commands:**

```bash
# Validate JSON syntax
python -m json.tool app/config/panel_grammar_library_v1.json

# Check config loading
python -c "from app.config.loaders import load_grammar_library_v1; print(load_grammar_library_v1())"

# Force config reload in Python shell
from app.config.loaders import clear_config_cache
clear_config_cache()
```

## See Also

- [Prompt System](03-prompt-system.md) - How configs influence prompt generation
- [LangGraph Architecture](02-langgraph-architecture.md) - Where configs are used in workflows
- [Database Models](04-database-models.md) - StylePreset model for style management
- [SKILLS.md](../SKILLS.md) - Quick reference guide
