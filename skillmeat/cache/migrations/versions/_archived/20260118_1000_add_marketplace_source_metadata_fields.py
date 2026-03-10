"""Add metadata fields to marketplace_sources table

Revision ID: 20260118_1000_add_marketplace_source_metadata_fields
Revises: 20260108_1700_add_mcp_to_type_constraints
Create Date: 2026-01-18 10:00:00.000000+00:00

This migration adds four new columns to the marketplace_sources table to store
metadata fetched from GitHub and aggregated artifact counts:

- repo_description: Repository description from GitHub API (max 2000 chars)
- repo_readme: README content from GitHub (Text, up to 50KB)
- tags: JSON-serialized list of tags for categorization
- counts_by_type: JSON-serialized dict mapping artifact type to count

These fields support the marketplace sources enhancement feature, enabling
richer source metadata display and better filtering/search capabilities.

Schema Changes:
- Add repo_description column: VARCHAR(2000), nullable
- Add repo_readme column: TEXT, nullable
- Add tags column: TEXT, nullable
- Add counts_by_type column: TEXT, nullable

All columns are nullable to maintain compatibility with existing data.
No data migration is required as these are new optional fields that will
be populated during subsequent source scans.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260118_1000_add_marketplace_source_metadata_fields"
down_revision: Union[str, None] = "20260108_1700_add_mcp_to_type_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add metadata columns to marketplace_sources table.

    This migration adds four new nullable columns to support GitHub-fetched
    metadata and artifact count aggregation:

    - repo_description: Short description from GitHub (2000 char limit)
    - repo_readme: Full README content from GitHub (Text for larger content)
    - tags: JSON array of categorization tags
    - counts_by_type: JSON object mapping artifact types to counts

    All columns are nullable to maintain compatibility with existing data.
    """
    # Add repo_description column (GitHub API description)
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "repo_description",
            sa.String(2000),
            nullable=True,
            comment="Description fetched from GitHub API",
        ),
    )

    # Add repo_readme column (GitHub README content)
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "repo_readme",
            sa.Text(),
            nullable=True,
            comment="README content from GitHub (up to 50KB)",
        ),
    )

    # Add tags column (JSON array of tags)
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "tags",
            sa.Text(),
            nullable=True,
            comment="JSON-serialized list of tags for categorization",
        ),
    )

    # Add counts_by_type column (JSON object with type counts)
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "counts_by_type",
            sa.Text(),
            nullable=True,
            comment="JSON-serialized dict mapping artifact type to count",
        ),
    )


def downgrade() -> None:
    """Remove metadata columns from marketplace_sources table.

    This reverts the migration by dropping all four columns. Any data stored
    in these columns will be permanently lost.

    WARNING: This is a destructive operation and should only be used if
    rolling back to a version that does not support these fields.
    """
    # Drop columns in reverse order of addition
    op.drop_column("marketplace_sources", "counts_by_type")
    op.drop_column("marketplace_sources", "tags")
    op.drop_column("marketplace_sources", "repo_readme")
    op.drop_column("marketplace_sources", "repo_description")
