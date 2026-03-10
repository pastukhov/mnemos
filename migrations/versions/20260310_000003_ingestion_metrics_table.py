"""create ingestion metrics table

Revision ID: 20260310_000003
Revises: 20260310_000002
Create Date: 2026-03-10 00:00:03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260310_000003"
down_revision: str | None = "20260310_000002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
  op.create_table(
    "ingestion_metrics",
    sa.Column("source_type", sa.String(length=64), nullable=False),
    sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("duplicates_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("errors_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    sa.PrimaryKeyConstraint("source_type"),
  )
  op.execute(
    """
    INSERT INTO ingestion_metrics (source_type, items_total, duplicates_total, errors_total)
    SELECT metadata->>'source_type' AS source_type, COUNT(*)::integer, 0, 0
    FROM memory_items
    WHERE metadata ? 'source_type'
    GROUP BY metadata->>'source_type'
    """
  )


def downgrade() -> None:
  op.drop_table("ingestion_metrics")
