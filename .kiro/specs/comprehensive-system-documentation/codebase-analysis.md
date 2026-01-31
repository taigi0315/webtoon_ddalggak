# Codebase Analysis - Ssuljaengi v4 Webtoon Generation System
## Analysis Date: January 2026

## Executive Summary

The ssuljaengi_v4 system is a sophisticated webtoon generation pipeline that converts story text into visual panel sequences using LangGraph state machines and Google Gemini AI. The system follows a three-tier architecture with clear separation between story-level processing, scene-level planning, and image rendering.

**Key Technologies:**
- FastAPI for REST API
- LangGraph for workflow orchestration
- Google Gemini (Vertex AI) for text and image generation
- SQLAlchemy for database ORM
- Jinja2 for prompt templating
- Prometheus for metrics
- OpenTelemetry for tracing

**System Scale:**
- 30+ database models
- 3 main LangGraph workflows
- 20+ API endpoint modules
- 50+ prompt templates
- 10+ JSON configuration files

## System Architecture Overview

### Three-Tier Processing Architecture

1. **Episode-Level (StoryBuildGraph)**
   - Input: Raw story text
   - Processing: Scene splitting, character extraction, visual planning
   - Output: Scenes, Characters, Visual Plans, Blind Test Reports
   - Mode: Synchronous or Async (via job queue)

2. **Scene-Level (ScenePlanningGraph)**
   - Input: Scene text
   - Processing: Intent extraction, panel planning, layout resolution, semantic filling
   - Output: Panel plans, layouts, semantics, QC reports
   - Mode: Synchronous

3. **Render-Level (SceneRenderGraph)**
   - Input: Panel semantics + layout
   - Processing: Prompt compilation, image generation, QC validation
   - Output: Rendered images
   - Mode: Synchronous or Async


## Core Components

### 1. Database Models (app/db/models.py)

**Core Hierarchy:**
- Project → Story → Scene
- Story has generation_status, progress (JSON), generation_error
- Scene has planning_locked flag, style overrides

**Character System:**
- Character: Main character entity (can be project-scoped or global/Actor)
- StoryCharacter: Many-to-many link between Story and Character
- CharacterVariant: Appearance variations (story-scoped or global)
- CharacterReferenceImage: Reference images for consistency

**Artifact System:**
- Artifact: Versioned intermediate outputs (scene-scoped)
- Version auto-increments per (scene_id, type)
- Parent-child lineage via parent_id
- Payload stores JSON data + request_id

**Other Key Models:**
- StylePreset: Custom styles with inheritance via parent_id
- DialogueLayer: Speech bubbles for scenes
- EnvironmentAnchor: Reusable environment descriptions
- Layer: Compositing layers
- Episode/EpisodeScene: Multi-scene compositions
- ExportJob: Video/image export tracking
- AuditLog: Change tracking with request correlation

**Key Patterns:**
- Canonical codes (CHAR_A, CHAR_B) for character consistency
- Actor system: Global characters (project_id=NULL) reusable across stories
- Planning lock: Prevents regeneration when manually edited
- Style resolution hierarchy: Scene override → Story default → System default


### 2. LangGraph Workflows

#### StoryBuildGraph (app/graphs/story_build.py)

**Planning Modes:**
- `full`: Complete pipeline with visual planning and blind tests
- `characters_only`: Stop after character extraction (no visual planning)

**Node Flow (full mode):**
1. validate_inputs → Normalize settings
2. scene_splitter → Chunk text into scenes
3. llm_character_extractor → Extract character profiles
4. llm_character_normalizer → Add visual details
5. persist_story_bundle → Save to DB with deduplication
6. llm_visual_plan_compiler → Create visual plans
7. per_scene_planning → Loop through scenes for planning
8. blind_test_runner → Evaluate quality

**Episode-Level Guardrails:**
- Prevents 3+ identical layouts in a row
- Ensures at least one hero single-panel scene (if required)
- Tracks recent templates to avoid repetition

**Character Deduplication:**
- Matches by name (case-insensitive)
- Assigns canonical codes (CHAR_A, CHAR_B, etc.)
- Merges visual details from new extractions
- Links characters to stories via StoryCharacter

#### ScenePlanningGraph (app/graphs/pipeline.py)

**Node Flow:**
1. llm_scene_intent → Extract pacing, importance
2. llm_panel_plan → Generate grammar-based plan
3. rule_panel_plan_normalize → Enforce grammar rules
4. rule_layout → Select layout template
5. llm_panel_semantics → Fill panel descriptions

**Planning Lock:**
- When scene.planning_locked=True, returns existing artifacts
- Prevents regeneration of manually edited plans
- Validates all required artifacts exist

#### SceneRenderGraph (app/graphs/pipeline.py)

**Node Flow:**
1. load_artifacts → Fetch semantics + layout
2. render_spec → Compile Gemini prompt
3. render → Generate image
4. qc_check → Validate quality

**Style Resolution:**
- Scene.image_style_override → Story.default_image_style → "default"
- Supports per-scene style customization


### 3. Prompt System (app/prompts/)

**Architecture:**
- Prompts stored in YAML files (versioned directory structure)
- Loaded via app/prompts/loader.py with caching
- Rendered using Jinja2 templates
- Supports metadata: required_variables, output_schema

**Directory Structure:**
```
prompts/
├── prompts.yaml (legacy)
└── v1/
    ├── shared/           # System prompts, constraints
    ├── story_build/      # Character extraction, normalization
    ├── scene_planning/   # Intent, panel plan, semantics
    ├── evaluation/       # Blind test prompts
    ├── dialogue/         # Dialogue extraction
    ├── utility/          # JSON repair
    └── casting/          # Actor generation
```

**Key Prompts:**
- system_prompt_json: JSON generation rules
- prompt_scene_intent: Narrative analysis
- prompt_panel_plan: Panel breakdown
- prompt_panel_semantics: Visual descriptions
- prompt_character_extraction: Character identification
- prompt_character_normalization: Visual enrichment
- prompt_blind_test: Quality evaluation
- prompt_profile_sheet: Actor generation
- prompt_variant_generation: Character variants

**Character Style Map:**
- Age/gender-based styling templates
- Korean manhwa aesthetic standards
- Used in character normalization
- Examples: AFTER_BECOMING_FINANCIALLY_FREE, I_WILL_START_BY_CHANGING_MY_HUSBAND

**Visual Prompt Formula:**
- 150-250 word structure for image generation
- Required elements: shot, environment, lighting, character, atmosphere
- Compiled with runtime context (characters, scenes, styles)

**Features:**
- Hot-reload support via clear_cache()
- Template validation on load (fails fast on syntax errors)
- Auto-includes shared prompts (system_prompt_json, global_constraints)
- Variable extraction and validation


### 4. Artifact System (app/services/artifacts.py)

**Purpose:**
- Versioned intermediate outputs
- Enable resumable workflows
- Provide audit trail
- Scene-scoped storage

**Artifact Types:**
- scene_intent: Pacing, logline, importance
- panel_plan: Raw grammar-driven plan
- panel_plan_normalized: Normalized grammar array
- layout_template: Layout metadata
- panel_semantics: Panel descriptions + dialogue
- render_spec: Compiled Gemini prompt
- render_result: Generated image metadata
- qc_report: Quality control metrics
- blind_test_report: Evaluation results
- visual_plan: Scene summaries + style hints
- dialogue_suggestions: Extracted dialogue

**Versioning:**
- Auto-incrementing per (scene_id, type)
- Parent-child lineage via parent_id
- Retry logic for version conflicts (3 attempts)
- Request ID embedded in payload

**ArtifactService API:**
- create_artifact(scene_id, type, payload, parent_id)
- get_artifact(artifact_id)
- get_latest_artifact(scene_id, type)
- list_artifacts(scene_id, type)
- get_next_version(scene_id, type)

**Integration:**
- Used by all graph nodes
- Enables planning lock feature
- Supports manual editing workflows
- Tracked in audit logs


### 5. GeminiClient (app/services/vertex_gemini.py)

**Error Handling:**
- Custom exceptions: GeminiRateLimitError, GeminiTimeoutError, GeminiContentFilterError, GeminiCircuitOpenError, GeminiModelUnavailableError
- Error classification: rate_limit, content_filter, timeout, model_unavailable, invalid_request
- Retry logic with exponential backoff
- Rate limit backoffs: [10, 30, 180, 600] seconds

**Circuit Breaker:**
- Per-operation tracking (generate_text, generate_image)
- Failure threshold: 5 (configurable)
- Recovery timeout: 60 seconds (configurable)
- States: closed, open, half-open
- Half-open requires 2 consecutive successes to close

**Model Fallback:**
- Primary models: gemini-2.5-flash (text), gemini-2.5-flash-image (image)
- Fallback models: gemini-2.0-flash (configurable)
- Automatic fallback on rate limit, timeout, unavailable errors
- Prevents fallback loops (won't retry fallback with same model)

**Features:**
- Request correlation via request_id
- Usage metadata tracking (tokens, model)
- Safety settings (BLOCK_NONE for all categories)
- Image config (9:16 aspect ratio)
- Reference image support for character consistency
- Timeout: 60 seconds (configurable)
- Max retries: 3 (configurable)

**Integration:**
- Wrapped by track_gemini_call for metrics
- Used by all LLM/image generation nodes
- Circuit breaker status exposed via API
- Manual reset capability


### 6. Configuration System (app/config/)

**Configuration Files:**

1. **panel_grammar_library_v1.json**
   - Valid grammar IDs: establishing, dialogue_medium, emotion_closeup, action, reaction, object_focus, reveal, impact_silence
   - Used in panel plan validation

2. **layout_templates_9x16_v1.json**
   - 9:16 vertical format templates
   - Panel geometry: {x, y, w, h} normalized coordinates
   - Template selection matches panel count

3. **layout_selection_rules_v1.json**
   - Decision-table rules for template selection
   - Matches: panel_count, scene_importance, pace
   - Weight-based selectors: min_large_panels, min_max_weight
   - Default template fallback

4. **qc_rules_v1.json**
   - closeup_ratio_max: 0.5
   - dialogue_ratio_max: 0.6
   - repeated_framing_run_length: 3
   - require_environment_on_establishing: true
   - environment_keywords: [room, street, cafe, school, ...]

5. **genre_guidelines_v1.json**
   - Genre-specific visual styles
   - Shot preferences, composition, camera, lighting
   - Shot distribution per genre

6. **image_styles.json**
   - Style presets for generation
   - ID, label, description, image_url

7. **grammar_to_prompt_mapping_v1.json**
   - Maps grammar IDs to prompt fragments

8. **continuity_rules_v1.json**
   - Continuity validation rules

**Loading:**
- Pydantic models for validation
- LRU cache for performance
- Hot-reload via clear_config_cache()
- Config watcher service for file changes
- Version tracking for cache invalidation

**Helper Functions:**
- get_grammar(grammar_id)
- get_layout_template(template_id)
- select_template(panel_plan, derived_features, excluded_template_ids)
- get_genre_guideline(genre)
- has_image_style(style_id)


### 7. API Structure (app/api/v1/)

**Base Path:** `/v1/`

**Endpoint Modules:**
- projects.py: Project CRUD
- stories.py: Story CRUD, progress tracking
- scenes.py: Scene CRUD
- characters.py: Character CRUD, canonical codes
- character_variants.py: Variant management
- artifacts.py: Artifact retrieval
- generation.py: Story blueprint, scene planning, rendering
- internal_generation.py: Internal generation endpoints
- gemini.py: Gemini health checks, circuit breaker status
- jobs.py: Background job status
- review.py: Review endpoints
- styles.py: Style listing
- style_presets.py: Custom style management
- dialogue.py: Dialogue layer management
- environments.py: Environment anchor management
- layers.py: Layer management
- episodes.py: Episode CRUD
- episode_planning.py: Episode planning
- exports.py: Export job management
- casting.py: Actor generation
- config.py: Configuration management

**Generation Workflow Endpoints:**
- POST /stories/{story_id}/generate/blueprint_async: Story → Scenes + Characters
- POST /scenes/{scene_id}/generate/scene-intent: Extract intent
- POST /scenes/{scene_id}/generate/panel-plan: Generate plan
- POST /scenes/{scene_id}/generate/panel-plan/normalize: Normalize plan
- POST /scenes/{scene_id}/generate/layout: Resolve layout
- POST /scenes/{scene_id}/generate/panel-semantics: Fill semantics
- POST /scenes/{scene_id}/generate/render: Render image
- POST /scenes/{scene_id}/generate/full_async: Full pipeline

**Key Features:**
- Async job support via job_queue
- Progress tracking via Story.progress
- Request correlation via x-request-id
- Error responses with request_id
- OpenAPI documentation at /docs


### 8. Observability & Telemetry

**Request Context (app/core/request_context.py):**
- x-request-id header propagation
- Context variable for thread-safe access
- Embedded in logs, artifacts, API calls
- Enables end-to-end tracing

**Telemetry (app/core/telemetry.py):**
- OpenTelemetry integration
- trace_span decorator for graphs
- FastAPI instrumentation
- LangChain instrumentation (optional)
- Phoenix/OTEL endpoint support
- Span attributes: story_id, scene_id, style_id

**Metrics (app/core/metrics.py):**
- Prometheus-compatible metrics
- GRAPH_NODE_DURATION: Histogram by graph/node
- JSON_PARSE_FAILURES: Counter by tier
- GEMINI_CALL_DURATION: Histogram by operation
- GEMINI_CALLS_TOTAL: Counter by operation/status
- BLIND_TEST_RESULTS: Counter by result
- QC_FAILURES: Counter by issue
- ARTIFACT_CREATIONS_TOTAL: Counter by type
- Exposed at /metrics endpoint

**Logging (app/core/logging.py):**
- Structured JSON logging
- RequestIdFilter for correlation
- RotatingFileHandler support
- Configurable log level
- Log file: configurable path

**Audit Logging (app/services/audit.py):**
- AuditLog model tracks changes
- Entity type, entity ID, action
- Old/new value snapshots
- Request ID correlation
- Timestamp tracking

**Progress Tracking:**
- Story.progress JSON field
- Updated by graph nodes
- Current node, message, step
- Total steps calculation
- progress_updated_at timestamp
- API endpoint for checking progress


### 9. Character System

**Character Extraction:**
- LLM-based extraction from story text
- Identifies names, roles, relationships
- Fallback to heuristic NER
- Prompt: prompt_character_extraction

**Character Normalization:**
- Adds visual details (hair, face, build, outfit)
- Creates identity_line for prompts
- Applies Korean manhwa aesthetics
- Uses character_style_map for age/gender styling
- Prompt: prompt_character_normalization

**Canonical Codes:**
- Sequential assignment (CHAR_A, CHAR_B, ...)
- Persists across stories within project
- Deduplication by name (case-insensitive)
- Assigned in persist_story_bundle

**Actor System:**
- Global character library (project_id = NULL)
- Reusable across stories and projects
- Approval workflow (approved flag)
- Display name for library browsing
- Default style preferences

**Character Variants:**
- Types: base, outfit_change, mood_change, variant, imported
- Story-scoped (story_id set) or global (story_id = NULL)
- Active variant selection (is_active_for_story)
- Default variant (is_default)
- Traits: {face, hair, mood, outfit}
- Override attributes for customization
- Reference image linkage
- Generated image tracking

**Reference Images:**
- Types: face, full_body, profile_sheet, variant, imported
- Approval workflow
- Primary image designation
- Metadata storage
- Used for consistency in rendering

**Casting Service (app/services/casting.py):**
- generate_character_profile_sheet: Create 9:16 profile image
- save_actor_to_library: Save to Actor library
- generate_variant_from_reference: Create variant with reference
- import_actor_from_image: Import from URL
- import_actor_from_local_file: Import from file system


### 10. Additional Services

**Storage (app/services/storage.py):**
- LocalMediaStore for file management
- Image saving with UUID naming
- URL generation
- Media root: ./storage/media (configurable)

**Job Queue (app/services/job_queue.py):**
- Background task processing
- Async story blueprint generation
- Async scene rendering
- Job status tracking
- Cancellation support

**Layout Selection (app/services/layout_selection.py):**
- Template matching logic
- Decision-table evaluation
- Weight-based selection
- Exclusion support for guardrails

**Scene Importance (app/services/scene_importance.py):**
- Importance classification
- Used in layout selection

**Story Analysis (app/services/story_analysis.py):**
- Story text analysis
- Scene chunking logic

**Variant Suggestions (app/services/variant_suggestions.py):**
- AI-powered variant suggestions
- Trait change recommendations

**Config Watcher (app/services/config_watcher.py):**
- File system monitoring
- Hot-reload on config changes
- Cache invalidation

**Images (app/services/images.py):**
- Image processing utilities
- Format conversion

**Video (app/services/video.py):**
- Video export functionality
- Scene composition


## Key Patterns and Conventions

### 1. State Management
- LangGraph uses TypedDict for state schemas
- Immutable state passed between nodes
- Nodes return dict updates to merge into state
- State persisted in Story.progress for debugging

### 2. Error Handling
- Custom exception hierarchy for Gemini errors
- Circuit breaker pattern for API resilience
- Retry with exponential backoff
- Model fallback on failures
- Error classification (retryable vs fatal)

### 3. Versioning
- Artifacts: Auto-incrementing version per (scene_id, type)
- Config: Version tracking for cache invalidation
- Prompts: Versioned directory structure (v1/)
- API: Versioned endpoints (/v1/)

### 4. Caching
- LRU cache for config loaders
- LRU cache for prompt loaders
- Clear cache functions for hot-reload
- Version tracking for invalidation

### 5. Validation
- Pydantic models for config validation
- JSON schema validation for LLM outputs
- QC rules for quality control
- Grammar validation for panel plans
- Prompt template syntax validation

### 6. Correlation
- Request ID propagation
- Embedded in logs, artifacts, metrics
- x-request-id header
- Context variables for thread safety

### 7. Observability
- Structured JSON logging
- Prometheus metrics
- OpenTelemetry tracing
- Audit logging
- Progress tracking

### 8. Idempotency
- Planning lock prevents regeneration
- Artifact versioning enables replay
- Latest artifact lookup before creation
- Retry logic with version conflict handling


## File Locations Reference

### Core Application
- `app/main.py` - FastAPI application entry point
- `app/api/v1/router.py` - API router configuration
- `app/db/models.py` - Database model definitions
- `app/db/session.py` - Database session management
- `app/db/base.py` - SQLAlchemy base configuration

### LangGraph Workflows
- `app/graphs/story_build.py` - StoryBuildGraph implementation
- `app/graphs/pipeline.py` - ScenePlanningGraph and SceneRenderGraph
- `app/graphs/nodes/` - Individual node implementations
- `app/graphs/nodes/planning/` - Planning node modules
- `app/graphs/nodes/prompts/` - Prompt compilation nodes
- `app/graphs/nodes/helpers/` - Helper utilities

### Prompts
- `app/prompts/prompts.yaml` - Legacy prompt file
- `app/prompts/loader.py` - Prompt loading and rendering
- `app/prompts/v1/` - Versioned prompt directory
- `app/prompts/v1/shared/` - System prompts
- `app/prompts/v1/story_build/` - Character extraction prompts
- `app/prompts/v1/scene_planning/` - Planning prompts
- `app/prompts/v1/evaluation/` - Blind test prompts

### Configuration
- `app/config/loaders.py` - Configuration loading
- `app/config/panel_grammar_library_v1.json` - Grammar definitions
- `app/config/layout_templates_9x16_v1.json` - Layout templates
- `app/config/layout_selection_rules_v1.json` - Selection rules
- `app/config/qc_rules_v1.json` - Quality control rules
- `app/config/genre_guidelines_v1.json` - Genre guidelines

- `app/config/image_styles.json` - Image styles

### Services
- `app/services/artifacts.py` - Artifact management
- `app/services/vertex_gemini.py` - Gemini client
- `app/services/casting.py` - Actor generation
- `app/services/storage.py` - File storage
- `app/services/job_queue.py` - Background jobs
- `app/services/layout_selection.py` - Layout selection
- `app/services/audit.py` - Audit logging
- `app/services/config_watcher.py` - Config hot-reload

### Core Utilities
- `app/core/settings.py` - Application settings
- `app/core/logging.py` - Logging configuration
- `app/core/metrics.py` - Prometheus metrics
- `app/core/telemetry.py` - OpenTelemetry setup
- `app/core/request_context.py` - Request correlation
- `app/core/character_styles.py` - Character style maps

### Tests
- `tests/conftest.py` - Test fixtures
- `tests/test_*.py` - Test modules

### Documentation
- `docs/langgraph_architecture.md` - LangGraph overview
- `docs/project_workflow.md` - Workflow guide
- `docs/api.md` - API documentation
- `README.md` - Project overview


## Documentation Status

### Existing Documentation
- `README.md` - Good overview, installation, API usage
- `docs/langgraph_architecture.md` - Detailed LangGraph documentation
- `docs/project_workflow.md` - Testing checklist
- `docs/api.md` - API reference (referenced but not found)
- Various technical documents in docs/

### Documentation Gaps
- No comprehensive system overview
- No database model documentation
- No prompt system guide
- No configuration file reference
- No character system documentation
- No artifact system documentation
- No error handling guide
- No SKILLS.md quick reference
- Outdated materials in /docs folder

### Documentation Needs
1. High-level application workflow guide
2. Complete database schema documentation
3. Prompt system structure and usage
4. Configuration file reference
5. Character extraction and variant system
6. Artifact versioning and storage
7. Error handling and observability
8. API endpoint reference
9. SKILLS.md for developers and AI agents
10. Updated architecture diagrams

## Key Insights for Documentation

### 1. System Complexity
- 3 main workflows with 20+ nodes
- 30+ database models with complex relationships
- 50+ prompt templates
- 10+ configuration files
- Multiple integration points (Gemini, storage, telemetry)

### 2. Documentation Approach
- Keep high-level and concise
- Focus on concepts, not implementation details
- Provide file locations for deep dives
- Use diagrams for complex flows
- Emphasize debugging direction over solutions

### 3. Key Concepts to Document
- Three-tier architecture
- Artifact versioning
- Character system (extraction, normalization, variants, actors)
- Planning lock mechanism
- Circuit breaker pattern
- Request correlation
- Style resolution hierarchy
- Episode-level guardrails

### 4. Common Debugging Scenarios
- Stuck jobs: Check Story.progress
- Planning issues: Check artifacts table
- Gemini errors: Check circuit breaker status
- Character consistency: Check canonical codes
- Layout issues: Check QC reports
- Style problems: Check style resolution

## Next Steps

1. Create documentation index (docs/README.md)
2. Write application workflow guide
3. Document LangGraph architecture
4. Create prompt system guide
5. Document database models
6. Write character system guide
7. Document artifact system
8. Create configuration reference
9. Write API reference
10. Document error handling
11. Create SKILLS.md
12. Review and validate all documentation

