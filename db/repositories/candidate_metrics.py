from datetime import UTC, datetime

from sqlalchemy.orm import Session

from db.models import CandidateMetric


class CandidateMetricRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def increment(
    self,
    *,
    domain: str,
    created: int = 0,
    accepted: int = 0,
    rejected: int = 0,
    validation_failures: int = 0,
  ) -> CandidateMetric:
    metric = self.session.get(CandidateMetric, domain)
    if metric is None:
      metric = CandidateMetric(domain=domain)
      self.session.add(metric)
      self.session.flush()

    metric.created_total += created
    metric.accepted_total += accepted
    metric.rejected_total += rejected
    metric.validation_failures_total += validation_failures
    metric.updated_at = datetime.now(UTC)
    self.session.add(metric)
    self.session.flush()
    return metric

  def list_all(self) -> list[CandidateMetric]:
    return list(self.session.query(CandidateMetric).all())
