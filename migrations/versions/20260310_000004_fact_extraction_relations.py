"""add fact extraction relations and metrics

Revision ID: 20260310_000004
Revises: 20260310_000003
Create Date: 2026-03-10 19:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260310_000004"
down_revision: str | None = "20260310_000003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
  op.create_table(
    "memory_relations",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("source_item_id", sa.Uuid(), nullable=False),
    sa.Column("target_item_id", sa.Uuid(), nullable=False),
    sa.Column("relation_type", sa.String(length=64), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["source_item_id"], ["memory_items.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["target_item_id"], ["memory_items.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index(
    "idx_memory_relations_source_item_id",
    "memory_relations",
    ["source_item_id"],
    unique=False,
  )
  op.create_index(
    "idx_memory_relations_target_item_id",
    "memory_relations",
    ["target_item_id"],
    unique=False,
  )
  op.create_index(
    "idx_memory_relations_relation_type",
    "memory_relations",
    ["relation_type"],
    unique=False,
  )
  op.create_index(
    "uq_memory_relations_source_target_type",
    "memory_relations",
    ["source_item_id", "target_item_id", "relation_type"],
    unique=True,
  )

  op.create_table(
    "fact_extraction_metrics",
    sa.Column("domain", sa.String(length=64), nullable=False),
    sa.Column("runs_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("facts_created_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("errors_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("domain"),
  )


def downgrade() -> None:
  op.drop_table("fact_extraction_metrics")
  op.drop_index("uq_memory_relations_source_target_type", table_name="memory_relations")
  op.drop_index("idx_memory_relations_relation_type", table_name="memory_relations")
  op.drop_index("idx_memory_relations_target_item_id", table_name="memory_relations")
  op.drop_index("idx_memory_relations_source_item_id", table_name="memory_relations")
  op.drop_table("memory_relations")
