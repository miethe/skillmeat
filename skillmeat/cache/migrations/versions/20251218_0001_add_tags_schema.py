"""Add tags and artifact_tags tables for artifact categorization

Revision ID: 20251218_0001_add_tags_schema
Revises: 20251217_1500_add_artifact_versions
Create Date: 2025-12-18 00:01:00.000000

This migration creates the database schema for tag-based artifact categorization,
enabling flexible organization and filtering of artifacts.

Tables Created:
- tags: Tag definitions with name, slug, and optional color
- artifact_tags: Many-to-many junction table between artifacts and tags

Key Features:
- Tag management: Unique tags with URL-friendly slugs
- Visual distinction: Optional hex color codes for UI display
- Many-to-many relationship: Artifacts can have multiple tags
- Cascade delete: Deleting a tag removes all artifact associations
- Fast lookups: Indexes on both artifact_id and tag_id
- Timestamp tracking: Track when tags are added to artifacts

Schema Version: 1.4.0
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251218_0001_add_tags_schema"
down_revision: Union[str, None] = "20251217_1500_add_artifact_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tags and artifact_tags tables for artifact categorization.

    Creates the schema for tag-based artifact organization:

    1. tags - Tag definitions with name, slug, color, and timestamps
    2. artifact_tags - Junction table linking artifacts to tags

    The tables use TEXT for all string columns (SQLite compatible) and include
    proper foreign key constraints with CASCADE delete for data integrity.
    """
    # ==========================================================================
    # Tags Table
    # ==========================================================================
    # Tag definitions for categorizing artifacts
    op.create_table(
        "tags",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(length=100), nullable=False),
        sa.Column("slug", sa.Text(length=100), nullable=False),
        sa.Column("color", sa.Text(length=7), nullable=True),
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
            "length(name) > 0 AND length(name) <= 100",
            name="check_tag_name_length",
        ),
        sa.CheckConstraint(
            "length(slug) > 0 AND length(slug) <= 100",
            name="check_tag_slug_length",
        ),
        sa.CheckConstraint(
            "color IS NULL OR (length(color) = 7 AND color LIKE '#%')",
            name="check_tag_color_format",
        ),
    )

    # Tags indexes
    op.create_index(
        "idx_tags_name",
        "tags",
        ["name"],
        unique=True,
    )
    op.create_index(
        "idx_tags_slug",
        "tags",
        ["slug"],
        unique=True,
    )

    # ==========================================================================
    # Artifact Tags Junction Table
    # ==========================================================================
    # Many-to-many relationship between artifacts and tags
    op.create_table(
        "artifact_tags",
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column("tag_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("artifact_id", "tag_id"),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            name="fk_artifact_tags_artifact_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name="fk_artifact_tags_tag_id",
            ondelete="CASCADE",
        ),
    )

    # Artifact tags indexes
    op.create_index(
        "idx_artifact_tags_artifact_id",
        "artifact_tags",
        ["artifact_id"],
    )
    op.create_index(
        "idx_artifact_tags_tag_id",
        "artifact_tags",
        ["tag_id"],
    )
    op.create_index(
        "idx_artifact_tags_created_at",
        "artifact_tags",
        ["created_at"],
    )

    # ==========================================================================
    # Update schema version
    # ==========================================================================
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.4.0'
        WHERE key = 'schema_version'
        """
    )


def downgrade() -> None:
    """Remove tags and artifact_tags tables.

    This reverts the migration by dropping the artifact_tags and tags tables
    and their indexes.

    WARNING: This is a destructive operation. All tag definitions and
    artifact-tag associations will be permanently lost.
    """
    # Drop junction table first (has FKs to tags table)
    op.drop_table("artifact_tags")

    # Drop tags table (indexes are automatically dropped)
    op.drop_table("tags")

    # Revert schema version
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.3.0'
        WHERE key = 'schema_version'
        """
    )
