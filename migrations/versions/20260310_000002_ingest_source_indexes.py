"""add source reference indexes for ingestion

Revision ID: 20260310_000002
Revises: 20260310_000001
Create Date: 2026-03-10 00:00:02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260310_000002"
down_revision: str | None = "20260310_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
  op.execute(
    """
    CREATE INDEX IF NOT EXISTS idx_memory_source_ref
    ON memory_items ((metadata->>'source_id'))
    """
  )
  op.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_memory_source_ref
    ON memory_items ((metadata->>'source_type'), (metadata->>'source_id'))
    WHERE metadata ? 'source_type' AND metadata ? 'source_id'
    """
  )


def downgrade() -> None:
  op.execute("DROP INDEX IF EXISTS uq_memory_source_ref")
  op.execute("DROP INDEX IF EXISTS idx_memory_source_ref")
