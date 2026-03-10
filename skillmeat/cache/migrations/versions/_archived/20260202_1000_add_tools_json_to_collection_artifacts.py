"""Add tools_json column to collection_artifacts table

Revision ID: 20260202_1000_add_tools_json_to_collection_artifacts
Revises: 20260201_1000_add_collection_artifact_metadata_cache_fields
Create Date: 2026-02-02 10:00:00.000000+00:00

This migration adds a tools_json column to the collection_artifacts table to
support artifacts that expose MCP tools. This enables filtering artifacts by
tool names and capabilities without parsing manifest files.

Field added:
- tools_json: TEXT - JSON array string of tool definitions from SKILL.md

The column is nullable for backward compatibility. An index is added to support
efficient filtering by tool availability.

Part of tools-api-support-v1 implementation (TOOLS-1.4).

Reference:
- PRD: docs/project_plans/implementation_plans/features/tools-api-support-v1.md
- TASK: TOOLS-1.4: Create Alembic migration for collection_artifacts.tools_json
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260202_1000_add_tools_json_to_collection_artifacts"
down_revision: Union[str, None] = "20260201_1000_add_collection_artifact_metadata_cache_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tools_json column to collection_artifacts table.

    Adds a TEXT column for storing JSON array of tool definitions extracted
    from artifact SKILL.md files. This enables:
    - Filtering artifacts that provide specific tools
    - Discovering available tool names without parsing manifests
    - API endpoints to query tools across the collection

    The column is nullable for backward compatibility. Existing entries will
    have NULL values until refreshed by sync operations that parse SKILL.md.
    """
    # Add tools_json column (JSON array string of tool definitions)
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "tools_json",
            sa.Text(),
            nullable=True,
            comment="JSON array string of tool definitions from SKILL.md",
        ),
    )

    # Add index on tools_json for efficient filtering
    # SQLite doesn't support expression indexes, so this is a simple column index
    # For tool-specific queries, application code will need to parse JSON
    op.create_index(
        "idx_collection_artifacts_tools_json",
        "collection_artifacts",
        ["tools_json"],
    )


def downgrade() -> None:
    """Remove tools_json column from collection_artifacts table.

    This reverts the migration by dropping the tools_json index and column.
    Any cached tool metadata will be permanently lost.

    WARNING: This is a destructive operation. Tool metadata must be re-parsed
    from SKILL.md files if the migration is later re-applied.
    """
    # Drop index first (before dropping the column it references)
    op.drop_index("idx_collection_artifacts_tools_json", "collection_artifacts")

    # Drop the tools_json column
    op.drop_column("collection_artifacts", "tools_json")
