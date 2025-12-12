"""Create collections schema for artifact organization

Revision ID: 20251212_1600_create_collections_schema
Revises: 20251212_1537_add_description_notes
Create Date: 2025-12-12 16:00:00.000000

This migration creates the database schema for Collections and Groups,
enabling users to organize artifacts into logical collections with
nested group organization.

Tables Created:
- collections: User-defined artifact collections
- groups: Custom groupings within collections
- collection_artifacts: M2M association Collection <-> Artifact
- group_artifacts: M2M association Group <-> Artifact (with ordering)

Key Features:
- Cascade delete: Deleting a collection removes its groups and associations
- Position ordering: Groups and artifacts within groups can be reordered
- Flexible artifact references: No FK on artifact_id to support external sources
- Timestamp tracking: added_at for membership auditing

Schema Version: 1.1.0
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251212_1600_create_collections_schema"
down_revision: Union[str, None] = "20251212_1537_add_description_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create collections, groups, and association tables.

    Creates the complete schema for artifact organization:

    1. collections - Top-level containers for organizing artifacts
    2. groups - Named subgroups within collections for categorization
    3. collection_artifacts - Links artifacts to collections
    4. group_artifacts - Links artifacts to groups with position ordering

    All tables use TEXT/VARCHAR for IDs (UUID hex format) and include
    proper foreign key constraints with CASCADE delete for data integrity.
    """
    # ==========================================================================
    # Collections Table
    # ==========================================================================
    # User-defined collections for organizing artifacts
    op.create_table(
        "collections",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="check_collection_name_length",
        ),
    )

    # Collections indexes
    op.create_index("idx_collections_name", "collections", ["name"])
    op.create_index("idx_collections_created_by", "collections", ["created_by"])
    op.create_index("idx_collections_created_at", "collections", ["created_at"])

    # ==========================================================================
    # Groups Table
    # ==========================================================================
    # Custom groupings within collections for artifact categorization
    op.create_table(
        "groups",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("collection_id", sa.Text(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
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
            ["collection_id"],
            ["collections.id"],
            name="fk_groups_collection_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "collection_id", "name",
            name="uq_group_collection_name",
        ),
        sa.CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="check_group_name_length",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="check_group_position",
        ),
    )

    # Groups indexes
    op.create_index("idx_groups_collection_id", "groups", ["collection_id"])
    op.create_index(
        "idx_groups_collection_position",
        "groups",
        ["collection_id", "position"],
    )

    # ==========================================================================
    # Collection Artifacts Association Table
    # ==========================================================================
    # Many-to-many: Collection <-> Artifact
    # Note: No FK on artifact_id - artifacts may be external (marketplace, etc.)
    op.create_table(
        "collection_artifacts",
        sa.Column("collection_id", sa.Text(), nullable=False),
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("collection_id", "artifact_id"),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            name="fk_collection_artifacts_collection_id",
            ondelete="CASCADE",
        ),
    )

    # Collection artifacts indexes
    op.create_index(
        "idx_collection_artifacts_collection_id",
        "collection_artifacts",
        ["collection_id"],
    )
    op.create_index(
        "idx_collection_artifacts_artifact_id",
        "collection_artifacts",
        ["artifact_id"],
    )
    op.create_index(
        "idx_collection_artifacts_added_at",
        "collection_artifacts",
        ["added_at"],
    )

    # ==========================================================================
    # Group Artifacts Association Table
    # ==========================================================================
    # Many-to-many: Group <-> Artifact with position ordering
    # Note: No FK on artifact_id - artifacts may be external
    op.create_table(
        "group_artifacts",
        sa.Column("group_id", sa.Text(), nullable=False),
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("group_id", "artifact_id"),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name="fk_group_artifacts_group_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="check_group_artifact_position",
        ),
    )

    # Group artifacts indexes
    op.create_index(
        "idx_group_artifacts_group_id",
        "group_artifacts",
        ["group_id"],
    )
    op.create_index(
        "idx_group_artifacts_artifact_id",
        "group_artifacts",
        ["artifact_id"],
    )
    op.create_index(
        "idx_group_artifacts_group_position",
        "group_artifacts",
        ["group_id", "position"],
    )
    op.create_index(
        "idx_group_artifacts_added_at",
        "group_artifacts",
        ["added_at"],
    )

    # ==========================================================================
    # Triggers for automatic updated_at maintenance
    # ==========================================================================

    # Collections updated_at trigger
    op.execute(
        """
        CREATE TRIGGER collections_updated_at
        AFTER UPDATE ON collections
        FOR EACH ROW
        BEGIN
            UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """
    )

    # Groups updated_at trigger
    op.execute(
        """
        CREATE TRIGGER groups_updated_at
        AFTER UPDATE ON groups
        FOR EACH ROW
        BEGIN
            UPDATE groups SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """
    )

    # ==========================================================================
    # Update schema version
    # ==========================================================================
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.1.0'
        WHERE key = 'schema_version'
        """
    )


def downgrade() -> None:
    """Remove collections, groups, and association tables.

    This reverts the migration by dropping all created triggers and tables.
    Tables are dropped in reverse dependency order:

    1. group_artifacts (depends on groups)
    2. collection_artifacts (depends on collections)
    3. groups (depends on collections)
    4. collections (no dependencies)

    WARNING: This is a destructive operation. All collection and group
    data will be permanently lost.
    """
    # Drop triggers first (SQLite requires explicit trigger drops)
    op.execute("DROP TRIGGER IF EXISTS collections_updated_at")
    op.execute("DROP TRIGGER IF EXISTS groups_updated_at")

    # Drop tables in reverse dependency order
    # Note: Indexes are automatically dropped when tables are dropped
    op.drop_table("group_artifacts")
    op.drop_table("collection_artifacts")
    op.drop_table("groups")
    op.drop_table("collections")

    # Revert schema version
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.0.0'
        WHERE key = 'schema_version'
        """
    )
