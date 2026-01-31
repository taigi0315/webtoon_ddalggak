# SKILLS.md - Quick Reference Guide

## System Overview

The ssuljaengi_v4 system transforms story text into fully rendered webtoon panels through a three-tier LangGraph-based pipeline. The system processes stories at the episode level (extracting characters and scenes), plans each scene (breaking into panels with visual descriptions), and renders final images with layout and styling. All intermediate outputs are versioned as artifacts in the database, enabling resumable workflows and manual editing.

## Key File Locations

```
ssuljaengi_v4/
├── app/
│   ├── api/v1/                    # REST API endpoints
│   │   ├── router.py              # Main API router
│   │   ├── stories.py             # Story endpoints
│   │   ├── scenes.py              # Scene endpoints
│   │   ├── generation.py          # Generation workflow endpoints
│   │   ├── characters.py          # Character CRUD
│   │   ├── character_variants.py  # Character variant management
│   │   ├── artifacts.py           # Artifact retrieval
│   │   └── schemas.py             # Request/response schemas
│   ├── config/                    # JSON configuration files
│   │   ├── panel_grammar_library_v1.json    # Valid shot types
│   │   ├── layout_templates_9x16_v1.json    # Panel geometry
│   │   ├── qc_rules_v1.json                 # Quality control rules
│   │   ├── genre_guidelines_v1.json         # Genre-specific styles
│   │   ├── image_styles.json                # Image style presets
│   │   └── loaders.py                       # Config loading logic
│   ├── core/                      # Core utilities
│   │   ├── settings.py            # Environment configuration
│   │   ├── telemetry.py           # OpenTelemetry tracing
│   │   ├── metrics.py             # Prometheus metrics
│   │   ├── logging.py             # Structured logging
│   │   └── request_context.py     # Request correlation
│   ├── db/                        # Database layer
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── base.py                # Database base config
│   │   └── session.py             # Session management
│   ├── graphs/                    # LangGraph workflows
│   │   ├── story_build.py         # Episode-level workflow
│   │   ├── pipeline.py            # Scene planning + rendering
│   │   ├── nodes/                 # Node implementations
│   │       ├── planning/          # Planning nodes
│   │       │   ├── character.py   # Character extraction
│   │       │   ├── script_writer.py # Webtoon script writing
│   │       │   └── ...
│   │       ├── rendering/         # Rendering nodes
│   │       ├── prompts/           # Prompt compilation
│   │       └── constants.py       # Artifact type constants
│   ├── prompts/                   # Prompt templates
│   │   ├── v1/                    # Versioned directory structure
│   │   │   ├── story_build/       # Script/Optimization prompts
│   │   │   ├── scene_planning/    # Scene intent/panel prompts
│   │   │   └── shared/            # Common constraints/styles
│   │   └── loader.py              # Jinja2 compilation
│   ├── services/                  # Business logic
│   │   ├── vertex_gemini.py       # Gemini API client
│   │   ├── artifacts.py           # Artifact versioning
│   │   ├── casting.py             # Actor system
│   │   ├── audit.py               # Audit logging
│   │   └── config_watcher.py      # Hot-reload configs
│   └── main.py                    # FastAPI app entry
├── tests/                         # Test suite
├── docs/                          # Comprehensive documentation
│   ├── 01-application-workflow.md
│   ├── 02-langgraph-architecture.md
│   ├── 03-prompt-system.md
│   ├── 04-database-models.md
│   ├── 05-character-system.md
│   ├── 06-artifact-system.md
│   ├── 07-configuration-files.md
│   ├── 08-api-reference.md
│   └── 09-error-handling-observability.md
├── frontend/                      # Next.js frontend
├── scripts/                       # Utility scripts
├── storage/media/                 # Local file storage
├── alembic.ini                    # Database migrations config
├── Makefile                       # Development commands
└── pyproject.toml                 # Python dependencies
```

## Common Patterns

### Adding a New LangGraph Node

```python
# File: app/graphs/nodes/planning/my_node.py

from sqlalchemy.orm import Session
import uuid
from app.db.models import Scene, Artifact
from app.services.artifacts import ArtifactService
from app.graphs.nodes.constants import ARTIFACT_MY_TYPE

def run_my_node(
    db: Session,
    scene_id: uuid.UUID,
    **kwargs
) -> Artifact:
    """Process scene and create artifact."""
    # 1. Load scene
    scene = db.query(Scene).filter(Scene.scene_id == scene_id).first()

    # 2. Check for existing artifact (resumability)
    svc = ArtifactService(db)
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_MY_TYPE)
    if existing and scene.planning_locked:
        return existing

    # 3. Process data
    result = process_scene(scene.source_text)

    # 4. Create versioned artifact
    payload = {"result": result, "metadata": {...}}
    return svc.create_artifact(scene_id, ARTIFACT_MY_TYPE, payload)
```

### Adding a New API Endpoint

```python
# File: app/api/v1/my_resource.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.v1.schemas import MyRequest, MyResponse

router = APIRouter()

@router.post("/my-resource/{resource_id}/action", response_model=MyResponse)
def perform_action(
    resource_id: uuid.UUID,
    request: MyRequest,
    db: Session = Depends(get_db)
):
    """Perform action on resource."""
    # 1. Validate input
    # 2. Load resource from database
    # 3. Perform business logic
    # 4. Return response
    return MyResponse(...)

# Register in app/api/v1/router.py:
# from app.api.v1 import my_resource
# api_router.include_router(my_resource.router, prefix="/my-resource", tags=["my-resource"])
```

### Adding a New Prompt Template

```yaml
# File: app/prompts/prompts.yaml

prompt_my_template: |
  {{ system_prompt_json }}

  {{ global_constraints }}

  # Task
  Process the following scene and extract key information.

  # Scene Text
  {{ scene_text }}

  # Characters
  {{ char_list }}

  # Output Format
  Return JSON with the following structure:
  {
    "result": "...",
    "confidence": 0.0-1.0
  }
```

```python
# File: app/graphs/nodes/prompts/builders.py

from app.prompts.loader import render_prompt

def compile_my_prompt(scene_text: str, characters: list) -> str:
    """Compile prompt with runtime context."""
    return render_prompt(
        "prompt_my_template",
        scene_text=scene_text,
        char_list=", ".join([c.name for c in characters])
    )
```

### Adding a New Artifact Type

```python
# File: app/graphs/nodes/constants.py

# Add constant
ARTIFACT_MY_TYPE = "my_type"

# File: app/services/artifacts.py (no changes needed - versioning is automatic)

# File: app/graphs/nodes/my_node.py

from app.graphs.nodes.constants import ARTIFACT_MY_TYPE
from app.services.artifacts import ArtifactService

def create_my_artifact(db: Session, scene_id: uuid.UUID, data: dict):
    svc = ArtifactService(db)
    payload = {"data": data, "version": "1.0"}
    return svc.create_artifact(scene_id, ARTIFACT_MY_TYPE, payload)
```

## Development Workflow

### Start Backend

```bash
# Start database (Docker)
make db-up

# Run migrations
make db-migrate

# Start backend server (with hot-reload)
make dev-back

# Or with OpenTelemetry tracing (requires Docker)
make dev-arize
```

### Start Frontend

```bash
# Install dependencies (first time only)
make install-front

# Start Next.js dev server
make dev-front
```

### Run Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_my_feature.py -v

# Run with coverage
pytest --cov=app tests/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add my_table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Clean cache files
make clean
```

## Debugging Quick Reference

### Story Generation Issues

**Check progress:**

```sql
SELECT generation_status, progress, generation_error
FROM stories WHERE story_id = ?;
```

**Check artifacts:**

```sql
SELECT type, version, created_at
FROM artifacts WHERE scene_id = ?
ORDER BY type, version DESC;
```

**Check logs:**

```bash
grep "story_id.*<uuid>" logs/*.log
grep "request_id.*<uuid>" logs/*.log
```

### Scene Planning Issues

**Check planning lock:**

```sql
SELECT scene_id, planning_locked FROM scenes WHERE scene_id = ?;
```

**Check required artifacts:**

```sql
SELECT type, version FROM artifacts
WHERE scene_id = ? AND type IN (
  'scene_intent', 'panel_plan', 'panel_plan_normalized',
  'layout_template', 'panel_semantics'
);
```

### Character Consistency Issues

**Check canonical codes:**

```sql
SELECT canonical_code, name, role FROM characters
WHERE project_id = ? ORDER BY canonical_code;
```

**Check active variants:**

```sql
SELECT cv.variant_name, c.name
FROM character_variants cv
JOIN characters c ON cv.character_id = c.character_id
WHERE cv.story_id = ? AND cv.is_active_for_story = true;
```

### Gemini API Issues

**Check circuit breaker status:**

```python
from app.services.vertex_gemini import gemini_client
print(gemini_client.get_circuit_breaker_status())
```

**Check logs for errors:**

```bash
grep "gemini.generate" logs/*.log
grep "circuit breaker" logs/*.log
grep "rate_limit" logs/*.log
```

### API Endpoint Issues

**Check request/response:**

```bash
curl -v http://localhost:8000/v1/scenes/{scene_id}/status
```

**Check OpenAPI docs:**

```
http://localhost:8000/docs
```

**Check metrics:**

```bash
curl http://localhost:8000/metrics
```

## Key Concepts Cheat Sheet

- **Artifact** - Versioned intermediate output stored in database (e.g., panel_plan, render_spec)
- **Canonical Code** - Sequential character identifier (CHAR_A, CHAR_B, etc.) for consistency
- **Character Variant** - Appearance variation (outfit_change, mood_change) scoped to story or global
- **Actor** - Global character (project_id = NULL) reusable across projects
- **Grammar ID** - Shot type identifier (establishing, dialogue_medium, emotion_closeup, etc.)
- **Layout Template** - Panel geometry definition with normalized coordinates (x, y, w, h)
- **Planning Lock** - Flag preventing scene regeneration to preserve manual edits
- **Style Resolution** - Hierarchy: Scene override → Story default → "default"
- **Circuit Breaker** - Protection against cascading failures (opens after 5 consecutive errors)
- **Request ID** - Unique identifier (x-request-id) for tracing requests through system
- **Visual Plan** - Character extraction and scene importance ratings for episode-level planning
- **Blind Test** - Evaluation of narrative coherence by reconstructing story from panels only
- **Webtoon Script** - Structured visual beat-by-beat translation of the raw story
- **QC Rules** - Quality control thresholds (closeup_ratio_max, dialogue_ratio_max, etc.)
- **Episode Guardrails** - Layout diversity enforcement and hero single-panel requirements
- **Identity Line** - Compiled character description for prompts (e.g., "Alice: young adult female, long black hair")

## Testing Patterns

### Unit Tests

```python
# File: tests/test_my_feature.py

import pytest
from app.services.my_service import my_function

def test_my_function_basic():
    """Test basic functionality."""
    result = my_function("input")
    assert result == "expected"

def test_my_function_edge_case():
    """Test edge case handling."""
    result = my_function("")
    assert result is None
```

### Integration Tests

```python
# File: tests/test_my_integration.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_endpoint(db_session):
    """Test API endpoint with database."""
    response = client.post("/v1/my-resource", json={"key": "value"})
    assert response.status_code == 200
    assert response.json()["result"] == "expected"
```

### Graph Node Tests

```python
# File: tests/test_my_node.py

from app.graphs.nodes.planning.my_node import run_my_node
from app.db.models import Scene

def test_my_node(db_session):
    """Test graph node execution."""
    scene = Scene(source_text="Test scene")
    db_session.add(scene)
    db_session.commit()

    artifact = run_my_node(db_session, scene.scene_id)
    assert artifact.type == "my_type"
    assert artifact.payload["result"] is not None
```

## Extending the Character System

### Add Character Extraction Logic

```python
# File: app/graphs/nodes/planning/character.py

def extract_characters_with_custom_logic(story_text: str) -> list[dict]:
    """Extract characters using custom logic."""
    # 1. Use LLM extraction
    llm_characters = extract_via_llm(story_text)

    # 2. Apply custom filtering
    filtered = [c for c in llm_characters if meets_criteria(c)]

    # 3. Enrich with additional data
    enriched = [enrich_character(c) for c in filtered]

    return enriched
```

### Add Character Variant Type

```python
# File: app/db/models.py (add to CharacterVariant.variant_type enum)

# Add new variant type to enum
variant_type = Column(Enum(
    "base", "outfit_change", "mood_change", "style_change",
    "my_custom_type",  # Add here
    name="variant_type_enum"
))

# Create migration
# alembic revision --autogenerate -m "Add my_custom_type variant"
```

## Observability and Telemetry

### Add Custom Metrics

```python
# File: app/core/metrics.py

from prometheus_client import Counter, Histogram

my_counter = Counter(
    "ssuljaengi_my_events_total",
    "Total number of my events",
    ["event_type"]
)

my_histogram = Histogram(
    "ssuljaengi_my_duration_seconds",
    "Duration of my operation",
    ["operation"]
)

# Usage
my_counter.labels(event_type="success").inc()
with my_histogram.labels(operation="process").time():
    process_data()
```

### Add Custom Tracing

```python
# File: app/core/telemetry.py

from app.core.telemetry import trace_span

def my_function(scene_id: uuid.UUID):
    """Function with custom tracing."""
    with trace_span("my_operation", scene_id=str(scene_id)):
        # All operations within this block are traced
        result = process_scene(scene_id)
        return result
```

### Add Audit Logging

```python
# File: app/services/audit.py

from app.services.audit import log_audit_entry

def update_resource(db: Session, resource_id: uuid.UUID, new_data: dict):
    """Update resource with audit logging."""
    resource = db.query(Resource).get(resource_id)
    old_value = {"status": resource.status}

    resource.status = new_data["status"]
    db.commit()

    log_audit_entry(
        db=db,
        entity_type="resource",
        entity_id=resource_id,
        action="update",
        old_value=old_value,
        new_value={"status": new_data["status"]}
    )
```

## See Also

- **[docs/README.md](docs/README.md)** - Documentation index and navigation
- **[docs/01-application-workflow.md](docs/01-application-workflow.md)** - High-level system overview
- **[docs/02-langgraph-architecture.md](docs/02-langgraph-architecture.md)** - Detailed graph and node documentation
- **[docs/03-prompt-system.md](docs/03-prompt-system.md)** - Prompt templates and compilation
- **[docs/04-database-models.md](docs/04-database-models.md)** - Complete schema documentation
- **[docs/05-character-system.md](docs/05-character-system.md)** - Character extraction and variants
- **[docs/06-artifact-system.md](docs/06-artifact-system.md)** - Versioning and storage patterns
- **[docs/07-configuration-files.md](docs/07-configuration-files.md)** - JSON config reference
- **[docs/08-api-reference.md](docs/08-api-reference.md)** - Endpoint documentation
- **[docs/09-error-handling-observability.md](docs/09-error-handling-observability.md)** - Debugging and monitoring
