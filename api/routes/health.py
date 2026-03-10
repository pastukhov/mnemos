from fastapi import APIRouter, Request
from sqlalchemy import text

from api.schemas import LivenessResponse, ReadinessCheckResponse, ReadinessResponse
from core.logging import get_logger
from core.metrics import POSTGRES_HEALTH, QDRANT_HEALTH, READINESS_FAILURES

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger(__name__)


@router.get("/live", response_model=LivenessResponse)
def live() -> LivenessResponse:
  return LivenessResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse)
def ready(request: Request) -> ReadinessResponse:
  postgres_status = "ok"
  qdrant_status = "ok"
  try:
    with request.app.state.session_factory() as session:
      session.execute(text("SELECT 1"))
    POSTGRES_HEALTH.set(1)
  except Exception:  # pragma: no cover - defensive
    postgres_status = "failed"
    POSTGRES_HEALTH.set(0)
    READINESS_FAILURES.labels(dependency="postgres").inc()
    logger.exception("postgres readiness failed", extra={"event": "readiness_failure"})

  try:
    request.app.state.qdrant.ping()
    QDRANT_HEALTH.set(1)
  except Exception:  # pragma: no cover - defensive
    qdrant_status = "failed"
    QDRANT_HEALTH.set(0)
    READINESS_FAILURES.labels(dependency="qdrant").inc()
    logger.exception("qdrant readiness failed", extra={"event": "readiness_failure"})

  overall = "ready" if postgres_status == "ok" and qdrant_status == "ok" else "degraded"
  return ReadinessResponse(
    status=overall,
    checks=ReadinessCheckResponse(postgres=postgres_status, qdrant=qdrant_status),
  )
