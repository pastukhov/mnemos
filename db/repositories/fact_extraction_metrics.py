from datetime import UTC, datetime

from sqlalchemy.orm import Session

from db.models import FactExtractionMetric


class FactExtractionMetricRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def increment(
    self,
    *,
    domain: str,
    runs: int = 0,
    facts_created: int = 0,
    errors: int = 0,
  ) -> FactExtractionMetric:
    metric = self.session.get(FactExtractionMetric, domain)
    if metric is None:
      metric = FactExtractionMetric(domain=domain)
      self.session.add(metric)
      self.session.flush()

    metric.runs_total += runs
    metric.facts_created_total += facts_created
    metric.errors_total += errors
    metric.updated_at = datetime.now(UTC)
    self.session.add(metric)
    self.session.flush()
    return metric

  def list_all(self) -> list[FactExtractionMetric]:
    return list(self.session.query(FactExtractionMetric).all())
