# Error Handling and Observability

## Overview

The system implements comprehensive error handling, retry logic, and observability features to ensure reliability and debuggability. Key patterns include custom exception types for Gemini API errors, circuit breaker protection, request correlation via `x-request-id`, OpenTelemetry tracing, progress tracking in `Story.progress`, audit logging, and Prometheus metrics collection.

## GeminiClient Error Handling

**File**: `app/services/vertex_gemini.py`

The `GeminiClient` wraps Google's Vertex AI Gemini API with robust error handling and retry logic.

### Custom Exception Types

- **`GeminiError`** - Base exception for all Gemini-related errors
- **`GeminiRateLimitError`** - Rate limit exceeded (429 errors)
- **`GeminiContentFilterError`** - Content blocked by safety filters
- **`GeminiTimeoutError`** - Request timeout or deadline exceeded
- **`GeminiCircuitOpenError`** - Circuit breaker is open (too many failures)
- **`GeminiModelUnavailableError`** - Model is unavailable (503 errors)

All exceptions include `request_id` and `model` attributes for debugging.

### Retry Logic

**Exponential Backoff**: Retries with exponential backoff (0.8s, 1.6s, 3.2s, etc.)

**Rate Limit Backoff**: Special backoff for rate limits (10s, 30s, 180s, 600s)

**Max Retries**: Default 3 attempts (extended for rate limits)

**Retryable Errors**: Rate limits, timeouts, model unavailable

**Non-Retryable Errors**: Content filters, invalid requests

### Circuit Breaker Pattern

**Purpose**: Prevent cascading failures by temporarily blocking requests after repeated failures

**Thresholds**:

- `failure_threshold: 5` - Open circuit after 5 consecutive failures
- `recovery_timeout: 60s` - Wait 60 seconds before allowing test requests
- `half_open_success_threshold: 2` - Close circuit after 2 successful test requests

**States**:

- **Closed** - Normal operation, all requests allowed
- **Open** - Too many failures, all requests blocked
- **Half-Open** - Testing recovery, limited requests allowed

**Per-Operation**: Separate circuit breakers for `generate_text` and `generate_image`

**Management**:

- `get_circuit_breaker_status()` - Check circuit breaker state
- `reset_circuit_breaker(operation_type)` - Manually reset circuit breaker

### Model Fallback Mechanism

**Fallback Models**: Optional fallback models for text and image generation

**Trigger Conditions**: Model unavailable, rate limit, timeout

**Usage**: Automatically tries fallback model on primary model failure

**Configuration**:

- `fallback_text_model` - Fallback for text generation
- `fallback_image_model` - Fallback for image generation

### Error Classification

The client automatically classifies errors by type:

- **rate_limit** - RESOURCE_EXHAUSTED, 429 errors
- **content_filter** - SAFETY blocks, content filtering
- **timeout** - Timeout, deadline exceeded
- **model_unavailable** - Unavailable, 503 errors
- **invalid_request** - Invalid input, 400 errors
- **unknown** - Unclassified errors

## Request Correlation

**File**: `app/core/request_context.py`

Request correlation enables tracing a single request through the entire system using a unique `request_id`.

### Context Variables

The system uses Python `contextvars` to propagate context across async boundaries:

- **`request_id`** - Unique identifier for the request (UUID)
- **`node_name`** - Current LangGraph node being executed
- **`scene_id`** - Scene being processed
- **`artifact_id`** - Artifact being created or retrieved

### Usage Pattern

```python
# File: app/core/request_context.py

from app.core.request_context import set_request_id, log_context

# Set request ID at API entry point
token = set_request_id(str(uuid.uuid4()))

# Scope additional context for structured logging
with log_context(node_name="scene_intent", scene_id=scene_id):
    # All logs within this block include node_name and scene_id
    logger.info("Processing scene intent")
```

### Propagation

Request IDs are propagated through:

- **HTTP headers** - `x-request-id` header in API requests/responses
- **Logs** - Included in all structured log records
- **Artifacts** - Stored in artifact metadata
- **Audit logs** - Linked to audit log entries
- **Telemetry** - Included in OpenTelemetry spans

## Telemetry and Tracing

**File**: `app/core/telemetry.py`

The system integrates with OpenTelemetry for distributed tracing and observability.

### Setup

**Configuration**: Set `PHOENIX_OTEL_ENDPOINT` or `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable

**Instrumentation**:

- **FastAPI** - Automatic HTTP request tracing
- **LangChain** - LangGraph node execution tracing (if available)

**Service Name**: `ssuljaengi`

### Trace Spans

Use `trace_span()` context manager to create custom spans:

```python
# File: app/core/telemetry.py

from app.core.telemetry import trace_span

with trace_span("scene_planning", scene_id=str(scene_id), story_id=str(story_id)):
    # All operations within this block are traced
    result = plan_scene(scene_id)
```

**Span Attributes**: Add custom attributes (scene_id, story_id, style_id, etc.) for filtering and analysis

**Automatic Spans**: FastAPI endpoints and LangGraph nodes automatically create spans

## Progress Tracking

**Field**: `Story.progress` (JSON)

The `Story.progress` field tracks story blueprint generation progress and errors.

### Progress Structure

```json
{
  "status": "running",
  "current_node": "extract_characters",
  "message": "Extracting characters from story text",
  "step": 3,
  "total_steps": 8,
  "error": null,
  "updated_at": "2026-01-15T10:30:45Z"
}
```

**Fields**:

- `status` - Generation status (queued, running, succeeded, failed)
- `current_node` - Current LangGraph node being executed
- `message` - Human-readable progress message
- `step` - Current step number (1-indexed)
- `total_steps` - Total number of steps
- `error` - Error message if failed
- `updated_at` - Last update timestamp

### Checking Progress

**API Endpoint**: `GET /v1/stories/{story_id}/progress`

**Database Query**:

```sql
SELECT generation_status, progress, progress_updated_at, generation_error
FROM stories
WHERE story_id = ?;
```

**Usage**: Poll this endpoint to track long-running story generation jobs

## Audit Logging

**File**: `app/services/audit.py`

The audit logging system tracks entity lifecycle events (create, update, delete) with old/new value snapshots.

### AuditLog Model

**Fields**:

- `entity_type` - Type of entity (story, scene, character, etc.)
- `entity_id` - UUID of the entity
- `action` - Action performed (create, update, delete, generation_start, etc.)
- `request_id` - Correlation ID from request context
- `old_value` - JSON snapshot of entity before change
- `new_value` - JSON snapshot of entity after change
- `created_at` - Timestamp of the audit event

### Usage

```python
# File: app/services/audit.py

from app.services.audit import log_audit_entry

log_audit_entry(
    db=db,
    entity_type="story",
    entity_id=story_id,
    action="generation_start",
    old_value={"generation_status": "idle"},
    new_value={"generation_status": "running"},
)
```

**Automatic Correlation**: Audit logs automatically capture `request_id` from context

**Querying**: Query audit logs by `entity_type`, `entity_id`, `action`, or `request_id` to trace changes

## Metrics Collection

**File**: `app/core/metrics.py`

The system exposes Prometheus-compatible metrics for monitoring and alerting.

### Available Metrics

**Graph Node Duration**:

- `ssuljaengi_graph_node_duration_seconds` - Histogram of node execution time
- Labels: `graph`, `node`

**JSON Parse Failures**:

- `ssuljaengi_json_parse_failures_total` - Counter of JSON parsing failures
- Labels: `tier` (scene_intent, panel_plan, etc.)

**Gemini API Calls**:

- `ssuljaengi_gemini_call_duration_seconds` - Histogram of API call latency
- `ssuljaengi_gemini_calls_total` - Counter of API calls by status
- Labels: `operation` (generate_text, generate_image), `status` (success, error)

**Blind Test Results**:

- `ssuljaengi_blind_test_results_total` - Counter of blind test outcomes
- Labels: `result` (pass, fail)

**QC Failures**:

- `ssuljaengi_qc_issues_total` - Counter of QC visual storytelling checks (note: some are soft warnings)
- Labels: `issue` (too_many_closeups, repeated_framing - now relaxed)

**Artifact Creations**:

- `ssuljaengi_artifact_creations_total` - Counter of artifacts created
- Labels: `type` (scene_intent, panel_plan, render_spec, etc.)

### Metrics Endpoint

**Endpoint**: `GET /metrics`

**Format**: Prometheus text format

**Usage**: Configure Prometheus to scrape this endpoint for monitoring

### Recording Metrics

```python
# File: app/core/metrics.py

from app.core.metrics import track_graph_node, record_artifact_creation

# Track node execution time
with track_graph_node(graph="story_build", node="extract_characters"):
    result = extract_characters(story_text)

# Record artifact creation
record_artifact_creation(artifact_type="scene_intent")
```

## Key Files

### Error Handling

- `app/services/vertex_gemini.py` - GeminiClient with retry logic and circuit breaker
- `app/core/request_context.py` - Request correlation context variables
- `app/core/logging.py` - Structured logging with request ID injection

### Observability

- `app/core/telemetry.py` - OpenTelemetry tracing setup
- `app/core/metrics.py` - Prometheus metrics collection
- `app/services/audit.py` - Audit logging service

### Models

- `app/db/models.py` - Story model with `progress` field, AuditLog model

## Debugging Direction

**When things go wrong, check:**

### Gemini API Errors

- **Rate limit errors**:
  - Check `GeminiClient.last_error_type` for error classification
  - Review circuit breaker status with `get_circuit_breaker_status()`
  - Check logs for retry attempts and backoff times
  - Consider increasing `rate_limit_backoff_seconds` or using fallback model

- **Content filter errors**:
  - Check `GeminiContentFilterError.blocked_categories` for specific safety categories
  - Review prompt content in artifact payloads
  - Adjust safety settings in `_DEFAULT_SAFETY_SETTINGS` if appropriate
  - Content filter errors are not retried (non-retryable)

- **Circuit breaker open**:
  - Check circuit breaker status: `client.get_circuit_breaker_status()`
  - Review logs for failure patterns leading to circuit open
  - Wait for recovery timeout (default 60s) or manually reset: `client.reset_circuit_breaker()`
  - Investigate root cause of repeated failures

- **Model fallback**:
  - Check logs for "trying fallback" messages
  - Verify fallback model is configured and available
  - Review `GeminiClient.last_model` to see which model was used
  - Compare results between primary and fallback models

### Request Tracing

- **Trace request through system**:
  - Extract `x-request-id` from API response headers
  - Search logs for `request_id` field: `grep "request_id.*<uuid>" logs/*.log`
  - Query audit logs: `SELECT * FROM audit_logs WHERE request_id = ?`
  - Check OpenTelemetry traces in observability platform (Phoenix, Jaeger, etc.)

- **Missing request ID**:
  - Verify `set_request_id()` is called at API entry point
  - Check `RequestIdFilter` is registered in logging configuration
  - Ensure context variables are propagated across async boundaries

### Progress Tracking

- **Story generation stuck**:
  - Check `Story.generation_status` field (queued, running, succeeded, failed)
  - Review `Story.progress` JSON for current node and error message
  - Check `Story.progress_updated_at` timestamp - if stale, job may be stuck
  - Query job queue for background job status
  - Review logs filtered by `story_id` for error traces

- **Progress not updating**:
  - Verify graph nodes are updating `Story.progress` field
  - Check database transaction commits are successful
  - Review logs for progress update failures
  - Ensure `progress_updated_at` is being set

### Audit Logging

- **Track entity changes**:
  - Query audit logs by entity: `SELECT * FROM audit_logs WHERE entity_type = 'story' AND entity_id = ?`
  - Review `old_value` and `new_value` JSON for change details
  - Filter by action: `SELECT * FROM audit_logs WHERE action = 'generation_start'`
  - Correlate with request: `SELECT * FROM audit_logs WHERE request_id = ?`

- **Missing audit logs**:
  - Verify `log_audit_entry()` is called for entity changes
  - Check database transaction commits are successful
  - Ensure `request_id` is set in context before audit logging

### Metrics and Monitoring

- **High error rates**:
  - Check `ssuljaengi_gemini_calls_total{status="error"}` for API failures
  - Review `ssuljaengi_qc_issues_total` for visual storytelling checks (note: some rules are soft warnings now)
  - Check `ssuljaengi_json_parse_failures_total` for LLM output parsing issues
  - Investigate `ssuljaengi_blind_test_results_total` for narrative/visual flow issues

- **Performance issues**:
  - Review `ssuljaengi_graph_node_duration_seconds` histogram for slow nodes
  - Check `ssuljaengi_gemini_call_duration_seconds` for API latency
  - Identify bottleneck nodes with high p95/p99 latencies
  - Consider optimizing slow nodes or adding caching

- **Metrics not updating**:
  - Verify Prometheus is scraping `/metrics` endpoint
  - Check metrics are being recorded in code: `track_graph_node()`, `record_artifact_creation()`, etc.
  - Review Prometheus scrape configuration and target health
  - Ensure metrics registry is properly initialized

**Useful queries**:

```sql
-- Check story generation status
SELECT story_id, generation_status, progress, progress_updated_at, generation_error
FROM stories
WHERE story_id = ?;

-- Find recent audit logs for entity
SELECT action, request_id, old_value, new_value, created_at
FROM audit_logs
WHERE entity_type = 'story' AND entity_id = ?
ORDER BY created_at DESC
LIMIT 10;

-- Find all actions for a request
SELECT entity_type, entity_id, action, created_at
FROM audit_logs
WHERE request_id = ?
ORDER BY created_at;

-- Check circuit breaker state (in Python)
from app.services.vertex_gemini import gemini_client
print(gemini_client.get_circuit_breaker_status())
```

**Key log patterns to search**:

- `gemini.generate_text` - Text generation traces
- `gemini.generate_image` - Image generation traces
- `circuit breaker OPEN` - Circuit breaker opened
- `circuit breaker CLOSED` - Circuit breaker recovered
- `trying fallback` - Fallback model used
- `request_id=<uuid>` - Trace specific request

**Testing error handling**:

```bash
# Test circuit breaker status
curl http://localhost:8000/v1/internal/circuit-breaker-status

# Test metrics endpoint
curl http://localhost:8000/metrics

# Test story progress tracking
curl http://localhost:8000/v1/stories/{story_id}/progress

# Simulate rate limit (requires test endpoint)
curl -X POST http://localhost:8000/v1/internal/test/rate-limit
```

## See Also

- [Application Workflow](01-application-workflow.md) - High-level system overview
- [LangGraph Architecture](02-langgraph-architecture.md) - Graph workflows and node execution
- [API Reference](08-api-reference.md) - API endpoints and error responses
- [Artifact System](06-artifact-system.md) - Artifact storage and retrieval
- [SKILLS.md](../SKILLS.md) - Quick reference guide
