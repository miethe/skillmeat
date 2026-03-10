"""Add exclusion columns to marketplace_catalog_entries

Revision ID: 20251231_2103_add_exclusion_to_catalog
Revises: 20251227_1100_populate_raw_score_for_existing_entries
Create Date: 2025-12-31 21:03:25.699331+00:00

This migration adds columns to support marking catalog entries as
"not an artifact" (excluded). This allows users to indicate that
a detected entry was a false positive and should not appear in
artifact listings or be considered for import.

Columns added:
- excluded_at: Timestamp when entry was marked as excluded (NULL if not excluded)
- excluded_reason: User-provided reason for exclusion (optional, max 500 chars)

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251231_2103_add_exclusion_to_catalog"
down_revision: Union[str, None] = (
    "20251227_1100_populate_raw_score_for_existing_entries"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add excluded_at and excluded_reason columns to marketplace_catalog_entries.

    These columns enable the "mark as not an artifact" feature, allowing users
    to flag false positives from the artifact detection system. Entries with
    a non-NULL excluded_at timestamp are considered excluded and will be
    filtered out of normal artifact listings.
    """
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column("excluded_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column("excluded_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove excluded_at and excluded_reason columns from marketplace_catalog_entries.

    This reverts the exclusion feature. Any exclusion data will be lost.
    """
    op.drop_column("marketplace_catalog_entries", "excluded_reason")
    op.drop_column("marketplace_catalog_entries", "excluded_at")
