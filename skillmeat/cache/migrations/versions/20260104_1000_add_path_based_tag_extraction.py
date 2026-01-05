"""Add path-based tag extraction columns to marketplace tables

Revision ID: 20260104_1000_add_path_based_tag_extraction
Revises: 20260102_1000_update_catalog_status_constraint
Create Date: 2026-01-04 10:00:00.000000+00:00

This migration adds two new columns to support path-based tag extraction:

1. MarketplaceSource.path_tag_config (Text, nullable):
   - Stores JSON configuration for path-based tag extraction rules
   - Defines patterns for extracting tags from repository paths
   - Example: {"patterns": [{"path": "skills/*/", "tag_template": "skill/{name}"}]}

2. MarketplaceCatalogEntry.path_segments (Text, nullable):
   - Stores JSON array of extracted path segments with approval status
   - Each segment contains extracted values and user approval state
   - Example: [{"segment": "skill", "value": "canvas", "approved": true}]

Schema Changes:
- Add path_tag_config to marketplace_sources (Text, nullable)
- Add path_segments to marketplace_catalog_entries (Text, nullable)

Both columns are nullable to maintain compatibility with existing data.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260104_1000_add_path_based_tag_extraction"
down_revision: Union[str, None] = "20260102_1000_update_catalog_status_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add path-based tag extraction columns to marketplace tables.

    This migration adds two new nullable columns:

    1. marketplace_sources.path_tag_config (Text):
       - JSON config for path-based tag extraction rules
       - Defines patterns to extract tags from repository paths
       - Nullable to support existing sources without configuration

    2. marketplace_catalog_entries.path_segments (Text):
       - JSON array of extracted path segments with approval status
       - Stores intermediate extraction results before tag generation
       - Nullable to support existing catalog entries

    No data migration is required as these are new optional fields.
    """
    # Add path_tag_config column to marketplace_sources
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "path_tag_config",
            sa.Text(),
            nullable=True,
            comment="JSON config for path-based tag extraction rules"
        )
    )

    # Add path_segments column to marketplace_catalog_entries
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "path_segments",
            sa.Text(),
            nullable=True,
            comment="JSON array of extracted path segments with approval status"
        )
    )


def downgrade() -> None:
    """Remove path-based tag extraction columns from marketplace tables.

    This reverts the migration by dropping both columns. Any data stored in
    these columns will be permanently lost.

    WARNING: This is a destructive operation and should only be used if
    rolling back to a version that does not support path-based tag extraction.
    """
    # Drop columns in reverse order for clarity
    op.drop_column("marketplace_catalog_entries", "path_segments")
    op.drop_column("marketplace_sources", "path_tag_config")
