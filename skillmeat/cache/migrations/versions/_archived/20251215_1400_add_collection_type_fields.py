"""Add collection_type and context_category to collections

Revision ID: 20251215_1400_add_collection_type_fields
Revises: 20251215_1200_add_project_templates
Create Date: 2025-12-15 14:00:00.000000

This migration adds type and category fields to the collections table
to support filtering and categorization of collections.

Changes:
- Add collection_type column to collections (nullable string)
- Add context_category column to collections (nullable string)
- Add idx_collections_type index for filtering by type

Use Cases:
- Filter context collections (collection_type='context')
- Categorize context files (context_category='rules', 'specs', 'context')
- Support different collection types (artifacts, context, etc.)

Schema Version: 1.2.1
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251215_1400_add_collection_type_fields"
down_revision: Union[str, None] = "20251215_1200_add_project_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add collection_type and context_category columns to collections table.

    Adds two new nullable string columns to support collection filtering
    and categorization:

    1. collection_type - General collection type (e.g., 'context', 'artifacts')
    2. context_category - Category for context collections (e.g., 'rules', 'specs')

    Also creates an index on collection_type for efficient filtering.
    """
    # Add collection_type column
    op.add_column(
        "collections",
        sa.Column("collection_type", sa.String(), nullable=True),
    )

    # Add context_category column
    op.add_column(
        "collections",
        sa.Column("context_category", sa.String(), nullable=True),
    )

    # Add index on collection_type for filtering
    op.create_index(
        "idx_collections_type",
        "collections",
        ["collection_type"],
    )


def downgrade() -> None:
    """Remove collection_type and context_category columns.

    Drops the columns and index added in the upgrade step.
    """
    # Drop index
    op.drop_index("idx_collections_type", table_name="collections")

    # Drop columns
    op.drop_column("collections", "context_category")
    op.drop_column("collections", "collection_type")
