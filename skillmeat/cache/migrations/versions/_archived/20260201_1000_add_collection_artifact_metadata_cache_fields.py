"""Add metadata cache fields to collection_artifacts table

Revision ID: 20260201_1000_add_collection_artifact_metadata_cache_fields
Revises: 20260124_1400_update_fts5_with_deep_search
Create Date: 2026-02-01 10:00:00.000000+00:00

This migration adds 11 metadata cache fields to the collection_artifacts table
to support DB-backed collection pages without requiring file system reads or
GitHub API calls.

Fields added:
- description: TEXT - Artifact description from manifest
- author: VARCHAR - Artifact author
- license: VARCHAR - License identifier (MIT, Apache-2.0, etc.)
- tags_json: TEXT - JSON array string of tags
- version: VARCHAR - Version string
- source: VARCHAR - Source identifier (github, local)
- origin: VARCHAR - Origin type (claude-artifact, github, local)
- origin_source: VARCHAR - Full origin path (owner/repo/path)
- resolved_sha: VARCHAR(64) - Git commit SHA
- resolved_version: VARCHAR - Resolved version tag
- synced_at: DATETIME - Last sync timestamp for staleness checks

An index is added on synced_at to support efficient staleness queries.

Phase 1 of artifact-metadata-cache implementation.

Reference:
- PRD: docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md
- TASK-1.2: Create Alembic migration for CollectionArtifact cache fields
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260201_1000_add_collection_artifact_metadata_cache_fields"
down_revision: Union[str, None] = "20260124_1400_update_fts5_with_deep_search"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add metadata cache fields to collection_artifacts table.

    Adds 11 columns for caching artifact metadata:
    - description, author, license, tags_json: Core metadata
    - version, source, origin, origin_source: Source tracking
    - resolved_sha, resolved_version: Version resolution
    - synced_at: Staleness tracking with index

    All columns are nullable for backward compatibility with existing entries.
    Existing entries will have NULL values until refreshed by sync operations.
    """
    # Add description column (from artifact manifest)
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Artifact description from manifest",
        ),
    )

    # Add author column
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "author",
            sa.String(),
            nullable=True,
            comment="Artifact author",
        ),
    )

    # Add license column
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "license",
            sa.String(),
            nullable=True,
            comment="License identifier (MIT, Apache-2.0, etc.)",
        ),
    )

    # Add tags_json column (JSON array string)
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "tags_json",
            sa.Text(),
            nullable=True,
            comment="JSON array string of artifact tags",
        ),
    )

    # Add version column
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "version",
            sa.String(),
            nullable=True,
            comment="Artifact version string",
        ),
    )

    # Add source column
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "source",
            sa.String(),
            nullable=True,
            comment="Source identifier (github, local)",
        ),
    )

    # Add origin column
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "origin",
            sa.String(),
            nullable=True,
            comment="Origin type (claude-artifact, github, local)",
        ),
    )

    # Add origin_source column
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "origin_source",
            sa.String(),
            nullable=True,
            comment="Full origin path (owner/repo/path)",
        ),
    )

    # Add resolved_sha column (64-char SHA)
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "resolved_sha",
            sa.String(64),
            nullable=True,
            comment="Git commit SHA for version tracking",
        ),
    )

    # Add resolved_version column
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "resolved_version",
            sa.String(),
            nullable=True,
            comment="Resolved version tag",
        ),
    )

    # Add synced_at column for staleness tracking
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "synced_at",
            sa.DateTime(),
            nullable=True,
            comment="Last sync timestamp for staleness checks",
        ),
    )

    # Add index on synced_at for efficient staleness queries
    op.create_index(
        "idx_collection_artifacts_synced_at",
        "collection_artifacts",
        ["synced_at"],
    )


def downgrade() -> None:
    """Remove metadata cache fields from collection_artifacts table.

    This reverts the migration by dropping the synced_at index and all 11
    metadata columns. Any cached metadata will be permanently lost.

    WARNING: This is a destructive operation. Cached metadata must be
    re-synced after downgrading if the migration is later re-applied.
    """
    # Drop index first (before dropping the column it references)
    op.drop_index("idx_collection_artifacts_synced_at", "collection_artifacts")

    # Drop columns in reverse order of addition
    op.drop_column("collection_artifacts", "synced_at")
    op.drop_column("collection_artifacts", "resolved_version")
    op.drop_column("collection_artifacts", "resolved_sha")
    op.drop_column("collection_artifacts", "origin_source")
    op.drop_column("collection_artifacts", "origin")
    op.drop_column("collection_artifacts", "source")
    op.drop_column("collection_artifacts", "version")
    op.drop_column("collection_artifacts", "tags_json")
    op.drop_column("collection_artifacts", "license")
    op.drop_column("collection_artifacts", "author")
    op.drop_column("collection_artifacts", "description")
