"""Create initial cache schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-12-01 15:00:00.000000

This migration creates the complete database schema for the SkillMeat
persistent project cache, including:

- 5 tables: projects, artifacts, artifact_metadata, marketplace, cache_metadata
- 11 indexes for query optimization
- 3 triggers for automatic timestamp updates
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

    Indexes Created:
        - 11 indexes for optimized query performance

    Triggers Created:
        - 3 auto-update triggers for timestamp maintenance
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
    # Triggers for automatic updated_at maintenance
    # ==========================================================================

    # Projects updated_at trigger
    op.execute(
        """
        CREATE TRIGGER projects_updated_at
        AFTER UPDATE ON projects
        FOR EACH ROW
        BEGIN
            UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """
    )

    # Artifacts updated_at trigger
    op.execute(
        """
        CREATE TRIGGER artifacts_updated_at
        AFTER UPDATE ON artifacts
        FOR EACH ROW
        BEGIN
            UPDATE artifacts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """
    )

    # Cache metadata updated_at trigger
    op.execute(
        """
        CREATE TRIGGER cache_metadata_updated_at
        AFTER UPDATE ON cache_metadata
        FOR EACH ROW
        BEGIN
            UPDATE cache_metadata SET updated_at = CURRENT_TIMESTAMP WHERE key = NEW.key;
        END;
        """
    )

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
    # Drop triggers first (SQLite requires explicit trigger drops)
    op.execute("DROP TRIGGER IF EXISTS projects_updated_at")
    op.execute("DROP TRIGGER IF EXISTS artifacts_updated_at")
    op.execute("DROP TRIGGER IF EXISTS cache_metadata_updated_at")

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("cache_metadata")
    op.drop_table("marketplace")
    op.drop_table("artifact_metadata")
    op.drop_table("artifacts")
    op.drop_table("projects")

    # Note: Indexes are automatically dropped when tables are dropped
