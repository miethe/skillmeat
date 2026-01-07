"""Populate raw_score for existing catalog entries

Revision ID: 20251227_1100_populate_raw_score_for_existing_entries
Revises: 20251227_1000_add_raw_score_and_breakdown_to_catalog
Create Date: 2025-12-27 11:00:00.000000

This data migration populates the raw_score column for all existing
marketplace_catalog_entries that were created before the Confidence Score
Enhancements feature was implemented.

Migration Strategy:
- Sets raw_score = LEAST(65, confidence_score) for existing entries
- The cap of 65 matches MAX_RAW_SCORE (before normalization)
- Only updates rows where raw_score IS NULL (safe for re-runs)
- Preserves existing confidence_score values unchanged

Background:
In the new scoring system, raw scores are capped at 65 and then normalized
to 0-100 scale. For backward compatibility, we cap existing confidence_score
values at 65 to match the new system's behavior.

Example: confidence_score=85 -> raw_score=65 (capped)
         confidence_score=45 -> raw_score=45 (unchanged)
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251227_1100_populate_raw_score_for_existing_entries"
down_revision: Union[str, None] = "20251227_1000_add_raw_score_and_breakdown_to_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Populate raw_score column for existing catalog entries.

    Sets raw_score to the minimum of 65 (MAX_RAW_SCORE) and the existing
    confidence_score value. This ensures consistency with the new scoring
    system which caps raw scores at 65 before normalization.

    The migration uses a CASE expression for SQL compatibility across
    different database engines (SQLite, PostgreSQL, etc.).

    Only updates rows where raw_score IS NULL to:
    1. Avoid overwriting manually set values
    2. Make migration safe to re-run
    3. Support rollback/replay scenarios
    """
    op.execute(
        """
        UPDATE marketplace_catalog_entries
        SET raw_score = CASE
            WHEN confidence_score > 65 THEN 65
            ELSE confidence_score
        END
        WHERE raw_score IS NULL
    """
    )


def downgrade() -> None:
    """Revert raw_score population by setting values back to NULL.

    This downgrade preserves the ability to cleanly rollback the migration.
    After downgrade, entries will have NULL raw_score values, matching the
    state immediately after the schema migration but before this data migration.

    Note: This does NOT restore the original NULL state before the schema
    migration was applied. To fully revert both migrations, you must downgrade
    both this data migration AND the schema migration.
    """
    op.execute(
        """
        UPDATE marketplace_catalog_entries
        SET raw_score = NULL
    """
    )
