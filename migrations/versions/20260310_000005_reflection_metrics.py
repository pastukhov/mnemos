"""add reflection metrics table

Revision ID: 20260310_000005
Revises: 20260310_000004
Create Date: 2026-03-10 23:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260310_000005"
down_revision: str | None = "20260310_000004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
  op.create_table(
    "reflection_metrics",
    sa.Column("domain", sa.String(length=64), nullable=False),
    sa.Column("runs_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("reflections_created_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("skipped_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("errors_total", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("domain"),
  )


def downgrade() -> None:
  op.drop_table("reflection_metrics")
