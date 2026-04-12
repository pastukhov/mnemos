"""add wiki page cache

Revision ID: 20260411_000007
Revises: 20260310_000006
Create Date: 2026-04-11 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260411_000007"
down_revision: str | None = "20260310_000006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
  op.create_table(
    "wiki_page_cache",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("page_name", sa.String(length=255), nullable=False),
    sa.Column("title", sa.String(length=255), nullable=False),
    sa.Column("content_md", sa.Text(), nullable=False),
    sa.Column("facts_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("reflections_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index(
    "uq_wiki_page_cache_page_name",
    "wiki_page_cache",
    ["page_name"],
    unique=True,
  )
  op.create_index(
    "idx_wiki_page_cache_invalidated_at",
    "wiki_page_cache",
    ["invalidated_at"],
    unique=False,
  )


def downgrade() -> None:
  op.drop_index("idx_wiki_page_cache_invalidated_at", table_name="wiki_page_cache")
  op.drop_index("uq_wiki_page_cache_page_name", table_name="wiki_page_cache")
  op.drop_table("wiki_page_cache")
