"""Add description and notes to marketplace_sources

Revision ID: 20251212_1537_add_description_notes
Revises: 001_initial_schema
Create Date: 2025-12-12 15:37:00.000000

This migration adds two new columns to the marketplace_sources table:
- description: Optional user-provided description (max 500 chars)
- notes: Optional internal notes/documentation (max 2000 chars)

These fields enable users to annotate and document their marketplace sources
for better organization and maintenance.

Schema Change:
- Add description column: VARCHAR(500), nullable
- Add notes column: VARCHAR(2000), nullable
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251212_1537_add_description_notes"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add description and notes columns to marketplace_sources table.

    This migration adds two new nullable text columns to support user-provided
    metadata and documentation for marketplace sources:

    - description: Short user-friendly description (500 char limit)
    - notes: Longer internal notes/documentation (2000 char limit)

    Both columns are nullable to maintain compatibility with existing data.
    No data migration is required as these are new optional fields.
    """
    # Add description column
    op.add_column(
        "marketplace_sources",
        sa.Column("description", sa.String(500), nullable=True)
    )

    # Add notes column
    op.add_column(
        "marketplace_sources",
        sa.Column("notes", sa.String(2000), nullable=True)
    )


def downgrade() -> None:
    """Remove description and notes columns from marketplace_sources table.

    This reverts the migration by dropping both columns. Any data stored in
    these columns will be permanently lost.

    WARNING: This is a destructive operation and should only be used if
    rolling back to a version that does not support these fields.
    """
    # Drop columns in reverse order for clarity
    op.drop_column("marketplace_sources", "notes")
    op.drop_column("marketplace_sources", "description")
