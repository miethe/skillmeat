"""Add cross-source search columns to marketplace_catalog_entries

Revision ID: 20260124_1000_add_search_columns_to_catalog_entries
Revises: 20260123_1000_add_indexing_enabled_to_marketplace_sources
Create Date: 2026-01-24 10:00:00.000000+00:00

This migration adds columns to the marketplace_catalog_entries table to support
cross-source artifact search. These columns store indexed frontmatter data:

- title: Artifact title from SKILL.md/COMMAND.md frontmatter (String 200)
- description: Artifact description from frontmatter (Text)
- search_tags: JSON array of tags from frontmatter (Text)
- search_text: Concatenated searchable text for full-text search (Text)

All columns are nullable to maintain backward compatibility with existing entries.
Existing entries will have NULL values until re-scanned with indexing enabled.

Phase 1 of cross-source search implementation (DB-001).
Indexes will be added in a separate migration (DB-002).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260124_1000_add_search_columns_to_catalog_entries"
down_revision: Union[str, None] = (
    "20260123_1000_add_indexing_enabled_to_marketplace_sources"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add search columns to marketplace_catalog_entries table.

    Adds four nullable columns for cross-source search functionality:
    - title: Short display title (max 200 chars)
    - description: Full description text
    - search_tags: JSON-serialized array of tags
    - search_text: Pre-concatenated searchable text for efficient queries
    """
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "title",
            sa.String(200),
            nullable=True,
            comment="Artifact title from frontmatter for search display",
        ),
    )

    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Artifact description from frontmatter for search",
        ),
    )

    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "search_tags",
            sa.Text(),
            nullable=True,
            comment="JSON array of tags from frontmatter for search filtering",
        ),
    )

    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "search_text",
            sa.Text(),
            nullable=True,
            comment="Concatenated searchable text (title + description + tags)",
        ),
    )


def downgrade() -> None:
    """Remove search columns from marketplace_catalog_entries table.

    This reverts the migration by dropping all four search columns.
    Any indexed frontmatter data will be permanently lost.

    WARNING: This is a destructive operation. Re-scanning sources will be
    required to repopulate this data after upgrading again.
    """
    op.drop_column("marketplace_catalog_entries", "search_text")
    op.drop_column("marketplace_catalog_entries", "search_tags")
    op.drop_column("marketplace_catalog_entries", "description")
    op.drop_column("marketplace_catalog_entries", "title")
