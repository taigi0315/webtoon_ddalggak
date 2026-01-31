# ssuljaengi_v4 Documentation

Welcome to the comprehensive documentation for the ssuljaengi_v4 webtoon generation system. This documentation provides a high-level overview of the system architecture, key components, and debugging guidance.

## How to Use This Documentation

This documentation is designed to be **concise and actionable**:

- **High-level focus**: Explains concepts and architecture, not implementation details
- **Debugging direction**: Points you to where to investigate issues, not how to fix them
- **File references**: Links to actual code files for detailed implementation
- **Visual clarity**: Uses Mermaid diagrams to illustrate complex concepts

**For AI agents and developers**: Start with [SKILLS.md](../SKILLS.md) for a quick reference guide, then dive into specific topics as needed.

**For new developers**: Read the documentation in order (01 → 09) to build a complete mental model of the system.

**For debugging**: Jump directly to the relevant section and check the "Debugging Direction" section for where to investigate.

## Documentation Structure

### Core System Documentation

1. **[Application Workflow](01-application-workflow.md)**
   - End-to-end system overview
   - Three-tier processing architecture (episode, scene, render)
   - Artifacts and workflow resumability
   - Synchronous vs asynchronous processing

2. **[LangGraph Architecture](02-langgraph-architecture.md)**
   - StoryBuildGraph: Episode-level processing
   - ScenePlanningGraph: Panel planning workflow
   - SceneRenderGraph: Image generation pipeline
   - State schemas and node responsibilities

3. **[Prompt System](03-prompt-system.md)**
   - Prompt template structure and loading
   - Key prompt templates and their purposes
   - Character style mapping
   - Visual prompt formula for image generation

4. **[Database Models](04-database-models.md)**
   - Complete schema documentation
   - Entity relationships and hierarchy
   - Character, artifact, and style models
   - Data model debugging guidance

5. **[Character System](05-character-system.md)**
   - Character extraction and normalization
   - Canonical codes and Actor system
   - Character variants for consistency
   - Reference images and identity lines

6. **[Artifact System](06-artifact-system.md)**
   - Versioned intermediate outputs
   - Artifact types and purposes
   - Resumable workflow patterns
   - ArtifactService API

7. **[Configuration Files](07-configuration-files.md)**
   - JSON configuration reference
   - Panel grammar library
   - Layout templates and QC rules
   - Genre guidelines and style presets

8. **[API Reference](08-api-reference.md)**
   - REST API structure and versioning
   - Endpoint categories and workflows
   - Generation pipeline endpoints
   - Artifact and character management

9. **[Error Handling & Observability](09-error-handling-observability.md)**
   - GeminiClient error handling and retries
   - Request correlation and tracing
   - Progress tracking and audit logging
   - Metrics collection and monitoring

### Quick Reference

- **[SKILLS.md](../SKILLS.md)** - Quick reference guide for developers and AI agents
  - System overview and key concepts
  - File locations and directory structure
  - Common patterns and code snippets
  - Development workflow and debugging tips

## Legacy Documentation

The following legacy documentation files are available but may be outdated:

- [AGENTS.md](AGENTS.md) - Agent system documentation
- [api.md](api.md) - API documentation
- [langgraph_architecture.md](langgraph_architecture.md) - LangGraph architecture
- [LANGGRAPH_SYSTEM_DESIGN.md](LANGGRAPH_SYSTEM_DESIGN.md) - System design
- [observability.md](observability.md) - Observability patterns
- [project_workflow.md](project_workflow.md) - Project workflow

**Note**: The numbered documentation files (01-09) above represent the current, accurate documentation as of January 2026. Legacy files are kept for reference but may contain outdated information.

## Key Concepts Cheat Sheet

- **LangGraph**: State machine framework for orchestrating multi-step workflows
- **Artifact**: Versioned intermediate output stored in the database (e.g., panel_plan, render_spec)
- **Node**: A discrete processing step within a LangGraph workflow
- **Scene**: A single narrative unit converted into one or more webtoon panels
- **Panel**: An individual frame/image in the webtoon layout
- **Webtoon Script**: A structured visual translation of the story with beats and SFX
- **Character Variant**: A specific visual representation of a character (outfit, style, mood)
- **Actor System**: Global character library allowing character reuse across stories
- **Grammar ID**: Predefined shot type identifier (establishing, dialogue_medium, emotion_closeup, etc.)
- **QC Rules**: Quality control validation rules applied to panel plans
- **Style Preset**: Configuration for story or image generation styles
- **Gemini Client**: Service wrapper for Google's Vertex AI Gemini API

## Getting Help

1. **Start with the relevant documentation section** - Use the structure above to find the right topic
2. **Check the "Debugging Direction" sections** - Each doc file has guidance on where to investigate issues
3. **Review SKILLS.md** - Quick patterns and common tasks
4. **Inspect the code** - Documentation points to specific files for implementation details
5. **Check artifacts and logs** - Most debugging starts with inspecting artifact payloads and request correlation IDs

## Contributing to Documentation

When updating documentation, follow the established standards and templates:

### Documentation Standards

- **[DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md)** - Quick reference for all standards
- **[TEMPLATE.md](TEMPLATE.md)** - Standard document structure and guidelines
- **[CODE_EXAMPLES_GUIDE.md](CODE_EXAMPLES_GUIDE.md)** - Code example formatting standards
- **[CROSS_REFERENCE_GUIDE.md](CROSS_REFERENCE_GUIDE.md)** - Cross-reference conventions

### Key Principles

1. **Keep it concise** - Focus on concepts, not implementation details
2. **Provide direction, not solutions** - Point to where to investigate, not how to fix
3. **Update file references** - Ensure all code file paths are current
4. **Use Mermaid diagrams** - Visual clarity for complex concepts
5. **Maintain consistency** - Follow the established structure and terminology

### Quick Start

1. Copy structure from [TEMPLATE.md](TEMPLATE.md)
2. Follow code example format from [CODE_EXAMPLES_GUIDE.md](CODE_EXAMPLES_GUIDE.md)
3. Use reference conventions from [CROSS_REFERENCE_GUIDE.md](CROSS_REFERENCE_GUIDE.md)
4. Validate against [DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md)

---

**Last Updated**: January 2026  
**Documentation Version**: 1.0
