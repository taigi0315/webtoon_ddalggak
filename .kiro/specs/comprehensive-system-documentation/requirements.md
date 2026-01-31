# Requirements Document

## Introduction

This specification defines the requirements for creating comprehensive, accurate, and actionable documentation for the ssuljaengi_v4 webtoon generation system. The documentation will replace outdated materials in the /docs folder and provide a SKILLS.md reference guide for AI agents and developers working on the codebase.

## Glossary

- **System**: The ssuljaengi_v4 webtoon generation application
- **LangGraph**: The state machine framework used for orchestrating multi-step workflows
- **Artifact**: A versioned intermediate output stored in the database (e.g., panel_plan, render_spec)
- **Node**: A discrete processing step within a LangGraph workflow
- **Scene**: A single narrative unit that gets converted into one or more webtoon panels
- **Panel**: An individual frame/image in the webtoon layout
- **Character_Variant**: A specific visual representation of a character (outfit, style, mood)
- **Actor_System**: The global character library allowing character reuse across stories
- **Grammar_ID**: A predefined shot type identifier (establishing, dialogue_medium, emotion_closeup, etc.)
- **QC_Rules**: Quality control validation rules applied to panel plans
- **Style_Preset**: Configuration for story or image generation styles
- **Gemini_Client**: The service wrapper for Google's Vertex AI Gemini API

## Requirements

### Requirement 1: Application Workflow Documentation

**User Story:** As a developer, I want a high-level overview of the complete system workflow, so that I can understand how story input becomes final webtoon output.

#### Acceptance Criteria

1. THE System SHALL document the end-to-end workflow from story text input to final rendered webtoon
2. THE Documentation SHALL include a visual Mermaid diagram showing the major processing stages
3. THE Documentation SHALL explain the three main processing levels: episode-level, scene-level, and render-level
4. THE Documentation SHALL describe the role of artifacts in preserving intermediate state
5. THE Documentation SHALL explain how the system handles both synchronous and asynchronous processing

### Requirement 2: LangGraph Architecture Documentation

**User Story:** As a developer, I want detailed documentation of the three main graphs, so that I can understand and modify the processing pipeline.

#### Acceptance Criteria

1. THE Documentation SHALL describe the StoryBuildGraph with all nodes and their responsibilities
2. THE Documentation SHALL describe the ScenePlanningGraph with all nodes and their responsibilities
3. THE Documentation SHALL describe the SceneRenderGraph with all nodes and their responsibilities
4. THE Documentation SHALL include Mermaid diagrams for each graph showing node flow
5. THE Documentation SHALL explain the state schemas (StoryBuildState, PlanningState, RenderState, PipelineState)
6. THE Documentation SHALL document the planning_mode options (full vs characters_only)
7. THE Documentation SHALL explain the per-scene planning loop and episode-level guardrails
8. THE Documentation SHALL document the blind test evaluation methodology

### Requirement 3: Prompt System Documentation

**User Story:** As a developer, I want to understand how prompts are structured and used, so that I can modify or add new prompts effectively.

#### Acceptance Criteria

1. THE Documentation SHALL explain the prompt loading mechanism from prompts.yaml
2. THE Documentation SHALL document all major prompt templates and their purposes
3. THE Documentation SHALL explain the character_style_map structure for age/gender-based styling
4. THE Documentation SHALL document the visual_prompt_formula and its required elements
5. THE Documentation SHALL explain how prompts are compiled with runtime context (characters, scenes, styles)
6. THE Documentation SHALL document the JSON repair mechanism for malformed LLM outputs
7. THE Documentation SHALL provide examples of prompt usage in different nodes

### Requirement 4: Database Models Documentation

**User Story:** As a developer, I want complete documentation of all database models, so that I can understand data relationships and add new features.

#### Acceptance Criteria

1. THE Documentation SHALL document all database models with field descriptions
2. THE Documentation SHALL include an entity relationship diagram showing model connections
3. THE Documentation SHALL explain the Project → Story → Scene hierarchy
4. THE Documentation SHALL document the Character and StoryCharacter relationship models
5. THE Documentation SHALL explain the CharacterVariant system for story-scoped and global variants
6. THE Documentation SHALL document the Artifact model and versioning system
7. THE Documentation SHALL explain the StylePreset model and inheritance via parent_id
8. THE Documentation SHALL document the EnvironmentAnchor, DialogueLayer, and Layer models
9. THE Documentation SHALL explain the Episode and EpisodeScene models for multi-scene compositions

### Requirement 5: Character System Documentation

**User Story:** As a developer, I want to understand the character extraction, normalization, and variant system, so that I can maintain character consistency features.

#### Acceptance Criteria

1. THE Documentation SHALL explain the character extraction process from story text
2. THE Documentation SHALL document the character normalization process that adds visual details
3. THE Documentation SHALL explain the canonical_code assignment (CHAR_A, CHAR_B, etc.)
4. THE Documentation SHALL document the Actor system for global character reuse
5. THE Documentation SHALL explain CharacterVariant types (base, outfit_change, etc.)
6. THE Documentation SHALL document how variants are scoped (story-specific vs global)
7. THE Documentation SHALL explain the CharacterReferenceImage system
8. THE Documentation SHALL document how character identity_lines are used in prompts
9. THE Documentation SHALL explain the character deduplication logic in persist_story_bundle

### Requirement 6: Artifact System Documentation

**User Story:** As a developer, I want to understand how artifacts are versioned and stored, so that I can implement new artifact types or modify existing ones.

#### Acceptance Criteria

1. THE Documentation SHALL explain the artifact versioning mechanism
2. THE Documentation SHALL document all artifact types and their purposes
3. THE Documentation SHALL explain the parent_id relationship for artifact lineage
4. THE Documentation SHALL document the ArtifactService API methods
5. THE Documentation SHALL explain how artifacts enable resumable workflows
6. THE Documentation SHALL document the artifact creation retry logic for version conflicts
7. THE Documentation SHALL provide examples of artifact payloads for each type

### Requirement 7: Configuration Files Documentation

**User Story:** As a developer, I want to understand all JSON configuration files, so that I can modify system behavior without code changes.

#### Acceptance Criteria

1. THE Documentation SHALL document panel_grammar_library_v1.json and valid grammar IDs
2. THE Documentation SHALL document layout_templates_9x16_v1.json and template structure
3. THE Documentation SHALL document qc_rules_v1.json and quality control thresholds
4. THE Documentation SHALL document genre_guidelines_v1.json for genre-specific visual styles
5. THE Documentation SHALL document image_styles.json
6. THE Documentation SHALL explain how configuration files are loaded and watched for changes
7. THE Documentation SHALL document the layout selection rules and template matching logic

### Requirement 8: SKILLS.md Reference Guide

**User Story:** As an AI agent or new developer, I want a quick reference guide, so that I can quickly understand common patterns and file locations.

#### Acceptance Criteria

1. THE SKILLS.md SHALL provide a quick overview of the system architecture
2. THE SKILLS.md SHALL document key file locations and their purposes
3. THE SKILLS.md SHALL explain common coding patterns used in the codebase
4. THE SKILLS.md SHALL document how to add a new LangGraph node
5. THE SKILLS.md SHALL document how to add a new API endpoint
6. THE SKILLS.md SHALL document how to add a new prompt template
7. THE SKILLS.md SHALL document how to add a new artifact type
8. THE SKILLS.md SHALL explain the testing patterns and how to run tests
9. THE SKILLS.md SHALL document common debugging techniques
10. THE SKILLS.md SHALL provide examples of extending the character system
11. THE SKILLS.md SHALL document the observability and telemetry patterns

### Requirement 9: API Endpoints Documentation

**User Story:** As a developer, I want documentation of the API structure, so that I can understand and extend the REST API.

#### Acceptance Criteria

1. THE Documentation SHALL document the API versioning structure (/v1/)
2. THE Documentation SHALL list all major endpoint categories (projects, stories, scenes, characters, etc.)
3. THE Documentation SHALL explain the generation endpoints and their workflows
4. THE Documentation SHALL document the artifact retrieval endpoints
5. THE Documentation SHALL explain the casting and character variant endpoints
6. THE Documentation SHALL document the style preset management endpoints

### Requirement 10: Error Handling and Observability Documentation

**User Story:** As a developer, I want to understand error handling and observability, so that I can debug issues and monitor system health.

#### Acceptance Criteria

1. THE Documentation SHALL explain the GeminiClient error handling and retry logic
2. THE Documentation SHALL document the circuit breaker pattern for API calls
3. THE Documentation SHALL explain the model fallback mechanism
4. THE Documentation SHALL document the custom exception types (GeminiRateLimitError, etc.)
5. THE Documentation SHALL explain the request context and correlation ID system
6. THE Documentation SHALL document the telemetry and tracing patterns (trace_span)
7. THE Documentation SHALL explain the progress tracking mechanism in Story.progress
8. THE Documentation SHALL document the audit logging system
9. THE Documentation SHALL explain the metrics collection patterns

### Requirement 11: Documentation Accuracy and Maintenance

**User Story:** As a developer, I want documentation that reflects the current codebase, so that I can trust the information when making changes.

#### Acceptance Criteria

1. THE Documentation SHALL be based on the actual codebase as of January 2026
2. THE Documentation SHALL include code examples from real implementation files
3. THE Documentation SHALL use consistent terminology matching the codebase
4. THE Documentation SHALL include file paths for all referenced code
5. THE Documentation SHALL be structured with clear sections and navigation
6. THE Documentation SHALL use Mermaid diagrams for visual clarity where appropriate
7. THE Documentation SHALL be practical and actionable for developers
