"""Add indexing_enabled column to marketplace_sources table

Revision ID: 20260123_1000_add_indexing_enabled_to_marketplace_sources
Revises: 20260122_1100_add_tools_and_linked_artifacts
Create Date: 2026-01-23 10:00:00.000000+00:00

This migration adds the indexing_enabled column to the marketplace_sources table
to support configurable frontmatter caching for search indexing.

The indexing_enabled flag controls whether frontmatter data from artifacts in this
source should be persisted for cross-source search indexing. This is separate from
the existing enable_frontmatter_detection flag which controls parsing for display.

When NULL, the effective value is determined by the global frontmatter caching mode:
- "on" mode: NULL defaults to True (opt-out)
- "opt-in" mode: NULL defaults to False (opt-in)
- "off" mode: Always False regardless of column value

Use Cases:
- Users who want to exclude specific sources from search indexing
- Users who want to include specific sources in opt-in mode
- Granular control over which sources contribute to search results

Schema Changes:
- Add indexing_enabled column: BOOLEAN, nullable (no default)
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260123_1000_add_indexing_enabled_to_marketplace_sources"
down_revision: Union[str, None] = "20260122_1100_add_tools_and_linked_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexing_enabled column to marketplace_sources table.

    This column controls whether frontmatter data from this source should be
    persisted for search indexing. The column is nullable to support mode-based
    defaulting:

    - NULL: Use default based on global mode (True for "on", False for "opt-in")
    - True: Explicitly enable indexing for this source
    - False: Explicitly disable indexing for this source

    The global "off" mode takes precedence and disables indexing regardless of
    this column's value.
    """
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "indexing_enabled",
            sa.Boolean(),
            nullable=True,
            comment="Enable frontmatter extraction for search indexing (NULL=use mode default)",
        ),
    )


def downgrade() -> None:
    """Remove indexing_enabled column from marketplace_sources table.

    This reverts the migration by dropping the indexing_enabled column. Any
    per-source indexing preferences will be permanently lost.

    WARNING: This is a destructive operation. Sources will revert to using
    only the global mode setting for indexing decisions.
    """
    op.drop_column("marketplace_sources", "indexing_enabled")
