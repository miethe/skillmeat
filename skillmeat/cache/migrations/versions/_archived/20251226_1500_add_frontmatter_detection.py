"""Add enable_frontmatter_detection to marketplace_sources

Revision ID: 20251226_1500_add_frontmatter_detection
Revises: 20251223_1430_update_match_history_schema
Create Date: 2025-12-26 15:00:00.000000

This migration adds a new column to the marketplace_sources table:
- enable_frontmatter_detection: Boolean flag to control whether the source
  should use frontmatter-based metadata extraction for matching artifacts

When enabled, artifacts from this source will attempt to extract metadata from
YAML frontmatter blocks (title, description, tags, etc.) in addition to the
standard GitHub API metadata. This is useful for repositories that maintain
rich metadata in their artifact files.

Schema Change:
- Add enable_frontmatter_detection column: BOOLEAN, NOT NULL, default FALSE
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251226_1500_add_frontmatter_detection"
down_revision: Union[str, None] = "20251223_1430_update_match_history_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add enable_frontmatter_detection column to marketplace_sources table.

    This migration adds a boolean flag to control frontmatter-based metadata
    extraction for marketplace sources. The column is NOT NULL with a default
    value of FALSE for backward compatibility.

    Existing sources will have this feature disabled by default. Users can
    enable it on a per-source basis through the API or UI.
    """
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "enable_frontmatter_detection",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    """Remove enable_frontmatter_detection column from marketplace_sources table.

    This reverts the migration by dropping the column. This is safe as the
    column only controls behavior and doesn't store critical data.

    WARNING: Any per-source frontmatter detection settings will be lost.
    After downgrade, all sources will use standard GitHub API metadata only.
    """
    op.drop_column("marketplace_sources", "enable_frontmatter_detection")
