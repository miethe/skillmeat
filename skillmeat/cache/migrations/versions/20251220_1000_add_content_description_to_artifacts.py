"""Add content and description columns to artifacts table

Revision ID: 20251220_1000_add_content_description_to_artifacts
Revises: 20251218_0001_add_tags_schema
Create Date: 2025-12-20 10:00:00.000000

This migration adds two new columns to the artifacts table to support
rich content and description metadata for context entities:

Schema Changes:
- Add content (TEXT): Full markdown content for the artifact
- Add description (TEXT): Short description/summary of the artifact

Both columns are nullable to preserve existing data. These fields enable
storing complete artifact content and metadata for context entities like
rules, specs, and progress templates.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251220_1000_add_content_description_to_artifacts"
down_revision: Union[str, None] = "20251218_0001_add_tags_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add content and description columns to artifacts table.

    This migration extends the artifacts table with two new text columns:
    - content: Stores full markdown content for context entities
    - description: Stores a short description/summary

    Both columns are nullable to preserve existing data. SQLite supports
    adding nullable columns without requiring table recreation.
    """
    # Add content column for storing markdown content
    op.add_column("artifacts", sa.Column("content", sa.TEXT(), nullable=True))

    # Add description column for entity descriptions
    op.add_column("artifacts", sa.Column("description", sa.TEXT(), nullable=True))


def downgrade() -> None:
    """Remove content and description columns from artifacts table.

    WARNING: This is a destructive operation. Any data stored in the
    content and description columns will be permanently lost.
    """
    # Note: SQLite requires special handling for dropping columns
    # Using batch operations for SQLite compatibility
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_column("description")
        batch_op.drop_column("content")
