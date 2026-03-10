import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

HTTP_REQUESTS_TOTAL = Counter(
  "mnemos_http_requests_total",
  "Total HTTP requests",
  ["method", "path", "status_code"],
)
HTTP_REQUEST_DURATION = Histogram(
  "mnemos_http_request_duration_seconds",
  "HTTP request latency",
  ["method", "path"],
)
MEMORY_QUERY_TOTAL = Counter("mnemos_memory_query_total", "Total memory queries")
MEMORY_QUERY_DURATION = Histogram(
  "mnemos_memory_query_duration_seconds",
  "Memory query latency",
)
MEMORY_CREATE_TOTAL = Counter("mnemos_memory_create_total", "Total memory item create attempts")
READINESS_FAILURES = Counter(
  "mnemos_readiness_failures_total",
  "Total readiness check failures",
  ["dependency"],
)
POSTGRES_HEALTH = Gauge("mnemos_postgres_health", "Postgres health status")
QDRANT_HEALTH = Gauge("mnemos_qdrant_health", "Qdrant health status")


class PrometheusMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next: Callable) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    HTTP_REQUESTS_TOTAL.labels(
      method=request.method,
      path=request.url.path,
      status_code=str(response.status_code),
    ).inc()
    HTTP_REQUEST_DURATION.labels(method=request.method, path=request.url.path).observe(elapsed)
    return response
