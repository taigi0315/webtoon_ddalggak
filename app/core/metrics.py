from __future__ import annotations

from contextlib import contextmanager

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

registry = CollectorRegistry(auto_describe=True)

GRAPH_NODE_DURATION = Histogram(
    "ssuljaengi_graph_node_duration_seconds",
    "Duration (seconds) broken down by graph stage.",
    ["graph", "node"],
    registry=registry,
)

JSON_PARSE_FAILURES = Counter(
    "ssuljaengi_json_parse_failures_total",
    "Number of times parsing JSON from Gemini failed, labeled by the extraction tier.",
    ["tier"],
    registry=registry,
)

GEMINI_CALL_DURATION = Histogram(
    "ssuljaengi_gemini_call_duration_seconds",
    "Latency for Gemini API calls per operation.",
    ["operation"],
    registry=registry,
)

GEMINI_CALLS_TOTAL = Counter(
    "ssuljaengi_gemini_calls_total",
    "Total Gemini API calls partitioned by operation and status.",
    ["operation", "status"],
    registry=registry,
)

BLIND_TEST_RESULTS = Counter(
    "ssuljaengi_blind_test_results_total",
    "Blind test pass/fail count.",
    ["result"],
    registry=registry,
)

QC_FAILURES = Counter(
    "ssuljaengi_qc_issues_total",
    "Quality-control failure counts by issue code.",
    ["issue"],
    registry=registry,
)

ARTIFACT_CREATIONS_TOTAL = Counter(
    "ssuljaengi_artifact_creations_total",
    "Number of artifacts created by type.",
    ["type"],
    registry=registry,
)


@contextmanager
def track_graph_node(graph: str, node: str):
    with GRAPH_NODE_DURATION.labels(graph=graph, node=node).time():
        yield


def increment_json_parse_failure(tier: str) -> None:
    JSON_PARSE_FAILURES.labels(tier=tier).inc()


@contextmanager
def track_gemini_call(operation: str):
    timer = GEMINI_CALL_DURATION.labels(operation=operation).time()
    timer.__enter__()
    try:
        yield
        GEMINI_CALLS_TOTAL.labels(operation=operation, status="success").inc()
    except Exception:
        GEMINI_CALLS_TOTAL.labels(operation=operation, status="error").inc()
        raise
    finally:
        timer.__exit__(None, None, None)


def record_blind_test_result(passed: bool) -> None:
    label = "pass" if passed else "fail"
    BLIND_TEST_RESULTS.labels(result=label).inc()


def record_qc_issues(issues: list[str]) -> None:
    for issue in issues:
        QC_FAILURES.labels(issue=issue).inc()


def record_artifact_creation(artifact_type: str) -> None:
    ARTIFACT_CREATIONS_TOTAL.labels(type=artifact_type).inc()


def get_metrics_payload() -> bytes:
    return generate_latest(registry)
