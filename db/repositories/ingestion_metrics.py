from datetime import UTC, datetime

from sqlalchemy.orm import Session

from db.models import IngestionMetric


class IngestionMetricRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def increment(
    self,
    *,
    source_type: str,
    loaded: int = 0,
    duplicates: int = 0,
    errors: int = 0,
  ) -> IngestionMetric:
    metric = self.session.get(IngestionMetric, source_type)
    if metric is None:
      metric = IngestionMetric(source_type=source_type)
      self.session.add(metric)
      self.session.flush()

    metric.items_total += loaded
    metric.duplicates_total += duplicates
    metric.errors_total += errors
    metric.updated_at = datetime.now(UTC)
    self.session.add(metric)
    self.session.flush()
    return metric

  def list_all(self) -> list[IngestionMetric]:
    return list(self.session.query(IngestionMetric).all())
