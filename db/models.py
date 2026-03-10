import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class MemoryItem(Base):
  __tablename__ = "memory_items"
  __table_args__ = (
    Index("idx_memory_items_domain", "domain"),
    Index("idx_memory_items_kind", "kind"),
    Index("idx_memory_items_status", "status"),
    Index("idx_memory_items_domain_kind", "domain", "kind"),
  )

  id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  domain: Mapped[str] = mapped_column(String(64), nullable=False)
  kind: Mapped[str] = mapped_column(String(64), nullable=False)
  statement: Mapped[str] = mapped_column(Text, nullable=False)
  confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
  status: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")
  metadata_json: Mapped[dict[str, object] | None] = mapped_column(
    "metadata",
    JSON().with_variant(JSONB, "postgresql"),
    nullable=True,
  )
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(UTC),
  )
  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(UTC),
  )


class IngestionMetric(Base):
  __tablename__ = "ingestion_metrics"

  source_type: Mapped[str] = mapped_column(String(64), primary_key=True)
  items_total: Mapped[int] = mapped_column(nullable=False, default=0)
  duplicates_total: Mapped[int] = mapped_column(nullable=False, default=0)
  errors_total: Mapped[int] = mapped_column(nullable=False, default=0)
  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(UTC),
  )
