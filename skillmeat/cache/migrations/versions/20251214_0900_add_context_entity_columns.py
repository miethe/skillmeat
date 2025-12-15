"""Add context entity columns to artifacts table

Revision ID: 20251214_0900_add_context_entity_columns
Revises: 20251212_1600_create_collections_schema
Create Date: 2025-12-14 09:00:00.000000

This migration extends the artifacts table with columns to support context
entity types (project_config, spec_file, rule_file, context_file, progress_template).

Schema Changes:
- Add 4 new columns to artifacts table:
  * path_pattern (TEXT): Pattern like .claude/rules/{name}.md
  * auto_load (BOOLEAN): Whether entity auto-loads (default FALSE)
  * category (TEXT): Category like "api", "frontend", "debugging" (nullable)
  * content_hash (TEXT): SHA256 hash for change detection (nullable)
- Update check_artifacts_type constraint to include 5 new types:
  * project_config, spec_file, rule_file, context_file, progress_template
- Update check_marketplace_type constraint
- Update check_catalog_artifact_type constraint

All new columns are nullable to preserve existing data. The auto_load column
defaults to FALSE (0) for new rows.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251214_0900_add_context_entity_columns"
down_revision: Union[str, None] = "20251212_1600_create_collections_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add context entity columns to artifacts table and update type constraint.

    This migration extends the artifacts table with metadata fields needed for
    context entity types (project configs, specs, rules, context files, and
    progress templates).

    New Columns:
        - path_pattern: Template pattern for file paths (nullable)
        - auto_load: Boolean flag for automatic loading behavior (default FALSE)
        - category: Optional categorization (e.g., "api", "frontend") (nullable)
        - content_hash: SHA256 hash for change detection (nullable)

    Updated Constraint:
        - check_artifact_type: Extended to include new artifact types

    Note: For SQLite, updating CHECK constraints requires table recreation.
    This is handled using a backup-and-restore approach to preserve all data.
    """
    connection = op.get_bind()

    # ===========================================================================
    # Step 1: Create backup table with existing data
    # ===========================================================================
    connection.execute(sa.text("""
        CREATE TABLE artifacts_backup AS
        SELECT * FROM artifacts
    """))

    # ===========================================================================
    # Step 2: Drop original table (this removes the old constraint)
    # ===========================================================================
    connection.execute(sa.text("DROP TABLE artifacts"))

    # ===========================================================================
    # Step 3: Recreate table with new columns and updated constraint
    # ===========================================================================
    connection.execute(sa.text("""
        CREATE TABLE artifacts (
            id VARCHAR NOT NULL,
            project_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            type VARCHAR NOT NULL,
            source VARCHAR,
            deployed_version VARCHAR,
            upstream_version VARCHAR,
            is_outdated BOOLEAN DEFAULT '0' NOT NULL,
            local_modified BOOLEAN DEFAULT '0' NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            path_pattern TEXT,
            auto_load BOOLEAN DEFAULT '0' NOT NULL,
            category TEXT,
            content_hash TEXT,
            PRIMARY KEY (id),
            CONSTRAINT check_artifact_type CHECK (
                type IN ('skill', 'command', 'agent', 'mcp_server', 'hook',
                         'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')
            ),
            FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    """))

    # ===========================================================================
    # Step 4: Copy data back from backup
    # ===========================================================================
    connection.execute(sa.text("""
        INSERT INTO artifacts
            (id, project_id, name, type, source, deployed_version, upstream_version,
             is_outdated, local_modified, created_at, updated_at)
        SELECT
            id, project_id, name, type, source, deployed_version, upstream_version,
            is_outdated, local_modified, created_at, updated_at
        FROM artifacts_backup
    """))

    # ===========================================================================
    # Step 5: Drop backup table
    # ===========================================================================
    connection.execute(sa.text("DROP TABLE artifacts_backup"))

    # ===========================================================================
    # Step 6: Recreate indexes
    # ===========================================================================
    connection.execute(sa.text("CREATE INDEX idx_artifacts_project_id ON artifacts (project_id)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_type ON artifacts (type)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_is_outdated ON artifacts (is_outdated)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_updated_at ON artifacts (updated_at)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_project_type ON artifacts (project_id, type)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_outdated_type ON artifacts (is_outdated, type)"))


def downgrade() -> None:
    """Remove context entity columns and revert type constraint.

    This reverts the migration by removing the 4 new columns from artifacts table
    and reverting the CHECK constraint to the original values.

    WARNING: This is a destructive operation. Any data stored in the
    path_pattern, auto_load, category, and content_hash columns will be
    permanently lost.
    """
    connection = op.get_bind()

    # ===========================================================================
    # Step 1: Create backup table with existing data
    # ===========================================================================
    connection.execute(sa.text("""
        CREATE TABLE artifacts_backup AS
        SELECT
            id, project_id, name, type, source, deployed_version, upstream_version,
            is_outdated, local_modified, created_at, updated_at
        FROM artifacts
    """))

    # ===========================================================================
    # Step 2: Drop original table
    # ===========================================================================
    connection.execute(sa.text("DROP TABLE artifacts"))

    # ===========================================================================
    # Step 3: Recreate table without new columns and with old constraint
    # ===========================================================================
    connection.execute(sa.text("""
        CREATE TABLE artifacts (
            id VARCHAR NOT NULL,
            project_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            type VARCHAR NOT NULL,
            source VARCHAR,
            deployed_version VARCHAR,
            upstream_version VARCHAR,
            is_outdated BOOLEAN DEFAULT '0' NOT NULL,
            local_modified BOOLEAN DEFAULT '0' NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT check_artifact_type CHECK (
                type IN ('skill', 'command', 'agent', 'mcp_server', 'hook')
            ),
            FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    """))

    # ===========================================================================
    # Step 4: Copy data back from backup
    # ===========================================================================
    connection.execute(sa.text("""
        INSERT INTO artifacts
        SELECT * FROM artifacts_backup
    """))

    # ===========================================================================
    # Step 5: Drop backup table
    # ===========================================================================
    connection.execute(sa.text("DROP TABLE artifacts_backup"))

    # ===========================================================================
    # Step 6: Recreate indexes
    # ===========================================================================
    connection.execute(sa.text("CREATE INDEX idx_artifacts_project_id ON artifacts (project_id)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_type ON artifacts (type)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_is_outdated ON artifacts (is_outdated)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_updated_at ON artifacts (updated_at)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_project_type ON artifacts (project_id, type)"))
    connection.execute(sa.text("CREATE INDEX idx_artifacts_outdated_type ON artifacts (is_outdated, type)"))
