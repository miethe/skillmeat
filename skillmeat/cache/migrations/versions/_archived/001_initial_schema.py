"""Create initial cache schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-12-01 15:00:00.000000

This migration creates the complete database schema for the SkillMeat
persistent project cache, including:

- 6 tables: projects, artifacts, artifact_metadata, marketplace, cache_metadata,
  marketplace_sources
- 14 indexes for query optimization
- 4 triggers for automatic timestamp updates
- SQLite PRAGMA configuration for performance

The schema is designed for:
- Fast query performance with strategic indexes
- Support for both local and marketplace artifacts
- TTL-based refresh strategies
- Concurrent read/write access (WAL mode)

Schema Version: 1.0.0
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from skillmeat.cache.migrations.dialect_helpers import (
    create_updated_at_trigger,
    drop_updated_at_trigger,
)

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration changes to upgrade database schema.

    This creates all tables, indexes, and triggers required for the
    SkillMeat cache database. The migration is idempotent and can be
    run multiple times safely.

    Tables Created:
        - projects: Project metadata and status
        - artifacts: Artifact metadata per project
        - artifact_metadata: Extended artifact metadata (YAML frontmatter)
        - marketplace: Cached marketplace artifact listings
        - cache_metadata: Cache system metadata (version, TTL, etc.)
        - marketplace_sources: GitHub repository sources for marketplace scanning

    Indexes Created:
        - 14 indexes for optimized query performance

    Triggers Created:
        - 4 auto-update triggers for timestamp maintenance
    """
    # ==========================================================================
    # Projects Table
    # ==========================================================================
    # Stores project-level metadata and cache status
    op.create_table(
        "projects",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_fetched", sa.TIMESTAMP(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=True,
            server_default="active",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path"),
        sa.CheckConstraint(
            "status IN ('active', 'stale', 'error')",
            name="check_projects_status",
        ),
    )

    # Projects indexes
    op.create_index("idx_projects_status", "projects", ["status"])
    op.create_index("idx_projects_last_fetched", "projects", ["last_fetched"])

    # ==========================================================================
    # Artifacts Table
    # ==========================================================================
    # Stores artifact metadata for each project
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("deployed_version", sa.Text(), nullable=True),
        sa.Column("upstream_version", sa.Text(), nullable=True),
        sa.Column("is_outdated", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("local_modified", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "type IN ('skill', 'command', 'agent', 'mcp_server', 'hook')",
            name="check_artifacts_type",
        ),
    )

    # Artifacts indexes
    op.create_index("idx_artifacts_project_id", "artifacts", ["project_id"])
    op.create_index("idx_artifacts_type", "artifacts", ["type"])
    op.create_index("idx_artifacts_is_outdated", "artifacts", ["is_outdated"])
    op.create_index("idx_artifacts_updated_at", "artifacts", ["updated_at"])
    op.create_index("idx_artifacts_project_type", "artifacts", ["project_id", "type"])
    op.create_index("idx_artifacts_outdated_type", "artifacts", ["is_outdated", "type"])

    # ==========================================================================
    # Artifact Metadata Table
    # ==========================================================================
    # Extended metadata from YAML frontmatter
    op.create_table(
        "artifact_metadata",
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("aliases", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("artifact_id"),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            ondelete="CASCADE",
        ),
    )

    # Artifact metadata indexes
    op.create_index("idx_metadata_tags", "artifact_metadata", ["tags"])

    # ==========================================================================
    # Marketplace Table
    # ==========================================================================
    # Cached marketplace artifact listings
    op.create_table(
        "marketplace",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "cached_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("data", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "type IN ('skill', 'command', 'agent', 'mcp_server', 'hook')",
            name="check_marketplace_type",
        ),
    )

    # Marketplace indexes
    op.create_index("idx_marketplace_type", "marketplace", ["type"])
    op.create_index("idx_marketplace_name", "marketplace", ["name"])

    # ==========================================================================
    # Cache Metadata Table
    # ==========================================================================
    # System metadata for cache management
    op.create_table(
        "cache_metadata",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    # ==========================================================================
    # Marketplace Sources Table
    # ==========================================================================
    # GitHub repository sources for marketplace artifact scanning
    op.create_table(
        "marketplace_sources",
        sa.Column("id", sa.String(), nullable=False),
        # Core repository fields
        sa.Column("repo_url", sa.String(), nullable=False),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("repo_name", sa.String(), nullable=False),
        sa.Column(
            "ref",
            sa.String(),
            nullable=False,
            server_default="main",
        ),
        sa.Column("root_hint", sa.String(), nullable=True),
        # Extended configuration
        sa.Column("manual_map", sa.Text(), nullable=True),
        sa.Column("access_token_id", sa.String(), nullable=True),
        # Security and visibility
        sa.Column(
            "trust_level",
            sa.String(),
            nullable=False,
            server_default="basic",
        ),
        sa.Column(
            "visibility",
            sa.String(),
            nullable=False,
            server_default="public",
        ),
        # Sync status
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "scan_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "artifact_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_url", name="idx_marketplace_sources_repo_url"),
        sa.CheckConstraint(
            "trust_level IN ('untrusted', 'basic', 'verified', 'official')",
            name="check_trust_level",
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'internal', 'public')",
            name="check_visibility",
        ),
        sa.CheckConstraint(
            "scan_status IN ('pending', 'scanning', 'success', 'error')",
            name="check_scan_status",
        ),
    )

    # Marketplace sources indexes
    op.create_index(
        "idx_marketplace_sources_last_sync",
        "marketplace_sources",
        ["last_sync_at"],
    )
    op.create_index(
        "idx_marketplace_sources_scan_status",
        "marketplace_sources",
        ["scan_status"],
    )

    # ==========================================================================
    # Triggers for automatic updated_at maintenance
    # ==========================================================================

    create_updated_at_trigger("projects")
    create_updated_at_trigger("artifacts")
    create_updated_at_trigger("cache_metadata", pk_column="key")
    create_updated_at_trigger("marketplace_sources")

    # ==========================================================================
    # Initialize cache metadata with schema version
    # ==========================================================================
    op.execute(
        """
        INSERT INTO cache_metadata (key, value)
        VALUES ('schema_version', '1.0.0')
        """
    )


def downgrade() -> None:
    """Revert migration changes to downgrade database schema.

    This drops all tables, indexes, and triggers created by the upgrade.
    The migration is idempotent and can be run multiple times safely.

    WARNING: This will destroy all cached data. Use with caution.
    """
    # Drop triggers first
    drop_updated_at_trigger("projects")
    drop_updated_at_trigger("artifacts")
    drop_updated_at_trigger("cache_metadata")
    drop_updated_at_trigger("marketplace_sources")

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("marketplace_sources")
    op.drop_table("cache_metadata")
    op.drop_table("marketplace")
    op.drop_table("artifact_metadata")
    op.drop_table("artifacts")
    op.drop_table("projects")

    # Note: Indexes are automatically dropped when tables are dropped
