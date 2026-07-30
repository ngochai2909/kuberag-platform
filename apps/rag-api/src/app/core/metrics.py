"""Low-cardinality Prometheus metrics for the public RAG API."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

API_INFO = Gauge("kuberag_api_info", "KubeRAG API build information", ["version"])
API_REQUESTS_TOTAL = Counter(
    "kuberag_api_requests_total",
    "Completed HTTP requests handled by FastAPI",
    ["method", "route", "status_code"],
)
API_REQUEST_DURATION_SECONDS = Histogram(
    "kuberag_api_request_duration_seconds",
    "End-to-end FastAPI request duration",
    ["method", "route", "status_code"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
RAG_STAGE_DURATION_SECONDS = Histogram(
    "kuberag_rag_stage_duration_seconds",
    "Duration of a bounded RAG pipeline stage",
    ["stage"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
RAG_QUERIES_TOTAL = Counter(
    "kuberag_rag_queries_total",
    "Completed RAG queries by bounded outcome",
    ["outcome"],
)


def record_http_request(
    *, method: str, route: str, status_code: int, duration_seconds: float
) -> None:
    labels = {"method": method, "route": route, "status_code": str(status_code)}
    API_REQUESTS_TOTAL.labels(**labels).inc()
    API_REQUEST_DURATION_SECONDS.labels(**labels).observe(duration_seconds)


def render_metrics(*, version: str) -> tuple[bytes, str]:
    API_INFO.labels(version=version).set(1)
    return generate_latest(), CONTENT_TYPE_LATEST
