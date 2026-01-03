"""Add raw_score and score_breakdown to marketplace_catalog_entries

Revision ID: 20251227_1000_add_raw_score_and_breakdown_to_catalog
Revises: 20251226_1500_add_frontmatter_detection
Create Date: 2025-12-27 10:00:00.000000

This migration adds confidence scoring enhancement columns to the
marketplace_catalog_entries table:
- raw_score: The unscaled raw confidence score (0-100 range)
- score_breakdown: JSON object containing detailed scoring components

These columns support the Confidence Score Enhancements feature (PRD: confidence-score-enhancements)
which provides detailed scoring breakdowns for artifact detection quality.

Schema Changes:
- Add raw_score column: INTEGER, NULLABLE (for backward compatibility)
- Add score_breakdown column: JSON, NULLABLE (for backward compatibility)

The existing confidence_score column remains unchanged as the primary normalized score.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251227_1000_add_raw_score_and_breakdown_to_catalog"
down_revision: Union[str, None] = "20251226_1500_add_frontmatter_detection"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add raw_score and score_breakdown columns to marketplace_catalog_entries table.

    This migration adds two new columns to support enhanced confidence scoring:
    1. raw_score: Integer column for unscaled raw confidence (0-100)
    2. score_breakdown: JSON column for detailed scoring component breakdown

    Both columns are nullable for backward compatibility with existing catalog entries.
    Existing entries will have NULL values until they are rescanned with the new
    scoring system.

    The score_breakdown JSON structure contains:
    {
        "component_scores": {
            "structure": 25,
            "metadata": 20,
            "content": 15,
            ...
        },
        "total_raw": 60,
        "total_scaled": 75,
        "version": "1.0"
    }
    """
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column("raw_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "marketplace_catalog_entries",
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove raw_score and score_breakdown columns from marketplace_catalog_entries.

    This reverts the migration by dropping both enhancement columns.

    WARNING: This will permanently delete all raw score and breakdown data.
    The normalized confidence_score column will remain unchanged, but detailed
    scoring information will be lost.
    """
    op.drop_column("marketplace_catalog_entries", "score_breakdown")
    op.drop_column("marketplace_catalog_entries", "raw_score")
