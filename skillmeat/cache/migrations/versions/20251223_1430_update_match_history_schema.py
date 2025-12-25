"""Update match_history schema to use outcome enum

Revision ID: 20251223_1430_update_match_history_schema
Revises: 20251222_152125_add_rating_tables
Create Date: 2025-12-23 14:30:00.000000

This migration updates the match_history table schema to support richer
outcome tracking for match success metrics.

Changes:
- Replace user_confirmed BOOLEAN with outcome TEXT enum
- Add confirmed_at TIMESTAMP for tracking when confirmation occurred
- Migrate existing data (user_confirmed=1 → outcome='confirmed')
- Add check constraint for valid outcome values

Schema Version: 1.6.0
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251223_1430_update_match_history_schema"
down_revision: Union[str, None] = "20251222_152125_add_rating_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update match_history table with outcome enum and confirmed_at timestamp.

    This migration:
    1. Adds new outcome TEXT column with check constraint
    2. Adds confirmed_at TIMESTAMP column
    3. Migrates existing user_confirmed data to outcome
    4. Drops old user_confirmed column

    Data Migration:
    - user_confirmed=1 → outcome='confirmed'
    - user_confirmed=0 → outcome='rejected'
    - user_confirmed=NULL → outcome=NULL (will be set to 'ignored' if needed)
    """
    # Add new columns
    op.add_column(
        "match_history",
        sa.Column("outcome", sa.Text(), nullable=True),
    )
    op.add_column(
        "match_history",
        sa.Column(
            "confirmed_at",
            sa.TIMESTAMP(),
            nullable=True,
        ),
    )

    # Migrate existing data
    # user_confirmed=1 → outcome='confirmed', user_confirmed=0 → outcome='rejected'
    op.execute(
        """
        UPDATE match_history
        SET outcome = CASE
            WHEN user_confirmed = 1 THEN 'confirmed'
            WHEN user_confirmed = 0 THEN 'rejected'
            ELSE NULL
        END
        """
    )

    # Drop old column (SQLite doesn't support DROP COLUMN directly in all versions,
    # but Alembic handles this with a table recreation strategy)
    with op.batch_alter_table("match_history") as batch_op:
        batch_op.drop_column("user_confirmed")

    # Add check constraint for valid outcome values
    op.create_check_constraint(
        "check_valid_outcome",
        "match_history",
        "outcome IS NULL OR outcome IN ('confirmed', 'rejected', 'ignored')",
    )

    # Update schema version
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.6.0'
        WHERE key = 'schema_version'
        """
    )


def downgrade() -> None:
    """Revert match_history table to use user_confirmed boolean.

    This migration:
    1. Adds back user_confirmed BOOLEAN column
    2. Migrates outcome data back to user_confirmed
    3. Drops outcome and confirmed_at columns

    Data Migration (lossy):
    - outcome='confirmed' → user_confirmed=1
    - outcome='rejected' → user_confirmed=0
    - outcome='ignored' → user_confirmed=NULL
    - outcome=NULL → user_confirmed=NULL

    WARNING: This is a lossy migration. The confirmed_at timestamps will be lost.
    """
    # Add back user_confirmed column
    op.add_column(
        "match_history",
        sa.Column("user_confirmed", sa.Boolean(), nullable=True),
    )

    # Migrate data back
    op.execute(
        """
        UPDATE match_history
        SET user_confirmed = CASE
            WHEN outcome = 'confirmed' THEN 1
            WHEN outcome = 'rejected' THEN 0
            ELSE NULL
        END
        """
    )

    # Drop check constraint
    op.drop_constraint("check_valid_outcome", "match_history", type_="check")

    # Drop new columns
    with op.batch_alter_table("match_history") as batch_op:
        batch_op.drop_column("outcome")
        batch_op.drop_column("confirmed_at")

    # Revert schema version
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.5.0'
        WHERE key = 'schema_version'
        """
    )
