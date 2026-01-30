# Observability (Logging, Metrics, Tracing)

This project supports:
- structured JSON logs (with correlation IDs and graph context)
- Prometheus metrics (`/metrics`)
- optional OpenTelemetry tracing (OTLP exporter)

## Structured Logging (JSON)

### What you get
All logs are emitted as JSON objects containing:
- `timestamp`, `level`, `logger`, `message`
- `request_id` (from `x-request-id`, generated if missing)
- `node_name`, `scene_id`, `artifact_id` (when emitted inside graph/node helpers)
- additional fields (via `logger.info(..., extra={...})`)

### Configuration

- `LOG_LEVEL` (default `INFO`)
- `LOG_FILE` (optional): when set, logs are written both to stdout and to a rotating file.

Log file behavior:
- Rotating file handler
- 10MB per file
- 5 backups

Example:
```bash
export LOG_LEVEL=INFO
export LOG_FILE=./storage/logs/ssuljaengi.jsonl
uvicorn app.main:app --reload
```

### Production ingestion patterns

You can ingest logs from either:
- container stdout/stderr (recommended for Kubernetes / managed platforms), or
- a local file tail (when you need an agent like Fluent Bit / Vector to tail JSON lines)

If you use `LOG_FILE`, ensure your log agent:
- tails the file path you configure
- parses JSON per line
- forwards fields like `request_id`, `node_name`, and `scene_id` so dashboards can filter by graph node and request

### Correlation ID (x-request-id)

The API middleware:
- reads `x-request-id` from the request or generates a UUID
- attaches it to logs and to the response header

When debugging a workflow:
1) call the API with a stable `x-request-id`
2) grep logs for that `request_id`
3) filter further by `scene_id` or `node_name`

## Metrics (Prometheus)

### Endpoint
- `GET /metrics` exposes a Prometheus text payload (`text/plain; version=0.0.4`)

### Included metrics (selected)
Custom metrics are defined in `app/core/metrics.py` and include:
- `ssuljaengi_graph_node_duration_seconds{graph,node}`
- `ssuljaengi_gemini_call_duration_seconds{operation}`
- `ssuljaengi_gemini_calls_total{operation,status}`
- `ssuljaengi_json_parse_failures_total{tier}`
- `ssuljaengi_artifact_creations_total{type}`
- `ssuljaengi_blind_test_results_total{result}`
- `ssuljaengi_qc_issues_total{issue}`

### Scrape configuration (example)
Prometheus scrape example (adjust host/port):
```yaml
scrape_configs:
  - job_name: ssuljaengi
    metrics_path: /metrics
    static_configs:
      - targets: ["127.0.0.1:8000"]
```

## Tracing (OpenTelemetry / OTLP)

Tracing is optional and off by default.

Set either of these environment variables to enable OTLP HTTP trace export:
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `PHOENIX_OTEL_ENDPOINT` (alternative alias)

When enabled, the app attempts to:
- configure an OTLP span exporter
- instrument FastAPI
- instrument LangChain via OpenInference (if available)

Notes:
- tracing dependencies are optional (`pip install -e ".[telemetry]"`)
- if imports fail, telemetry is disabled and the app continues to run

