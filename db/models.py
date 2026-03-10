import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text, Uuid
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


class MemoryRelation(Base):
  __tablename__ = "memory_relations"
  __table_args__ = (
    Index("idx_memory_relations_source_item_id", "source_item_id"),
    Index("idx_memory_relations_target_item_id", "target_item_id"),
    Index("idx_memory_relations_relation_type", "relation_type"),
    Index(
      "uq_memory_relations_source_target_type",
      "source_item_id",
      "target_item_id",
      "relation_type",
      unique=True,
    ),
  )

  id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  source_item_id: Mapped[uuid.UUID] = mapped_column(
    Uuid,
    ForeignKey("memory_items.id", ondelete="CASCADE"),
    nullable=False,
  )
  target_item_id: Mapped[uuid.UUID] = mapped_column(
    Uuid,
    ForeignKey("memory_items.id", ondelete="CASCADE"),
    nullable=False,
  )
  relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(UTC),
  )


class FactExtractionMetric(Base):
  __tablename__ = "fact_extraction_metrics"

  domain: Mapped[str] = mapped_column(String(64), primary_key=True)
  runs_total: Mapped[int] = mapped_column(nullable=False, default=0)
  facts_created_total: Mapped[int] = mapped_column(nullable=False, default=0)
  errors_total: Mapped[int] = mapped_column(nullable=False, default=0)
  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(UTC),
  )


class ReflectionMetric(Base):
  __tablename__ = "reflection_metrics"

  domain: Mapped[str] = mapped_column(String(64), primary_key=True)
  runs_total: Mapped[int] = mapped_column(nullable=False, default=0)
  reflections_created_total: Mapped[int] = mapped_column(nullable=False, default=0)
  skipped_total: Mapped[int] = mapped_column(nullable=False, default=0)
  errors_total: Mapped[int] = mapped_column(nullable=False, default=0)
  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(UTC),
  )
