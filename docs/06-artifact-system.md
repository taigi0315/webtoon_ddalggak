# Artifact System

## Overview

Artifacts are versioned intermediate outputs stored in the database that enable resumable workflows and provide an audit trail. Each artifact represents the output of a specific processing node (e.g., panel plan, render spec) and is automatically versioned to track changes over time.

## Artifact Concept

Artifacts serve three key purposes:

- **Resumability**: Graphs check for existing artifacts before regenerating, allowing workflows to resume from any point
- **Audit Trail**: Version history tracks all changes with parent-child lineage via `parent_id`
- **Manual Editing**: Users can edit artifacts (e.g., panel plans) and lock them to prevent regeneration

Each artifact is:
- **Scene-scoped**: Tied to a specific `scene_id`
- **Type-specific**: Identified by a `type` string (e.g., `scene_intent`, `panel_plan`)
- **Auto-versioned**: Version increments automatically per `(scene_id, type)` combination
- **Payload-based**: Stores JSON data with node output and metadata

## Artifact Types

The system defines 11 artifact types representing different pipeline stages:

- **`scene_intent`**: Narrative analysis extracting mood, pacing, and key beats from scene text
- **`panel_plan`**: Panel breakdown with grammar IDs, weights, and must-show elements
- **`panel_plan_normalized`**: Validated and normalized panel plan with QC checks applied
- **`layout_template`**: Selected layout template with panel geometry (x, y, w, h coordinates)
- **`panel_semantics`**: Visual descriptions for each panel with character, environment, and dialogue details
- **`render_spec`**: Complete image generation prompt with style, characters, and reference images
- **`render_result`**: Generated image URL, metadata, and generation parameters
- **`qc_report`**: Quality control validation results with issues and metrics
- **`blind_test_report`**: Blind reader evaluation of narrative clarity
- **`dialogue_suggestions`**: Extracted dialogue lines with speaker and emotion hints
- **`visual_plan`**: Character extraction and normalization with visual details

## Versioning

Artifacts use automatic versioning with conflict resolution:

- **Version Numbering**: Auto-increments starting at 1 for each `(scene_id, type)` pair
- **Parent Lineage**: New versions automatically link to previous version via `parent_id`
- **Conflict Retry**: Up to 3 retry attempts on version conflicts (race conditions)
- **Request Tracking**: Each artifact includes `request_id` for correlation across system

Example version history:
```
scene_intent v1 (parent_id: null)
  └─ scene_intent v2 (parent_id: v1.artifact_id)
      └─ scene_intent v3 (parent_id: v2.artifact_id)
```

## ArtifactService API

The `ArtifactService` provides five core methods:

- **`create_artifact(scene_id, type, payload, parent_id=None)`**: Create new versioned artifact with retry logic
- **`get_artifact(artifact_id)`**: Retrieve specific artifact by ID
- **`get_latest_artifact(scene_id, type)`**: Get most recent version for scene and type
- **`list_artifacts(scene_id, type=None)`**: List all artifacts for scene, optionally filtered by type
- **`get_next_version(scene_id, type)`**: Calculate next version number for scene and type

All methods operate within a database session and handle versioning automatically.

## Resumable Workflows

Graphs use artifacts to enable resumable execution:

1. **Check for Existing**: Node checks for latest artifact before processing
2. **Skip if Locked**: If `planning_locked=True` on scene, skip regeneration
3. **Use Existing**: Return existing artifact if found and valid
4. **Generate New**: Create new versioned artifact only if needed

Example pattern:
```python
# File: app/graphs/nodes/planning/scene_intent.py

def run_scene_intent_extractor(db: Session, scene_id: uuid.UUID) -> Artifact:
    """Extract narrative intent from scene text."""
    svc = ArtifactService(db)
    
    # Check for existing artifact
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_SCENE_INTENT)
    if existing and scene.planning_locked:
        return existing  # Skip regeneration
    
    # Generate new version
    payload = extract_intent(scene.source_text)
    return svc.create_artifact(scene_id, ARTIFACT_SCENE_INTENT, payload)
```

This pattern allows:
- **Partial regeneration**: Regenerate only specific artifacts
- **Manual editing**: Users can edit and lock artifacts
- **Debugging**: Inspect intermediate outputs at any stage

## Key Files

- `app/services/artifacts.py` - ArtifactService implementation with versioning logic
- `app/db/models.py` - Artifact model definition with parent-child relationship
- `app/graphs/nodes/constants.py` - Artifact type constants (ARTIFACT_*)
- `app/api/v1/artifacts.py` - Artifact retrieval endpoints
- `app/graphs/nodes/utils.py` - Artifact type constant imports and usage

## Debugging Direction

**When things go wrong, check:**

- **Missing artifacts**: Query `artifacts` table for `scene_id` and `type` to verify creation
- **Version conflicts**: Check logs for `IntegrityError` indicating retry exhaustion
- **Stale data**: Verify `planning_locked` flag on scene isn't preventing regeneration
- **Payload errors**: Inspect `artifact.payload` JSON for malformed or missing fields
- **Lineage issues**: Follow `parent_id` chain to trace artifact evolution

**Useful queries:**

```sql
-- List all artifacts for a scene
SELECT type, version, created_at FROM artifacts 
WHERE scene_id = 'uuid-here' 
ORDER BY type, version;

-- Get latest artifact of each type
SELECT DISTINCT ON (type) type, version, artifact_id, created_at
FROM artifacts 
WHERE scene_id = 'uuid-here'
ORDER BY type, version DESC;

-- Trace artifact lineage
WITH RECURSIVE lineage AS (
  SELECT artifact_id, parent_id, version, type
  FROM artifacts WHERE artifact_id = 'uuid-here'
  UNION ALL
  SELECT a.artifact_id, a.parent_id, a.version, a.type
  FROM artifacts a JOIN lineage l ON a.artifact_id = l.parent_id
)
SELECT * FROM lineage ORDER BY version;
```

**API endpoints for inspection:**

- `GET /v1/scenes/{scene_id}/artifacts` - List all artifacts for scene
- `GET /v1/scenes/{scene_id}/artifacts?type=panel_plan` - Filter by type
- `GET /v1/artifacts/{artifact_id}` - Get specific artifact with payload

## See Also

- [LangGraph Architecture](02-langgraph-architecture.md) - How graphs use artifacts
- [Database Models](04-database-models.md) - Artifact model schema
- [Error Handling & Observability](09-error-handling-observability.md) - Request correlation with artifacts
- [SKILLS.md](../SKILLS.md) - Quick reference for adding new artifact types
