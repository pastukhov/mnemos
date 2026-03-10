from datetime import UTC, datetime

from sqlalchemy.orm import Session

from db.models import ReflectionMetric


class ReflectionMetricRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def increment(
    self,
    *,
    domain: str,
    runs: int = 0,
    reflections_created: int = 0,
    skipped: int = 0,
    errors: int = 0,
  ) -> ReflectionMetric:
    metric = self.session.get(ReflectionMetric, domain)
    if metric is None:
      metric = ReflectionMetric(domain=domain)
      self.session.add(metric)
      self.session.flush()

    metric.runs_total += runs
    metric.reflections_created_total += reflections_created
    metric.skipped_total += skipped
    metric.errors_total += errors
    metric.updated_at = datetime.now(UTC)
    self.session.add(metric)
    self.session.flush()
    return metric

  def list_all(self) -> list[ReflectionMetric]:
    return list(self.session.query(ReflectionMetric).all())
