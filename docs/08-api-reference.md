# API Reference

## Overview

The system exposes a RESTful API for managing webtoon generation workflows. All endpoints are versioned under `/v1/` and organized by resource type. The API supports both synchronous and asynchronous processing for long-running operations, with job queue management for background tasks.

## API Structure

**Base Path**: `/v1/`

**Authentication**: Not currently implemented (future enhancement)

**Content Type**: `application/json`

**Response Format**: JSON with Pydantic schema validation

## Key Endpoint Groups

The API is organized into the following resource categories:

- **Projects** - Project management (top-level container)
- **Stories** - Story creation and blueprint generation
- **Scenes** - Scene management and CRUD operations
- **Generation** - Scene planning and rendering workflows
- **Characters** - Character profiles and management
- **Character Variants** - Character appearance variations
- **Casting** - Actor library and character casting
- **Artifacts** - Intermediate output retrieval
- **Style Presets** - Style configuration management
- **Styles** - Style listing and discovery
- **Episodes** - Multi-scene episode composition
- **Episode Planning** - Episode-level planning workflows
- **Exports** - Export jobs for final output
- **Dialogue** - Dialogue layer management
- **Environments** - Environment anchor management
- **Layers** - Generic layer management (dialogue, narration, SFX)
- **Review** - Review and approval workflows
- **Jobs** - Background job status and management
- **Gemini** - Direct Gemini API testing
- **Config** - Configuration management
- **Internal Generation** - Internal-only generation endpoints

## Generation Workflow Endpoints

### Story Blueprint Generation

**Endpoint**: `POST /v1/stories/{story_id}/generate/blueprint`

**Purpose**: Generate story blueprint (scenes and characters) from story text

**Processing**: Synchronous (blocks until complete)

**Workflow**:
1. Split story text into scenes
2. Extract character profiles
3. Normalize character visual details
4. Persist scenes and characters to database
5. Assign canonical codes (CHAR_A, CHAR_B, etc.)

**Key Parameters**:
- `source_text` - Raw story text input
- `max_scenes` - Maximum scenes to create (1-30)
- `max_characters` - Maximum characters to extract (1-20)
- `panel_count` - Panels per scene (1-12)
- `allow_append` - Allow adding scenes to existing story
- `require_hero_single` - Enforce at least one single-panel scene

**Response**: List of created scenes and characters

**Async Alternative**: `POST /v1/stories/{story_id}/generate/blueprint_async` (returns job ID)

### Scene Planning

**Endpoint**: `POST /v1/scenes/{scene_id}/plan`

**Purpose**: Generate panel plan and visual descriptions for a scene

**Processing**: Synchronous (blocks until complete)

**Workflow**:
1. Extract scene intent (mood, pacing, key moments)
2. Generate panel plan with shot types (grammar IDs)
3. Normalize and validate panel plan
4. Resolve layout template based on panel count
5. Fill detailed visual descriptions for each panel

**Key Parameters**:
- `panel_count` - Number of panels to generate (1-12)

**Response**: Artifact IDs for scene_intent, panel_plan, panel_plan_normalized, layout_template, panel_semantics

**Planning Lock**: If `Scene.planning_locked = true`, returns existing artifacts instead of regenerating

### Scene Rendering

**Endpoint**: `POST /v1/scenes/{scene_id}/render`

**Purpose**: Generate final images from panel descriptions

**Processing**: Synchronous (blocks until complete)

**Workflow**:
1. Load panel semantics and layout template artifacts
2. Compile render spec with style resolution
3. Generate images via Vertex AI Gemini API
4. Run quality control validation

**Key Parameters**:
- `style_id` - Optional image style preset ID (resolved if not provided)
- `prompt_override` - Optional custom prompt text
- `enforce_qc` - Whether to raise error on QC failure

**Response**: Artifact IDs for panel_semantics, layout_template, render_spec, render_result, qc_report

**Style Resolution Hierarchy**: Scene override → Story default → "default"

### Full Pipeline

**Endpoint**: `POST /v1/scenes/{scene_id}/generate/full`

**Purpose**: Run complete planning + rendering pipeline for a scene

**Processing**: Synchronous (blocks until complete)

**Workflow**: Combines scene planning and scene rendering workflows

**Key Parameters**:
- `panel_count` - Number of panels to generate (1-12)
- `style_id` - Image style preset ID (required)
- `prompt_override` - Optional custom prompt text

**Response**: Artifact IDs for all planning and rendering artifacts, plus blind_test_report

**Async Alternative**: `POST /v1/scenes/{scene_id}/generate/full_async` (returns job ID)

### Scene Status

**Endpoint**: `GET /v1/scenes/{scene_id}/status`

**Purpose**: Check scene workflow completion status

**Response**:
- `planning_locked` - Whether planning is locked
- `planning_complete` - Whether all planning artifacts exist
- `render_complete` - Whether all render artifacts exist
- `latest_artifacts` - Map of artifact types to latest artifact IDs

### Story Progress

**Endpoint**: `GET /v1/stories/{story_id}/progress`

**Purpose**: Check story blueprint generation progress

**Response**:
- `status` - Generation status (queued, running, succeeded, failed)
- `progress` - Progress tracking (current_node, message, step, total_steps)
- `error` - Error message if failed
- `updated_at` - Last progress update timestamp

## Artifact Retrieval Endpoints

### Get Artifact

**Endpoint**: `GET /v1/artifacts/{artifact_id}`

**Purpose**: Retrieve specific artifact by ID

**Response**: Artifact metadata and payload JSON

### Get Latest Artifact

**Endpoint**: `GET /v1/scenes/{scene_id}/artifacts/{artifact_type}/latest`

**Purpose**: Retrieve latest version of artifact type for a scene

**Response**: Artifact metadata and payload JSON

### List Artifacts

**Endpoint**: `GET /v1/scenes/{scene_id}/artifacts`

**Purpose**: List all artifacts for a scene

**Query Parameters**:
- `artifact_type` - Optional filter by artifact type
- `limit` - Maximum number of artifacts to return

**Response**: List of artifact metadata (without payloads)

## Character and Casting Endpoints

### List Characters

**Endpoint**: `GET /v1/projects/{project_id}/characters`

**Purpose**: List all characters in a project

**Response**: List of character profiles with visual details

### Get Character

**Endpoint**: `GET /v1/characters/{character_id}`

**Purpose**: Retrieve specific character by ID

**Response**: Character profile with visual details

### List Character Variants

**Endpoint**: `GET /v1/characters/{character_id}/variants`

**Purpose**: List all appearance variants for a character

**Response**: List of character variants (outfit_change, mood_change, etc.)

### Create Character Variant

**Endpoint**: `POST /v1/characters/{character_id}/variants`

**Purpose**: Create new appearance variant for a character

**Key Parameters**:
- `variant_name` - Human-readable name (e.g., "Summer Look")
- `variant_type` - Type (base, outfit_change, mood_change, style_change)
- `traits` - JSON with face, hair, mood, outfit overrides
- `story_id` - Optional story scope (NULL for global)

**Response**: Created character variant

### Activate Character Variant

**Endpoint**: `POST /v1/character-variants/{variant_id}/activate`

**Purpose**: Set variant as active for a story (deactivates others)

**Response**: Updated character variant

### Generate Profile Sheet

**Endpoint**: `POST /v1/characters/{character_id}/generate-profile-sheet`

**Purpose**: Generate 9:16 profile sheet with full-body view and expression insets

**Response**: Generated image URL and reference image record

### Cast Actor

**Endpoint**: `POST /v1/casting/cast-actor`

**Purpose**: Cast global actor into a project or story

**Key Parameters**:
- `actor_id` - Global character ID (project_id = NULL)
- `target_project_id` - Project to cast into
- `target_story_id` - Optional story to link

**Response**: Created character link

## Style Preset Endpoints

### List Styles

**Endpoint**: `GET /v1/styles`

**Purpose**: List all available style presets

**Query Parameters**:
- `style_type` - Filter by type (story, image)

**Response**: List of style presets with descriptions

### Get Style

**Endpoint**: `GET /v1/styles/{style_id}`

**Purpose**: Retrieve specific style preset by ID

**Response**: Style preset with full configuration

### Create Style Preset

**Endpoint**: `POST /v1/style-presets`

**Purpose**: Create custom style preset

**Key Parameters**:
- `name` - Style name
- `style_type` - Type (story, image)
- `config` - Style configuration JSON
- `parent_id` - Optional parent style for inheritance

**Response**: Created style preset

## Episode and Export Endpoints

### Create Episode

**Endpoint**: `POST /v1/projects/{project_id}/episodes`

**Purpose**: Create multi-scene episode composition

**Key Parameters**:
- `title` - Episode title
- `scene_ids` - List of scene UUIDs to include

**Response**: Created episode

### Add Scene to Episode

**Endpoint**: `POST /v1/episodes/{episode_id}/scenes`

**Purpose**: Add scene to episode composition

**Key Parameters**:
- `scene_id` - Scene UUID to add
- `sequence_order` - Position in episode (0-indexed)

**Response**: Created episode-scene link

### Export Episode

**Endpoint**: `POST /v1/episodes/{episode_id}/export`

**Purpose**: Export episode as final output (video, PDF, etc.)

**Key Parameters**:
- `export_format` - Format (video, pdf, images)
- `export_options` - Format-specific options

**Response**: Export job ID

### Get Export Job Status

**Endpoint**: `GET /v1/exports/{job_id}`

**Purpose**: Check export job status

**Response**: Job status, progress, and download URL when complete

## Job Management Endpoints

### Get Job Status

**Endpoint**: `GET /v1/jobs/{job_id}`

**Purpose**: Check background job status

**Response**:
- `job_id` - Job UUID
- `job_type` - Job type (story_blueprint, scene_full, etc.)
- `status` - Status (queued, running, succeeded, failed)
- `progress` - Progress tracking
- `result` - Result payload when succeeded
- `error` - Error message when failed
- `created_at`, `updated_at` - Timestamps

### List Jobs

**Endpoint**: `GET /v1/jobs`

**Purpose**: List all background jobs

**Query Parameters**:
- `job_type` - Optional filter by job type
- `status` - Optional filter by status
- `limit` - Maximum number of jobs to return

**Response**: List of job records

## Key Files

### API Router Configuration
- `app/api/v1/router.py` - Main API router with all endpoint groups
- `app/main.py` - FastAPI application setup

### Endpoint Modules
- `app/api/v1/projects.py` - Project endpoints
- `app/api/v1/stories.py` - Story endpoints
- `app/api/v1/scenes.py` - Scene endpoints
- `app/api/v1/generation.py` - Generation workflow endpoints
- `app/api/v1/characters.py` - Character endpoints
- `app/api/v1/character_variants.py` - Character variant endpoints
- `app/api/v1/casting.py` - Casting endpoints
- `app/api/v1/artifacts.py` - Artifact retrieval endpoints
- `app/api/v1/style_presets.py` - Style preset endpoints
- `app/api/v1/styles.py` - Style listing endpoints
- `app/api/v1/episodes.py` - Episode endpoints
- `app/api/v1/episode_planning.py` - Episode planning endpoints
- `app/api/v1/exports.py` - Export endpoints
- `app/api/v1/dialogue.py` - Dialogue layer endpoints
- `app/api/v1/environments.py` - Environment anchor endpoints
- `app/api/v1/layers.py` - Generic layer endpoints
- `app/api/v1/review.py` - Review workflow endpoints
- `app/api/v1/jobs.py` - Job management endpoints
- `app/api/v1/gemini.py` - Gemini API testing endpoints
- `app/api/v1/config.py` - Configuration endpoints
- `app/api/v1/internal_generation.py` - Internal generation endpoints

### Schema Definitions
- `app/api/v1/schemas.py` - Request/response Pydantic models

### Dependencies
- `app/api/deps.py` - Dependency injection (database session, etc.)

## Debugging Direction

**When API requests fail or produce unexpected results, check:**

### Request Validation Errors

- **400 Bad Request**: Check request body against Pydantic schema in `app/api/v1/schemas.py`
- **Invalid style_id**: Verify style exists in `app/config/image_styles.json`
- **Panel count out of range**: Ensure panel_count is 1-12
- **Max scenes/characters exceeded**: Check limits (max_scenes: 1-30, max_characters: 1-20)

### Resource Not Found Errors

- **404 Not Found**: Verify resource UUID exists in database
- **Scene not found**: Query `scenes` table for scene_id
- **Story not found**: Query `stories` table for story_id
- **Artifact not found**: Query `artifacts` table for artifact_id

### Generation Workflow Errors

- **Planning locked**: Check `Scene.planning_locked` field - if true, planning cannot be regenerated
- **Missing artifacts**: Verify required artifacts exist for locked scenes
- **Style resolution failure**: Check `Scene.image_style_override` and `Story.default_image_style`
- **Gemini API errors**: Review logs for rate limits, content filtering, or quota issues
- **QC validation failure**: Check `qc_report` artifact for specific violations

### Async Job Errors

- **Job stuck in queued**: Check job queue worker is running
- **Job failed**: Query `jobs` table for error message
- **Story generation failed**: Check `Story.generation_error` and `Story.progress` fields
- **Progress not updating**: Verify `Story.progress_updated_at` timestamp is recent

### Character and Casting Errors

- **Duplicate canonical codes**: Check `Character.canonical_code` uniqueness within project
- **Variant activation failure**: Verify only one variant is active per character per story
- **Actor casting failure**: Ensure actor has `project_id = NULL` (global actor)
- **Profile sheet generation failure**: Check reference image generation logs

**Useful queries**:

```sql
-- Check API request logs
SELECT * FROM audit_logs 
WHERE entity_type = 'story' AND action LIKE 'generation_%'
ORDER BY created_at DESC LIMIT 10;

-- Check job queue status
SELECT job_id, job_type, status, error 
FROM jobs 
WHERE status IN ('queued', 'running', 'failed')
ORDER BY created_at DESC;

-- Check scene workflow status
SELECT s.scene_id, s.planning_locked, 
       COUNT(a.artifact_id) as artifact_count
FROM scenes s
LEFT JOIN artifacts a ON s.scene_id = a.scene_id
WHERE s.scene_id = ?
GROUP BY s.scene_id;

-- Check story generation status
SELECT story_id, generation_status, generation_error, 
       progress, progress_updated_at
FROM stories 
WHERE story_id = ?;
```

**Key log patterns to search**:
- `api.generation` - Generation endpoint traces
- `api.stories` - Story endpoint traces
- `api.scenes` - Scene endpoint traces
- `job_queue` - Background job execution traces
- `request_id` - Trace specific request through system

**Testing endpoints**:

```bash
# Test story blueprint generation (sync)
curl -X POST http://localhost:8000/v1/stories/{story_id}/generate/blueprint \
  -H "Content-Type: application/json" \
  -d '{
    "source_text": "Story text here...",
    "max_scenes": 10,
    "max_characters": 5,
    "panel_count": 3
  }'

# Test scene planning
curl -X POST http://localhost:8000/v1/scenes/{scene_id}/plan \
  -H "Content-Type: application/json" \
  -d '{
    "panel_count": 3
  }'

# Test scene rendering
curl -X POST http://localhost:8000/v1/scenes/{scene_id}/render \
  -H "Content-Type: application/json" \
  -d '{
    "style_id": "soft_webtoon",
    "enforce_qc": true
  }'

# Check job status
curl http://localhost:8000/v1/jobs/{job_id}

# Check scene status
curl http://localhost:8000/v1/scenes/{scene_id}/status
```

## See Also

- [Application Workflow](01-application-workflow.md) - High-level system overview
- [LangGraph Architecture](02-langgraph-architecture.md) - Graph workflows behind generation endpoints
- [Artifact System](06-artifact-system.md) - Artifact versioning and retrieval
- [Character System](05-character-system.md) - Character extraction and variant management
- [Configuration Files](07-configuration-files.md) - Style presets and configuration
- [Error Handling & Observability](09-error-handling-observability.md) - Debugging and monitoring
- [SKILLS.md](../SKILLS.md) - Quick reference guide
