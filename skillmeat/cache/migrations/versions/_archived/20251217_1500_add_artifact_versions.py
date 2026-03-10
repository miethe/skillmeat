"""Add artifact_versions table for change origin tracking

Revision ID: 20251217_1500_add_artifact_versions
Revises: 20251215_1400_add_collection_type_fields
Create Date: 2025-12-17 15:00:00.000000

This migration creates the database schema for Artifact Version History,
enabling three-way merge operations with change origin attribution.

Tables Created:
- artifact_versions: Version history with change origin tracking

Key Features:
- Change origin attribution: Track whether changes came from deployment, sync, or local modification
- Parent hash tracking: Build version lineage through parent_hash references
- Version lineage: JSON array of ancestor hashes for fast ancestry queries
- Content-based deduplication: UNIQUE index on content_hash prevents duplicates
- Cascade delete: Deleting an artifact removes its version history
- Self-referential FK: parent_hash references content_hash (enforced at application level for SQLite)

Schema Version: 1.3.0
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251217_1500_add_artifact_versions"
down_revision: Union[str, None] = "20251215_1400_add_collection_type_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create artifact_versions table for version history tracking.

    Creates the schema for artifact version history with change origin attribution:

    1. artifact_versions - Version history with parent tracking and origin attribution

    The table uses TEXT for all string columns (SQLite compatible) and includes
    proper foreign key constraints with CASCADE delete for data integrity.

    Note: Self-referential foreign key (parent_hash -> content_hash) must be
    enforced at application level since SQLite doesn't support foreign keys
    to non-primary key columns.
    """
    # ==========================================================================
    # Artifact Versions Table
    # ==========================================================================
    # Version history with change origin attribution for three-way merge
    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("parent_hash", sa.Text(), nullable=True),  # NULL for root versions
        sa.Column(
            "change_origin",
            sa.Text(),
            nullable=False,
        ),
        sa.Column("version_lineage", sa.Text(), nullable=True),  # JSON array
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("metadata", sa.Text(), nullable=True),  # Additional JSON metadata
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            name="fk_artifact_versions_artifact_id",
            ondelete="CASCADE",
        ),
        # Note: Self-referential FK to parent_hash is enforced at application level
        # SQLite doesn't support foreign keys to non-primary key columns
        sa.CheckConstraint(
            "change_origin IN ('deployment', 'sync', 'local_modification')",
            name="check_artifact_versions_change_origin",
        ),
    )

    # Artifact versions indexes
    op.create_index(
        "idx_artifact_versions_artifact_id",
        "artifact_versions",
        ["artifact_id"],
    )
    op.create_index(
        "idx_artifact_versions_content_hash",
        "artifact_versions",
        ["content_hash"],
        unique=True,  # Content-based deduplication
    )
    op.create_index(
        "idx_artifact_versions_parent_hash",
        "artifact_versions",
        ["parent_hash"],
    )
    op.create_index(
        "idx_artifact_versions_artifact_created",
        "artifact_versions",
        ["artifact_id", "created_at"],
    )
    op.create_index(
        "idx_artifact_versions_change_origin",
        "artifact_versions",
        ["change_origin"],
    )

    # ==========================================================================
    # Update schema version
    # ==========================================================================
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.3.0'
        WHERE key = 'schema_version'
        """
    )


def downgrade() -> None:
    """Remove artifact_versions table.

    This reverts the migration by dropping the artifact_versions table
    and its indexes.

    WARNING: This is a destructive operation. All artifact version
    history data will be permanently lost.
    """
    # Drop table (indexes are automatically dropped)
    op.drop_table("artifact_versions")

    # Revert schema version
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.2.1'
        WHERE key = 'schema_version'
        """
    )
