# Webtoon Generation Pipeline - Task List for Improvements

**Generated:** 2026-01-29
**Scope:** Full codebase analysis focusing on LangGraph architecture, prompts, code quality, and features

---

## Table of Contents

1. [Critical Priority - Reliability & Stability](#1-critical-priority---reliability--stability)
2. [High Priority - Code Refactoring](#2-high-priority---code-refactoring)
3. [High Priority - Prompt Engineering](#3-high-priority---prompt-engineering)
4. [High Priority - Documentation](#4-high-priority---documentation)
5. [Medium Priority - API Design](#5-medium-priority---api-design)
6. [Medium Priority - Observability & Monitoring](#6-medium-priority---observability--monitoring)
7. [Medium Priority - Testing](#7-medium-priority---testing)
8. [Medium Priority - Database & State](#8-medium-priority---database--state)
9. [Lower Priority - Feature Enhancements](#9-lower-priority---feature-enhancements)
10. [Lower Priority - Configuration System](#10-lower-priority---configuration-system)

---

## 1. Critical Priority - Reliability & Stability

### 1.1 JSON Parsing Self-Repair Fallback ✅ COMPLETED
**File:** `app/graphs/nodes/utils.py` (lines 1617-1770)
**Tests:** `tests/test_json_parsing.py` (25 tests)
**Completed:** 2026-01-29

**Implementation Summary:**
- Added `_strip_markdown_fences()` - removes ```json and ``` code fences
- Added `_clean_json_text()` - strips prose, removes trailing commas
- Added `_extract_json_object()` - bracket-matching extraction for `{}`
- Added `_extract_json_array()` - bracket-matching extraction for `[]`
- Enhanced `_repair_json_with_llm()` - now retries up to 2 times with all extraction methods
- Updated `_maybe_json_from_gemini()` - 5-tier extraction: direct → cleaned → object → array → LLM repair
- Added comprehensive logging at each tier

**Original Issues (now resolved):**
- ~~`_maybe_json_from_gemini()` has limited error recovery~~
- ~~Does not strip markdown code fences~~
- ~~Regex only captures objects, not arrays~~
- ~~Greedy regex can fail with nested structures~~
- ~~No retry mechanism within the function itself~~
- ~~Limited logging for debugging parse failures~~

---

### 1.2 Graceful Degradation for Gemini Failures ✅ COMPLETED
**File:** `app/services/vertex_gemini.py`, `app/core/settings.py`
**Tests:** `tests/test_gemini_error_handling.py` (18 tests)
**Completed:** 2026-01-29

**Implementation Summary:**
- Added custom exception classes: `GeminiError`, `GeminiRateLimitError`, `GeminiContentFilterError`, `GeminiTimeoutError`, `GeminiCircuitOpenError`, `GeminiModelUnavailableError`
- Implemented `CircuitBreakerState` class with open/half-open/closed states
- Added error classification: `_classify_error()` determines error type and retryability
- Added content filter detection: `_check_response_safety()` checks for blocked content
- Added fallback model support: tries alternate model on rate limit/timeout/unavailable
- Added settings: `GEMINI_FALLBACK_TEXT_MODEL`, `GEMINI_FALLBACK_IMAGE_MODEL`, `GEMINI_CIRCUIT_BREAKER_THRESHOLD`, `GEMINI_CIRCUIT_BREAKER_TIMEOUT`
- Added `get_circuit_breaker_status()` and `reset_circuit_breaker()` methods

**Original Issues (now resolved):**
- ~~Timeout just raises RuntimeError~~ → Now raises `GeminiTimeoutError` with retry info
- ~~Rate limit handling exists but no circuit breaker~~ → Full circuit breaker with half-open recovery
- ~~Content filter blocks not handled gracefully~~ → `GeminiContentFilterError` with blocked categories
- ~~No fallback model support~~ → Automatic fallback on retryable errors

---

### 1.3 Async Job Queue for Long-Running Operations
**File:** `app/api/v1/stories.py`, `app/api/v1/generation.py`

**Current Issues:**
- `POST /v1/stories/{story_id}/generate` blocks until completion
- HTTP timeouts on long stories
- Poor UX (no progress feedback without polling)
- Server resource exhaustion risk

**Improvement Points:**
- Implement background job queue (asyncio.Queue or Celery/Redis)
- Return job_id immediately (202 Accepted)
- Add `GET /v1/jobs/{job_id}` for status polling
- Optional WebSocket endpoint for real-time progress
- Add job cancellation support
- Integrate with existing `Story.progress` JSON field

---

## 2. High Priority - Code Refactoring

### 2.1 Split planning.py into Single-Responsibility Modules
**File:** `app/graphs/nodes/planning.py` (565 lines)

**Current Issues:**
- Multiple node implementations mixed together
- Helpers scattered throughout
- Difficult to test individual nodes
- Hard to navigate and maintain

**Proposed Split:**
```
app/graphs/nodes/
├── planning/
│   ├── __init__.py
│   ├── scene_intent.py          # run_scene_intent_extractor
│   ├── panel_plan.py            # run_panel_plan_generator, run_panel_plan_normalizer
│   ├── panel_semantics.py       # run_panel_semantic_filler
│   ├── layout.py                # run_layout_template_resolver
│   ├── character_extraction.py  # compute_character_profiles_llm, normalize_character_profiles_llm
│   ├── blind_test.py            # run_blind_test_evaluator
│   ├── visual_plan.py           # compile_visual_plan_bundle_llm
│   ├── dialogue.py              # run_dialogue_extractor
│   └── qc.py                    # run_qc_checker
```

---

### 2.2 Split utils.py by Domain
**File:** `app/graphs/nodes/utils.py` (1939 lines)

**Current Issues:**
- Massive file with mixed concerns
- Prompt builders, helpers, constants all mixed
- Hard to find specific functionality

**Proposed Split:**
```
app/graphs/nodes/
├── constants.py           # ARTIFACT_*, VALID_GRAMMAR_IDS, PACING_OPTIONS
├── helpers/
│   ├── __init__.py
│   ├── text.py            # _summarize_text, _split_sentences, _extract_names
│   ├── scene.py           # _extract_setting, _extract_beats, _choose_mid_grammar
│   ├── panel.py           # _heuristic_panel_plan, _normalize_panel_plan, _assign_panel_weights
│   ├── character.py       # _character_codes, _inject_character_identities
│   ├── media.py           # _resolve_media_path, _load_character_reference_images
│   └── similarity.py      # _rough_similarity
├── prompts/
│   ├── __init__.py
│   ├── builders.py        # All _prompt_* functions
│   └── compile.py         # _compile_prompt
├── json_parser.py         # _maybe_json_from_gemini, _repair_json_with_llm
└── genre_guidelines.py    # GENRE_VISUAL_GUIDELINES, SHOT_DISTRIBUTION_BY_GENRE
```

---

### 2.3 Refactor API Endpoints to Workflow-Based
**File:** `app/api/v1/generation.py`

**Current Issues:**
- Per-node endpoints expose implementation details:
  - `POST /generate/scene-intent`
  - `POST /generate/panel-plan`
  - `POST /generate/panel-semantics`
- Tightly couples API to internal node structure
- Complex for clients to use correctly

**Improvement Points:**
- Create workflow-based endpoints:
  - `POST /scenes/{id}/plan` - Run full planning workflow
  - `POST /scenes/{id}/render` - Run rendering workflow
  - `GET /scenes/{id}/status` - Get workflow status
- Keep internal node endpoints under `/v1/internal/` for debugging only
- Simplify client integration

---

## 3. High Priority - Prompt Engineering

### 3.1 Organize Prompts by Domain with Versioning
**File:** `app/prompts/prompts.yaml` (691 lines, single file)

**Current Issues:**
- All prompts in single YAML file
- No versioning or A/B testing support
- Difficult to track prompt changes
- No organization by domain

**Proposed Structure:**
```
app/prompts/
├── loader.py
├── v1/
│   ├── story_build/
│   │   ├── character_extraction.yaml
│   │   ├── character_normalization.yaml
│   │   └── visual_plan.yaml
│   ├── scene_planning/
│   │   ├── scene_intent.yaml
│   │   ├── panel_plan.yaml
│   │   └── panel_semantics.yaml
│   ├── rendering/
│   │   └── render_spec.yaml
│   ├── evaluation/
│   │   ├── blind_reader.yaml
│   │   ├── comparator.yaml
│   │   └── blind_test.yaml
│   └── shared/
│       ├── system_prompts.yaml
│       └── constraints.yaml
```

**Each file should include:**
- Version number
- Description
- Template
- Example input/output
- Required variables

---

### 3.2 Prompt Template Validation and Testing
**File:** `app/prompts/loader.py`

**Current Issues:**
- No validation that templates are syntactically correct
- No check for required variables
- No output schema validation
- Runtime errors from malformed prompts

**Improvement Points:**
- Add Jinja2 syntax validation on load
- Check all `{{variables}}` have defaults or documentation
- Add output schema validation (expected JSON structure)
- Create unit tests for each prompt template with sample inputs
- Add CI check that all prompts are valid before deploy

---

### 3.3 Expand Character Style Map
**File:** `app/prompts/prompts.yaml` (character_style_map section)

**Current Issues:**
- Only covers gender × age combinations
- No ethnicity variations
- No body type variations
- No distinctive features (glasses, scars)
- Hardcoded in YAML

**Improvement Points:**
- Add ethnicity variations (East Asian, South Asian, European, African, etc.)
- Add body type variations
- Add distinctive features options
- Add art style variations (chibi, realistic, semi-realistic)
- Move to database-driven style presets for user customization

---

### 3.4 Add Prompt A/B Testing and Metrics Infrastructure

**Current Issues:**
- No mechanism to test prompt variations
- No tracking of prompt effectiveness
- Can't measure blind test pass rate by prompt version

**Improvement Points:**
- Implement prompt variant system (e.g., `scene_intent_v1`, `scene_intent_v2`)
- Add variant selection based on experiment config or random sampling
- Track metrics: blind test pass rate, user approval rate, regeneration count
- Create prompt performance dashboard or export
- Allow flagging prompts as "production" vs "experimental"

---

## 4. High Priority - Documentation

### 4.1 Create Developer Setup and Contribution Guide
**Missing Files:** `README.md` (incomplete), `CONTRIBUTING.md`, `.env.example`

**Required Documentation:**
- Project overview and architecture summary
- Prerequisites (Python version, dependencies)
- Installation steps
- Environment variables (with `.env.example`)
- Database setup (migrations)
- Gemini API key configuration
- Quick start guide
- Code style guide
- PR process and testing requirements
- Docker compose for local development

---

### 4.2 Document LangGraph Architecture with Diagrams
**Missing:** Architecture documentation

**Required Documentation:**
- Architecture diagram showing all three graphs:
  - StoryBuildGraph
  - ScenePlanningGraph
  - SceneRenderGraph
- Node flow diagram for each graph with decision points
- State schema documentation:
  - StoryBuildState
  - ScenePlanningState
  - SceneRenderState
- Artifact lifecycle documentation (types, versioning, lineage)
- Error handling and retry behavior
- Use Mermaid or similar for diagrams

---

### 4.3 Create Comprehensive API Documentation

**Current Issues:**
- Only auto-generated FastAPI docs
- No workflow guide
- No error code reference

**Required Documentation:**
- API overview explaining resource hierarchy:
  - Project → Story → Scene → Artifact
- Workflow guide: "How to generate a webtoon from story text"
- Schema documentation with examples for each endpoint
- Error code reference
- Rate limiting and usage guidelines
- Authentication setup (if applicable)

---

## 5. Medium Priority - API Design

### 5.1 Add Request Tracing with Correlation IDs

**Current Issues:**
- No request ID correlation for distributed tracing
- Difficult to debug pipeline issues
- No way to track Gemini calls per request

**Improvement Points:**
- Generate unique request_id for each API call
- Pass request_id through LangGraph nodes
- Include request_id in all logs and artifact metadata
- Return request_id in response headers (X-Request-ID)
- Add Gemini call tracking linked to request_id

---

### 5.2 Add Audit Trail for Modifications
**File:** `app/db/models.py`

**Current Issues:**
- No tracking of who modified what and when
- No history of artifact changes
- No user accountability

**Improvement Points:**
- Add `created_by`, `updated_by`, `updated_at` fields to key models
- Create audit log table:
  - entity_type
  - entity_id
  - action (create/update/delete)
  - old_value
  - new_value
  - user_id
  - timestamp
- Log all artifact creations with user context
- Log scene planning lock/unlock events
- Log character approval/rejection events

---

## 6. Medium Priority - Observability & Monitoring

### 6.1 Add Structured Logging
**Current Issues:**
- Inconsistent log formats
- No structured data for log aggregation
- Missing context in log messages

**Improvement Points:**
- Standardize log format with JSON structure
- Include: timestamp, level, request_id, node_name, scene_id, message
- Add log levels consistently (DEBUG for parsing, INFO for node execution, WARNING for recoverable errors)
- Create log aggregation setup documentation

---

### 6.2 Add Metrics Collection

**Current Issues:**
- No metrics for pipeline performance
- No visibility into failure rates
- No Gemini usage tracking

**Metrics to Add:**
- Pipeline duration by graph and node
- JSON parse failure rate by tier
- Blind test pass/fail rate
- Gemini API latency and token usage
- QC check failure rate by issue type
- Artifact creation rate

---

## 7. Medium Priority - Testing

### 7.1 Add Integration Tests with Real Gemini API
**File:** `tests/` directory

**Current Issues:**
- All tests use mocked Gemini returning hardcoded JSON
- No validation of actual LLM output quality
- No prompt robustness testing

**Improvement Points:**
- Create integration test suite marked with `@pytest.mark.integration`
- Tests that hit real Gemini API (gated by env variable)
- Validate actual LLM output structure
- Test prompt robustness with edge cases:
  - Very short story
  - Many characters
  - Non-English content
  - Ambiguous dialogue
- Add cost tracking for integration tests
- Run in CI with rate limiting

---

### 7.2 Add Prompt Unit Tests

**Current Issues:**
- No tests for prompt rendering
- No validation of prompt template syntax
- No expected output validation

**Improvement Points:**
- Test each prompt template with sample inputs
- Validate Jinja2 rendering works correctly
- Check all required variables are present
- Verify output follows expected schema
- Test edge cases (empty inputs, special characters)

---

### 7.3 Add Load/Stress Tests

**Current Issues:**
- No load testing
- Unknown concurrent request capacity
- No memory leak detection

**Improvement Points:**
- Create load test suite with locust or similar
- Test concurrent story generation
- Measure memory usage under load
- Identify bottlenecks
- Document capacity limits

---

## 8. Medium Priority - Database & State

### 8.1 Type Story.progress JSON Field
**File:** `app/db/models.py` (Story model)

**Current Issues:**
- `Story.progress` is untyped JSON
- Contains: current_node, message, step, total_steps
- Error-prone, no validation

**Improvement Points:**
- Create Pydantic model:
```python
class StoryProgress(BaseModel):
    current_node: str
    message: str
    step: int
    total_steps: int
    started_at: datetime
    last_updated_at: datetime
    error: Optional[str] = None
```
- Use SQLAlchemy JSON type with Pydantic validation
- Update all progress writes to use typed model

---

### 8.2 Add Environment Model
**File:** `app/db/models.py`

**Current Issues:**
- `Scene.environment_id` foreign key exists but no Environment model
- No way to ensure consistent backgrounds across scenes

**Improvement Points:**
- Create Environment model:
  - id, name, description
  - seed_image_url
  - style_overrides (JSON)
- Add environment library presets (indoor, outdoor, urban, rural, fantasy)
- Use environment seed image for consistent backgrounds
- Apply environment style_overrides to render spec
- Add API endpoints for environment CRUD

---

### 8.3 Add Database Migration Tests

**Current Issues:**
- 13 migrations exist but no migration tests
- Risky to run migrations in production
- No rollback testing

**Improvement Points:**
- Add upgrade/downgrade tests for each migration
- Test data preservation during migration
- Add CI check for migration validity
- Document migration strategy

---

## 9. Lower Priority - Feature Enhancements

### 9.1 Add Scene Importance Auto-Detection

**Current Issues:**
- Scene importance is manually set
- Could be auto-detected from text analysis

**Improvement Points:**
- Analyze scene text for importance signals:
  - Conflict
  - Revelation
  - Emotional peak
  - Cliffhanger
- Use LLM to score importance (1-5 scale) with reasoning
- Suggest importance to user for approval
- Use importance for layout selection
- Track accuracy vs user overrides

---

### 9.2 Add ML-Based Layout Template Selection
**File:** `app/config/loaders.py`

**Current Issues:**
- Simple decision table (panel_count → template_id)
- Limited visual variety
- No learning from user preferences

**Improvement Points:**
- Extract features: panel_count, scene_importance, pacing, emotional_arc, grammar_distribution
- Track historical data: which templates led to approval/regeneration
- Train simple ML model (logistic regression or decision tree)
- A/B test ML selection vs rule-based
- Fallback to rules when insufficient data

---

### 9.3 Add Character Variant Suggestions Auto-Generation

**Current Issues:**
- Variants (outfit changes) are manually created
- No automatic detection of outfit change needs

**Improvement Points:**
- Analyze story text for outfit change signals:
  - Time jumps
  - Scene changes (home → work)
  - Special events
- Auto-suggest variants based on story context
- Generate variant reference images automatically

---

## 10. Lower Priority - Configuration System

### 10.1 Implement Configuration Hot-Reload
**File:** `app/config/loaders.py`

**Current Issues:**
- Config files require server restart to update
- No config versioning
- No validation before apply

**Improvement Points:**
- Add config watcher using `watchfiles` or similar
- Reload configs on file change without restart
- Store config versions in database for audit trail
- Validate config schema before applying changes
- Expose config reload endpoint for admin use

---

### 10.2 Move Genre Guidelines to Config
**File:** `app/graphs/nodes/utils.py` (GENRE_VISUAL_GUIDELINES)

**Current Issues:**
- Genre guidelines hardcoded in Python
- Can't update without code change
- No user customization

**Improvement Points:**
- Move to `app/config/genre_guidelines_v1.json`
- Add loader function
- Allow per-project genre customization
- Add validation schema

---

### 10.3 Add Style Preset Management API

**Current Issues:**
- Styles hardcoded in JSON files
- No user customization
- No way to add custom styles

**Improvement Points:**
- Add styles to database
- Create API for style CRUD
- Allow per-project custom styles
- Support style inheritance/composition

---

## Summary Statistics

| Priority | Total | Completed | Remaining |
|----------|-------|-----------|-----------|
| Critical | 3 | 2 | 1 |
| High | 7 | 0 | 7 |
| Medium | 9 | 0 | 9 |
| Lower | 6 | 0 | 6 |
| **Total** | **25** | **2** | **23** |

---

## Recommended Implementation Order

### Phase 1: Stability (Week 1-2)
1. ~~JSON Parsing Self-Repair (1.1)~~ ✅ DONE
2. ~~Graceful Degradation for Gemini (1.2)~~ ✅ DONE
3. Developer Setup Guide (4.1)

### Phase 2: Maintainability (Week 3-4)
4. Split planning.py (2.1)
5. Organize Prompts by Domain (3.1)
6. LangGraph Architecture Docs (4.2)

### Phase 3: Observability (Week 5-6)
7. Request Tracing (5.1)
8. Structured Logging (6.1)
9. Prompt Validation (3.2)

### Phase 4: Scalability (Week 7-8)
10. Async Job Queue (1.3)
11. Integration Tests (7.1)
12. API Documentation (4.3)

### Phase 5: Features (Ongoing)
13. Scene Importance Auto-Detection (9.1)
14. Config Hot-Reload (10.1)
15. Remaining items based on user feedback
