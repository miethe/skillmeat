"""Add search indexes to marketplace_catalog_entries

Revision ID: 20260124_1100_add_search_indexes_to_catalog_entries
Revises: 20260124_1000_add_search_columns_to_catalog_entries
Create Date: 2026-01-24 11:00:00.000000+00:00

This migration adds indexes to the marketplace_catalog_entries table to support
efficient cross-source artifact search. These indexes optimize common query patterns:

- idx_catalog_search_name: Index on name column for name-based lookups
- idx_catalog_search_type_status: Composite index on (artifact_type, status)
  for filtering by type and status simultaneously
- idx_catalog_search_confidence: Index on confidence_score for sorting/filtering
  by quality score

Phase 1 of cross-source search implementation (DB-002).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260124_1100_add_search_indexes_to_catalog_entries"
down_revision: Union[str, None] = "20260124_1000_add_search_columns_to_catalog_entries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add search indexes to marketplace_catalog_entries table.

    Creates three indexes to optimize cross-source search queries:
    1. Name index for artifact name lookups
    2. Composite type+status index for filtered listing queries
    3. Confidence score index for quality-based sorting/filtering
    """
    op.create_index(
        "idx_catalog_search_name",
        "marketplace_catalog_entries",
        ["name"],
    )

    op.create_index(
        "idx_catalog_search_type_status",
        "marketplace_catalog_entries",
        ["artifact_type", "status"],
    )

    op.create_index(
        "idx_catalog_search_confidence",
        "marketplace_catalog_entries",
        ["confidence_score"],
    )


def downgrade() -> None:
    """Remove search indexes from marketplace_catalog_entries table.

    This reverts the migration by dropping all three search indexes.
    This is a non-destructive operation - only index metadata is removed.
    """
    op.drop_index(
        "idx_catalog_search_confidence",
        table_name="marketplace_catalog_entries",
    )

    op.drop_index(
        "idx_catalog_search_type_status",
        table_name="marketplace_catalog_entries",
    )

    op.drop_index(
        "idx_catalog_search_name",
        table_name="marketplace_catalog_entries",
    )
