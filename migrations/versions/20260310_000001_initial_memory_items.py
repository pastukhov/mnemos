"""initial memory items

Revision ID: 20260310_000001
Revises:
Create Date: 2026-03-10 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260310_000001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
  op.create_table(
    "memory_items",
    sa.Column("id", sa.UUID(), nullable=False),
    sa.Column("domain", sa.String(length=64), nullable=False),
    sa.Column("kind", sa.String(length=64), nullable=False),
    sa.Column("statement", sa.Text(), nullable=False),
    sa.Column("confidence", sa.Float(), nullable=True),
    sa.Column("status", sa.String(length=32), nullable=False, server_default="accepted"),
    sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index("idx_memory_items_domain", "memory_items", ["domain"], unique=False)
  op.create_index("idx_memory_items_kind", "memory_items", ["kind"], unique=False)
  op.create_index("idx_memory_items_status", "memory_items", ["status"], unique=False)
  op.create_index(
    "idx_memory_items_domain_kind",
    "memory_items",
    ["domain", "kind"],
    unique=False,
  )


def downgrade() -> None:
  op.drop_index("idx_memory_items_domain_kind", table_name="memory_items")
  op.drop_index("idx_memory_items_status", table_name="memory_items")
  op.drop_index("idx_memory_items_kind", table_name="memory_items")
  op.drop_index("idx_memory_items_domain", table_name="memory_items")
  op.drop_table("memory_items")
