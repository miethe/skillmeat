"""Add single_artifact_mode to marketplace_sources table

Revision ID: 20260120_1000_add_single_artifact_mode_to_marketplace_sources
Revises: 20260118_1000_add_marketplace_source_metadata_fields
Create Date: 2026-01-20 10:00:00.000000+00:00

This migration adds two new columns to the marketplace_sources table to support
"single artifact mode" - a feature that allows treating an entire repository
(or root_hint directory) as a single artifact, bypassing automatic detection.

- single_artifact_mode: Boolean flag to enable single artifact mode
- single_artifact_type: The artifact type to use when mode is enabled

Use Cases:
- Repositories that contain a single skill/command/agent at the root level
- Repositories with non-standard structures that don't match detection heuristics
- Quick manual override for known single-artifact repositories

When single_artifact_mode=True:
- The scanner bypasses normal artifact detection
- Creates a synthetic artifact with 100% confidence
- Uses the entire repo (or root_hint dir) as the artifact path
- Applies the specified single_artifact_type

Schema Changes:
- Add single_artifact_mode column: BOOLEAN, NOT NULL, default=false
- Add single_artifact_type column: VARCHAR(20), nullable
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260120_1000_add_single_artifact_mode_to_marketplace_sources"
down_revision: Union[str, None] = "20260118_1000_add_marketplace_source_metadata_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add single artifact mode columns to marketplace_sources table.

    This migration adds two columns to support treating a repository as a
    single artifact:

    - single_artifact_mode: Boolean flag (default: false)
    - single_artifact_type: Artifact type when mode is enabled (nullable)

    The single_artifact_mode column has a server_default of 'false' to ensure
    existing rows have a valid value without data migration.
    """
    # Add single_artifact_mode column (Boolean flag)
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "single_artifact_mode",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Treat entire repository (or root_hint dir) as single artifact",
        ),
    )

    # Add single_artifact_type column (Artifact type when mode is enabled)
    op.add_column(
        "marketplace_sources",
        sa.Column(
            "single_artifact_type",
            sa.String(20),
            nullable=True,
            comment="Artifact type when single_artifact_mode is True (skill, command, agent, mcp_server, hook)",
        ),
    )


def downgrade() -> None:
    """Remove single artifact mode columns from marketplace_sources table.

    This reverts the migration by dropping both columns. Any data stored
    in these columns will be permanently lost.

    WARNING: This is a destructive operation and should only be used if
    rolling back to a version that does not support single artifact mode.
    """
    # Drop columns in reverse order of addition
    op.drop_column("marketplace_sources", "single_artifact_type")
    op.drop_column("marketplace_sources", "single_artifact_mode")
