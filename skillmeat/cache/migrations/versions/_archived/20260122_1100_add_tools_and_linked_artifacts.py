"""Add tools and linked_artifacts columns to marketplace_catalog_entries table

Revision ID: 20260122_1100_add_tools_and_linked_artifacts
Revises: 20260122_1000_add_auto_tags_to_marketplace_sources
Create Date: 2026-01-22 11:00:00.000000+00:00

This migration adds two new columns to the marketplace_catalog_entries table to
support enhanced frontmatter utilization (Phase 1):

1. tools: JSON array of tool identifiers that the artifact uses or requires
   - Extracted from frontmatter `tools:` field
   - Enables filtering artifacts by required tools (e.g., "Bash", "Read", "WebFetch")
   - Indexed for efficient filter queries

2. linked_artifacts: JSON array of linked artifact references
   - Extracted from frontmatter `linked_artifacts:` field
   - Supports artifact relationship tracking and dependency graphs
   - Stores references like ["skill:canvas-design", "command:deploy"]

JSON Structure for tools:
["Bash", "Read", "Edit", "WebFetch", "Grep"]

JSON Structure for linked_artifacts:
[
    {"type": "skill", "name": "canvas-design", "relationship": "requires"},
    {"type": "command", "name": "deploy", "relationship": "related"}
]

Schema Changes:
- Add tools column: TEXT (JSON), nullable, default '[]'
- Add linked_artifacts column: TEXT (JSON), nullable, default '[]'
- Add index on tools column for filter queries
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260122_1100_add_tools_and_linked_artifacts"
down_revision: Union[str, None] = "20260122_1000_add_auto_tags_to_marketplace_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tools and linked_artifacts columns to marketplace_catalog_entries table.

    This migration adds two new columns to support enhanced frontmatter fields:

    1. tools: JSON array of tool identifiers (Bash, Read, Edit, etc.)
       - Enables filtering catalog entries by required tools
       - Default: empty JSON array '[]'

    2. linked_artifacts: JSON array of artifact relationships
       - Enables dependency tracking and related artifact discovery
       - Default: empty JSON array '[]'

    Both columns are nullable with defaults for backward compatibility.
    Existing entries will have empty arrays until rescanned with frontmatter
    extraction enabled.
    """
    # Add tools column (JSON array of tool identifiers)
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "tools",
            sa.Text(),
            nullable=True,
            server_default=sa.text("'[]'"),
            comment="JSON array of tool identifiers (e.g., ['Bash', 'Read', 'Edit'])",
        ),
    )

    # Add linked_artifacts column (JSON array of artifact references)
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column(
            "linked_artifacts",
            sa.Text(),
            nullable=True,
            server_default=sa.text("'[]'"),
            comment="JSON array of linked artifact references with type and relationship",
        ),
    )

    # Create index on tools column for efficient filtering
    # Using standard index since SQLite doesn't support GIN indexes
    op.create_index(
        "idx_catalog_entries_tools",
        "marketplace_catalog_entries",
        ["tools"],
    )


def downgrade() -> None:
    """Remove tools and linked_artifacts columns from marketplace_catalog_entries.

    This reverts the migration by dropping the index and both columns. Any data
    stored in these columns will be permanently lost.

    WARNING: This is a destructive operation and should only be used if
    rolling back to a version that does not support these frontmatter fields.
    """
    # Drop index first
    op.drop_index("idx_catalog_entries_tools", "marketplace_catalog_entries")

    # Drop columns in reverse order of addition
    op.drop_column("marketplace_catalog_entries", "linked_artifacts")
    op.drop_column("marketplace_catalog_entries", "tools")
