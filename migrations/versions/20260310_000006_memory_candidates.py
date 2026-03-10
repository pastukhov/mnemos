"""add memory candidates and candidate metrics

Revision ID: 20260310_000006
Revises: 20260310_000005
Create Date: 2026-03-10 23:58:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260310_000006"
down_revision: str | None = "20260310_000005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
  op.create_table(
    "memory_candidates",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("domain", sa.String(length=64), nullable=False),
    sa.Column("kind", sa.String(length=64), nullable=False),
    sa.Column("statement", sa.Text(), nullable=False),
    sa.Column("confidence", sa.Float(), nullable=True),
    sa.Column("agent_id", sa.String(length=64), nullable=True),
    sa.Column("evidence", sa.JSON(), nullable=True),
    sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
    sa.Column("metadata", sa.JSON(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("idx_memory_candidates_status", "memory_candidates", ["status"], unique=False)
  op.create_index("idx_memory_candidates_domain", "memory_candidates", ["domain"], unique=False)
  op.create_index("idx_memory_candidates_kind", "memory_candidates", ["kind"], unique=False)
  op.create_index(
    "idx_memory_candidates_domain_status",
    "memory_candidates",
    ["domain", "status"],
    unique=False,
  )

  op.create_table(
    "candidate_metrics",
    sa.Column("domain", sa.String(length=64), nullable=False),
    sa.Column("created_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("accepted_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("rejected_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("validation_failures_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("domain"),
  )


def downgrade() -> None:
  op.drop_table("candidate_metrics")
  op.drop_index("idx_memory_candidates_domain_status", table_name="memory_candidates")
  op.drop_index("idx_memory_candidates_kind", table_name="memory_candidates")
  op.drop_index("idx_memory_candidates_domain", table_name="memory_candidates")
  op.drop_index("idx_memory_candidates_status", table_name="memory_candidates")
  op.drop_table("memory_candidates")
