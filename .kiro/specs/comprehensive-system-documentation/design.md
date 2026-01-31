# Design Document: Comprehensive System Documentation

## Overview

This design outlines the structure and content for comprehensive documentation of the ssuljaengi_v4 webtoon generation system. The documentation will replace outdated materials in the /docs folder and provide a SKILLS.md reference guide for developers and AI agents.

The documentation project consists of:
1. **Application Workflow Guide** - High-level system overview
2. **LangGraph Architecture Guide** - Detailed graph and node documentation
3. **Prompt System Guide** - Prompt structure and usage
4. **Database Models Guide** - Complete schema documentation
5. **Character System Guide** - Character extraction and variant system
6. **Artifact System Guide** - Versioning and storage patterns
7. **Configuration Guide** - JSON config file reference
8. **API Reference** - Endpoint documentation
9. **Error Handling & Observability Guide** - Debugging and monitoring
10. **SKILLS.md** - Quick reference for developers and AI agents

## Architecture

### Documentation Structure

The documentation will be organized in the /docs folder with the following structure:

```
docs/
├── README.md                          # Documentation index and navigation
├── 01-application-workflow.md         # High-level system overview
├── 02-langgraph-architecture.md       # Graph and node details
├── 03-prompt-system.md                # Prompt templates and usage
├── 04-database-models.md              # Schema and relationships
├── 05-character-system.md             # Character extraction and variants
├── 06-artifact-system.md              # Versioning and storage
├── 07-configuration-files.md          # JSON config reference
├── 08-api-reference.md                # Endpoint documentation
├── 09-error-handling-observability.md # Debugging and monitoring
└── SKILLS.md                          # Quick reference guide
```

### Documentation Principles

1. **Brevity**: Keep documentation short and clear, high-level overview
2. **Accuracy**: All content based on actual codebase (January 2026)
3. **Direction over Solutions**: Provide debugging direction, not specific bug fixes
4. **Clarity**: Use diagrams (Mermaid) for complex concepts
5. **Maintainability**: Structured for easy updates
6. **File References**: Point to code files for detailed implementation


## Components and Interfaces

### Component 1: Application Workflow Documentation

**File**: `docs/01-application-workflow.md`

**Purpose**: Provide a high-level overview of how the system processes story text into final webtoon output.

**Content Structure**:
1. System Overview (2-3 sentences)
2. Three Processing Tiers
   - Episode-level: What it does
   - Scene-level: What it does
   - Render-level: What it does
3. Workflow Diagram (Mermaid)
4. Key Concepts
   - Artifacts: What they are and why
   - Synchronous vs Async: When each is used
5. Key Files
   - `app/graphs/story_build.py` - Episode workflow
   - `app/graphs/pipeline.py` - Scene/render workflows
6. Debugging Direction
   - Where to check for stuck jobs
   - How to inspect workflow state

**Code References**:
- `app/graphs/story_build.py` - Episode-level workflow
- `app/graphs/pipeline.py` - Scene and render workflows
- `app/services/artifacts.py` - Artifact management

### Component 2: LangGraph Architecture Documentation

**File**: `docs/02-langgraph-architecture.md`

**Purpose**: Detailed documentation of the three main LangGraph state machines and their nodes.

**Content Structure**:

1. Three Main Graphs (high-level)
   - StoryBuildGraph: Episode processing
   - ScenePlanningGraph: Panel planning
   - SceneRenderGraph: Image generation

2. StoryBuildGraph Overview
   - Key nodes and their purpose (bullet list)
   - Planning modes: full vs characters_only
   - Flow diagram (Mermaid)

3. ScenePlanningGraph Overview
   - Key nodes and their purpose (bullet list)
   - Planning lock concept
   - Flow diagram (Mermaid)

4. SceneRenderGraph Overview
   - Key nodes and their purpose (bullet list)
   - Style resolution hierarchy
   - Flow diagram (Mermaid)

5. State Schemas
   - Brief description of each state type
   - Key fields to know about

6. Key Files
   - `app/graphs/story_build.py` - Episode workflow
   - `app/graphs/pipeline.py` - Scene/render workflows
   - `app/graphs/nodes/` - Individual node implementations

7. Debugging Direction
   - Where to check graph execution state
   - How to inspect node outputs (artifacts)

**Code References**:
- `app/graphs/story_build.py` - StoryBuildGraph implementation
- `app/graphs/pipeline.py` - ScenePlanningGraph and SceneRenderGraph
- `app/graphs/nodes/` - Individual node implementations


### Component 3: Prompt System Documentation

**File**: `docs/03-prompt-system.md`

**Purpose**: Explain how prompts are structured, loaded, and used throughout the pipeline.

**Content Structure**:

1. Prompt System Overview
   - Prompts stored in `prompts.yaml`
   - Loaded via `app/prompts/loader.py`
   - Compiled with runtime context (Jinja2)

2. Key Prompt Templates (bullet list with purpose)
   - `system_prompt_json`: JSON generation rules
   - `prompt_scene_intent`: Narrative analysis
   - `prompt_panel_plan`: Panel breakdown
   - `prompt_panel_semantics`: Visual descriptions
   - `prompt_character_extraction`: Character identification
   - `prompt_character_normalization`: Visual enrichment
   - `prompt_blind_test`: Quality evaluation

3. Character Style Map
   - Age/gender-based styling templates
   - Korean manhwa aesthetic standards
   - Used in character normalization

4. Visual Prompt Formula
   - 150-250 word structure for image generation
   - Required elements (shot, environment, lighting, character, atmosphere)

5. Key Files
   - `app/prompts/prompts.yaml` - All templates
   - `app/prompts/loader.py` - Loading logic
   - `app/graphs/nodes/prompts/` - Compilation

6. Debugging Direction
   - Check prompt compilation in artifact payloads
   - Review LLM responses in logs

**Code References**:
- `app/prompts/prompts.yaml` - All prompt templates
- `app/prompts/loader.py` - Prompt loading
- `app/graphs/nodes/prompts/` - Prompt compilation logic
- `app/core/character_styles.py` - Character style map


### Component 4: Database Models Documentation

**File**: `docs/04-database-models.md`

**Purpose**: Complete documentation of all database models with relationships and field meanings.

**Content Structure**:

1. Entity Relationship Diagram (Mermaid)
   - Shows all models and relationships

2. Core Hierarchy
   - Project → Story → Scene
   - Key fields for each

3. Character System Models
   - Character: Main character definition
   - StoryCharacter: Links characters to stories
   - CharacterVariant: Appearance variations
   - CharacterReferenceImage: Reference images

4. Artifact System
   - Artifact: Versioned intermediate outputs
   - Image: Generated images

5. Other Key Models (brief list)
   - StylePreset, DialogueLayer, Layer, EnvironmentAnchor
   - Episode, EpisodeScene, EpisodeAsset
   - AuditLog, ExportJob

6. Key Files
   - `app/db/models.py` - All model definitions

7. Debugging Direction
   - Where to check model relationships
   - How to inspect database state

**Code References**:
- `app/db/models.py` - All model definitions
- `app/db/base.py` - SQLAlchemy base configuration
- `app/db/session.py` - Database session management


### Component 5: Character System Documentation

**File**: `docs/05-character-system.md`

**Purpose**: Explain character extraction, normalization, and the Actor/variant system for consistency.

**Content Structure**:

1. Character Extraction
   - LLM-based extraction from story text
   - Identifies names, roles, relationships
   - Fallback to heuristic NER

2. Character Normalization
   - Adds visual details (hair, face, build, outfit)
   - Creates identity_line for prompts
   - Applies Korean manhwa aesthetics

3. Canonical Codes
   - Sequential assignment (CHAR_A, CHAR_B, ...)
   - Persists across stories
   - Deduplication by name

4. Actor System
   - Global character library (project_id = NULL)
   - Reusable across stories
   - Approval workflow

5. Character Variants
   - Types: base, outfit_change, mood_change
   - Story-scoped vs global
   - Active variant selection

6. Reference Images
   - Types: face, full_body
   - Used for consistency in rendering

7. Key Files
   - `app/graphs/nodes/planning/visual_plan.py` - Extraction/normalization
   - `app/graphs/story_build.py` - Deduplication logic
   - `app/services/casting.py` - Variant management

8. Debugging Direction
   - Check Character table for canonical_code assignments
   - Review identity_line in character records
   - Inspect CharacterVariant for active variants

**Code References**:
- `app/graphs/nodes/planning/visual_plan.py` - Character extraction and normalization
- `app/graphs/story_build.py` - persist_story_bundle with deduplication
- `app/services/casting.py` - Character variant management
- `app/services/variant_suggestions.py` - AI variant suggestions
- `app/api/v1/characters.py` - Character CRUD endpoints
- `app/api/v1/character_variants.py` - Variant management endpoints


### Component 6: Artifact System Documentation

**File**: `docs/06-artifact-system.md`

**Purpose**: Explain how intermediate outputs are versioned, stored, and enable resumable workflows.

**Content Structure**:

1. Artifact Concept
   - Versioned intermediate outputs
   - Enable resumability and audit trail
   - Scene-scoped

2. Artifact Types (bullet list with purpose)
   - scene_intent, panel_plan, panel_plan_normalized
   - layout_template, panel_semantics
   - render_spec, render_result
   - qc_report, blind_test_report
   - dialogue_suggestions, visual_plan

3. Versioning
   - Auto-incrementing per (scene_id, type)
   - Parent-child lineage via parent_id
   - Retry logic for conflicts

4. ArtifactService API
   - create_artifact(), get_artifact()
   - get_latest_artifact(), list_artifacts()

5. Resumable Workflows
   - Graphs check for existing artifacts
   - Planning lock prevents regeneration
   - Manual editing supported

6. Key Files
   - `app/services/artifacts.py` - Service implementation
   - `app/db/models.py` - Artifact model

7. Debugging Direction
   - Check artifacts table for scene outputs
   - Review artifact.payload for node results
   - Inspect version history for changes

**Code References**:
- `app/services/artifacts.py` - ArtifactService implementation
- `app/db/models.py` - Artifact model definition
- `app/graphs/nodes/utils.py` - Artifact type constants
- `app/api/v1/artifacts.py` - Artifact retrieval endpoints


### Component 7: Configuration Files Documentation

**File**: `docs/07-configuration-files.md`

**Purpose**: Document all JSON configuration files and their structure.

**Content Structure**:

1. Configuration Files Overview (bullet list)
   - panel_grammar_library_v1.json: Valid shot types
   - layout_templates_9x16_v1.json: Panel geometry
   - qc_rules_v1.json: Quality thresholds
   - genre_guidelines_v1.json: Genre-specific styles
   - image_styles.json: Style presets

2. Panel Grammar Library
   - Valid grammar IDs (establishing, dialogue_medium, emotion_closeup, action, reaction, object_focus, reveal, impact_silence)
   - Used in panel plan validation

3. Layout Templates
   - 9:16 vertical format
   - Template structure: {x, y, w, h} normalized coordinates
   - Selection matches panel count

4. QC Rules
   - Thresholds: closeup_ratio_max, dialogue_ratio_max
   - Repeated framing limits
   - Environment requirements

5. Configuration Loading
   - Hot-reload via config watcher
   - Caching strategy

6. Key Files
   - `app/config/*.json` - All configs
   - `app/config/loaders.py` - Loading logic
   - `app/services/config_watcher.py` - Hot-reload

7. Debugging Direction
   - Check config files for rule definitions
   - Review QC failures against qc_rules.json
   - Inspect layout selection logic

**Code References**:
- `app/config/*.json` - All configuration files
- `app/config/loaders.py` - Configuration loading
- `app/services/config_watcher.py` - Hot-reload service
- `app/services/layout_selection.py` - Layout template matching


### Component 8: API Reference Documentation

**File**: `docs/08-api-reference.md`

**Purpose**: Document the REST API structure and endpoints.

**Content Structure**:

1. API Structure
   - Base: `/v1/`
   - Endpoint categories (bullet list)

2. Key Endpoint Groups
   - Projects, Stories, Scenes
   - Generation (blueprint, intent, plan, semantics, render)
   - Artifacts
   - Characters and Variants
   - Casting
   - Style Presets
   - Episodes and Exports

3. Generation Workflow Endpoints
   - Story blueprint (async)
   - Scene planning (intent → plan → layout → semantics)
   - Scene rendering
   - Full pipeline

4. Key Files
   - `app/api/v1/router.py` - Router config
   - `app/api/v1/*.py` - Endpoint modules

5. Debugging Direction
   - Check endpoint logs for request/response
   - Review API schemas for expected formats
   - Inspect async job status for long-running tasks

**Code References**:
- `app/api/v1/router.py` - API router configuration
- `app/api/v1/*.py` - Individual endpoint modules
- `app/api/v1/schemas.py` - Request/response schemas


### Component 9: Error Handling and Observability Documentation

**File**: `docs/09-error-handling-observability.md`

**Purpose**: Document error handling patterns, retry logic, and observability features.

**Content Structure**:

1. GeminiClient Error Handling
   - Custom exceptions (RateLimit, Timeout, ContentFilter, QuotaExceeded)
   - Retry logic with exponential backoff
   - Circuit breaker pattern
   - Model fallback mechanism

2. Request Correlation
   - x-request-id header
   - Propagated through logs, artifacts, API calls
   - Enables tracing across system

3. Telemetry and Tracing
   - trace_span decorator for graphs
   - OpenTelemetry integration
   - Span attributes (story_id, scene_id, style_id)

4. Progress Tracking
   - Story.progress JSON field
   - Updated by graphs during execution
   - API endpoint for checking progress

5. Audit Logging
   - AuditLog model tracks changes
   - Captures old/new values
   - Request ID correlation

6. Metrics Collection
   - Prometheus-compatible metrics
   - Counters, histograms, gauges
   - Key metrics: artifact_creation, graph_node_execution, gemini_api_calls

7. Key Files
   - `app/services/vertex_gemini.py` - GeminiClient
   - `app/core/request_context.py` - Request correlation
   - `app/core/telemetry.py` - Tracing
   - `app/core/metrics.py` - Metrics
   - `app/services/audit.py` - Audit logging

8. Debugging Direction
   - Check Story.progress for error messages
   - Trace request_id through logs
   - Review circuit breaker state
   - Inspect artifact payloads for failures
   - Check metrics for anomalies

**Code References**:
- `app/services/vertex_gemini.py` - GeminiClient with error handling
- `app/core/request_context.py` - Request correlation
- `app/core/telemetry.py` - Tracing infrastructure
- `app/core/metrics.py` - Metrics collection
- `app/core/logging.py` - Logging configuration
- `app/services/audit.py` - Audit logging


### Component 10: SKILLS.md Quick Reference Guide

**File**: `SKILLS.md` (root level)

**Purpose**: Provide a quick reference guide for AI agents and developers working on the codebase.

**Content Structure**:

1. Quick System Overview (3-4 sentences)
   - What the system does
   - Three-tier architecture
   - Key technologies

2. Key File Locations (directory tree with brief descriptions)

3. Common Patterns (code snippets)
   - Adding a LangGraph node
   - Adding an API endpoint
   - Adding a prompt template
   - Adding an artifact type

4. Development Workflow
   - Start backend/frontend
   - Run tests
   - Create migrations

5. Debugging Quick Reference
   - Where to check for common issues
   - Key fields to inspect
   - Useful tools and commands

6. Key Concepts Cheat Sheet (bullet list with one-line definitions)

**Note**: SKILLS.md should be concise and scannable, providing quick answers without deep explanations.

**Code References**:
- All files mentioned in sections above
- `docs/` - Comprehensive documentation
- `tests/` - Test examples


## Data Models

### Documentation File Structure

Each documentation file will follow a concise, high-level structure:

```markdown
# [Title]

## Overview
Brief 2-3 sentence introduction

## [Main Concept 1]
High-level explanation with key points

## [Main Concept 2]
High-level explanation with key points

## Key Files
- `path/to/file.py` - Brief description
- `path/to/other.py` - Brief description

## Debugging Direction
Where to look when things go wrong (not how to fix)

## See Also
- Related documentation files
```

### Content Guidelines

1. **Keep It High-Level**
   - Focus on concepts, not implementation details
   - Explain "what" and "why", not "how" (code shows "how")
   - Use bullet points for clarity
   - Avoid long paragraphs

2. **Provide Direction, Not Solutions**
   - Point to where to investigate issues
   - List relevant files and tools
   - Describe what to check, not what to change
   - Example: "Check Story.progress field for error messages" not "Set Story.progress to {...}"

3. **Minimal Code Examples**
   - Only include code when it clarifies a concept
   - Keep examples short (5-10 lines max)
   - Focus on structure/pattern, not full implementation
   - Always include file path reference

### Mermaid Diagram Standards

All diagrams will use Mermaid syntax for consistency and maintainability:

1. **Workflow Diagrams**: Use `graph TD` (top-down) or `graph LR` (left-right)
2. **Entity Relationship Diagrams**: Use `erDiagram`
3. **Sequence Diagrams**: Use `sequenceDiagram` for API flows
4. **State Diagrams**: Use `stateDiagram-v2` for state machines

### Code Example Format

All code examples will include:
- Language identifier for syntax highlighting
- File path comment at the top
- Inline comments explaining key concepts
- Ellipsis (...) for omitted code

Example:
```python
# File: app/graphs/nodes/planning.py

def run_scene_intent_extractor(
    db: Session,
    scene_id: uuid.UUID,
    genre: str | None = None,
    gemini: GeminiClient | None = None,
) -> Artifact:
    """Extract narrative intent from scene text."""
    # ... implementation details
```

### Cross-Reference System

Documentation will use consistent cross-references:
- Internal links: `[See Character System](05-character-system.md)`
- Code references: `` `app/db/models.py` ``
- API references: `` `POST /v1/scenes/{scene_id}/generate/panel-plan` ``


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After reviewing all acceptance criteria, the vast majority are about documentation content and completeness, which cannot be automatically tested through property-based testing. The few testable criteria are specific examples (checking that certain diagrams exist in the documentation).

The nature of this project is documentation creation, which is inherently a manual, human-reviewed process. Automated testing would focus on:
1. Documentation file existence
2. Markdown syntax validity
3. Mermaid diagram syntax validity
4. Link integrity (internal and code references)

However, these are better suited for linting tools and CI checks rather than property-based tests.

### Testable Properties

Since this is a documentation project, traditional property-based testing is not applicable. Instead, we can define validation checks:

**Validation Check 1: Documentation File Existence**
*For all* required documentation files in the specification, the file should exist in the /docs directory.
**Validates: Requirements 1-11 (file creation)**

**Validation Check 2: Mermaid Diagram Syntax**
*For all* Mermaid code blocks in documentation files, the syntax should be valid and parseable.
**Validates: Requirements 1.2, 2.4, 4.2**

**Validation Check 3: Code Reference Validity**
*For all* code file references in documentation (e.g., `app/db/models.py`), the referenced file should exist in the codebase.
**Validates: Requirements 11.4**

**Validation Check 4: Internal Link Integrity**
*For all* internal documentation links (e.g., `[See Character System](05-character-system.md)`), the target file should exist.
**Validates: Requirements 11.5**

Note: These are validation checks rather than property-based tests, as they verify documentation completeness and correctness rather than testing algorithmic properties.


## Error Handling

### Documentation Creation Errors

1. **Missing Source Information**
   - **Issue**: Required information not found in codebase
   - **Handling**: Document what exists, note gaps, suggest investigation
   - **Example**: If a feature is referenced but implementation is unclear

2. **Outdated Code References**
   - **Issue**: Code has changed since documentation was written
   - **Handling**: Verify all code references against current codebase
   - **Prevention**: Include file paths and line numbers where helpful

3. **Inconsistent Terminology**
   - **Issue**: Same concept called different names
   - **Handling**: Use glossary from requirements, maintain consistency
   - **Prevention**: Define terms in glossary section

4. **Diagram Complexity**
   - **Issue**: Mermaid diagrams too complex or unclear
   - **Handling**: Break into multiple simpler diagrams
   - **Prevention**: Focus each diagram on one concept

### Documentation Maintenance

1. **Code Changes**
   - Documentation should be updated when code changes
   - Use TODO comments in code to flag documentation updates needed
   - Regular documentation review cycles

2. **Version Tracking**
   - Documentation reflects codebase as of January 2026
   - Future updates should note version/date
   - Consider adding "Last Updated" timestamps

3. **Feedback Integration**
   - Collect feedback from developers using documentation
   - Track common questions and add clarifications
   - Maintain changelog of documentation updates


## Testing Strategy

### Documentation Quality Assurance

Since this is a documentation project, testing focuses on validation and quality checks rather than traditional unit or property-based testing.

#### Manual Review Process

1. **Technical Accuracy Review**
   - Verify all code examples compile/run
   - Check all file paths exist
   - Validate API endpoint descriptions against actual implementation
   - Confirm database model descriptions match schema

2. **Completeness Review**
   - Ensure all requirements are addressed
   - Check that all major system components are documented
   - Verify all configuration files are explained
   - Confirm all API endpoints are listed

3. **Clarity Review**
   - Read documentation as if unfamiliar with codebase
   - Check that explanations are clear and logical
   - Verify diagrams are understandable
   - Ensure examples are helpful

#### Automated Validation Checks

While not property-based tests, these automated checks ensure documentation quality:

1. **Markdown Linting**
   - Tool: `markdownlint` or similar
   - Checks: Consistent formatting, heading hierarchy, list formatting
   - Run: As part of CI/CD pipeline

2. **Link Checking**
   - Tool: `markdown-link-check` or similar
   - Checks: Internal links, code file references
   - Run: Before committing documentation

3. **Mermaid Diagram Validation**
   - Tool: `mermaid-cli` or similar
   - Checks: Syntax validity, renderability
   - Run: As part of CI/CD pipeline

4. **Code Reference Validation**
   - Custom script to extract file paths from documentation
   - Verify each referenced file exists in codebase
   - Report missing or moved files

#### Documentation Testing Workflow

```bash
# 1. Lint markdown files
markdownlint docs/**/*.md

# 2. Check internal links
markdown-link-check docs/**/*.md

# 3. Validate Mermaid diagrams
mmdc -i docs/**/*.md --validate

# 4. Verify code references
python scripts/validate_doc_references.py
```

#### Acceptance Criteria Validation

For each requirement, manual verification:

- **Requirement 1**: Review 01-application-workflow.md for completeness
- **Requirement 2**: Review 02-langgraph-architecture.md, verify all graphs documented
- **Requirement 3**: Review 03-prompt-system.md, verify all prompts explained
- **Requirement 4**: Review 04-database-models.md, verify all models documented
- **Requirement 5**: Review 05-character-system.md, verify all character features explained
- **Requirement 6**: Review 06-artifact-system.md, verify all artifact types documented
- **Requirement 7**: Review 07-configuration-files.md, verify all configs explained
- **Requirement 8**: Review SKILLS.md, verify all quick reference sections present
- **Requirement 9**: Review 08-api-reference.md, verify all endpoints listed
- **Requirement 10**: Review 09-error-handling-observability.md, verify all patterns documented
- **Requirement 11**: Verify all documentation uses current codebase, includes file paths

#### Documentation Maintenance Testing

1. **Quarterly Review**
   - Review documentation against current codebase
   - Update any outdated information
   - Add documentation for new features

2. **New Feature Documentation**
   - When adding new features, update relevant documentation files
   - Add new sections as needed
   - Update SKILLS.md with new patterns

3. **Feedback Loop**
   - Track documentation issues/questions
   - Prioritize updates based on user feedback
   - Measure documentation effectiveness (time to onboard new developers)

### Success Metrics

Documentation quality can be measured by:
1. **Onboarding Time**: How quickly new developers become productive
2. **Question Frequency**: Reduction in repeated questions about system
3. **Code Confidence**: Developer confidence when making changes
4. **Reference Usage**: How often documentation is consulted
5. **Accuracy**: Number of documentation bugs/corrections needed

