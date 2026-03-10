import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, REGISTRY
from prometheus_client.core import CounterMetricFamily
from sqlalchemy.exc import ProgrammingError
from starlette.middleware.base import BaseHTTPMiddleware

from db.repositories.fact_extraction_metrics import FactExtractionMetricRepository
from db.repositories.ingestion_metrics import IngestionMetricRepository
from db.repositories.reflection_metrics import ReflectionMetricRepository

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

_ingestion_collector = None
_fact_extraction_collector = None
_reflection_collector = None


class IngestionMetricsCollector:
  def __init__(self, session_factory) -> None:
    self.session_factory = session_factory

  def update_session_factory(self, session_factory) -> None:
    self.session_factory = session_factory

  def collect(self):
    items_metric = CounterMetricFamily(
      "mnemos_ingest_items_total",
      "Total ingested items",
      labels=["source_type"],
    )
    duplicates_metric = CounterMetricFamily(
      "mnemos_ingest_duplicates_total",
      "Total duplicate ingestion skips",
      labels=["source_type"],
    )
    errors_metric = CounterMetricFamily(
      "mnemos_ingest_errors_total",
      "Total ingestion errors",
      labels=["source_type"],
    )

    with self.session_factory() as session:
      repository = IngestionMetricRepository(session)
      try:
        items = repository.list_all()
      except ProgrammingError:
        items = []
      for item in items:
        items_metric.add_metric([item.source_type], item.items_total)
        duplicates_metric.add_metric([item.source_type], item.duplicates_total)
        errors_metric.add_metric([item.source_type], item.errors_total)

    yield items_metric
    yield duplicates_metric
    yield errors_metric

  def describe(self):
    yield CounterMetricFamily(
      "mnemos_ingest_items_total",
      "Total ingested items",
      labels=["source_type"],
    )
    yield CounterMetricFamily(
      "mnemos_ingest_duplicates_total",
      "Total duplicate ingestion skips",
      labels=["source_type"],
    )
    yield CounterMetricFamily(
      "mnemos_ingest_errors_total",
      "Total ingestion errors",
      labels=["source_type"],
    )


def register_ingestion_metrics_collector(session_factory) -> None:
  global _ingestion_collector
  if _ingestion_collector is None:
    _ingestion_collector = IngestionMetricsCollector(session_factory)
    REGISTRY.register(_ingestion_collector)
    return
  _ingestion_collector.update_session_factory(session_factory)


class FactExtractionMetricsCollector:
  def __init__(self, session_factory) -> None:
    self.session_factory = session_factory

  def update_session_factory(self, session_factory) -> None:
    self.session_factory = session_factory

  def collect(self):
    runs_metric = CounterMetricFamily(
      "mnemos_fact_extraction_runs_total",
      "Total fact extraction runs",
      labels=["domain"],
    )
    facts_metric = CounterMetricFamily(
      "mnemos_facts_created_total",
      "Total facts created",
      labels=["domain"],
    )
    errors_metric = CounterMetricFamily(
      "mnemos_fact_extraction_errors_total",
      "Total fact extraction errors",
      labels=["domain"],
    )

    with self.session_factory() as session:
      repository = FactExtractionMetricRepository(session)
      try:
        items = repository.list_all()
      except ProgrammingError:
        items = []
      for item in items:
        runs_metric.add_metric([item.domain], item.runs_total)
        facts_metric.add_metric([item.domain], item.facts_created_total)
        errors_metric.add_metric([item.domain], item.errors_total)

    yield runs_metric
    yield facts_metric
    yield errors_metric

  def describe(self):
    yield CounterMetricFamily(
      "mnemos_fact_extraction_runs_total",
      "Total fact extraction runs",
      labels=["domain"],
    )
    yield CounterMetricFamily(
      "mnemos_facts_created_total",
      "Total facts created",
      labels=["domain"],
    )
    yield CounterMetricFamily(
      "mnemos_fact_extraction_errors_total",
      "Total fact extraction errors",
      labels=["domain"],
    )


def register_fact_extraction_metrics_collector(session_factory) -> None:
  global _fact_extraction_collector
  if _fact_extraction_collector is None:
    _fact_extraction_collector = FactExtractionMetricsCollector(session_factory)
    REGISTRY.register(_fact_extraction_collector)
    return
  _fact_extraction_collector.update_session_factory(session_factory)


class ReflectionMetricsCollector:
  def __init__(self, session_factory) -> None:
    self.session_factory = session_factory

  def update_session_factory(self, session_factory) -> None:
    self.session_factory = session_factory

  def collect(self):
    runs_metric = CounterMetricFamily(
      "mnemos_reflection_runs_total",
      "Total reflection generation runs",
      labels=["domain"],
    )
    reflections_metric = CounterMetricFamily(
      "mnemos_reflections_created_total",
      "Total reflections created",
      labels=["domain"],
    )
    skipped_metric = CounterMetricFamily(
      "mnemos_reflection_skipped_total",
      "Total skipped reflection batches",
      labels=["domain"],
    )
    errors_metric = CounterMetricFamily(
      "mnemos_reflection_errors_total",
      "Total reflection generation errors",
      labels=["domain"],
    )

    with self.session_factory() as session:
      repository = ReflectionMetricRepository(session)
      try:
        items = repository.list_all()
      except ProgrammingError:
        items = []
      for item in items:
        runs_metric.add_metric([item.domain], item.runs_total)
        reflections_metric.add_metric([item.domain], item.reflections_created_total)
        skipped_metric.add_metric([item.domain], item.skipped_total)
        errors_metric.add_metric([item.domain], item.errors_total)

    yield runs_metric
    yield reflections_metric
    yield skipped_metric
    yield errors_metric

  def describe(self):
    yield CounterMetricFamily(
      "mnemos_reflection_runs_total",
      "Total reflection generation runs",
      labels=["domain"],
    )
    yield CounterMetricFamily(
      "mnemos_reflections_created_total",
      "Total reflections created",
      labels=["domain"],
    )
    yield CounterMetricFamily(
      "mnemos_reflection_skipped_total",
      "Total skipped reflection batches",
      labels=["domain"],
    )
    yield CounterMetricFamily(
      "mnemos_reflection_errors_total",
      "Total reflection generation errors",
      labels=["domain"],
    )


def register_reflection_metrics_collector(session_factory) -> None:
  global _reflection_collector
  if _reflection_collector is None:
    _reflection_collector = ReflectionMetricsCollector(session_factory)
    REGISTRY.register(_reflection_collector)
    return
  _reflection_collector.update_session_factory(session_factory)


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
